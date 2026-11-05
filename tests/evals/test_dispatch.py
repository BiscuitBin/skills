"""Planning a manual live-eval dispatch: changed-skill selection, input checks, the secret scan."""

import json
import subprocess
import sys
from typing import TYPE_CHECKING

import pytest

from skills_tooling.evals import dispatch, workspace
from skills_tooling.evals.dispatch import DispatchError, changed_paths, plan, select_changed

if TYPE_CHECKING:
    from pathlib import Path

SUITES = ["cowsay", "haiku"]
TOKEN = "sk-ant-oat01-fake-dispatch-test-token"
API_KEY = "sk-proj-fake-dispatch-test-api-key"


@pytest.mark.parametrize(
    ("paths", "selected"),
    [
        (["skills/cowsay/SKILL.md"], ["cowsay"]),
        (["evals/haiku/evals.json"], ["haiku"]),
        (["skills/haiku/scripts/x.py", "skills/cowsay/README.md"], ["cowsay", "haiku"]),
        (["src/skills_tooling/evals/grader.py"], SUITES),
        (["src/skills_tooling/evals/codex.py"], SUITES),
        (["package.json"], SUITES),
        (["package-lock.json"], SUITES),
        ([".node-version"], SUITES),
        (["docs/reference/evals.md", "README.md", "src/skills_tooling/validator.py"], []),
        # A skill with no eval suite, or one deleted on the branch, is never selected.
        (["skills/no-suite/SKILL.md", "evals/gone/evals.json"], []),
        # Only a path under skills/ or evals/ names a skill.
        (["docs/skills/cowsay.md", "skills"], []),
        ([], []),
    ],
)
def test_changed_paths_select_their_skill_or_every_suite(
    paths: list[str], selected: list[str]
) -> None:
    assert select_changed(paths, SUITES) == selected


def suite(root: Path, name: str) -> None:
    (root / "evals" / name).mkdir(parents=True)
    (root / "evals" / name / "evals.json").write_text("{}")
    (root / "skills" / name).mkdir(parents=True)
    (root / "skills" / name / "SKILL.md").write_text(f"# {name}\n")


def git(root: Path, *args: str) -> None:
    result = workspace.git(*args, cwd=root)
    assert result.returncode == 0, result.stderr


def repo(tmp_path: Path) -> Path:
    """A repository whose main has cowsay and haiku, checked out on a branch off main."""
    root = tmp_path / "repo"
    root.mkdir()
    git(root, "init", "--quiet", "--initial-branch=main")
    suite(root, "cowsay")
    suite(root, "haiku")
    git(root, "add", ".")
    git(root, "commit", "--quiet", "-m", "main")
    git(root, "switch", "--quiet", "-c", "work")
    return root


def test_a_branch_selects_what_it_changed_since_the_merge_base(tmp_path: Path) -> None:
    root = repo(tmp_path)
    assert dispatch.changed(root, "main") == []
    (root / "skills/haiku/SKILL.md").write_text("# haiku, edited\n")
    git(root, "commit", "--quiet", "-am", "edit haiku")
    # main moves on after the branch: its change is not the branch's.
    git(root, "switch", "--quiet", "main")
    (root / "skills/cowsay/SKILL.md").write_text("# cowsay, edited on main\n")
    git(root, "commit", "--quiet", "-am", "edit cowsay on main")
    git(root, "switch", "--quiet", "work")
    assert dispatch.changed(root, "main") == ["haiku"]
    # Uncommitted and untracked files count too, so it works before a commit.
    (root / "evals/cowsay/notes.txt").write_text("new\n")
    assert dispatch.changed(root, "main") == ["cowsay", "haiku"]


def test_a_deleted_suite_is_not_selected(tmp_path: Path) -> None:
    root = repo(tmp_path)
    git(root, "rm", "--quiet", "-r", "evals/haiku", "skills/haiku")
    git(root, "commit", "--quiet", "-m", "drop haiku")
    assert "skills/haiku/SKILL.md" in changed_paths(root, "main")
    assert dispatch.changed(root, "main") == []


def test_a_missing_base_is_an_error_not_an_empty_selection(tmp_path: Path) -> None:
    root = repo(tmp_path)
    with pytest.raises(DispatchError, match="no-such-ref"):
        changed_paths(root, "no-such-ref")


