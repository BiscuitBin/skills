"""Per-trial isolation: the workspace, the homes, the constructed PATH and teardown."""

import os
import signal
import subprocess
import sys
import time
from pathlib import Path

import pytest

from skills_tooling.evals import workspace
from skills_tooling.evals.adapter import PythonCall
from skills_tooling.evals.claude_code import ClaudeCode
from tests.evals.test_runner import TOKEN, fake_root

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
