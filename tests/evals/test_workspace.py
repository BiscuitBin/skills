"""Per-trial isolation: the workspace, the homes, the constructed PATH and teardown."""

import os
import resource
import shutil
import signal
import stat
import subprocess
import sys
import time
from pathlib import Path
from typing import TYPE_CHECKING, Any

import pytest

from skills_tooling.evals import results, workspace
from skills_tooling.evals.adapter import PythonCall
from skills_tooling.evals.claude_code import ClaudeCode
from tests.evals.test_runner import TOKEN, fake_root

if TYPE_CHECKING:
    from collections.abc import Callable, Iterator

ROOT = Path(__file__).parents[2]
# The real command with run_suite replaced by one trial, so nothing but the agent is faked.
# "teardown" and "group" signal the harness from inside that cleanup step.
TERMINATED_RUN = """
import os, shutil, signal, sys
from pathlib import Path

from skills_tooling.evals import __main__ as cli
from skills_tooling.evals import workspace

base, scenario, signum = Path(sys.argv[1]), sys.argv[2], int(sys.argv[3])
signal.signal(signal.SIGINT, signal.default_int_handler)


def signal_first_call(real, applies=lambda *args: True):
    fired = []

    def hooked(*args, **kwargs):
        if not fired and applies(*args):
            fired.append(True)
            os.kill(os.getpid(), signum)
        return real(*args, **kwargs)

    return hooked


script, timeout = "echo $$; exec sleep 600", 60
if scenario == "teardown":
    script = "exit 0"
    shutil.rmtree = signal_first_call(shutil.rmtree)
if scenario == "group":
    script, timeout = 'trap "" TERM; echo $$; exec sleep 600', 1
    workspace.GRACE_SECONDS = 0.2
    os.killpg = signal_first_call(os.killpg, lambda _group, sig: sig == signal.SIGTERM)


def agent(trial, script, timeout):
    workspace.run_isolated(
        ["/bin/sh", "-c", script],
        cwd=trial.workspace,
        env={"PATH": "/usr/bin:/bin"},
        stdout=base / "out",
        stderr=base / "err",
        timeout=timeout,
    )


def run_suite(_settings):
    trial = workspace.create_trial(base, "run", "case")
    (trial.home / "auth.json").write_text("{}")
    try:
        agent(trial, script, timeout)
    finally:
        workspace.teardown(trial)
    if scenario == "teardown":
        agent(trial, "sleep 600", 60)
    return 0


cli.run_suite = run_suite
sys.argv = ["evals", "run", "cowsay", "--agent", "claude", "--root", str(base / "repo")]
cli.main()
"""


def fake_repo(tmp_path: Path, *, ignore: bool = True) -> Path:
    repo = tmp_path / "repo"
    repo.mkdir()
    subprocess.run(["git", "init", "--quiet"], cwd=repo, check=True)  # noqa: S607
    if ignore:
        (repo / ".gitignore").write_text(".eval-workspaces/\n")
    return repo


