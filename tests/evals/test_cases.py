"""The eval case schema: what loads, and what is rejected with a reason."""

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import TYPE_CHECKING, Any

import pytest

from skills_tooling.evals.cases import CaseError, load_suite, validate_all
from skills_tooling.evals.fixture import case_clashes, load_fixture
from skills_tooling.evals.grader import invocation_mentions

if TYPE_CHECKING:
    from collections.abc import Callable, Mapping

ROOT = Path(__file__).parents[2]
GIT_FIXTURES = ROOT / "tests/fixtures/evals/git"


def behaviour(**overrides: object) -> dict[str, Any]:
    case: dict[str, Any] = {
        "id": "behaviour-hi",
        "kind": "behaviour",
        "prompt": "Have a cow say hi",
        "should_trigger": True,
        "expected_output": "A cow saying hi",
        "files": [],
        "assertions": [
            {"type": "skill_triggered"},
            {"type": "script_ran", "script": "scripts/cowsay.py", "args": ["--", "hi"]},
            {
                "type": "final_contains_script_output",
                "script": "scripts/cowsay.py",
                "args": ["--", "hi"],
            },
            {"type": "output_contains", "value": "(oo)"},
            {"type": "output_matches", "pattern": r"<\s*hi\s*>"},
        ],
    }
    case.update(overrides)
    return case


def trigger(case_id: str = "trigger-cow", *, should: bool = True) -> dict[str, Any]:
    return {
        "id": case_id,
        "kind": "trigger",
        "prompt": "Make a cow talk",
        "should_trigger": should,
    }


def write_suite(root: Path, suite: dict[str, Any], directory: str = "cowsay") -> Path:
    skill = root / "skills/cowsay/scripts"
    skill.mkdir(parents=True, exist_ok=True)
    (skill / "cowsay.py").write_text("print('moo')\n")
    (skill.parent / "SKILL.md").write_text("---\nname: cowsay\ndescription: d\n---\n")
    path = root / "evals" / directory / "evals.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(suite))
    return path


def errors(root: Path, suite: dict[str, Any], directory: str = "cowsay") -> list[str]:
    write_suite(root, suite, directory)
    with pytest.raises(CaseError) as raised:
        load_suite(root, directory)
    return raised.value.problems


def test_cowsay_suite_loads_with_both_kinds() -> None:
    suite = load_suite(ROOT, "cowsay")
    kinds = [(case.kind, case.should_trigger) for case in suite.cases]
    assert kinds.count(("trigger", True)) >= 3
    assert kinds.count(("trigger", False)) >= 3
    assert kinds.count(("behaviour", True)) >= 2
    assert any(
        a.type == "final_contains_script_output" for case in suite.cases for a in case.assertions
    )


def test_a_valid_suite_loads(tmp_path: Path) -> None:
    write_suite(tmp_path, {"skill_name": "cowsay", "evals": [behaviour(), trigger()]})
    suite = load_suite(tmp_path, "cowsay")
    assert [case.id for case in suite.cases] == ["behaviour-hi", "trigger-cow"]
    assert suite.cases[0].assertions[1].args == ("--", "hi")
    assert suite.cases[0].expectations == ()


def test_expectations_load_blinded_unless_they_need_the_transcript(tmp_path: Path) -> None:
    rubric = ["A cow appears", {"text": "The script ran once", "needs_transcript": True}]
    write_suite(tmp_path, {"skill_name": "cowsay", "evals": [behaviour(expectations=rubric)]})
    [case] = load_suite(tmp_path, "cowsay").cases
    assert [(e.text, e.blinded) for e in case.expectations] == [
        ("A cow appears", True),
        ("The script ran once", False),
    ]


def test_assertions_are_classed_as_skill_use_or_outcome(tmp_path: Path) -> None:
    write_suite(tmp_path, {"skill_name": "cowsay", "evals": [behaviour()]})
    [case] = load_suite(tmp_path, "cowsay").cases
    assert [(a.type, a.skill_use) for a in case.assertions] == [
        ("skill_triggered", True),
        ("script_ran", True),
        ("final_contains_script_output", False),
        ("output_contains", False),
        ("output_matches", False),
    ]


