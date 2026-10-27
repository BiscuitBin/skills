"""Deterministic assertions over a trace, including the negatives that must fail."""

import subprocess
from dataclasses import replace
from pathlib import Path

import pytest

from skills_tooling.evals import assertions
from skills_tooling.evals.adapter import Command, PythonCall, Trace
from skills_tooling.evals.assertions import contains_lines, evaluate, expected_script_output
from skills_tooling.evals.cases import Assertion

ROOT = Path(__file__).parents[2]
SKILL_DIR = ROOT / "skills/cowsay"
WORKSPACE = Path("/trial/workspace")
INSTALLED = WORKSPACE / ".claude/skills/cowsay"
SCRIPT = "scripts/cowsay.py"
ARGS = ("--", "Ship it, team!")
COW = (
    " ________________\n"
    "< Ship it, team! >\n"
    " ----------------\n"
    "    \\   ^__^\n"
    "     \\  (oo)\\_______\n"
    "        (__)\\       )\\/\\\n"
    "            ||----w |\n"
    "            ||     ||\n"
)
RUN = "python3 .claude/skills/cowsay/scripts/cowsay.py -- 'Ship it, team!'"
CALL = PythonCall(str(WORKSPACE), (".claude/skills/cowsay/scripts/cowsay.py", *ARGS))


def trace(**overrides: object) -> Trace:
    base = Trace(
        skills_triggered=["cowsay"],
        skills_invoked=["cowsay"],
        commands=[Command(RUN, ok=True, output=COW.rstrip("\n"))],
        final_message=f"Here you go:\n\n```text\n{COW}```\n",
        cli_version="2.1.309",
        model="claude-sonnet-5-5",
        exit_code=0,
        timed_out=False,
        stream_completed=True,
        status="ok",
        status_reason="",
        visible_skills=None,
        visible_plugins=None,
        python_calls=(CALL,),
    )
    return replace(base, **overrides)  # type: ignore[arg-type]


def check(assertion: Assertion, observed: Trace) -> bool:
    return evaluate(
        assertion, observed, skill="cowsay", skill_dir=SKILL_DIR, installed=INSTALLED
    ).passed


SCRIPT_RAN = Assertion("script_ran", script=SCRIPT, args=ARGS)
FINAL = Assertion("final_contains_script_output", script=SCRIPT, args=ARGS)


def test_the_harness_computes_the_expected_output_by_running_the_script() -> None:
    assert expected_script_output(SKILL_DIR, SCRIPT, ARGS) == COW


def test_a_real_run_passes_every_assertion() -> None:
    for assertion in (
        Assertion("skill_triggered"),
        SCRIPT_RAN,
        Assertion("script_ran", script=SCRIPT),
        FINAL,
        Assertion("output_contains", value="(oo)"),
        Assertion("output_matches", pattern=r"<\s*Ship it, team!\s*>"),
    ):
        assert check(assertion, trace()), assertion


@pytest.mark.parametrize(
    "command",
    [
        "printf '%s\\n' .claude/skills/cowsay/scripts/cowsay.py",
        "echo .claude/skills/cowsay/scripts/cowsay.py",
        "cat .claude/skills/cowsay/scripts/cowsay.py",
        "true # python3 .claude/skills/cowsay/scripts/cowsay.py",
        "sh -c 'python3 .claude/skills/cowsay/scripts/cowsay.py -- hi'",
        "python3 -c 'print(1)' .claude/skills/cowsay/scripts/cowsay.py",
    ],
)
def test_script_ran_fails_when_the_command_only_names_the_script(command: str) -> None:
    assert not check(SCRIPT_RAN, trace(commands=[Command(command, ok=True, output=COW)]))


def test_script_ran_fails_when_the_command_skipped_the_script() -> None:
    skipped = "false && python3 .claude/skills/cowsay/scripts/cowsay.py; true"
    observed = trace(commands=[Command(skipped, ok=True, output="")], python_calls=())
    assert not check(SCRIPT_RAN, observed)


def test_script_ran_fails_when_the_tool_result_lacks_the_output() -> None:
    assert not check(SCRIPT_RAN, trace(commands=[Command(RUN, ok=True, output="moo")]))


