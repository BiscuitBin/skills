"""The Claude Code adapter. See docs/reference/evals.md for the facts it relies on."""

import json
import re
import shutil
from dataclasses import dataclass, field
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

if TYPE_CHECKING:
    from collections.abc import Mapping

    from skills_tooling.evals.adapter import TrialPaths

# Recorded from the pinned CLI's system/init event with nothing installed and an
# OAuth token set, the harness's only credential. `schedule` is listed only when
# a token is set. A new CLI version needs a new entry: rerun the canary sweep and
# copy what it reports.
BUILTIN_SKILLS = {
    "2.1.309": frozenset(
        {
            "batch",
            "claude-api",
            "code-review",
            "dataviz",
            "debug",
            "deep-research",
            "doctor",
            "fewer-permission-prompts",
            "loop",
            "plugin-authoring",
            "run",
            "run-skill-generator",
            "schedule",
            "simplify",
            "update-config",
            "verify",
            "workflow-authoring",
        }
    ),
}
BUILTIN_PLUGINS = {
    "2.1.309": frozenset({"cc-plugin-agents-md@builtin", "cc-plugin-plugin-authoring@builtin"}),
}
# Each of these switches off something that would reach outside the trial.
RUN_FLAGS = {
    # Every CLAUDE.md, CLAUDE.local.md, .claude/rules and AGENTS.md, including
    # ones above the workspace's git root.
    "CLAUDE_CODE_DISABLE_CLAUDE_MDS": "1",
    "CLAUDE_CODE_DISABLE_POLICY_SKILLS": "1",
    "DISABLE_AUTOUPDATER": "1",
    "CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC": "1",
    "DISABLE_TELEMETRY": "1",
}
ALLOWED_TOOLS = ("Skill", "Read", "Bash")
BUDGET_USD = "1.00"
# The debug log lines the contamination check reads; the rest of the log is dropped.
DEBUG_KEPT = re.compile(
    r"Loading skills from: |Loaded \d+ unique skills \(|\[skills\] Dynamically discovered"
)
TIMESTAMP = re.compile(r"^\S+ \[DEBUG\] ")
LOADING = re.compile(r"Loading skills from: managed=(.*?), user=(.*?), project=\[(.*)\]$")
LOADED = re.compile(r"Loaded \d+ unique skills \((.*)\)$")
COUNT = re.compile(r"(managed|user|project|additional): (\d+)")


