"""Building a git fixture into a trial's workspace: the same commits every time, in both arms."""

import json
import shutil
import stat
import subprocess
from pathlib import Path
from typing import TYPE_CHECKING

import pytest

from skills_tooling.evals import fixture, workspace
from skills_tooling.evals.claude_code import ClaudeCode
from skills_tooling.evals.codex import Codex, pinned_executable

if TYPE_CHECKING:
    from collections.abc import Callable

    from skills_tooling.evals.adapter import Adapter, TrialPaths

ROOT = Path(__file__).parents[2]
GIT_FIXTURES = ROOT / "tests/fixtures/evals/git"
ROBIN = "Robin Hale <robin@example.com>"
# 2026-01-01T00:00:00Z, then an hour per commit across main and then the branch.
FIRST = 1767225600
# What a fixture trial adds to the agent's environment (design-16 §6), so the
# agent's git reads no system or global config and takes no optional lock.
AGENT_GIT_ENV = {
    "GIT_OPTIONAL_LOCKS": "0",
    "GIT_CONFIG_NOSYSTEM": "1",
    "GIT_CONFIG_GLOBAL": "/dev/null",
}


def load(
    tmp_path: Path, name: str, change: Callable[[Path], object] | None = None
) -> fixture.Fixture:
    """A shipped fixture, copied into a temporary root and changed there, loaded and valid."""
    directory = tmp_path / "repo/evals/cowsay/fixtures" / name
    shutil.copytree(GIT_FIXTURES / name, directory)
    if change is not None:
        change(directory)
    problems: list[str] = []
    loaded = fixture.load_fixture(tmp_path / "repo", directory, problems)
    assert loaded is not None, problems
    return loaded


def respec(**spec: object) -> Callable[[Path], None]:
    def change(directory: Path) -> None:
        path = directory / "fixture.json"
        path.write_text(json.dumps({**json.loads(path.read_text()), **spec}))

    return change


def built(tmp_path: Path, loaded: fixture.Fixture, run: str = "run") -> TrialPaths:
    trial = workspace.create_trial(tmp_path / "trials", run, "case")
    fixture.build(loaded, trial)
    return trial


def git(trial: TrialPaths, *args: str) -> str:
    result = workspace.git(*args, cwd=trial.workspace)
    assert result.returncode == 0, result.stderr
    return result.stdout


def agent_env(trial: TrialPaths) -> dict[str, str]:
    """The agent's environment in a fixture trial: its homes, its PATH and the three git variables."""
    homes = ClaudeCode(ROOT / "node_modules/.bin/claude").prepare_homes(trial)
    return {**homes.env, **AGENT_GIT_ENV}