@pytest.mark.parametrize(
    ("case", "expected"),
    [
        (
            behaviour(files=["input.txt"]),
            (
                "input files are staged with a fixture (see `fixture`); "
                "remove `files` or leave it empty"
            ),
        ),
        (behaviour(fixture="Small_Tally"), "fixture must be a lowercase slug"),
        (behaviour(fixture=["small-tally"]), "fixture must be a lowercase slug"),
        (
            behaviour(fixture="ghost"),
            "fixture 'ghost' has no directory evals/cowsay/fixtures/ghost/",
        ),
        (behaviour(expectations="rubric"), "expectations must be a list"),
        (behaviour(expectations=[""]), "expectation text must be a nonempty string"),
        (behaviour(expectations=["  "]), "expectation text must be a nonempty string"),
        (behaviour(expectations=[{"text": ""}]), "expectation text must be a nonempty string"),
        (behaviour(expectations=[3]), "an expectation must be a string or an object"),
        (behaviour(expectations=["Moo", "Moo"]), "duplicate expectation 'Moo'"),
        (
            behaviour(expectations=["Moo", {"text": "Moo", "needs_transcript": True}]),
            "duplicate expectation 'Moo'",
        ),
        (
            behaviour(expectations=[{"text": "Moo", "needs_transcript": False}]),
            "needs_transcript must be true",
        ),
        (behaviour(expectations=[{"text": "Moo", "weight": 2}]), "unknown key 'weight'"),
        (
            {**trigger(), "expectations": ["A cow appears"]},
            "expectations are allowed on behaviour cases only",
        ),
        (
            {**trigger(), "assertions": [{"type": "output_contains", "value": "x"}]},
            "assertions are allowed on behaviour cases only",
        ),
        (behaviour(kind="vibes"), "kind must be 'trigger' or 'behaviour'"),
        (behaviour(should_trigger=False), "behaviour cases need should_trigger: true"),
        (behaviour(assertions=[]), "behaviour cases need at least one assertion"),
        (behaviour(id="Bad Id"), "id must be a lowercase slug"),
        ({**trigger(), "should_trigger": "yes"}, "should_trigger must be true or false"),
        (
            {k: v for k, v in trigger().items() if k != "should_trigger"},
            "missing 'should_trigger'",
        ),
        (behaviour(assertions=[{"type": "vibes"}]), "unknown assertion type 'vibes'"),
        (behaviour(assertions=[{"type": ["skill_triggered"]}]), "unknown assertion type"),
        (behaviour(kind=["trigger"]), "kind must be 'trigger' or 'behaviour'"),
        (
            behaviour(assertions=[{"type": "output_contains", "value": "x", "extra": 1}]),
            "unknown key 'extra'",
        ),
        (behaviour(assertions=[{"type": "output_matches", "pattern": "("}]), "does not compile"),
        (behaviour(assertions=[{"type": "output_contains"}]), "missing 'value'"),
        (
            behaviour(assertions=[{"type": "script_ran", "script": "../../../etc/passwd"}]),
            "must be a file inside the skill",
        ),
        (
            behaviour(assertions=[{"type": "script_ran", "script": "scripts/missing.py"}]),
            "must be a file inside the skill",
        ),
        (
            behaviour(
                assertions=[
                    {"type": "final_contains_script_output", "script": "scripts/cowsay.py"}
                ]
            ),
            "missing 'args'",
        ),
        (
            behaviour(
                assertions=[{"type": "script_ran", "script": "scripts/cowsay.py", "args": [1]}]
            ),
            "args must be a list of strings",
        ),
        (
            behaviour(
                assertions=[
                    {
                        "type": "final_contains_script_output",
                        "script": "scripts/cowsay.py",
                        "args": None,
                    }
                ]
            ),
            "args must be a list of strings",
        ),
    ],
)
def test_invalid_cases_are_rejected_with_a_reason(
    tmp_path: Path, case: dict[str, Any], expected: str
) -> None:
    problems = errors(tmp_path, {"skill_name": "cowsay", "evals": [case]})
    assert any(expected in problem for problem in problems), problems


def test_duplicate_ids_and_unknown_top_level_keys_are_rejected(tmp_path: Path) -> None:
    problems = errors(
        tmp_path, {"skill_name": "cowsay", "evals": [trigger(), trigger()], "notes": "x"}
    )
    assert any("duplicate id 'trigger-cow'" in p for p in problems)
    assert any("unknown key 'notes'" in p for p in problems)


def test_skill_name_must_match_the_directory_and_a_shipped_skill(tmp_path: Path) -> None:
    assert any(
        "must match its directory" in p
        for p in errors(tmp_path, {"skill_name": "other", "evals": [trigger()]})
    )
    assert any(
        "no shipped skill skills/ghost" in p
        for p in errors(tmp_path, {"skill_name": "ghost", "evals": [trigger()]}, "ghost")
    )


def test_validate_all_reports_every_suite(tmp_path: Path) -> None:
    write_suite(tmp_path, {"skill_name": "cowsay", "evals": [trigger()]})
    assert validate_all(tmp_path) == []
    write_suite(tmp_path, {"skill_name": "cowsay", "evals": []}, "cowsay")
    assert validate_all(tmp_path) == ["evals/cowsay/evals.json: evals must be a nonempty list"]


