"""Per-trial directories: a fresh git workspace, empty homes, and a constructed PATH.

See docs/explanation/eval-isolation.md for what this isolates and what it does not.
"""

import contextlib
import os
import shlex
import shutil
import signal
import stat
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

from skills_tooling.evals.adapter import PythonCall, TrialPaths

if TYPE_CHECKING:
    from collections.abc import Iterator, Mapping
    from types import FrameType

GRACE_SECONDS = 2.0
# Signals that end a run. SIGKILL cannot be caught; that limit is documented.
TERMINATING = (signal.SIGINT, signal.SIGTERM, signal.SIGHUP)

# Git sees neither the user's nor the system's config, so no hooks, helpers or
# templates reach the workspace.
GIT_ENV = {
    "GIT_CONFIG_GLOBAL": os.devnull,
    "GIT_CONFIG_NOSYSTEM": "1",
    "GIT_AUTHOR_NAME": "Eval Harness",
    "GIT_AUTHOR_EMAIL": "eval@example.invalid",
    "GIT_COMMITTER_NAME": "Eval Harness",
    "GIT_COMMITTER_EMAIL": "eval@example.invalid",
}
SYSTEM_PATH = "/usr/bin:/bin"
RECORD_END = "\x1e"
FIELD_END = "\x1f"