def plan_for(root: Path, **overrides: object) -> dispatch.Plan:
    inputs: dict[str, object] = {
        "skills": "cowsay",
        "agents": "both",
        "trials": "1",
        "baseline": "false",
        "have_claude": True,
        "have_openai": True,
        "root": root,
        "base": "main",
        **overrides,
    }
    return plan(**inputs)  # type: ignore[arg-type]


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("skills", "cowsay; rm -rf /"),
        ("skills", "$(id)"),
        ("skills", "../cowsay"),
        ("skills", "no-such-skill"),
        ("skills", ""),
        ("agents", "pi"),
        ("agents", "claude codex"),
        ("trials", "0"),
        ("trials", "6"),
        ("trials", "1.5"),
        ("trials", "+1"),
        ("trials", " 1"),
        ("trials", ""),
        ("baseline", "yes"),
    ],
)
def test_invalid_inputs_are_refused(tmp_path: Path, field: str, value: str) -> None:
    root = repo(tmp_path)
    with pytest.raises(DispatchError):
        plan_for(root, **{field: value})


@pytest.mark.parametrize(
    ("have_claude", "have_openai", "runs", "grade", "notices"),
    [
        (False, False, [], False, ["Claude Code skipped", "Codex skipped"]),
        (True, False, [("cowsay", "claude")], True, ["Codex skipped"]),
        (False, True, [("cowsay", "codex")], False, ["Claude Code skipped", "Grading skipped"]),
        (True, True, [("cowsay", "claude"), ("cowsay", "codex")], True, []),
    ],
)
def test_an_agent_without_its_secret_is_skipped_with_a_notice(  # noqa: PLR0913, PLR0917 -- one row of the matrix
    tmp_path: Path,
    have_claude: bool,
    have_openai: bool,
    runs: list[tuple[str, str]],
    grade: bool,
    notices: list[str],
) -> None:
    planned = plan_for(repo(tmp_path), have_claude=have_claude, have_openai=have_openai)
    assert planned.runs == runs
    assert planned.grade is grade
    assert [n.split(":")[0] for n in planned.notices] == notices
    assert ("--no-grader" in planned.flags) is not grade


def test_the_flags_carry_the_trials_and_the_baseline(tmp_path: Path) -> None:
    planned = plan_for(repo(tmp_path), trials="3", baseline="true", agents="codex")
    assert planned.runs == [("cowsay", "codex")]
    assert planned.flags == ["--trials", "3", "--baseline"]


def test_changed_with_nothing_changed_selects_nothing_and_says_so(tmp_path: Path) -> None:
    planned = plan_for(repo(tmp_path), skills="changed")
    assert planned.runs == []
    assert any("Nothing changed since main" in n for n in planned.notices)


def run_dispatch(
    *args: str, env: dict[str, str] | None = None
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", "skills_tooling.evals.dispatch", *args],
        capture_output=True,
        text=True,
        env=env,
        check=False,
    )


def test_the_plan_command_writes_runs_flags_and_a_summary(tmp_path: Path) -> None:
    root = repo(tmp_path)
    out = root / "eval-results/dispatch"
    result = run_dispatch(
        "plan",
        *("--skills", "changed", "--agents", "both", "--trials", "2", "--baseline", "false"),
        *("--has-claude", "false", "--has-openai", "true", "--base", "main"),
        *("--out", str(out), "--root", str(root)),
    )
    assert result.returncode == 0, result.stderr
    assert (out / "runs.txt").read_text() == ""
    assert (out / "flags").read_text() == "--trials 2 --no-grader\n"
    summary = (out / "summary.md").read_text()
    assert "Nothing changed since main" in summary
    assert "Claude Code skipped" in summary
    (root / "skills/cowsay/SKILL.md").write_text("# edited\n")
    again = run_dispatch(
        "plan",
        *("--skills", "changed", "--agents", "both", "--trials", "2", "--baseline", "false"),
        *("--has-claude", "true", "--has-openai", "true", "--base", "main"),
        *("--out", str(out), "--root", str(root)),
    )
    assert again.returncode == 0, again.stderr
    assert (out / "runs.txt").read_text() == "cowsay claude\ncowsay codex\n"