def test_validate_command_checks_the_repo_suites_without_an_agent(tmp_path: Path) -> None:
    shutil.copytree(ROOT / "evals", tmp_path / "evals")
    shutil.copytree(ROOT / "skills", tmp_path / "skills")
    result = subprocess.run(
        [sys.executable, "-m", "skills_tooling.evals", "validate", "--root", str(tmp_path)],
        capture_output=True,
        text=True,
        check=False,
    )
    assert (result.returncode, result.stderr) == (0, "")
    count = len(list((tmp_path / "evals").glob("*/evals.json")))
    assert f"{count} eval suite{'' if count == 1 else 's'} valid." in result.stdout
    (tmp_path / "evals/cowsay/evals.json").write_text("{")
    result = subprocess.run(
        [sys.executable, "-m", "skills_tooling.evals", "validate", "--root", str(tmp_path)],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 1
    assert "evals/cowsay/evals.json: not valid JSON" in result.stderr


def test_a_placeholder_case_loads_marked_as_a_placeholder(tmp_path: Path) -> None:
    write_suite(
        tmp_path,
        {"skill_name": "cowsay", "evals": [{**trigger(), "placeholder": True}, behaviour()]},
    )
    assert [case.placeholder for case in load_suite(tmp_path, "cowsay").cases] == [True, False]


def test_placeholder_false_is_rejected(tmp_path: Path) -> None:
    problems = errors(tmp_path, {"skill_name": "cowsay", "evals": [behaviour(placeholder=False)]})
    assert any("placeholder must be true, or left out" in p for p in problems), problems


@pytest.mark.parametrize("kind", ["trigger", "behaviour"])
def test_a_case_invoked_by_name_loads_marked(tmp_path: Path, kind: str) -> None:
    case = behaviour() if kind == "behaviour" else trigger()
    write_suite(
        tmp_path,
        {"skill_name": "cowsay", "evals": [{**case, "by_name": True}, trigger("trigger-plain")]},
    )
    assert [case.by_name for case in load_suite(tmp_path, "cowsay").cases] == [True, False]


def by_name(prompt: str) -> dict[str, Any]:
    return {**trigger(), "by_name": True, "prompt": prompt}


@pytest.mark.parametrize(
    ("case", "expected"),
    [
        ({**trigger(), "by_name": False}, "by_name must be true, or left out"),
        ({**trigger(), "by_name": "yes"}, "by_name must be true, or left out"),
        (
            {**trigger(should=False), "by_name": True},
            "by_name cases need should_trigger: true",
        ),
        (by_name("/cowsay Make a cow talk"), "must not start with / or $"),
        (by_name("$cowsay:cowsay Make a cow talk"), "must not start with / or $"),
        (by_name("  /tmp/cow.txt needs a cow"), "must not start with / or $"),
        (by_name("$HOME needs a cow"), "must not start with / or $"),
        (
            by_name("Make a cow talk, as $cowsay:cowsay would"),
            "holds an invocation of the skill ('$cowsay:cowsay')",
        ),
        (
            by_name("Make a cow talk with /cowsay."),
            "holds an invocation of the skill ('/cowsay')",
        ),
        (
            by_name("Make a cow talk with `/COWSAY`"),
            "holds an invocation of the skill ('/COWSAY')",
        ),
    ],
)
def test_a_case_invoked_by_name_is_rejected_with_a_reason(
    tmp_path: Path, case: dict[str, Any], expected: str
) -> None:
    problems = errors(tmp_path, {"skill_name": "cowsay", "evals": [case]})
    assert any(expected in problem for problem in problems), problems


@pytest.mark.parametrize(
    "prompt",
    [
        "Make a cow read src/app.py",
        "Make a cow read src/cowsay/x.py",
        "Make a cow read docs/cowsay.md",
        "Make a cow read ~/cowsay",
        "Make a cow say $HOME",
    ],
)
def test_a_by_name_prompt_may_hold_paths_and_variables(tmp_path: Path, prompt: str) -> None:
    write_suite(tmp_path, {"skill_name": "cowsay", "evals": [by_name(prompt)]})
    [case] = load_suite(tmp_path, "cowsay").cases
    assert (case.prompt, case.by_name) == (prompt, True)


def test_an_unmarked_case_may_invoke_the_skill_in_its_prompt(tmp_path: Path) -> None:
    case = {**trigger(), "prompt": "$cowsay:cowsay Make a cow talk"}
    write_suite(tmp_path, {"skill_name": "cowsay", "evals": [case]})
    [loaded] = load_suite(tmp_path, "cowsay").cases
    assert (loaded.prompt, loaded.by_name) == ("$cowsay:cowsay Make a cow talk", False)


@pytest.mark.parametrize(
    ("text", "found"),
    [
        ("/cowsay hi", ["/cowsay"]),
        ("Run `/cowsay` on it", ["/cowsay"]),
        ("Use $cowsay now", ["$cowsay"]),
        ("Ask $cowsay:cowsay, then stop", ["$cowsay:cowsay"]),
        ("Ask $kit.v2:cowsay", ["$kit.v2:cowsay"]),
        ("It ends with /cowsay.", ["/cowsay"]),
        ("Say /CowSay, then $COWSAY", ["/CowSay", "$COWSAY"]),
        ("src/cowsay/x.py docs/cowsay.md ~/cowsay /cowsay/notes.txt /cowsay-extra", []),
        ("src/app.py $HOME /cowsays $cowsay_x /cowsay.py a:/cowsay x$cowsay $$cowsay", []),
    ],
)
def test_an_invocation_is_the_skills_name_after_a_slash_or_dollar_as_a_whole_token(
    text: str, found: list[str]
) -> None:
    assert invocation_mentions(text, "cowsay") == found


def run_command(root: Path, *args: str) -> subprocess.CompletedProcess[str]:
    env = {k: v for k, v in os.environ.items() if k != "CLAUDE_CODE_OAUTH_TOKEN"}
    return subprocess.run(
        [sys.executable, "-m", "skills_tooling.evals", *args, "--root", str(root)],
        capture_output=True,
        text=True,
        env=env,
        check=False,
    )


PLACEHOLDER_SUITE = {
    "skill_name": "cowsay",
    "evals": [
        {**trigger("trigger-todo"), "placeholder": True},
        behaviour(placeholder=True, id="behaviour-todo"),
        trigger("trigger-written"),
    ],
}


@pytest.mark.parametrize("dry_run", [True, False])
def test_eval_refuses_placeholder_cases_before_any_agent_call(
    tmp_path: Path, *, dry_run: bool
) -> None:
    write_suite(tmp_path, PLACEHOLDER_SUITE)
    flags = ["--dry-run"] if dry_run else []
    result = run_command(tmp_path, "run", "cowsay", "--agent", "claude", *flags)
    assert result.returncode == 2
    assert "UNWRITTEN cowsay/trigger-todo" in result.stderr
    assert "UNWRITTEN cowsay/behaviour-todo" in result.stderr
    assert "trigger-written" not in result.stderr
    # Refused before the credential check, so no agent could have started.
    assert "CLAUDE_CODE_OAUTH_TOKEN" not in result.stderr
    assert not (tmp_path / "eval-results").exists()


def test_eval_runs_written_cases_picked_out_of_a_placeholder_suite(tmp_path: Path) -> None:
    write_suite(tmp_path, PLACEHOLDER_SUITE)
    result = run_command(
        tmp_path, "run", "cowsay", "--agent", "claude", "--case", "trigger-written", "--dry-run"
    )
    assert result.returncode == 0, result.stderr
    assert "skill arm: 1 agent calls" in result.stdout


def list_in_marketplace(root: Path, *names: str) -> None:
    (root / ".claude-plugin").mkdir(exist_ok=True)
    plugins = [{"name": name, "source": f"./skills/{name}"} for name in names]
    (root / ".claude-plugin/marketplace.json").write_text(json.dumps({"plugins": plugins}))


def test_validate_warns_when_a_distributed_skill_has_only_placeholder_cases(
    tmp_path: Path,
) -> None:
    only_placeholders = {"skill_name": "cowsay", "evals": PLACEHOLDER_SUITE["evals"][:2]}
    write_suite(tmp_path, only_placeholders)
    list_in_marketplace(tmp_path, "cowsay")
    result = run_command(tmp_path, "validate")
    assert result.returncode == 0, result.stderr
    assert (
        "warning: cowsay is in .claude-plugin/marketplace.json but "
        "evals/cowsay/evals.json has only placeholder cases"
    ) in result.stderr


def test_validate_warns_when_a_distributed_skill_still_has_some_placeholder_cases(
    tmp_path: Path,
) -> None:
    write_suite(tmp_path, PLACEHOLDER_SUITE)
    list_in_marketplace(tmp_path, "cowsay")
    result = run_command(tmp_path, "validate")
    assert result.returncode == 0, result.stderr
    assert (
        "warning: cowsay is in .claude-plugin/marketplace.json but evals/cowsay/evals.json "
        "still has placeholder cases: trigger-todo, behaviour-todo"
    ) in result.stderr


@pytest.mark.parametrize("listed", [True, False])
def test_validate_is_quiet_about_written_or_undistributed_suites(
    tmp_path: Path, *, listed: bool
) -> None:
    written = {**PLACEHOLDER_SUITE, "evals": [trigger("trigger-written")]}
    write_suite(tmp_path, written if listed else PLACEHOLDER_SUITE)
    if listed:
        list_in_marketplace(tmp_path, "cowsay")
    result = run_command(tmp_path, "validate")
    assert (result.returncode, result.stderr) == (0, "")


def add_fixture(root: Path, name: str = "clean-branch", source: str | None = None) -> Path:
    """Copy a shipped git fixture into root's evals/cowsay/fixtures/<name>/."""
    directory = root / "evals/cowsay/fixtures" / name
    shutil.copytree(GIT_FIXTURES / (source or name), directory)
    return directory


@pytest.mark.parametrize("kind", ["behaviour", "trigger"])
def test_a_case_names_a_fixture_beside_empty_files(tmp_path: Path, kind: str) -> None:
    add_fixture(tmp_path, "small-tally")
    case = behaviour() if kind == "behaviour" else trigger()
    write_suite(tmp_path, {"skill_name": "cowsay", "evals": [{**case, "fixture": "small-tally"}]})
    [loaded] = load_suite(tmp_path, "cowsay").cases
    assert loaded.fixture is not None
    assert loaded.fixture.name == "small-tally"
    assert loaded.fixture.path == tmp_path / "evals/cowsay/fixtures/small-tally"
    assert loaded.fixture.branch == "add-average"
    assert [(c.tree, c.message) for c in loaded.fixture.main] == [
        ("start", "Add the tally command"),
        ("tested", "Test the totals"),
    ]
    assert [(c.tree, c.message) for c in loaded.fixture.commits] == [
        ("average", "Print the average after the total")
    ]
    assert (loaded.fixture.staged, loaded.fixture.worktree) == ("average-staged", "average-wip")
    assert loaded.fixture.executable == frozenset({"tally.py"})


def test_a_case_without_a_fixture_has_none(tmp_path: Path) -> None:
    write_suite(tmp_path, {"skill_name": "cowsay", "evals": [trigger()]})
    [loaded] = load_suite(tmp_path, "cowsay").cases
    assert loaded.fixture is None


@pytest.mark.parametrize("name", sorted(p.name for p in GIT_FIXTURES.iterdir()))
def test_every_shipped_git_fixture_loads(tmp_path: Path, name: str) -> None:
    add_fixture(tmp_path, name)
    write_suite(tmp_path, {"skill_name": "cowsay", "evals": [{**trigger(), "fixture": name}]})
    [loaded] = load_suite(tmp_path, "cowsay").cases
    assert loaded.fixture is not None
    assert loaded.fixture.name == name


def fixture_problems(
    root: Path,
    change: Callable[[Path], object] | None = None,
    *,
    spec: Mapping[str, object] | None = None,
    drop: tuple[str, ...] = (),
) -> list[str]:
    """The load problems of clean-branch as fixture f, with spec merged into its fixture.json.

    drop leaves keys out of fixture.json, and change, if given, then edits the directory.
    """
    directory = add_fixture(root, "f", "clean-branch")
    path = directory / "fixture.json"
    data = {k: v for k, v in json.loads(path.read_text()).items() if k not in drop}
    path.write_text(json.dumps({**data, **(spec or {})}))
    if change is not None:
        change(directory)
    return errors(root, {"skill_name": "cowsay", "evals": [{**trigger(), "fixture": "f"}]})


def commit(
    tree: object = "start", message: object = "Add the greeting script"
) -> dict[str, object]:
    return {"tree": tree, "message": message}


@pytest.mark.parametrize(
    ("spec", "expected"),
    [
        ({"colour": "red"}, "fixtures/f/fixture.json: unknown key 'colour'"),
        ({"main": []}, "main must be a nonempty list of commits"),
        ({"main": "start"}, "main must be a nonempty list of commits"),
        ({"commits": "start"}, "commits must be a list of commits"),
        ({"main": [5]}, "main[0]: a commit must be an object"),
        ({"main": [{**commit(), "author": "x"}]}, "main[0]: unknown key 'author'"),
        ({"main": [commit("missing")]}, "main[0]: tree 'missing' is not a directory under trees/"),
        (
            {"main": [commit("../trees")]},
            "main[0]: tree '../trees' is not a directory under trees/",
        ),
        ({"commits": [commit("gone")]}, "commits[0]: tree 'gone' is not a directory under trees/"),
        ({"main": [{"tree": "start"}]}, "main[0]: message must be"),
        ({"main": [commit(message="")]}, "main[0]: message must be"),
        ({"main": [commit(message="  ")]}, "main[0]: message must be"),
        ({"main": [commit(message=5)]}, "main[0]: message must be"),
        ({"main": [commit(message="Add it\n\nThen more")]}, "main[0]: message must be"),
        ({"main": [commit(message="Add it\n  \nThen more")]}, "main[0]: message must be"),
        ({"main": [commit(message=" Add it")]}, "main[0]: message must be"),
        ({"main": [commit(message="Add it\n")]}, "main[0]: message must be"),
        ({"staged": "missing"}, "staged 'missing' is not a directory under trees/"),
        ({"worktree": 3}, "worktree 3 is not a directory under trees/"),
        ({"worktree": {}}, "worktree {} is not a directory under trees/"),
        ({"staged": ["start"]}, "staged ['start'] is not a directory under trees/"),
        ({"main": [commit(["start"])]}, "main[0]: tree ['start'] is not a directory under trees/"),
        ({"commits": [commit({})]}, "commits[0]: tree {} is not a directory under trees/"),
        ({"executable": "greet.py"}, "executable must be a list of paths"),
        ({"executable": ["nope.py"]}, "executable 'nope.py' is not a file in any tree"),
        (
            {"executable": ["start/greet.py"]},
            "executable 'start/greet.py' is not a file in any tree",
        ),
    ],
)
def test_an_invalid_fixture_json_is_rejected_with_a_reason(
    tmp_path: Path, spec: dict[str, object], expected: str
) -> None:
    problems = fixture_problems(tmp_path, spec=spec)
    assert any(expected in problem for problem in problems), problems


@pytest.mark.parametrize(
    ("spec", "expected"),
    [
        ({"worktree": "empty"}, "fixture.json: worktree 'empty' is not a directory under trees/"),
        ({"main": [commit("empty")]}, "main[0]: tree 'empty' is not a directory under trees/"),
    ],
    ids=["worktree", "commit"],
)
def test_an_empty_tree_is_rejected_as_a_checkout_would_be(
    tmp_path: Path, spec: dict[str, object], expected: str
) -> None:
    # Git keeps no empty directory, so a checkout has no trees/empty/ at all.
    problems = fixture_problems(tmp_path, lambda d: (d / "trees/empty").mkdir(), spec=spec)
    assert any(expected in p and "Git keeps no empty directory" in p for p in problems), problems


def test_a_two_line_commit_message_is_one_paragraph(tmp_path: Path) -> None:
    add_fixture(tmp_path, "f", "clean-branch")
    path = tmp_path / "evals/cowsay/fixtures/f/fixture.json"
    data = json.loads(path.read_text())
    path.write_text(
        json.dumps({**data, "main": [commit(message="Add the greeting\nwith a name")]})
    )
    write_suite(tmp_path, {"skill_name": "cowsay", "evals": [{**trigger(), "fixture": "f"}]})
    [loaded] = load_suite(tmp_path, "cowsay").cases
    assert loaded.fixture is not None
    assert loaded.fixture.main[0].message == "Add the greeting\nwith a name"


def test_a_fixture_without_branch_or_main_is_rejected(tmp_path: Path) -> None:
    problems = fixture_problems(tmp_path, drop=("branch", "main"))
    assert any("fixture.json: branch must be a string" in p for p in problems), problems
    assert any("fixture.json: main must be a nonempty list of commits" in p for p in problems)


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("{", "fixture.json: not valid JSON"),
        ("[]", "fixture.json: the fixture must be a JSON object"),
    ],
)
def test_a_malformed_fixture_json_is_rejected(tmp_path: Path, text: str, expected: str) -> None:
    problems = fixture_problems(tmp_path, lambda d: (d / "fixture.json").write_text(text))
    assert any(expected in problem for problem in problems), problems