def git(*args: str, cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(  # noqa: S603 -- arguments come from this module
        ["git", *args],  # noqa: S607 -- git is a documented host prerequisite
        cwd=cwd,
        env={"PATH": SYSTEM_PATH, "HOME": os.devnull, **GIT_ENV},
        capture_output=True,
        text=True,
        check=False,
    )


def create_trial(base: Path, run_id: str, case_id: str) -> TrialPaths:
    """Create <base>/<run-id>/<case-id>/ with a fresh git workspace and empty homes."""
    root = (base / run_id / case_id).resolve()
    root.mkdir(parents=True)
    trial = TrialPaths(root, root / "workspace", root / "home", root / "tmp", root / "bin")
    for path in (trial.workspace, trial.home, trial.tmp, trial.bin):
        path.mkdir()
    initialised = git("init", "--quiet", "--initial-branch=main", cwd=trial.workspace)
    if initialised.returncode != 0:
        msg = f"git init failed in {trial.workspace}: {initialised.stderr.strip()}"
        raise RuntimeError(msg)
    _write_bin(trial)
    return trial


def _write_bin(trial: TrialPaths) -> None:
    """python3 and python run the harness's own interpreter, then log the call and its status."""
    real = Path(sys.executable).resolve()
    log = shlex.quote(str(trial.python_log))
    wrapper = (
        "#!/bin/sh\n"
        "# Written by the eval harness: records this call for the script_ran assertion.\n"
        # In the background so a trap can run while it waits, which ignores SIGINT in
        # the child: every signal goes on as SIGTERM. A background job's stdin is
        # /dev/null, and in dash `<&0` then copies that, so stdin goes through fd 9.
        # The subshell tries the copy first: a failed `exec` redirection ends the shell.
        "exec 9</dev/null\n"
        "(exec 9<&0) 2>/dev/null && exec 9<&0\n"
        f'{shlex.quote(str(real))} "$@" <&9 9<&- &\n'
        "child=$!\n"
        "exec 9<&-\n"
        "trap 'kill -TERM \"$child\" 2>/dev/null' TERM INT HUP\n"
        'wait "$child"\n'
        "code=$?\n"
        # A trapped signal ends the wait, not the interpreter.
        'while kill -0 "$child" 2>/dev/null; do wait "$child"; code=$?; done\n'
        f'{{ printf \'%s{FIELD_END}\' "$PWD" "$code" "$@"; printf \'{RECORD_END}\'; }} >>{log}\n'
        'exit "$code"\n'
    )
    for name in ("python3", "python"):
        path = trial.bin / name
        path.write_text(wrapper)
        path.chmod(0o755)
    found = shutil.which("git", path=SYSTEM_PATH)
    if found is not None:
        (trial.bin / "git").symlink_to(found)


@dataclass
class _Termination:
    """The signal that is ending the run, if any, and whether it may raise now."""

    received: int | None = None
    stoppable: bool = False

    def stop_if_received(self) -> None:
        if self.received is not None and self.stoppable:
            # Cleared first: the unwinding runs cleanup, which no signal may interrupt.
            self.stoppable = False
            raise SystemExit(128 + self.received)


_termination = _Termination()


def _on_termination(signum: int, _frame: FrameType | None) -> None:
    if _termination.received is None:
        _termination.received = signum
    _termination.stop_if_received()


@contextlib.contextmanager
def _stoppable() -> Iterator[None]:
    _termination.stoppable = True
    try:
        _termination.stop_if_received()
        yield
    finally:
        _termination.stoppable = False


@contextlib.contextmanager
def end_on_termination() -> Iterator[None]:
    """While a run lasts, a terminating signal ends it without cutting cleanup short.

    The signal raises SystemExit only while run_isolated waits on an agent, the
    one wait worth breaking, so the `finally` blocks run as they do for any other
    failure. Anywhere else it waits for the next agent or the end of the run, so
    it cannot land inside cleanup. A signal already ignored, as under nohup, stays
    ignored. Installed only here, so library callers and tests keep their handlers.
    """
    _termination.received = None
    previous = {signum: signal.getsignal(signum) for signum in TERMINATING}
    for signum, handler in previous.items():
        if handler != signal.SIG_IGN:
            signal.signal(signum, _on_termination)
    try:
        yield
        with _stoppable():
            pass
    finally:
        for signum, handler in previous.items():
            signal.signal(signum, handler)


@dataclass(frozen=True)
class Finished:
    exit_code: int | None
    timed_out: bool
    survivors: bool
    elapsed: float


def run_isolated(  # noqa: PLR0913 -- one keyword per stream and limit
    argv: list[str],
    *,
    cwd: Path,
    env: Mapping[str, str],
    stdout: Path,
    stderr: Path,
    timeout: float,
) -> Finished:
    """Run argv in its own process group, and end the whole group however the wait ends.

    A descendant the agent started in the background would otherwise outlive the
    run, and could write files after the harness has checked them. One that
    calls setsid leaves the group, and a SIGKILL of the harness skips this; those
    limits are documented.
    """
    started = time.monotonic()
    timed_out = False
    # A signal that arrived outside a wait ends the run before this agent starts.
    with _stoppable():
        pass
    with stdout.open("wb") as out, stderr.open("wb") as err:
        # Again, for one during the opens. Raising inside Popen could lose the process, so
        # one landing there waits for the `_stoppable` below, which ends the group.
        with _stoppable():
            pass
        process = subprocess.Popen(  # noqa: S603 -- argv is built by the adapter
            argv,
            cwd=cwd,
            env=dict(env),
            stdin=subprocess.DEVNULL,
            stdout=out,
            stderr=err,
            start_new_session=True,
        )
        try:
            with _stoppable():
                process.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            timed_out = True
        finally:
            survivors = _end_group(process)
    exit_code = None if timed_out else process.returncode
    return Finished(exit_code, timed_out, survivors, time.monotonic() - started)


def _end_group(process: subprocess.Popen[bytes]) -> bool:
    """SIGTERM, then SIGKILL, the process group; True if anything is still alive."""
    group = process.pid
    for sig in (signal.SIGTERM, signal.SIGKILL):
        with contextlib.suppress(ProcessLookupError):
            os.killpg(group, sig)
        # Reap the leader, or a zombie leader keeps the group looking alive.
        with contextlib.suppress(subprocess.TimeoutExpired):
            process.wait(timeout=GRACE_SECONDS)
        deadline = time.monotonic() + GRACE_SECONDS
        while time.monotonic() < deadline:
            if not _group_alive(group):
                return False
            time.sleep(0.05)
    return _group_alive(group)


def _group_alive(group: int) -> bool:
    try:
        os.killpg(group, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


def _grant(path: Path, bits: int) -> None:
    """Add bits to path's mode, unless it is a link: chmod would follow it out of the trial."""
    with contextlib.suppress(OSError):
        mode = path.lstat().st_mode
        if not stat.S_ISLNK(mode):
            path.chmod(stat.S_IMODE(mode) | bits)


def restore_access(root: Path) -> None:
    """Give the owner back whatever the agent locked under root, as far as chmod can."""
    _grant(root, stat.S_IRWXU)
    # Top-down, so each directory opens before the walk descends into it.
    for directory, dirnames, filenames in os.walk(root):
        for name in dirnames:
            _grant(Path(directory, name), stat.S_IRWXU)
        for name in filenames:
            _grant(Path(directory, name), stat.S_IRUSR | stat.S_IWUSR)


def teardown(trial: TrialPaths) -> None:
    """Remove everything but the workspace: the homes, temporary files and PATH shims."""
    for path in (trial.home, trial.tmp, trial.bin):
        shutil.rmtree(path, ignore_errors=True)


def isolation_problems(trial: TrialPaths, repo_root: Path) -> list[str]:
    """Where the workspace sits: its own git root, gitignored, outside the skill trees."""
    problems = []
    toplevel = git("rev-parse", "--show-toplevel", cwd=trial.workspace).stdout.strip()
    if not toplevel or Path(toplevel).resolve() != trial.workspace:
        problems.append(f"workspace is not its own git root (git reports {toplevel!r})")
    if git("check-ignore", "--quiet", str(trial.workspace), cwd=repo_root).returncode != 0:
        problems.append(f"workspace is not gitignored by {repo_root}")
    problems += [
        f"workspace is inside {tree}/"
        for tree in ("skills", "dev-skills")
        if trial.workspace.is_relative_to((repo_root / tree).resolve())
    ]
    return problems


def inventory_problems(workspace: Path, skills_dir: str, skill: str | None) -> list[str]:
    """The workspace may hold its .git and the installed skill, and nothing else.

    Anything more could carry expected outputs, other cases, or a nested skills
    directory the agent would discover mid-run.
    """
    allowed = [*Path(skills_dir).parts, skill] if skill is not None else []
    problems: list[str] = []

    def walk(directory: Path, remaining: list[str]) -> None:
        for entry in sorted(directory.iterdir()):
            if directory == workspace and entry.name == ".git":
                continue
            if remaining and entry.name == remaining[0] and entry.is_dir():
                if len(remaining) > 1:
                    walk(entry, remaining[1:])
                continue
            problems.append(f"unexpected in workspace: {entry.relative_to(workspace)}")

    walk(workspace, allowed)
    return problems


def child_path(trial: TrialPaths) -> str:
    return f"{trial.bin}:{SYSTEM_PATH}"


def python_calls(trial: TrialPaths) -> tuple[PythonCall, ...]:
    try:
        raw = trial.python_log.read_text(errors="replace")
    except FileNotFoundError:
        return ()
    # Each record is the cwd, the exit status, then each argument, each ending in FIELD_END.
    records = [record.split(FIELD_END) for record in raw.split(RECORD_END)]
    return tuple(call for call in map(_python_call, records) if call is not None)


def _python_call(fields: list[str]) -> PythonCall | None:
    """The call in one record, or None for a malformed one, which counts as no run.

    An argument can hold RECORD_END and the agent can write to the log, so a
    record may be a fragment.
    """
    if len(fields) < 3:  # noqa: PLR2004 -- the cwd, the status and the final empty field
        return None
    try:
        return PythonCall(fields[0], tuple(fields[2:-1]), int(fields[1]))
    except ValueError:
        return None