def agent_git(trial: TrialPaths, *args: str) -> bytes:
    """Run git as the agent would, from the trial's PATH, and return its raw output."""
    result = subprocess.run(
        ["git", *args],  # noqa: S607 -- the trial's PATH finds its git
        cwd=trial.workspace,
        env=agent_env(trial),
        capture_output=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    return result.stdout


def test_two_builds_give_the_same_commits_trees_and_index(tmp_path: Path) -> None:
    loaded = load(tmp_path, "small-tally")
    first, second = built(tmp_path, loaded, "one"), built(tmp_path, loaded, "two")
    for args in (("rev-parse", "HEAD", "HEAD^{tree}", "main"), ("ls-files", "--stage")):
        assert git(first, *args) == git(second, *args)
    assert git(first, "rev-parse", "HEAD").strip() == "c63fc294563293a6dbacf229d040cc4dafc59f58"


def test_every_commit_is_robin_hale_at_the_fixed_dates(tmp_path: Path) -> None:
    trial = built(tmp_path, load(tmp_path, "small-tally"))
    log = git(trial, "log", "--reverse", "--format=%an <%ae>|%ad|%cn <%ce>|%cd|%s", "--date=raw")
    assert log.splitlines() == [
        f"{ROBIN}|{FIRST} +0000|{ROBIN}|{FIRST} +0000|Add the tally command",
        f"{ROBIN}|{FIRST + 3600} +0000|{ROBIN}|{FIRST + 3600} +0000|Test the totals",
        f"{ROBIN}|{FIRST + 7200} +0000|{ROBIN}|{FIRST + 7200} +0000|Print the average after the total",
    ]
    assert "Eval Harness" not in git(trial, "log", "--all", "--format=%an%n%cn")


def test_the_host_time_zone_changes_nothing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    loaded = load(tmp_path, "small-tally")
    utc = git(built(tmp_path, loaded, "utc"), "rev-parse", "HEAD")
    monkeypatch.setenv("TZ", "Pacific/Chatham")
    assert git(built(tmp_path, loaded, "chatham"), "rev-parse", "HEAD") == utc


def test_main_the_branch_and_each_state_are_in_place(tmp_path: Path) -> None:
    trial = built(tmp_path, load(tmp_path, "small-tally"))
    assert git(trial, "symbolic-ref", "HEAD") == "refs/heads/add-average\n"
    assert git(trial, "rev-list", "--count", "main").strip() == "2"
    assert git(trial, "rev-list", "--count", "main..add-average").strip() == "1"
    assert agent_git(trial, "status", "--porcelain").decode().splitlines() == [
        "M  README.md",
        " M tally.py",
        "?? notes.txt",
    ]
    tree = GIT_FIXTURES / "small-tally/trees/average-wip"
    on_disk = {p.relative_to(trial.workspace).as_posix() for p in trial.workspace.rglob("*")}
    assert {p for p in on_disk if not p.startswith(".git")} == {
        p.relative_to(tree).as_posix() for p in tree.rglob("*")
    }
    for path in tree.rglob("*"):
        assert (trial.workspace / path.relative_to(tree)).read_bytes() == path.read_bytes()


def test_a_branch_with_nothing_ahead_and_a_clean_tree(tmp_path: Path) -> None:
    trial = built(tmp_path, load(tmp_path, "clean-branch"))
    assert git(trial, "symbolic-ref", "HEAD") == "refs/heads/tidy-up\n"
    assert git(trial, "rev-parse", "HEAD") == git(trial, "rev-parse", "main")
    assert agent_git(trial, "status", "--porcelain") == b""


def test_uncommitted_edits_only(tmp_path: Path) -> None:
    trial = built(tmp_path, load(tmp_path, "small-tally", respec(commits=[])))
    assert git(trial, "rev-parse", "HEAD") == git(trial, "rev-parse", "main")
    assert agent_git(trial, "status", "--porcelain").decode().splitlines() == [
        "M  README.md",
        "MM tally.py",
        "M  test_tally.py",
        "?? notes.txt",
    ]


def test_an_executable_path_is_100755_in_git_and_on_disk(tmp_path: Path) -> None:
    trial = built(tmp_path, load(tmp_path, "clean-branch", respec(executable=["greet.py"])))
    assert git(trial, "ls-tree", "HEAD", "greet.py").startswith("100755 blob ")
    assert stat.S_IMODE((trial.workspace / "greet.py").stat().st_mode) == 0o755
    assert agent_git(trial, "status", "--porcelain") == b""


def test_every_other_path_is_100644(tmp_path: Path) -> None:
    trial = built(tmp_path, load(tmp_path, "small-tally"))
    modes = {line.split()[0] for line in git(trial, "ls-files", "--stage").splitlines()}
    listing = git(trial, "ls-tree", "-r", "HEAD").splitlines()
    assert modes == {"100644", "100755"}
    assert [line.split("\t")[1] for line in listing if line.startswith("100755")] == ["tally.py"]
    assert stat.S_IMODE((trial.workspace / "README.md").stat().st_mode) == 0o644


def test_no_ref_log_is_written(tmp_path: Path) -> None:
    trial = built(tmp_path, load(tmp_path, "small-tally"))
    assert not (trial.workspace / ".git/logs").exists()


def test_the_exclude_file_hides_exactly_the_two_skill_directories(tmp_path: Path) -> None:
    trial = built(tmp_path, load(tmp_path, "clean-branch"))
    assert (trial.workspace / ".git/info/exclude").read_bytes() == b"/.claude/\n/.agents/\n"


def test_the_build_leaves_nothing_in_the_trial_tmp(tmp_path: Path) -> None:
    trial = built(tmp_path, load(tmp_path, "small-tally"))
    assert list(trial.tmp.iterdir()) == []


def test_git_status_has_nothing_to_write_to_the_index(tmp_path: Path) -> None:
    trial = built(tmp_path, load(tmp_path, "small-tally"))
    index = trial.workspace / ".git/index"
    before = index.read_bytes(), index.stat().st_mtime_ns
    git(trial, "status", "--porcelain")
    assert (index.read_bytes(), index.stat().st_mtime_ns) == before


def test_an_unedited_crlf_file_is_clean_and_stored_byte_for_byte(tmp_path: Path) -> None:
    crlf = b"one\r\ntwo\r\n"

    def add_crlf(directory: Path) -> None:
        (directory / "trees/start/windows.txt").write_bytes(crlf)

    trial = built(tmp_path, load(tmp_path, "clean-branch", add_crlf))
    assert agent_git(trial, "status", "--porcelain") == b""
    assert agent_git(trial, "cat-file", "blob", "HEAD:windows.txt") == crlf


def test_a_repository_that_is_not_sha1_is_refused(tmp_path: Path) -> None:
    trial = workspace.create_trial(tmp_path / "trials", "run", "case")
    shutil.rmtree(trial.workspace / ".git")
    git(trial, "init", "--quiet", "--object-format=sha256")
    with pytest.raises(RuntimeError, match="sha1"):
        fixture.build(load(tmp_path, "clean-branch"), trial)


@pytest.mark.parametrize(
    "adapter",
    [
        ClaudeCode(ROOT / "node_modules/.bin/claude"),
        Codex(pinned_executable(ROOT)),
        None,
    ],
    ids=["claude", "codex", "baseline"],
)
def test_git_lists_only_the_fixture_edits_with_the_skill_installed_or_not(
    tmp_path: Path, adapter: Adapter | None
) -> None:
    trial = built(tmp_path, load(tmp_path, "small-tally"))
    if adapter is not None:
        assert adapter.install_skill(ROOT / "skills/cowsay", trial.workspace) is not None
    status = agent_git(trial, "status", "--porcelain")
    others = agent_git(trial, "ls-files", "--others", "--exclude-standard")
    assert status.decode().splitlines() == ["M  README.md", " M tally.py", "?? notes.txt"]
    assert others == b"notes.txt\n"