def test_a_fixture_without_fixture_json_is_rejected_even_if_no_case_names_it(
    tmp_path: Path,
) -> None:
    (tmp_path / "evals/cowsay/fixtures/unused/trees/start").mkdir(parents=True)
    problems = errors(tmp_path, {"skill_name": "cowsay", "evals": [trigger()]})
    assert problems == ["evals/cowsay/fixtures/unused: missing fixture.json"]


@pytest.mark.parametrize("branch", ["main", "Main", "MAIN", "main/topic", "Main/topic"])
def test_a_branch_that_clashes_with_main_is_rejected(tmp_path: Path, branch: str) -> None:
    problems = fixture_problems(tmp_path, spec={"branch": branch})
    expected = f"fixture.json: branch {branch!r} clashes with main"
    assert any(expected in problem for problem in problems), problems


@pytest.mark.parametrize("branch", ["", "a..b", "-x", "HEAD", "@{-1}", "x@{y", "ends.lock", "a b"])
def test_a_branch_git_would_refuse_is_rejected(tmp_path: Path, branch: str) -> None:
    problems = fixture_problems(tmp_path, spec={"branch": branch})
    expected = f"fixture.json: branch {branch!r} is not a valid branch name"
    assert any(expected in problem for problem in problems), problems


@pytest.mark.parametrize("branch", ["mainline", "fix/main", "feature/add-retry"])
def test_a_branch_that_only_contains_main_loads(tmp_path: Path, branch: str) -> None:
    add_fixture(tmp_path, "f", "clean-branch")
    path = tmp_path / "evals/cowsay/fixtures/f/fixture.json"
    path.write_text(json.dumps({**json.loads(path.read_text()), "branch": branch}))
    write_suite(tmp_path, {"skill_name": "cowsay", "evals": [{**trigger(), "fixture": "f"}]})
    [loaded] = load_suite(tmp_path, "cowsay").cases
    assert loaded.fixture is not None
    assert loaded.fixture.branch == branch


