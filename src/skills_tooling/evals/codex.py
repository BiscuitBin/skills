"""The Codex adapter. See docs/reference/evals.md for the facts it relies on."""

import contextlib
import json
import os
import platform
import re
import shutil
import sys
from pathlib import Path
from typing import TYPE_CHECKING, Any, ClassVar

from skills_tooling.evals import workspace
from skills_tooling.evals.adapter import (
    Command,
    CredentialError,
    Homes,
    Location,
    RawRun,
    Trace,
)
from skills_tooling.evals.assertions import ASSIGNMENT, command_list, simple_commands

if TYPE_CHECKING:
    from collections.abc import Collection, Iterator, Mapping

    from skills_tooling.evals.adapter import TrialPaths

# The bundled skills the pinned CLI writes to $CODEX_HOME/skills/.system on
# startup. review-agent is written but not listed to the model. A new CLI
# version needs a new entry: run a trial and copy the directory names.
BUILTIN_SKILLS = {
    "0.163.0": frozenset(
        {"imagegen", "openai-docs", "review-agent", "skill-creator", "skill-installer"}
    ),
}
# Plugins are disabled, so none are allowed.
BUILTIN_PLUGINS: dict[str, frozenset[str]] = {"0.163.0": frozenset()}
SYSTEM_MARKER = ".codex-system-skills.marker"
# Each of these switches off something that would reach outside the trial.
CONFIG = (
    # A login shell runs the system profile, whose path_helper puts /usr/bin
    # ahead of the trial's python3 wrapper.
    "allow_login_shell=false",
    # AGENTS.md in the workspace and every directory above it. The global
    # $CODEX_HOME/AGENTS.md still loads, so the discovery report checks for it.
    "project_doc_max_bytes=0",
    "analytics.enabled=false",
)
# Plugins and apps add skills and tools, and Codex syncs the account's remote
# plugins into its home mid-run.
DISABLED = ("plugins", "remote_plugin", "apps")
# Writes are confined to the workspace and the trial's TMPDIR, where the
# python3 wrapper logs its calls.
SANDBOX = "workspace-write"
# Only Codex's own log-only telemetry events, which name the CLI version, the
# model and each explicitly invoked skill, and warnings and errors.
RUST_LOG = "warn,codex_otel.log_only=info"
# The binary codex.js would start, by platform and machine.
NATIVE = {
    ("darwin", "arm64"): ("codex-darwin-arm64", "aarch64-apple-darwin"),
    ("darwin", "x86_64"): ("codex-darwin-x64", "x86_64-apple-darwin"),
    ("linux", "x86_64"): ("codex-linux-x64", "x86_64-unknown-linux-musl"),
    ("linux", "aarch64"): ("codex-linux-arm64", "aarch64-unknown-linux-musl"),
}
STARTS = re.compile(r'event\.name="codex\.conversation_starts"')
INVOCATION = re.compile(r'event\.name="codex\.skill_invocation"')
SANDBOX_OUTCOME = re.compile(r'event\.name="codex\.sandbox_outcome"')
FIELD = re.compile(r'(?<![\w.])([\w.]+)=("(?:[^"\\]|\\.)*"|\S+)')
FAILED_LOAD = re.compile(r"(failed to load skill .*)$", re.IGNORECASE)
# A log record starts with a timestamp; lines without one continue the record above.
RECORD_START = re.compile(r"^\d{4}-\d\d-\d\dT\S+\s+(TRACE|DEBUG|INFO|WARN|ERROR)\s")
TELEMETRY = "codex_otel"
STARTS_FIELDS = ("app.version", "model")
INVOCATION_FIELDS = ("skill.name", "skill.scope", "skill.invocation_type")
SANDBOX_FIELDS = ("tool_name", "call_id", "outcome")
# Programs that print a file's contents. A command that only names the path,
# such as ls, test or echo, is not a read. awk is not one: whether it opens an
# operand depends on its program, so an awk read is left to Codex's own event.
READERS = {"cat", "head", "tail", "sed", "nl", "less", "more", "bat"}
# A redirection can make a reader write the path, or send its output elsewhere.
# Quoting is gone by the time the words are checked, so a quoted < or > counts too.
REDIRECTION = re.compile(r"[<>]")
# Flags that make a reader print help or its version instead of the file.
NO_READ_FLAGS = {"--help", "--version", "-h", "-V"}
# Codex wraps each command as `<shell> -c '<command>'`, or -lc for a login shell.
SHELLS = {"bash", "zsh", "sh"}
# Characters the shell expands, so the name in the text is not the directory read.
UNPLACEABLE = re.compile(r"[*?\[\]{}$~`]")
# The directory a skill directory sits in: .agents/skills, skills, dev-skills, .system.
SKILLS_DIR = re.compile(r"skills$|^\.system$")
# auth.json fields that are not secret. Short strings are not secret either:
# keys, tokens and account ids are long, and a short label such as a plan name
# would scrub every occurrence of a common word.
NOT_SECRET = {"auth_mode", "last_refresh"}
SECRET_MIN_LENGTH = 20
TRANSCRIPT = "transcript.jsonl"