class ClaudeCode:
    name: ClassVar[str] = "claude"
    default_model: ClassVar[str] = "claude-sonnet-5-5"
    credential_env: ClassVar[tuple[str, ...]] = ("CLAUDE_CODE_OAUTH_TOKEN",)
    home_env: ClassVar[tuple[str, ...]] = ("CLAUDE_CONFIG_DIR",)
    skills_dir: ClassVar[str] = ".claude/skills"
    reports_skills: ClassVar[bool] = True
    builtin_skills: ClassVar[Mapping[str, frozenset[str]]] = BUILTIN_SKILLS
    builtin_plugins: ClassVar[Mapping[str, frozenset[str]]] = BUILTIN_PLUGINS

    def __init__(self, executable: Path, *, api_base_url: str | None = None) -> None:
        self.executable = executable.resolve()
        # Only tests set this, to point the CLI at a local fake API.
        self.api_base_url = api_base_url

    def read_credentials(self, environ: Mapping[str, str]) -> Mapping[str, str]:
        credentials = {name: environ.get(name, "") for name in self.credential_env}
        missing = [name for name, value in credentials.items() if not value]
        if missing:
            msg = (
                f"{', '.join(missing)} is not set. Live evals need an authenticated agent: "
                "run `claude setup-token` and export the token. See docs/reference/evals.md."
            )
            raise CredentialError(msg)
        return credentials

    def secrets(self, credentials: Mapping[str, str]) -> list[str]:
        return [value for value in credentials.values() if value]

    def discovery_locations(self, trial: TrialPaths) -> list[Location]:
        ws, home = trial.workspace, trial.home
        return [
            Location(
                "user skills",
                f"{home}/.claude/skills",
                ("redirected", "reported"),
                "test_contamination_canaries::config-dir-skill",
            ),
            Location(
                "home ~/.claude/skills",
                "$HOME/.claude/skills",
                ("not-a-location",),
                "test_contamination_canaries::home-skills",
            ),
            Location(
                "home ~/.agents/skills",
                "$HOME/.agents/skills",
                ("not-a-location",),
                "test_contamination_canaries::home-agents-skills",
            ),
            Location(
                "project skills",
                f"{ws}/.claude/skills",
                ("controlled", "reported"),
                "test_contamination_canaries::second-project-skill",
            ),
            Location(
                "nested project skills",
                f"{ws}/<subdir>/.claude/skills",
                ("controlled", "reported"),
                "test_contamination_canaries::nested-skill",
            ),
            Location(
                "parent repository skills",
                "<ancestor>/.claude/skills, <ancestor>/.agents/skills",
                ("not-a-location",),
                "test_contamination_canaries::parent-skills",
            ),
            Location(
                "managed skills",
                "/Library/Application Support/ClaudeCode or /etc/claude-code",
                ("suppressed", "reported"),
                "test_contamination_canaries::managed-skill (CI only)",
            ),
            Location(
                "plugin skills",
                f"{home}/.claude/plugins",
                ("redirected", "reported"),
                "test_contamination::unexpected-plugin",
            ),
            Location(
                "instruction files",
                "CLAUDE.md, CLAUDE.local.md, .claude/rules, AGENTS.md, here and above",
                ("suppressed",),
                "test_contamination_canaries::context-*",
            ),
        ]

    def context_isolation(self, env: Mapping[str, str]) -> list[str]:
        if env.get("CLAUDE_CODE_DISABLE_CLAUDE_MDS") != "1":
            return ["CLAUDE_CODE_DISABLE_CLAUDE_MDS=1 is not set, so instruction files load"]
        return []

    def prepare_homes(self, trial: TrialPaths) -> Homes:
        home = trial.home
        agent_home = home / ".claude"
        agent_home.mkdir(parents=True, exist_ok=True)
        # Built from scratch: nothing from the caller's environment comes along,
        # including the Justfile's shared CLAUDE_CONFIG_DIR.
        env = {
            "PATH": workspace.child_path(trial),
            "HOME": str(home),
            "CLAUDE_CONFIG_DIR": str(agent_home),
            "XDG_CONFIG_HOME": str(home / ".config"),
            "XDG_DATA_HOME": str(home / ".local/share"),
            "XDG_CACHE_HOME": str(home / ".cache"),
            "XDG_STATE_HOME": str(home / ".local/state"),
            "TMPDIR": str(trial.tmp),
            "SHELL": "/bin/bash",
            **RUN_FLAGS,
        }
        if self.api_base_url is not None:
            env["ANTHROPIC_BASE_URL"] = self.api_base_url
        return Homes(agent_home, home, env)

    def install_skill(self, skill_dir: Path | None, workspace: Path) -> Path | None:
        if skill_dir is None:
            return None
        # A copy, never a symlink, which would resolve back into the repo.
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
        debug_log = trial.tmp / "debug.log"
        transcript = trial.tmp / "transcript.jsonl"
        argv = [
            str(self.executable),
            "-p",
            prompt,
            "--output-format",
            "stream-json",
            "--verbose",
            "--model",
            model,
            "--no-session-persistence",
            "--strict-mcp-config",
            "--permission-mode",
            "dontAsk",
            "--max-budget-usd",
            BUDGET_USD,
            "--debug-file",
            str(debug_log),
            "--allowedTools",
            *ALLOWED_TOOLS,
        ]
        env = {**homes.env, **{k: credentials[k] for k in self.credential_env}}
        finished = workspace.run_isolated(
            argv,
            cwd=trial.workspace,
            env=env,
            stdout=transcript,
            stderr=trial.tmp / "stderr.txt",
            timeout=timeout,
        )
        return RawRun(
            exit_code=finished.exit_code,
            timed_out=finished.timed_out,
            transcript=transcript,
            stderr=(trial.tmp / "stderr.txt").read_text(errors="replace"),
            debug_lines=_kept_debug_lines(debug_log),
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


def _kept_debug_lines(debug_log: Path) -> tuple[str, ...]:
    try:
        lines = debug_log.read_text(errors="replace").splitlines()
    except FileNotFoundError:
        return ()
    debug_log.unlink()
    return tuple(TIMESTAMP.sub("", line) for line in lines if DEBUG_KEPT.search(line))


def _content_text(content: object) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return "".join(str(part.get("text", "")) for part in content if isinstance(part, dict))
    return ""


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


def _blocks(event: Mapping[str, Any], role: str) -> list[dict[str, Any]]:
    if event.get("type") != role:
        return []
    content = event.get("message", {}).get("content", [])
    return [b for b in content if isinstance(b, dict)] if isinstance(content, list) else []


@dataclass
class _Calls:
    """Tool calls in order, each with its result once the CLI reports one."""

    calls: dict[str, tuple[str, dict[str, Any]]] = field(default_factory=dict)
    results: dict[str, tuple[bool, str]] = field(default_factory=dict)
    last_text: str = ""

    def read(self, event: Mapping[str, Any]) -> None:
        for block in _blocks(event, "assistant"):
            if block.get("type") == "tool_use":
                self.calls[str(block.get("id"))] = (
                    str(block.get("name", "")),
                    block.get("input") or {},
                )
            elif block.get("type") == "text":
                self.last_text = str(block.get("text", ""))
        for block in _blocks(event, "user"):
            if block.get("type") == "tool_result":
                self.results[str(block.get("tool_use_id", ""))] = (
                    bool(block.get("is_error", False)),
                    _content_text(block.get("content")),
                )


def parse_stream(raw: RawRun) -> Trace:
    """Normalise a stream-json transcript. Run status never comes from `subtype`."""
    events, clean = _read_events(raw.transcript)
    init = next(
        (e for e in events if e.get("type") == "system" and e.get("subtype") == "init"), {}
    )
    seen = _Calls()
    dynamic: list[str] = []
    for event in events:
        seen.read(event)
        if event.get("type") == "system" and event.get("subtype") == "commands_changed":
            dynamic += [
                str(c.get("name")) for c in event.get("commands", []) if isinstance(c, dict)
            ]
    triggered, invoked, commands = [], [], []
    for call_id, (name, tool_input) in seen.calls.items():
        error, output = seen.results.get(call_id, (True, ""))
        if name == "Skill":
            # The trigger rule: a Skill call whose result is not an error. The
            # name may carry a plugin prefix.
            skill = str(tool_input.get("skill", "")).rsplit(":", 1)[-1]
            invoked.append(skill)
            if call_id in seen.results and not error:
                triggered.append(skill)
        elif name == "Bash":
            commands.append(Command(str(tool_input.get("command", "")), not error, output))
    last = events[-1] if events else {}
    completed = clean and last.get("type") == "result"
    last_text = seen.last_text
    final = str(last.get("result", "")) if completed else last_text
    reason = _status_reason(raw, completed=completed, result=last)
    return Trace(
        skills_triggered=triggered,
        skills_invoked=invoked,
        commands=commands,
        final_message=final,
        cli_version=str(init.get("claude_code_version", "")),
        model=str(init.get("model", "")),
        exit_code=raw.exit_code,
        timed_out=raw.timed_out,
        stream_completed=completed,
        status="infra_error" if reason else "ok",
        status_reason=reason,
        visible_skills=frozenset(init["skills"]) if "skills" in init else None,
        visible_plugins=(
            frozenset(str(p.get("source")) for p in init["plugins"]) if "plugins" in init else None
        ),
        initial_commands=(frozenset(init["slash_commands"]) if "slash_commands" in init else None),
        dynamic_commands=dynamic,
        debug_lines=raw.debug_lines,
        python_calls=raw.python_calls,
    )


def _status_reason(raw: RawRun, *, completed: bool, result: Mapping[str, Any]) -> str:
    if raw.timed_out:
        return f"timed out after {raw.elapsed:.0f}s"
    if raw.survivors:
        return "trial processes survived teardown"
    if not completed:
        return "stream truncated: the last event is not a result"
    if result.get("is_error"):
        return f"agent reported an error: {str(result.get('result', ''))[:200]}"
    if raw.exit_code != 0:
        return f"nonzero exit {raw.exit_code}"
    return ""


def _entries(directory: Path) -> list[str]:
    try:
        return [p.name for p in directory.iterdir()]
    except FileNotFoundError, NotADirectoryError, PermissionError:
        return []


def _inside(path: str, root: Path) -> bool:
    return Path(path).resolve().is_relative_to(root.resolve())


def discovery_report_problems(
    trace: Trace, trial: TrialPaths, *, installed: bool, system_root: Path
) -> list[str]:
    """Check the CLI's own report of where it looked for skills and what it loaded."""
    loading = [m for line in trace.debug_lines if (m := LOADING.search(line))]
    counts = [m for line in trace.debug_lines if (m := LOADED.search(line))]
    if not loading or not counts:
        return ["no discovery report in the debug log; failing closed"]
    problems = []
    for match in loading:
        managed, user, projects = match.groups()
        if not _inside(user, trial.home):
            problems.append(f"user skills location {user} is outside the trial home")
        problems += [
            f"project skills location {project} is outside the workspace"
            for project in projects.split(", ")
            if project and not _inside(project, trial.workspace)
        ]
        managed_dir = system_root / managed.lstrip("/")
        if _entries(managed_dir):
            problems.append(f"managed skills location {managed_dir} is not empty")
    wanted = {"managed": 0, "user": 0, "additional": 0, "project": 1 if installed else 0}
    for match in counts:
        found = {name: int(n) for name, n in COUNT.findall(match.group(1))}
        problems += [
            f"skills loaded from {name}: {found.get(name)} (expected {count})"
            for name, count in wanted.items()
            if found.get(name) != count
        ]
    return problems