def plant(path: Path, content: bytes = b"x\n") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content)


def in_tree(path: str, content: bytes = b"x\n", tree: str = "start") -> Callable[[Path], None]:
    return lambda directory: plant(directory / "trees" / tree / path, content)


@pytest.mark.parametrize(
    ("path", "reserved"),
    [
        (".claude/settings.json", ".claude"),
        (".agents/notes.txt", ".agents"),
        (".codex/config.toml", ".codex"),
        (".git/config", ".git"),
        ("CLAUDE.md", "CLAUDE.md"),
        ("CLAUDE.local.md", "CLAUDE.local.md"),
        ("AGENTS.md", "AGENTS.md"),
        ("AGENTS.override.md", "AGENTS.override.md"),
        ("SKILL.md", "SKILL.md"),
        (".GIT/config", ".git"),
        (".Claude/settings.json", ".claude"),
        ("claude.md", "CLAUDE.md"),
        ("sub/Agents.md", "AGENTS.md"),
        ("docs/.codex/notes.txt", ".codex"),
    ],
)
def test_a_reserved_name_anywhere_in_a_tree_is_rejected_ignoring_case(
    tmp_path: Path, path: str, reserved: str
) -> None:
    problems = fixture_problems(tmp_path, in_tree(path))
    expected = f"fixtures/f: trees/start/{path}: reserved name {reserved!r}, ignoring case"
    assert any(expected in problem for problem in problems), problems