def pinned_executable(root: Path) -> Path:
    """The native binary node_modules/.bin/codex starts, for this platform."""
    machine = platform.machine().lower()
    key = (sys.platform, "x86_64" if machine == "amd64" else machine)
    if key not in NATIVE:
        msg = f"no pinned Codex binary for {sys.platform} {machine}"
        raise FileNotFoundError(msg)
    package, triple = NATIVE[key]
    return root / "node_modules/@openai" / package / "vendor" / triple / "bin/codex"


class Codex:
    name: ClassVar[str] = "codex"
    default_model: ClassVar[str] = "gpt-5.6-terra"
    credential_env: ClassVar[tuple[str, ...]] = ("CODEX_HOME",)
    home_env: ClassVar[tuple[str, ...]] = ("CODEX_HOME",)
    skills_dir: ClassVar[str] = ".agents/skills"
    # Codex lists its skills only inside the model request, which a live run
    # cannot observe. The proof is the discovery report over every location.
    reports_skills: ClassVar[bool] = False
    builtin_skills: ClassVar[Mapping[str, frozenset[str]]] = BUILTIN_SKILLS
    builtin_plugins: ClassVar[Mapping[str, frozenset[str]]] = BUILTIN_PLUGINS

    def __init__(self, executable: Path, *, api_base_url: str | None = None) -> None:
        self.executable = executable.resolve()
        # Only tests set this, to point the CLI at a local fake API.
        self.api_base_url = api_base_url
        # Tests drop an entry to show what it suppresses.
        self.config: tuple[str, ...] = CONFIG

    def read_credentials(self, environ: Mapping[str, str]) -> Mapping[str, str]:
        """auth.json from the caller's CODEX_HOME, which the Justfile keeps in the project."""
        home = environ.get("CODEX_HOME", "")
        if not home:
            msg = "CODEX_HOME is not set. Run the eval through `just eval`."
            raise CredentialError(msg)
        source = Path(home) / "auth.json"
        try:
            text = source.read_text()
            json.loads(text)
        except (OSError, json.JSONDecodeError) as error:
            msg = (
                f"no readable Codex login at {source} ({type(error).__name__}). Log in once with "
                "`just run ./node_modules/.bin/codex login`. See docs/reference/evals.md."
            )
            raise CredentialError(msg) from error
        return {"auth.json": text}

    def secrets(self, credentials: Mapping[str, str]) -> list[str]:
        found: list[str] = []
        for text in credentials.values():
            found.append(text)
            with contextlib.suppress(json.JSONDecodeError):
                found += _secret_leaves(json.loads(text))
        return [value for value in found if value]

    def trial_secrets(self, trial: TrialPaths) -> list[str]:
        """The trial's auth.json as it is now: Codex rewrites it when it refreshes a login.

        There is none before `run` installs the login. After that, a missing,
        unreadable or partial file raises, because a refreshed token in it
        would escape the scrub and the sweep.
        """
        auth = trial.home / ".codex/auth.json"
        if not auth.exists() and not (trial.tmp / TRANSCRIPT).exists():
            return []
        text = auth.read_text()
        json.loads(text)
        return self.secrets({"auth.json": text})

    def trial_credentials(
        self, trial: TrialPaths, credentials: Mapping[str, str]
    ) -> Mapping[str, str]:
        """The trial's auth.json, so the next trial starts from a refreshed login.

        A provider can rotate the refresh token, which would leave the caller's
        copy unusable once its access token expires. The caller's file is never
        written.
        """
        try:
            text = (trial.home / ".codex/auth.json").read_text()
            data = json.loads(text)
        except OSError, ValueError:
            return credentials
        return {"auth.json": text} if isinstance(data, dict) else credentials

    def discovery_locations(self, trial: TrialPaths) -> list[Location]:
        ws, home = trial.workspace, trial.home
        codex_home = home / ".codex"
        return [
            Location(
                "repo skills",
                f"{ws}/.agents/skills",
                ("controlled", "reported"),
                "test_codex_contamination::repo-skills",
            ),
            Location(
                "parent repository skills",
                "<ancestor>/.agents/skills",
                ("not-a-location",),
                "test_codex_adapter::parent-skills",
            ),
            Location(
                "user skills",
                f"{home}/.agents/skills",
                ("redirected", "reported"),
                "test_codex_contamination::home-agents-skills",
            ),
            Location(
                "Codex home skills",
                f"{codex_home}/skills",
                ("redirected", "reported"),
                "test_codex_contamination::codex-home-skills",
            ),
            Location(
                "bundled skills",
                f"{codex_home}/skills/.system",
                ("redirected", "reported"),
                "test_codex_contamination::system-skills",
            ),
            Location(
                "system skills and config",
                "/etc/codex",
                ("reported",),
                "test_codex_contamination::etc-codex",
            ),
            Location(
                "plugin skills",
                f"{codex_home}/plugins, {codex_home}/.tmp/plugins",
                ("suppressed", "reported"),
                "test_codex_contamination::plugins",
            ),
            Location(
                "global instructions",
                f"{codex_home}/AGENTS.md, AGENTS.override.md",
                ("redirected", "reported"),
                "test_codex_contamination::global-agents-md",
            ),
            Location(
                "project instructions",
                "AGENTS.md here and above",
                ("suppressed",),
                "test_codex_adapter::agents-md",
            ),
        ]

    def context_isolation(self, env: Mapping[str, str]) -> list[str]:  # noqa: ARG002 -- the adapter interface
        if "project_doc_max_bytes=0" not in self.config:
            return ["project_doc_max_bytes=0 is not set, so AGENTS.md files load"]
        return []

    def prepare_homes(self, trial: TrialPaths) -> Homes:
        home = trial.home
        agent_home = home / ".codex"
        agent_home.mkdir(parents=True, exist_ok=True)
        # Built from scratch: nothing from the caller's environment comes along,
        # including the Justfile's shared CODEX_HOME.
        env = {
            "PATH": workspace.child_path(trial),
            "HOME": str(home),
            "CODEX_HOME": str(agent_home),
            "XDG_CONFIG_HOME": str(home / ".config"),
            "XDG_DATA_HOME": str(home / ".local/share"),
            "XDG_CACHE_HOME": str(home / ".cache"),
            "XDG_STATE_HOME": str(home / ".local/state"),
            "TMPDIR": str(trial.tmp),
            "SHELL": "/bin/bash",
            "RUST_LOG": RUST_LOG,
        }
        return Homes(agent_home, home, env)

    def install_skill(self, skill_dir: Path | None, workspace: Path) -> Path | None:
        if skill_dir is None:
            return None
        # A copy of the whole shipped payload, as `npx skills` installs it for
        # Codex, never a symlink, which would resolve back into the repo.
        target = workspace / self.skills_dir / skill_dir.name
        shutil.copytree(skill_dir, target, ignore=shutil.ignore_patterns("__pycache__"))
        return target

    def run(  # noqa: PLR0913 -- the adapter interface
        self,
        prompt: str,
        trial: TrialPaths,
        homes: Homes,
        *,
        model: str,
        timeout: float,
        credentials: Mapping[str, str],
    ) -> RawRun:
        # The login reaches the trial's own CODEX_HOME, which teardown removes.
        auth = os.open(homes.agent_home / "auth.json", os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(auth, "w") as file:
            file.write(credentials["auth.json"])
        transcript = trial.tmp / TRANSCRIPT
        stderr = trial.tmp / "stderr.txt"
        argv = [
            str(self.executable),
            "exec",
            "--json",
            "--ephemeral",
            "--ignore-user-config",
            "--ignore-rules",
            "--sandbox",
            SANDBOX,
            "--model",
            model,
            "--cd",
            str(trial.workspace),
        ]
        for setting in self.config:
            argv += ["-c", setting]
        for feature in DISABLED:
            argv += ["--disable", feature]
        if self.api_base_url is not None:
            argv += ["-c", f'openai_base_url="{self.api_base_url}"']
        argv += ["--", prompt]
        finished = workspace.run_isolated(
            argv,
            cwd=trial.workspace,
            env=homes.env,
            stdout=transcript,
            stderr=stderr,
            timeout=timeout,
        )
        # Bytes, not read_text: universal newlines would turn a \r a tool printed
        # into a line break, and the event stream's lines split only on \n.
        logged = stderr.read_bytes().decode(errors="replace")
        echoed = echoed_lines(_read_events(transcript)[0])
        return RawRun(
            exit_code=finished.exit_code,
            timed_out=finished.timed_out,
            transcript=transcript,
            # Telemetry can name the account, so only the kept fields stay.
            stderr=stored_stderr(logged, echoed),
            debug_lines=kept_lines(logged, echoed),
            python_calls=workspace.python_calls(trial),
            survivors=finished.survivors,
            elapsed=finished.elapsed,
        )

    def parse(self, raw: RawRun) -> Trace:
        return parse_stream(raw)

    def discovery_report_problems(
        self, trace: Trace, trial: TrialPaths, *, installed: bool, system_root: Path
    ) -> list[str]:
        return discovery_report_problems(
            trace, trial, installed=installed, system_root=system_root
        )


def _secret_leaves(data: object, key: str = "") -> Iterator[str]:
    if isinstance(data, dict):
        for name, value in data.items():
            yield from _secret_leaves(value, str(name))
    elif isinstance(data, list):
        for value in data:
            yield from _secret_leaves(value, key)
    elif isinstance(data, str) and key not in NOT_SECRET and len(data) >= SECRET_MIN_LENGTH:
        yield data


def _fields(line: str, wanted: tuple[str, ...]) -> str:
    found = {name: value.strip('"') for name, value in FIELD.findall(line)}
    return " ".join(f"{name}={found[name]}" for name in wanted if name in found)


def _target(header: str) -> str:
    """The log target in `[<span>{…}:…: ]<target>: <message>`.

    Span fields hold quoted strings with spaces and colons, so the separators
    count only outside braces and quotes.
    """
    depth, quoted, start, parts = 0, False, 0, []
    for index, char in enumerate(header):
        if char == '"' and header[index - 1 : index] != "\\":
            quoted = not quoted
        elif not quoted and char in "{}":
            depth += 1 if char == "{" else -1
        elif not quoted and depth == 0 and header.startswith(": ", index):
            parts.append(header[start:index])
            start = index + 2
            if "{" not in parts[-1]:
                return parts[-1]
    return ""


def echoed_lines(events: list[dict[str, Any]]) -> frozenset[str]:
    """Lines in the event stream that look like the first line of a log record.

    Codex copies a tool's output into its telemetry raw, unquoted, so such a
    line in stderr may be text a tool printed rather than a record of Codex's.
    """
    found: set[str] = set()

    def walk(value: object) -> None:
        if isinstance(value, dict):
            for item in value.values():
                walk(item)
        elif isinstance(value, list):
            for item in value:
                walk(item)
        elif isinstance(value, str):
            found.update(line for line in value.split("\n") if RECORD_START.match(line))

    walk(events)
    return frozenset(found)


def _records(stderr: str, echoed: Collection[str]) -> Iterator[tuple[bool, bool, str]]:
    """Each stderr line, whether it belongs to a telemetry record, and whether it starts one.

    A telemetry field can hold tool output or prompt text over several lines,
    so the lines after a telemetry record's first line belong to it too. A
    line that is all or the start of an echoed line, or that an echoed line
    starts with (Codex can truncate an output), continues the record above:
    its text came from a tool, so it starts no record of its own.
    """
    telemetry = False
    for line in stderr.split("\n"):
        match = RECORD_START.match(line)
        starts = match is not None and not any(
            line.startswith(text) or text.startswith(line) for text in echoed
        )
        if match and starts:
            telemetry = _target(line[match.end() :]).startswith(TELEMETRY)
        yield telemetry, starts, line


def kept_lines(stderr: str, echoed: Collection[str] = ()) -> tuple[str, ...]:
    """The stderr lines the trace reads, reduced to the fields it needs.

    A failed skill load counts only from Codex's own log, never from a
    telemetry record, which can carry any text a tool printed.
    """
    kept = []
    for telemetry, starts, line in _records(stderr, echoed):
        if telemetry and starts and STARTS.search(line):
            kept.append(f"conversation_starts {_fields(line, STARTS_FIELDS)}")
        elif telemetry and starts and INVOCATION.search(line):
            kept.append(f"skill_invocation {_fields(line, INVOCATION_FIELDS)}")
        elif telemetry and starts and SANDBOX_OUTCOME.search(line):
            kept.append(f"sandbox_outcome {_fields(line, SANDBOX_FIELDS)}")
        elif not telemetry and (match := FAILED_LOAD.search(line)):
            kept.append(match.group(1))
    return tuple(kept)


def stored_stderr(stderr: str, echoed: Collection[str] = ()) -> str:
    """stderr without the telemetry records, which can name the account."""
    return "\n".join(line for telemetry, _, line in _records(stderr, echoed) if not telemetry)


def _read_events(transcript: Path) -> tuple[list[dict[str, Any]], bool]:
    """The transcript's JSON events, and whether every nonblank line parsed."""
    try:
        # Only \n ends a JSONL record: splitlines() would also split on U+2028
        # and the like, which JSON strings may hold raw.
        lines = transcript.read_text(errors="replace").split("\n")
    except FileNotFoundError:
        return [], True
    events: list[dict[str, Any]] = []
    clean = True
    for line in filter(str.strip, lines):
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            clean = False
            continue
        if isinstance(event, dict):
            events.append(event)
    return events, clean


def unwrap(command: str) -> str:
    """The command the agent asked for, without Codex's `<shell> -c` wrapper."""
    for words in simple_commands(command):
        if (
            len(words) == 3  # noqa: PLR2004 -- shell, flag, script
            and Path(words[0]).name in SHELLS
            and words[1] in ("-c", "-lc")
        ):
            return words[2]
        break
    return command


def _read_paths(command: str) -> Iterator[Path]:
    """Each file a reader program names, after any `cd <dir>` before it.

    A path named by anything other than a reader, such as `ls`, `test` or
    `echo`, or as a `name=value` assignment, is not a read.
    """
    cwd = Path()
    for words, _ in command_list(command):
        if words[0] == "cd" and len(words) == 2:  # noqa: PLR2004 -- cd and its directory
            cwd = cwd / words[1]
            continue
        if Path(words[0]).name not in READERS:
            continue
        for word in words[1:]:
            if not word.startswith("-") and not ASSIGNMENT.fullmatch(word):
                yield Path(os.path.normpath(cwd / word))


def skills_read(command: str) -> list[str]:
    """The skill of each SKILL.md in a skills directory a reader program names.

    `cd <dir> && cat SKILL.md` names <dir>/SKILL.md. A path counts only when
    its grandparent is a skills directory (`.agents/skills`, `skills`,
    `.system`), so `/tmp/cowsay/SKILL.md` is not a skill. A path whose skill
    directory the text cannot place (`../SKILL.md`, a glob, a variable) names
    no skill; it can still back Codex's own implicit event (see `parse_stream`).
    """
    skills = []
    for path in _read_paths(command):
        skill = path.parent.name
        if (
            path.name == "SKILL.md"
            and skill not in ("", "..")
            and not UNPLACEABLE.search(skill)
            and SKILLS_DIR.search(path.parent.parent.name)
        ):
            skills.append(skill)
    return skills


def reads_a_skill_md(command: str) -> bool:
    """Whether a reader program names a file called SKILL.md, placeable or not."""
    return any(path.name == "SKILL.md" for path in _read_paths(command))


def outcome_is_the_read(command: str, output: str) -> bool:
    """Whether the command's exit status and output show its read printed something.

    Only `cd <dir>` and `pwd` may come before the read, joined by `&&`, and
    the read comes last. `cd` prints nothing and `pwd` one line, so the output
    must have a line more than the `pwd`s print. After `||`, `;`, `&` or a
    pipe, or after any other command, a command can exit 0 and print something
    whatever the read did. A redirection, or a help or version flag, can make a
    reader not read. Every other shape is not a read the trace can confirm.
    """
    parts = command_list(command)
    if not parts or any(operator not in ("&&", "") for _, operator in parts):
        return False
    *before, (read, _) = parts
    pwds = sum(words == ["pwd"] for words, _ in before)
    return (
        all(
            words == ["pwd"]
            # `cd -` prints the directory it changes to.
            or (words[0] == "cd" and len(words) == 2 and not words[1].startswith("-"))  # noqa: PLR2004 -- cd and its directory
            for words, _ in before
        )
        and Path(read[0]).name in READERS
        and not any(REDIRECTION.search(word) or word in NO_READ_FLAGS for word in read[1:])
        and bool(output.strip())
        and len(output.strip("\n").split("\n")) > pwds
    )


def parse_stream(raw: RawRun) -> Trace:
    """Normalise `codex exec --json` output and the kept stderr lines.

    The trigger rule: a completed command that reads <skill>/SKILL.md with a
    reader program, exits 0, and whose output shows the read printed something
    (see `outcome_is_the_read`). Codex's own skill_invocation events count too:
    `explicit` for a `$skill` mention, whose SKILL.md it injects without
    running a command, and `implicit` only when such a read of a file called
    SKILL.md, placeable or not, succeeded. Codex logs `implicit` from the
    command text before the command runs, and for a run of the skill's
    scripts too, so the event alone shows no read.
    """
    events, clean = _read_events(raw.transcript)
    triggered: list[str] = []
    invoked: list[str] = []
    implicit: list[str] = []
    commands: list[Command] = []
    final = ""
    # Whether any completed command read a SKILL.md, for Codex's implicit event.
    read_skill_md = False
    for event in events:
        item = event.get("item")
        if event.get("type") != "item.completed" or not isinstance(item, dict):
            continue
        if item.get("type") == "agent_message":
            final = str(item.get("text", ""))
        elif item.get("type") == "command_execution":
            command = unwrap(str(item.get("command", "")))
            output = str(item.get("aggregated_output", ""))
            ok = item.get("status") == "completed" and item.get("exit_code") == 0
            commands.append(Command(command, ok, output))
            read = skills_read(command)
            invoked += read
            if ok and outcome_is_the_read(command, output):
                triggered += read
                read_skill_md = read_skill_md or reads_a_skill_md(command)
    starts = ""
    denied = 0
    for line in raw.debug_lines:
        fields = dict(FIELD.findall(line))
        if line.startswith("conversation_starts ") and not starts:
            starts = line
        elif line.startswith("sandbox_outcome "):
            denied += fields.get("outcome") == "denied"
        elif line.startswith("skill_invocation "):
            # The name may carry a plugin prefix: cowsay:cowsay.
            skill = fields.get("skill.name", "").rsplit(":", 1)[-1]
            invoked.append(skill)
            if fields.get("skill.invocation_type") == "explicit":
                triggered.append(skill)
            elif fields.get("skill.invocation_type") == "implicit":
                implicit.append(skill)
    if read_skill_md:
        triggered += implicit
    started = dict(FIELD.findall(starts))
    last = events[-1] if events else {}
    completed = clean and last.get("type") == "turn.completed"
    reason = _status_reason(raw, completed=completed, last=last, denied=denied)
    return Trace(
        # A read and Codex's event for it are one trigger.
        skills_triggered=list(dict.fromkeys(triggered)),
        skills_invoked=list(dict.fromkeys(invoked)),
        commands=commands,
        final_message=final,
        cli_version=started.get("app.version", ""),
        model=started.get("model", ""),
        exit_code=raw.exit_code,
        timed_out=raw.timed_out,
        stream_completed=completed,
        status="infra_error" if reason else "ok",
        status_reason=reason,
        visible_skills=None,
        visible_plugins=None,
        debug_lines=raw.debug_lines,
        python_calls=raw.python_calls,
    )


def _status_reason(  # noqa: PLR0911 -- one return per status, checked in order
    raw: RawRun, *, completed: bool, last: Mapping[str, Any], denied: int
) -> str:
    if raw.timed_out:
        return f"timed out after {raw.elapsed:.0f}s"
    if raw.survivors:
        return "trial processes survived teardown"
    failed = [line for line in raw.debug_lines if FAILED_LOAD.match(line)]
    if failed:
        return "; ".join(failed)[:300]
    if denied:
        # A denied command leaves no command_execution item, so the trace
        # cannot show what the agent ran.
        return (
            f"sandbox denied {denied} command(s), which the event stream omits;"
            " see docs/reference/evals.md"
        )
    if last.get("type") == "turn.failed":
        error = last.get("error")
        text = error.get("message", "") if isinstance(error, dict) else ""
        return f"agent reported an error: {str(text)[:200]}"
    if not completed:
        return "stream truncated: the last event is not turn.completed"
    if raw.exit_code != 0:
        return f"nonzero exit {raw.exit_code}"
    return ""


def _entries(directory: Path) -> list[str]:
    try:
        return sorted(p.name for p in directory.iterdir())
    except FileNotFoundError, NotADirectoryError:
        # Not PermissionError: a location the check cannot list is unverified,
        # and Codex may still open a known path in it.
        return []


def discovery_report_problems(
    trace: Trace, trial: TrialPaths, *, installed: bool, system_root: Path
) -> list[str]:
    """Check every location Codex reads skills, plugins or instructions from.

    Codex reports none of them, so the report is the locations themselves,
    read after the run and before teardown.
    """
    codex_home = trial.home / ".codex"
    problems = []
    repo = _entries(trial.workspace / ".agents/skills")
    if len(repo) != (1 if installed else 0):
        problems.append(f"repo skills: {repo} (expected {1 if installed else 0} skill)")
    if found := _entries(trial.home / ".agents/skills"):
        problems.append(f"user skills in {trial.home}/.agents/skills: {found}")
    if found := [name for name in _entries(codex_home / "skills") if name != ".system"]:
        problems.append(f"Codex home skills in {codex_home}/skills: {found}")
    builtins = BUILTIN_SKILLS.get(trace.cli_version, frozenset()) | {SYSTEM_MARKER}
    if found := sorted(set(_entries(codex_home / "skills/.system")) - builtins):
        problems.append(f"unexpected bundled skills in {codex_home}/skills/.system: {found}")
    problems += [
        f"plugins in {codex_home / name}: {_entries(codex_home / name)}"
        for name in ("plugins", ".tmp/plugins")
        if (codex_home / name).exists()
    ]
    problems += [
        f"global instructions {codex_home / name} exist"
        for name in ("AGENTS.md", "AGENTS.override.md")
        if (codex_home / name).exists()
    ]
    if found := _entries(system_root / "etc/codex"):
        problems.append(f"system location {system_root / 'etc/codex'} is not empty: {found}")
    return problems