def test_child_env_overrides_the_shared_config_dir(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("CLAUDE_CONFIG_DIR", str(ROOT / ".tools/agent-homes/claude"))
    monkeypatch.setenv("SOME_USER_SETTING", "leaks")
    trial = workspace.create_trial(tmp_path, "run", "case")
    env = ClaudeCode(ROOT / "node_modules/.bin/claude").prepare_homes(trial).env
    assert env["CLAUDE_CONFIG_DIR"] == str(trial.home / ".claude")
    assert env["HOME"] == str(trial.home)
    assert env["TMPDIR"] == str(trial.tmp)
    assert "SOME_USER_SETTING" not in env
    assert env["CLAUDE_CODE_DISABLE_CLAUDE_MDS"] == "1"


def test_constructed_path_runs_python3_and_git_and_logs_python(tmp_path: Path) -> None:
    trial = workspace.create_trial(tmp_path, "run", "case")
    env = dict(ClaudeCode(ROOT / "node_modules/.bin/claude").prepare_homes(trial).env)
    printed = subprocess.run(
        ["python3", "-c", "import sys; print(sys.version_info[:2])", "x y"],  # noqa: S607
        cwd=trial.workspace,
        env=env,
        capture_output=True,
        text=True,
        check=True,
    )
    assert printed.stdout == "(3, 14)\n"
    git = subprocess.run(["git", "--version"], env=env, capture_output=True, check=False)  # noqa: S607
    assert git.returncode == 0
    [call] = workspace.python_calls(trial)
    assert call.cwd == str(trial.workspace)
    assert call.argv == ("-c", "import sys; print(sys.version_info[:2])", "x y")
    assert call.exit_code == 0


def test_python_wrapper_passes_on_and_logs_the_exit_status(tmp_path: Path) -> None:
    trial = workspace.create_trial(tmp_path, "run", "case")
    env = {"PATH": workspace.child_path(trial)}
    missing = subprocess.run(
        ["python3", "missing.py"],  # noqa: S607
        cwd=trial.workspace,
        env=env,
        capture_output=True,
        check=False,
    )
    assert missing.returncode == 2
    [call] = workspace.python_calls(trial)
    assert call.argv == ("missing.py",)
    assert call.exit_code == 2


def test_python_calls_tolerates_an_argument_holding_the_record_separator(
    tmp_path: Path,
) -> None:
    trial = workspace.create_trial(tmp_path, "run", "case")
    env = {"PATH": workspace.child_path(trial)}
    subprocess.run(
        ["python3", "-c", "pass", f"a{workspace.RECORD_END}b"],  # noqa: S607
        cwd=trial.workspace,
        env=env,
        check=True,
    )
    [call] = workspace.python_calls(trial)
    assert call.argv[:2] == ("-c", "pass")
    assert call.exit_code == 0


def test_python_calls_skips_a_record_without_a_numeric_status(tmp_path: Path) -> None:
    trial = workspace.create_trial(tmp_path, "run", "case")
    fields = workspace.FIELD_END, workspace.RECORD_END
    trial.python_log.write_text(
        "/w{0}x{0}script.py{0}{1}/w{0}{2}{0}script.py{0}{1}/w{0}0{0}script.py{0}{1}".format(
            *fields, "9" * 5000
        )
    )
    assert workspace.python_calls(trial) == (PythonCall("/w", ("script.py",)),)


def test_workspace_is_its_own_ignored_git_root(tmp_path: Path) -> None:
    repo = fake_repo(tmp_path)
    trial = workspace.create_trial(repo / ".eval-workspaces", "run", "case")
    assert workspace.isolation_problems(trial, repo) == []


def test_unignored_or_nested_workspace_is_reported(tmp_path: Path) -> None:
    repo = fake_repo(tmp_path, ignore=False)
    trial = workspace.create_trial(repo / ".eval-workspaces", "run", "case")
    assert any("gitignored" in p for p in workspace.isolation_problems(trial, repo))
    (trial.workspace / ".git").rename(trial.workspace / "git-moved")
    assert any("own git root" in p for p in workspace.isolation_problems(trial, repo))


def test_inventory_allows_only_git_and_the_installed_skill(tmp_path: Path) -> None:
    trial = workspace.create_trial(tmp_path, "run", "case")
    ClaudeCode(ROOT / "node_modules/.bin/claude").install_skill(
        ROOT / "skills/cowsay", trial.workspace
    )
    assert workspace.inventory_problems(trial.workspace, ".claude/skills", "cowsay") == []
    nested = trial.workspace / "sub/.claude/skills/canary"
    nested.mkdir(parents=True)
    (trial.workspace / "notes.txt").write_text("expected output\n")
    assert workspace.inventory_problems(trial.workspace, ".claude/skills", "cowsay") == [
        "unexpected in workspace: notes.txt",
        "unexpected in workspace: sub",
    ]


def test_baseline_inventory_is_only_git(tmp_path: Path) -> None:
    trial = workspace.create_trial(tmp_path, "run", "case")
    assert workspace.inventory_problems(trial.workspace, ".claude/skills", None) == []
    (trial.workspace / ".claude/skills/cowsay").mkdir(parents=True)
    assert workspace.inventory_problems(trial.workspace, ".claude/skills", None) == [
        "unexpected in workspace: .claude"
    ]


def test_normal_exit_ends_background_descendants(tmp_path: Path) -> None:
    out, err = tmp_path / "out", tmp_path / "err"
    finished = workspace.run_isolated(
        ["/bin/sh", "-c", "sleep 600 & echo $!"],
        cwd=tmp_path,
        env={"PATH": "/usr/bin:/bin"},
        stdout=out,
        stderr=err,
        timeout=30,
    )
    assert (finished.exit_code, finished.timed_out, finished.survivors) == (0, False, False)
    with pytest.raises(ProcessLookupError):
        os.kill(int(out.read_text()), 0)


def test_timeout_ends_the_run_and_records_it(tmp_path: Path) -> None:
    finished = workspace.run_isolated(
        ["/bin/sh", "-c", "sleep 600"],
        cwd=tmp_path,
        env={"PATH": "/usr/bin:/bin"},
        stdout=tmp_path / "out",
        stderr=tmp_path / "err",
        timeout=0.5,
    )
    assert (finished.exit_code, finished.timed_out, finished.survivors) == (None, True, False)


def start_terminated_run(tmp_path: Path, scenario: str, signum: int) -> subprocess.Popen[str]:
    root = fake_root(tmp_path)
    (root / "node_modules/.bin").mkdir(parents=True)
    (root / "node_modules/.bin/claude").touch()
    return subprocess.Popen(
        [sys.executable, "-c", TERMINATED_RUN, str(tmp_path), scenario, str(signum)],
        env={**os.environ, "CLAUDE_CODE_OAUTH_TOKEN": TOKEN},
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        text=True,
    )


def agent_pid(out: Path) -> int:
    deadline = time.monotonic() + 15
    while time.monotonic() < deadline:
        written = out.read_text().strip() if out.exists() else ""
        if written:
            return int(written)
        time.sleep(0.05)
    pytest.fail("the agent never started")


def assert_cleaned_up(tmp_path: Path, process: subprocess.Popen[str], signum: int) -> None:
    assert process.wait(timeout=30) == 128 + signum
    assert [p.name for p in (tmp_path / "run/case").iterdir()] == ["workspace"]


@pytest.mark.parametrize("signum", [signal.SIGTERM, signal.SIGHUP])
def test_a_signal_while_the_agent_runs_ends_it_and_removes_the_homes(
    tmp_path: Path, signum: signal.Signals
) -> None:
    process = start_terminated_run(tmp_path, "agent", signum)
    pid = agent_pid(tmp_path / "out")
    process.send_signal(signum)
    assert_cleaned_up(tmp_path, process, signum)
    with pytest.raises(ProcessLookupError):
        os.kill(pid, 0)


@pytest.mark.parametrize("signum", [signal.SIGINT, signal.SIGTERM, signal.SIGHUP])
def test_a_first_signal_during_teardown_lets_it_finish_and_starts_no_more_agents(
    tmp_path: Path, signum: signal.Signals
) -> None:
    process = start_terminated_run(tmp_path, "teardown", signum)
    # The next agent sleeps for 600 seconds, so this returns only if the run stopped at it.
    assert_cleaned_up(tmp_path, process, signum)


def test_a_first_signal_while_ending_the_group_still_kills_a_stubborn_agent(
    tmp_path: Path,
) -> None:
    process = start_terminated_run(tmp_path, "group", signal.SIGTERM)
    assert_cleaned_up(tmp_path, process, signal.SIGTERM)
    with pytest.raises(ProcessLookupError):
        os.kill(int((tmp_path / "out").read_text()), 0)


def test_termination_handlers_last_for_the_run_and_leave_an_ignored_signal_alone() -> None:
    term, hup = signal.getsignal(signal.SIGTERM), signal.signal(signal.SIGHUP, signal.SIG_IGN)
    try:
        with workspace.end_on_termination():
            assert signal.getsignal(signal.SIGTERM) == workspace._on_termination
            assert signal.getsignal(signal.SIGHUP) == signal.SIG_IGN
        assert signal.getsignal(signal.SIGTERM) == term
        assert signal.getsignal(signal.SIGHUP) == signal.SIG_IGN
    finally:
        signal.signal(signal.SIGHUP, hup)


def test_teardown_removes_homes_and_keeps_the_workspace(tmp_path: Path) -> None:
    trial = workspace.create_trial(tmp_path, "run", "case")
    (trial.home / ".claude").mkdir()
    workspace.teardown(trial)
    assert [p.name for p in trial.root.iterdir()] == ["workspace"]


def test_a_pending_signal_starts_no_agent(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    # A fresh state: the signal would otherwise stay recorded for later tests.
    monkeypatch.setattr(workspace, "_termination", workspace._Termination())
    monkeypatch.setattr(subprocess, "Popen", lambda *_args, **_kwargs: pytest.fail("launched"))
    with pytest.raises(SystemExit) as stopped, workspace.end_on_termination():
        os.kill(os.getpid(), signal.SIGTERM)
        workspace.run_isolated(
            ["/usr/bin/true"],
            cwd=tmp_path,
            env={},
            stdout=tmp_path / "out",
            stderr=tmp_path / "err",
            timeout=5,
        )
    assert stopped.value.code == 128 + signal.SIGTERM
    assert not (tmp_path / "out").exists()


def test_a_signal_while_the_output_files_open_starts_no_agent(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(workspace, "_termination", workspace._Termination())
    monkeypatch.setattr(subprocess, "Popen", lambda *_args, **_kwargs: pytest.fail("launched"))
    out = tmp_path / "out"
    real_open = Path.open

    def signalling_open(self: Path, *args: Any, **kwargs: Any) -> Any:  # noqa: ANN401
        if self == out:
            os.kill(os.getpid(), signal.SIGTERM)
        return real_open(self, *args, **kwargs)

    monkeypatch.setattr(Path, "open", signalling_open)
    with pytest.raises(SystemExit) as stopped, workspace.end_on_termination():
        workspace.run_isolated(
            ["/usr/bin/true"],
            cwd=tmp_path,
            env={},
            stdout=out,
            stderr=tmp_path / "err",
            timeout=5,
        )
    assert stopped.value.code == 128 + signal.SIGTERM


def test_a_signal_during_the_launch_ends_the_agent_it_started(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Pins the documented limit: the launch cannot be stopped, so its agent is ended at once.
    monkeypatch.setattr(workspace, "_termination", workspace._Termination())
    real_popen = subprocess.Popen
    started = []

    def signalling_popen(*args: Any, **kwargs: Any) -> Any:  # noqa: ANN401
        os.kill(os.getpid(), signal.SIGTERM)
        started.append(real_popen(*args, **kwargs))
        return started[-1]

    monkeypatch.setattr(subprocess, "Popen", signalling_popen)
    with pytest.raises(SystemExit) as stopped, workspace.end_on_termination():
        workspace.run_isolated(
            ["/bin/sleep", "30"],
            cwd=tmp_path,
            env={},
            stdout=tmp_path / "out",
            stderr=tmp_path / "err",
            timeout=30,
        )
    assert stopped.value.code == 128 + signal.SIGTERM
    assert started[0].poll() is not None


def test_a_signal_to_the_python_wrapper_reaches_the_interpreter(tmp_path: Path) -> None:
    trial = workspace.create_trial(tmp_path, "run", "case")
    ready = tmp_path / "ready"
    gone = tmp_path / "gone"
    code = (
        "import pathlib, signal, sys, time\n"
        "def stop(*_): pathlib.Path(sys.argv[2]).touch(); sys.exit(3)\n"
        "signal.signal(signal.SIGTERM, stop)\n"
        "pathlib.Path(sys.argv[1]).touch()\n"
        "time.sleep(30)\n"
    )
    process = subprocess.Popen(
        [str(trial.bin / "python3"), "-c", code, str(ready), str(gone)],
        env={"PATH": "/usr/bin:/bin"},
    )
    try:
        deadline = time.monotonic() + 10
        while not ready.exists() and time.monotonic() < deadline:
            time.sleep(0.02)
        process.terminate()
        assert process.wait(timeout=10) == 3
    finally:
        process.kill()
    assert gone.exists()
    assert workspace.python_calls(trial)[-1].exit_code == 3


# dash is /bin/sh on Ubuntu, and gives a background job /dev/null as stdin.
SHELLS = [name for name in ("sh", "dash", "bash") if shutil.which(name)]


@pytest.mark.parametrize("shell", SHELLS)
def test_the_python_wrapper_passes_stdin_to_the_interpreter(tmp_path: Path, shell: str) -> None:
    trial = workspace.create_trial(tmp_path, "run", "case")
    done = subprocess.run(
        [shell, str(trial.bin / "python3"), "-c", "import sys; print(sys.stdin.read().upper())"],
        env={"PATH": "/usr/bin:/bin"},
        input="moo",
        capture_output=True,
        text=True,
        timeout=30,
        check=True,
    )
    assert done.stdout == "MOO\n"


@pytest.mark.parametrize("shell", SHELLS)
def test_the_python_wrapper_runs_with_stdin_closed(tmp_path: Path, shell: str) -> None:
    trial = workspace.create_trial(tmp_path, "run", "case")
    done = subprocess.run(
        [shell, str(trial.bin / "python3"), "-c", "raise SystemExit(7)"],
        env={"PATH": "/usr/bin:/bin"},
        preexec_fn=lambda: os.close(0),
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    assert (done.returncode, done.stderr) == (7, "")
    assert workspace.python_calls(trial)[-1].exit_code == 7


@pytest.mark.parametrize("shell", SHELLS)
def test_the_python_wrapper_does_not_leak_its_stdin_copy(tmp_path: Path, shell: str) -> None:
    trial = workspace.create_trial(tmp_path, "run", "case")
    done = subprocess.run(
        [shell, str(trial.bin / "python3"), "-c", "import os; print(os.get_inheritable(9))"],
        env={"PATH": "/usr/bin:/bin"},
        input="",
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    assert "Bad file descriptor" in done.stderr


def _mode(path: Path) -> int:
    return stat.S_IMODE(path.lstat().st_mode)


def test_restore_access_does_not_follow_a_link_as_root_or_below_it(tmp_path: Path) -> None:
    outside = tmp_path / "outside"
    outside.mkdir()
    target = outside / "file"
    target.write_text("x")
    target.chmod(0o444)
    root = tmp_path / "root"
    root.mkdir()
    (root / "to-directory").symlink_to(outside)
    (root / "to-file").symlink_to(target)
    (tmp_path / "link-root").symlink_to(outside)

    workspace.restore_access(root)
    workspace.restore_access(tmp_path / "link-root")

    assert _mode(target) == 0o444
    assert _mode(outside) == 0o755


def test_restore_access_still_opens_a_locked_tree(tmp_path: Path) -> None:
    deepest = tmp_path / "root/a/b"
    deepest.mkdir(parents=True)
    (deepest / "file").write_text("x")
    (deepest / "file").chmod(0)
    for path in (deepest, deepest.parent, deepest.parent.parent):
        path.chmod(0)

    workspace.restore_access(tmp_path / "root")

    assert _mode(deepest / "file") == 0o600
    assert _mode(deepest) == 0o700


def test_restore_access_stays_inside_when_a_directory_is_swapped_for_a_link_mid_walk(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / "file").write_text("x")
    (outside / "file").chmod(0o444)
    root = tmp_path / "root"
    swapped = root / "swapped"
    swapped.mkdir(parents=True)
    (swapped / "file").write_text("x")
    (swapped / "file").chmod(0o400)
    real_fwalk = os.fwalk

    def fwalk_then_swap(*args: Any, **kwargs: Any) -> Iterator[Any]:  # noqa: ANN401
        for entry in real_fwalk(*args, **kwargs):
            # After the listing, before the grants: the moment a path could be redirected.
            if Path(entry[0]) == swapped:
                swapped.rename(root / "moved")
                swapped.symlink_to(outside)
            yield entry

    monkeypatch.setattr(os, "fwalk", fwalk_then_swap)
    workspace.restore_access(root)

    assert _mode(outside / "file") == 0o444
    assert _mode(root / "moved/file") == 0o600


@pytest.mark.parametrize("kind", ["file", "directory"])
def test_restore_access_stays_inside_when_an_entry_becomes_a_link_after_its_stat(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, kind: str
) -> None:
    def make(path: Path) -> None:
        if kind == "file":
            path.write_text("x")
            path.chmod(0o400)
        else:
            path.mkdir()
            path.chmod(0o500)

    target = tmp_path / "outside"
    make(target)
    locked_mode = _mode(target)
    root = tmp_path / "root"
    root.mkdir()
    make(root / "entry")
    real_stat = os.stat
    swapped = False

    def stat_then_swap(path: Any, *args: Any, **kwargs: Any) -> os.stat_result:  # noqa: ANN401
        nonlocal swapped
        found = real_stat(path, *args, **kwargs)
        if path == "entry" and not swapped:
            swapped = True
            (root / "entry").rename(root / "moved")
            (root / "entry").symlink_to(target)
        return found

    monkeypatch.setattr(os, "stat", stat_then_swap)
    workspace.restore_access(root)

    assert swapped
    assert _mode(target) == locked_mode


def test_a_tree_deeper_than_the_descriptor_limit_fails_closed(tmp_path: Path) -> None:
    limit = len(list(Path("/dev/fd").iterdir())) + 8
    depth = limit * 2
    root = tmp_path / "root"
    root.joinpath(*["a"] * depth).mkdir(parents=True)
    locked = root.joinpath(*["a"] * (depth - 3))
    (locked / "file").write_text("x")
    locked.chmod(0)
    soft, hard = resource.getrlimit(resource.RLIMIT_NOFILE)

    def under_the_limit(call: Callable[[], None]) -> None:
        resource.setrlimit(resource.RLIMIT_NOFILE, (limit, hard))
        try:
            call()
        finally:
            resource.setrlimit(resource.RLIMIT_NOFILE, (soft, hard))

    try:
        under_the_limit(lambda: workspace.restore_access(root))
        with pytest.raises(OSError):
            results.files_holding(root, ["secret"])
        under_the_limit(lambda: shutil.rmtree(root, ignore_errors=True))
        assert not results.gone(root)
    finally:
        workspace.restore_access(root)
        shutil.rmtree(root, ignore_errors=True)
    assert results.gone(root)