@pytest.mark.parametrize("path", ["myskills/notes.txt", "src/Toolskills/a.py"])
def test_a_directory_ending_in_skills_is_rejected(tmp_path: Path, path: str) -> None:
    problems = fixture_problems(tmp_path, in_tree(path))
    directory = path.rsplit("/", 1)[0].rsplit("/", 1)[-1]
    expected = f"trees/start/{path}: directory {directory!r} ends in 'skills', ignoring case"
    assert any(expected in problem for problem in problems), problems


@pytest.mark.parametrize(
    "path",
    [
        "trees/start/.gitattributes",
        "trees/start/sub/.GitAttributes",
        "trees/.gitattributes",
        ".gitattributes",
    ],
)
def test_a_gitattributes_anywhere_in_a_fixture_is_rejected(tmp_path: Path, path: str) -> None:
    problems = fixture_problems(tmp_path, lambda d: plant(d / path, b"* text\n"))
    expected = f"fixtures/f: {path}: "
    assert any(expected in p and "'.gitattributes'" in p for p in problems), problems


@pytest.mark.parametrize("path", ["trees/start/link.py", "notes.json", "trees/alias"])
def test_a_symlink_anywhere_in_a_fixture_is_rejected(tmp_path: Path, path: str) -> None:
    def link(directory: Path) -> None:
        target = "start" if path == "trees/alias" else "fixture.json"
        (directory / path).symlink_to(target)

    problems = fixture_problems(tmp_path, link)
    assert any(f"fixtures/f: {path}: is a symlink" in p for p in problems), problems


