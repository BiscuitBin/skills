"""The eval case schema: what loads, and what is rejected with a reason."""

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest

from skills_tooling.evals.cases import CaseError, load_suite, validate_all

ROOT = Path(__file__).parents[2]


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
        (behaviour(files=["input.txt"]), "input files are not staged yet"),
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
    assert "1 eval suite valid" in result.stdout
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


@pytest.mark.parametrize("listed", [True, False])
def test_validate_is_quiet_about_written_or_undistributed_suites(
    tmp_path: Path, *, listed: bool
) -> None:
    write_suite(
        tmp_path,
        PLACEHOLDER_SUITE
        if listed
        else {**PLACEHOLDER_SUITE, "evals": PLACEHOLDER_SUITE["evals"][:2]},
    )
    if listed:
        list_in_marketplace(tmp_path, "cowsay")
    result = run_command(tmp_path, "validate")
    assert (result.returncode, result.stderr) == (0, "")