def test_the_plan_command_refuses_bad_input_and_writes_nothing(tmp_path: Path) -> None:
    root = repo(tmp_path)
    out = root / "eval-results/dispatch"
    result = run_dispatch(
        "plan",
        *("--skills", "$(id)", "--agents", "both", "--trials", "1", "--baseline", "false"),
        *("--has-claude", "true", "--has-openai", "true"),
        *("--out", str(out), "--root", str(root)),
    )
    assert result.returncode == 2
    assert "skill" in result.stderr
    assert not out.exists()


def test_the_plan_command_writes_only_under_eval_results(tmp_path: Path) -> None:
    root = repo(tmp_path)
    result = run_dispatch(
        "plan",
        *("--skills", "cowsay", "--agents", "both", "--trials", "1", "--baseline", "false"),
        *("--has-claude", "true", "--has-openai", "true"),
        *("--out", str(tmp_path / "elsewhere"), "--root", str(root)),
    )
    assert result.returncode == 2
    assert not (tmp_path / "elsewhere").exists()


def test_runs_lists_the_finished_runs_of_one_skill(tmp_path: Path) -> None:
    root = tmp_path
    for run_id, skill, complete in [
        ("20261104T000000Z-aaaa", "cowsay", True),
        ("20261104T000001Z-bbbb", "haiku", True),
        ("20261104T000002Z-cccc", "cowsay", False),
    ]:
        directory = root / "eval-results" / run_id
        directory.mkdir(parents=True)
        (directory / "results.json").write_text(json.dumps({"skill": skill}))
        if complete:
            (directory / "benchmark.json").write_text("{}")
    assert dispatch.finished_runs(root, "cowsay") == ["20261104T000000Z-aaaa"]


def results_dir(tmp_path: Path) -> Path:
    directory = tmp_path / "eval-results"
    (directory / "run/transcripts").mkdir(parents=True)
    (directory / "run/results.json").write_text('{"ok": true}\n')
    return directory


def test_the_scan_finds_a_secret_in_a_file_and_never_prints_it(tmp_path: Path) -> None:
    directory = results_dir(tmp_path)
    leaked = directory / "run/transcripts/case.jsonl"
    leaked.write_text(f"the token is {API_KEY}\n")
    env = {"OPENAI_API_KEY": API_KEY, "CLAUDE_CODE_OAUTH_TOKEN": TOKEN}
    result = run_dispatch("scan", str(directory), env=env)
    assert result.returncode == 1
    assert "run/transcripts/case.jsonl" in result.stdout + result.stderr
    assert API_KEY not in result.stdout + result.stderr
    # The scan reports; it never deletes the evidence.
    assert leaked.is_file()


def test_the_scan_finds_a_secret_in_a_path_and_prints_it_scrubbed(tmp_path: Path) -> None:
    directory = results_dir(tmp_path)
    (directory / f"run/{TOKEN}.txt").write_text("nothing here\n")
    result = run_dispatch("scan", str(directory), env={"CLAUDE_CODE_OAUTH_TOKEN": TOKEN})
    assert result.returncode == 1
    assert "[REDACTED].txt" in result.stdout + result.stderr
    assert TOKEN not in result.stdout + result.stderr


def test_the_scan_reads_the_codex_login(tmp_path: Path) -> None:
    directory = results_dir(tmp_path)
    home = tmp_path / "codex-home"
    home.mkdir()
    (home / "auth.json").write_text(json.dumps({"auth_mode": "apikey", "OPENAI_API_KEY": API_KEY}))
    (directory / "run/transcripts/case.jsonl").write_text(API_KEY)
    result = run_dispatch("scan", str(directory), env={"CODEX_HOME": str(home)})
    assert result.returncode == 1
    assert API_KEY not in result.stdout + result.stderr


def test_a_clean_scan_passes(tmp_path: Path) -> None:
    directory = results_dir(tmp_path)
    env = {"OPENAI_API_KEY": API_KEY, "CLAUDE_CODE_OAUTH_TOKEN": TOKEN}
    result = run_dispatch("scan", str(directory), env=env)
    assert result.returncode == 0, result.stderr
    assert dispatch.SCANNED_ENV == ("CLAUDE_CODE_OAUTH_TOKEN", "OPENAI_API_KEY")