def test_a_fixture_directory_that_is_a_symlink_is_rejected(tmp_path: Path) -> None:
    add_fixture(tmp_path, "clean-branch")
    (tmp_path / "evals/cowsay/fixtures/alias").symlink_to("clean-branch")
    problems = errors(tmp_path, {"skill_name": "cowsay", "evals": [trigger()]})
    assert problems == ["evals/cowsay/fixtures/alias: is a symlink"]


def test_a_path_that_is_not_ascii_is_rejected(tmp_path: Path) -> None:
    problems = fixture_problems(tmp_path, in_tree("café.txt"))
    assert any("trees/start/caf" in p and "is not ASCII" in p for p in problems), problems


def folds_case(directory: Path) -> bool:
    probe = directory / "case-probe"
    probe.touch()
    try:
        return (directory / "CASE-PROBE").exists()
    finally:
        probe.unlink()


@pytest.mark.parametrize(
    ("paths", "clash"),
    [
        (["Greet.py"], "trees/start/greet.py clashes with trees/start/Greet.py, ignoring case"),
        (["Docs/a.txt", "docs/b.txt"], "trees/start/docs clashes with trees/start/Docs"),
    ],
)
def test_two_paths_that_differ_only_in_case_are_rejected(
    tmp_path: Path, paths: list[str], clash: str
) -> None:
    if folds_case(tmp_path):
        pytest.skip("this file system folds case, so the two paths are one")

    def plant_all(directory: Path) -> None:
        for path in paths:
            plant(directory / "trees/start" / path)

    problems = fixture_problems(tmp_path, plant_all)
    assert any(clash in problem for problem in problems), problems


def test_case_clashes_finds_paths_and_directories_that_differ_only_in_case() -> None:
    paths = ["greet.py", "Greet.py", "Docs/a.txt", "docs/b.txt", "docs/c.txt", "src/x.py"]
    assert case_clashes(paths) == [("docs", "Docs"), ("greet.py", "Greet.py")]


DENIAL_KEYWORDS = [
    "operation not permitted",
    "permission denied",
    "read-only file system",
    "seccomp",
    "sandbox",
    "landlock",
    "failed to write file",
]


@pytest.mark.parametrize(
    ("change", "spec", "expected"),
    [
        (in_tree("skill-notes.txt"), {}, "trees/start/skill-notes.txt: the path holds 'skill'"),
        (in_tree("docs/Skills/a.txt"), {}, "trees/start/docs/Skills/a.txt: the path holds"),
        (in_tree("notes.txt", b"This skill greets\n"), {}, "notes.txt: the file holds 'skill'"),
        (in_tree("notes.txt", b"SKILLS: none\n"), {}, "notes.txt: the file holds 'skill'"),
        (in_tree("blob.bin", b"\xff\xfe\x00skill\x00"), {}, "blob.bin: the file holds 'skill'"),
        (None, {"branch": "add-skill"}, "branch 'add-skill' holds 'skill'"),
        (None, {"main": [commit(message="Add a skill")]}, "main[0]: the message holds 'skill'"),
    ],
)
def test_skill_wording_anywhere_in_a_fixture_is_rejected(
    tmp_path: Path,
    change: Callable[[Path], None] | None,
    spec: dict[str, object],
    expected: str,
) -> None:
    problems = fixture_problems(tmp_path, change, spec=spec)
    assert any(expected in problem for problem in problems), problems


def test_words_that_only_start_with_skill_load(tmp_path: Path) -> None:
    add_fixture(tmp_path, "f", "clean-branch")
    plant(tmp_path / "evals/cowsay/fixtures/f/trees/start/notes.txt", b"A skilled cook\n")
    write_suite(tmp_path, {"skill_name": "cowsay", "evals": [{**trigger(), "fixture": "f"}]})
    assert load_suite(tmp_path, "cowsay").cases[0].fixture is not None


@pytest.mark.parametrize("keyword", DENIAL_KEYWORDS)
def test_a_sandbox_denial_keyword_in_a_file_is_rejected(tmp_path: Path, keyword: str) -> None:
    text = f"Error: {keyword.upper()}\n".encode()
    problems = fixture_problems(tmp_path, in_tree("errors.txt", text))
    expected = f"trees/start/errors.txt: the file holds the sandbox denial keyword {keyword!r}"
    assert any(expected in problem for problem in problems), problems


def test_a_sandbox_denial_keyword_in_a_path_is_rejected(tmp_path: Path) -> None:
    problems = fixture_problems(tmp_path, in_tree("src/SandBox.py"))
    expected = "trees/start/src/SandBox.py: the path holds the sandbox denial keyword 'sandbox'"
    assert any(expected in problem for problem in problems), problems


@pytest.mark.parametrize(
    ("spec", "expected"),
    [
        (
            {"branch": "sandbox-cleanup"},
            "fixture.json: branch 'sandbox-cleanup' holds the sandbox denial keyword 'sandbox'",
        ),
        (
            {"main": [commit(message="Fix Permission Denied on read")]},
            "main[0]: the message holds the sandbox denial keyword 'permission denied'",
        ),
    ],
    ids=["branch", "message"],
)
def test_a_sandbox_denial_keyword_in_the_branch_or_a_message_is_rejected(
    tmp_path: Path, spec: dict[str, object], expected: str
) -> None:
    # git log prints the messages and git status the branch, as part of a failing command's output.
    problems = fixture_problems(tmp_path, spec=spec)
    assert any(expected in problem for problem in problems), problems