def test_script_ran_fails_when_the_command_errored() -> None:
    assert not check(SCRIPT_RAN, trace(commands=[Command(RUN, ok=False, output=COW)]))


def test_script_ran_fails_without_a_python_call_for_the_installed_copy() -> None:
    assert not check(SCRIPT_RAN, trace(python_calls=()))
    elsewhere = PythonCall("/repo", ("skills/cowsay/scripts/cowsay.py", *ARGS))
    assert not check(SCRIPT_RAN, trace(python_calls=(elsewhere,)))
    other_text = replace(CALL, argv=(CALL.argv[0], "--", "something else"))
    assert not check(SCRIPT_RAN, trace(python_calls=(other_text,)))


@pytest.mark.parametrize(
    "command",
    [
        "python3 -X utf8 .claude/skills/cowsay/scripts/cowsay.py -- 'Ship it, team!'",
        "python3 -W ignore -I .claude/skills/cowsay/scripts/cowsay.py -- 'Ship it, team!'",
        "env -i PYTHONUTF8=1 python3 .claude/skills/cowsay/scripts/cowsay.py -- 'Ship it, team!'",
    ],
)
def test_script_ran_accepts_interpreter_options_and_env(command: str) -> None:
    assert check(SCRIPT_RAN, trace(commands=[Command(command, ok=True, output=COW)]))


def test_script_ran_accepts_a_cd_then_relative_path_and_stdin() -> None:
    command = (
        "cd .claude/skills/cowsay && printf '%s' 'Ship it, team!' | python3 scripts/cowsay.py"
    )
    call = PythonCall(str(INSTALLED), (SCRIPT,))
    observed = trace(commands=[Command(command, ok=True, output=COW)], python_calls=(call,))
    assert check(SCRIPT_RAN, observed)


@pytest.mark.parametrize(
    "final",
    [
        COW.replace("< Ship it, team! >", "<  Ship it, team! >"),
        COW.replace("            ||     ||\n", ""),
        COW.replace("Ship it, team!", "Ship it team!"),
        COW.replace("(oo)", "(00)"),
        COW.replace("\n", " ", 1),
        "",
    ],
    ids=[
        "altered-whitespace",
        "missing-line",
        "wrong-text",
        "freehand-cow",
        "joined-lines",
        "empty",
    ],
)
def test_final_contains_script_output_fails_on_any_difference(final: str) -> None:
    assert not check(FINAL, trace(final_message=f"```text\n{final}```"))


def test_final_contains_script_output_accepts_crlf_and_surrounding_text() -> None:
    assert check(FINAL, trace(final_message="Sure!\r\n" + COW.replace("\n", "\r\n") + "Enjoy"))


def test_skill_triggered_and_output_assertions_fail_when_absent() -> None:
    assert not check(Assertion("skill_triggered"), trace(skills_triggered=[]))
    assert not check(Assertion("output_contains", value="(oo)"), trace(final_message="moo"))
    assert not check(Assertion("output_matches", pattern=r"\(oo\)"), trace(final_message="moo"))


def test_results_carry_evidence() -> None:
    result = evaluate(
        SCRIPT_RAN,
        trace(python_calls=()),
        skill="cowsay",
        skill_dir=SKILL_DIR,
        installed=INSTALLED,
    )
    assert (result.type, result.passed) == ("script_ran", False)
    assert "python" in result.evidence


def test_exact_output_keeps_trailing_blank_lines() -> None:
    assert not contains_lines("hello", "hello\n\n")
    assert contains_lines("hello\n", "hello\n\n")


def test_expected_output_never_waits_on_stdin_or_hangs(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    scripts = tmp_path / "skill/scripts"
    scripts.mkdir(parents=True)
    (scripts / "reads.py").write_text("import sys\nprint(repr(sys.stdin.read()))\n")
    (scripts / "hangs.py").write_text("import time\ntime.sleep(60)\n")
    assert expected_script_output(tmp_path / "skill", "scripts/reads.py", ()) == "''\n"
    monkeypatch.setattr(assertions, "SCRIPT_TIMEOUT", 0.5)
    with pytest.raises(subprocess.TimeoutExpired):
        expected_script_output(tmp_path / "skill", "scripts/hangs.py", ())
