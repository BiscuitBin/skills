"""Per-trial isolation: the workspace, the homes, the constructed PATH and teardown."""

import os
import subprocess
from pathlib import Path

import pytest

from skills_tooling.evals import workspace
from skills_tooling.evals.claude_code import ClaudeCode

ROOT = Path(__file__).parents[2]


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


def test_teardown_removes_homes_and_keeps_the_workspace(tmp_path: Path) -> None:
    trial = workspace.create_trial(tmp_path, "run", "case")
    (trial.home / ".claude").mkdir()
    workspace.teardown(trial)
    assert [p.name for p in trial.root.iterdir()] == ["workspace"]