@pytest.mark.parametrize(
    ("name", "text", "line"),
    [
        (".gitignore", b"!/.claude/\n", 1),
        (".gitignore", b"build/\n!*/\n", 2),
        (".GITIGNORE", b"!.agents\n", 1),
        (".gitignore", b"\xef\xbb\xbf  !x\n", 1),
        (".gitignore", b"*.log\r\n\t!keep.log\r\n", 2),
    ],
)
def test_a_negation_in_a_tree_root_gitignore_is_rejected(
    tmp_path: Path, name: str, text: bytes, line: int
) -> None:
    problems = fixture_problems(tmp_path, in_tree(name, text))
    expected = f"trees/start/{name}: line {line} is a negation"
    assert any(expected in problem for problem in problems), problems


@pytest.mark.parametrize(
    ("path", "text"), [("sub/.gitignore", b"*\n!foo\n"), (".gitignore", b"\\!literal\n")]
)
def test_a_nested_negation_or_an_escaped_bang_loads(
    tmp_path: Path, path: str, text: bytes
) -> None:
    add_fixture(tmp_path, "f", "clean-branch")
    plant(tmp_path / "evals/cowsay/fixtures/f/trees/start" / path, text)
    write_suite(tmp_path, {"skill_name": "cowsay", "evals": [{**trigger(), "fixture": "f"}]})
    assert load_suite(tmp_path, "cowsay").cases[0].fixture is not None


def git_root(root: Path) -> Path:
    """Make root its own git repository that ignores logs and Python caches."""
    root.mkdir(parents=True, exist_ok=True)
    (root / ".gitignore").write_text("*.log\n__pycache__/\n")
    subprocess.run(["git", "init", "--quiet"], cwd=root, check=True)  # noqa: S607
    return root


@pytest.mark.parametrize(
    "path", ["trees/start/debug.log", "trees/start/__pycache__/greet.cpython-314.pyc", "build.log"]
)
def test_a_path_the_repository_ignores_is_rejected(tmp_path: Path, path: str) -> None:
    root = git_root(tmp_path / "repo")
    problems = fixture_problems(root, lambda d: plant(d / path))
    expected = f"fixtures/f: {path}: Git ignores it, so a checkout would not have it"
    assert any(expected in problem for problem in problems), problems


@pytest.mark.parametrize("configured", [False, True], ids=["xdg", "core-excludesfile"])
def test_a_path_the_authors_global_ignore_file_ignores_is_rejected(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, *, configured: bool
) -> None:
    # The harness's own git calls skip the author's config, but the author's own
    # git leaves the file out of every commit, so no checkout would have it.
    root = git_root(tmp_path / "repo")
    config = tmp_path / "gitconfig"
    if configured:
        ignore = tmp_path / "my-ignore"
        config.write_text(f"[core]\n\texcludesFile = {ignore}\n")
    else:
        ignore = tmp_path / "xdg/git/ignore"
        ignore.parent.mkdir(parents=True)
        config.write_text("")
    ignore.write_text("local.json\n")
    monkeypatch.setenv("GIT_CONFIG_GLOBAL", str(config))
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "xdg"))
    problems = fixture_problems(root, in_tree("local.json"))
    expected = (
        "fixtures/f: trees/start/local.json: Git ignores it, so a checkout would not have it"
    )
    assert any(expected in problem for problem in problems), problems


PYCACHE = "a fixture may hold no '__pycache__', which evals_sha256 leaves out"


@pytest.mark.parametrize(
    "path",
    [
        "trees/start/sub/__pycache__/data.txt",
        "trees/start/__pycache__",
        "trees/__pycache__/data.txt",
        "__pycache__/fixture.cpython-314.pyc",
    ],
)
def test_a_pycache_anywhere_in_a_fixture_is_rejected_outside_a_repository(
    tmp_path: Path, path: str
) -> None:
    problems = fixture_problems(tmp_path, lambda d: plant(d / path))
    assert f"evals/cowsay/fixtures/f: {path}: {PYCACHE}" in problems, problems


def test_a_pycache_a_nested_gitignore_re_includes_is_rejected(tmp_path: Path) -> None:
    root = git_root(tmp_path / "repo")

    def re_include(directory: Path) -> None:
        plant(directory / "trees/start/sub/.gitignore", b"!__pycache__/\n")
        plant(directory / "trees/start/sub/__pycache__/data.txt")

    # The only problem: the repository's ignore check does not see this file.
    assert fixture_problems(root, re_include) == [
        f"evals/cowsay/fixtures/f: trees/start/sub/__pycache__/data.txt: {PYCACHE}"
    ]


def test_a_fixture_in_a_repository_that_ignores_none_of_it_loads(tmp_path: Path) -> None:
    root = git_root(tmp_path / "repo")
    add_fixture(root, "small-tally")
    write_suite(root, {"skill_name": "cowsay", "evals": [{**trigger(), "fixture": "small-tally"}]})
    assert load_suite(root, "cowsay").cases[0].fixture is not None


@pytest.mark.parametrize("name", sorted(p.name for p in GIT_FIXTURES.iterdir()))
def test_every_shipped_git_fixture_is_valid_where_it_sits_in_this_repository(name: str) -> None:
    problems: list[str] = []
    assert load_fixture(ROOT, GIT_FIXTURES / name, problems) is not None, problems
