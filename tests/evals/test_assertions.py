"""Deterministic assertions over a trace, including the negatives that must fail."""

import contextlib
import os
import shlex
import signal
import subprocess
from dataclasses import replace
from pathlib import Path
from typing import TYPE_CHECKING

import pytest

from skills_tooling.evals import assertions
from skills_tooling.evals.adapter import Command, PythonCall, Trace
from skills_tooling.evals.assertions import (
    AssertionResult,
    command_list,
    contains_lines,
    evaluate,
    expected_script_output,
)
from skills_tooling.evals.cases import Assertion
from tests.evals.test_claude_parser import parse
from tests.evals.test_codex_parser import parse as parse_codex

if TYPE_CHECKING:
    from collections.abc import Callable

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
        "python3 -c'print(1)' .claude/skills/cowsay/scripts/cowsay.py",
        "python3 -Ic 'print(1)' .claude/skills/cowsay/scripts/cowsay.py",
        "python3 -Ic'print(1)' .claude/skills/cowsay/scripts/cowsay.py",
        "python3 -mjson.tool .claude/skills/cowsay/scripts/cowsay.py",
    ],
)
def test_script_ran_fails_when_the_command_only_names_the_script(command: str) -> None:
    assert not check(SCRIPT_RAN, trace(commands=[Command(command, ok=True, output=COW)]))


@pytest.mark.parametrize("flag", ["--version", "-V", "-h", "-?", "--help", "-IV"])
def test_script_ran_fails_when_the_interpreter_only_reports_itself(flag: str) -> None:
    # Without args the tool result need only be nonempty, and the version text is.
    command = f"python3 {flag} .claude/skills/cowsay/scripts/cowsay.py"
    call = PythonCall(str(WORKSPACE), (flag, ".claude/skills/cowsay/scripts/cowsay.py"))
    observed = trace(
        commands=[Command(command, ok=True, output="Python 3.13.1")], python_calls=(call,)
    )
    assert not check(Assertion("script_ran", script=SCRIPT), observed)


def test_script_ran_fails_when_the_command_skipped_the_script() -> None:
    skipped = "false && python3 .claude/skills/cowsay/scripts/cowsay.py; true"
    observed = trace(commands=[Command(skipped, ok=True, output="")], python_calls=())
    assert not check(SCRIPT_RAN, observed)


def test_script_ran_fails_when_the_tool_result_lacks_the_output() -> None:
    assert not check(SCRIPT_RAN, trace(commands=[Command(RUN, ok=True, output="moo")]))


def test_script_ran_fails_when_the_command_errored() -> None:
    assert not check(SCRIPT_RAN, trace(commands=[Command(RUN, ok=False, output=COW)]))


def test_script_ran_fails_when_a_fallback_masks_the_failed_script() -> None:
    masked = trace(
        commands=[Command(f"{RUN} || echo fallback", ok=True, output=COW)],
        python_calls=(replace(CALL, exit_code=2),),
    )
    assert not check(SCRIPT_RAN, masked)
    no_args = trace(
        commands=[
            Command(
                "python3 .claude/skills/cowsay/scripts/cowsay.py || echo fallback",
                ok=True,
                output="fallback",
            )
        ],
        python_calls=(PythonCall(str(WORKSPACE), (CALL.argv[0],), exit_code=2),),
    )
    assert not check(Assertion("script_ran", script=SCRIPT), no_args)


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
        "python3 -Xutf8 -Wignore .claude/skills/cowsay/scripts/cowsay.py -- 'Ship it, team!'",
        "python3 -IuX utf8 .claude/skills/cowsay/scripts/cowsay.py -- 'Ship it, team!'",
        "python3 --check-hash-based-pycs never .claude/skills/cowsay/scripts/cowsay.py -- 'Ship it, team!'",
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


def test_script_ran_accepts_a_cd_into_the_scripts_directory() -> None:
    command = "cd .claude/skills/cowsay/scripts && python3 cowsay.py -- 'Ship it, team!'"
    call = PythonCall(str(INSTALLED / "scripts"), ("cowsay.py", *ARGS))
    observed = trace(commands=[Command(command, ok=True, output=COW)], python_calls=(call,))
    assert check(SCRIPT_RAN, observed)


def test_script_ran_fails_for_a_different_script_of_the_same_name() -> None:
    command = "python3 elsewhere/cowsay.py -- 'Ship it, team!'"
    assert not check(SCRIPT_RAN, trace(commands=[Command(command, ok=True, output=COW)]))


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


def test_expected_output_points_home_and_temp_at_the_throwaway_directory(tmp_path: Path) -> None:
    scripts = tmp_path / "skill/scripts"
    scripts.mkdir(parents=True)
    (scripts / "where.py").write_text(
        "import pathlib, tempfile\n"
        "cwd = pathlib.Path.cwd().resolve()\n"
        "print(pathlib.Path(tempfile.gettempdir()).resolve() == cwd)\n"
        "print(pathlib.Path.home().resolve() == cwd)\n"
    )
    assert expected_script_output(tmp_path / "skill", "scripts/where.py", ()) == "True\nTrue\n"


def test_a_timed_out_script_leaves_no_descendants(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    scripts = tmp_path / "skill/scripts"
    scripts.mkdir(parents=True)
    pid_file = tmp_path / "child.pid"
    (scripts / "spawns.py").write_text(
        "import pathlib, subprocess, sys, time\n"
        "child = subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(60)'])\n"
        f"pathlib.Path({str(pid_file)!r}).write_text(str(child.pid))\n"
        "time.sleep(60)\n"
    )
    monkeypatch.setattr(assertions, "SCRIPT_TIMEOUT", 1.0)
    try:
        with pytest.raises(subprocess.TimeoutExpired):
            expected_script_output(tmp_path / "skill", "scripts/spawns.py", ())
        with pytest.raises(ProcessLookupError):
            os.kill(int(pid_file.read_text()), 0)
    finally:
        if pid_file.exists():
            with contextlib.suppress(ProcessLookupError):
                os.kill(int(pid_file.read_text()), signal.SIGKILL)


def test_the_cowsay_behaviour_assertions_over_the_recorded_live_transcript() -> None:
    observed = parse("live-behaviour")
    assert check(FINAL, observed)
    assert check(Assertion("skill_triggered"), observed)
    assert check(Assertion("output_contains", value="< Ship it, team! >"), observed)
    assert not check(
        Assertion("final_contains_script_output", script=SCRIPT, args=("--", "Ship it")), observed
    )


NOT_RUN = Assertion("python_not_run")
NOTHING_RAN = "no python call logged, none named in a command, no bytecode in the workspace"


def not_run(observed: Trace, root: Path) -> AssertionResult:
    return evaluate(
        NOT_RUN,
        observed,
        skill="cowsay",
        skill_dir=SKILL_DIR,
        installed=INSTALLED,
        workspace=root,
    )


def quiet(*commands: str) -> Trace:
    """A trace of commands that printed nothing, with no python call logged."""
    return trace(commands=[Command(c, ok=True, output="") for c in commands], python_calls=())


def test_python_not_run_needs_the_trials_workspace() -> None:
    with pytest.raises(ValueError, match="workspace"):
        evaluate(NOT_RUN, quiet(), skill="cowsay", skill_dir=SKILL_DIR, installed=INSTALLED)


def test_python_not_run_passes_when_no_witness_shows_python(tmp_path: Path) -> None:
    (tmp_path / "fingerprint.py").write_text("print('x')\n")
    # Only the workspace's own .git/ is left out of the bytecode check.
    (tmp_path / ".git").mkdir()
    (tmp_path / ".git/x.pyc").write_bytes(b"")
    observed = quiet("git --no-optional-locks status", "git --no-optional-locks diff main...HEAD")
    assert not_run(observed, tmp_path) == AssertionResult("python_not_run", True, NOTHING_RAN)


def test_python_not_run_fails_on_any_call_the_wrapper_logged(tmp_path: Path) -> None:
    check_run = PythonCall(str(tmp_path), ("fingerprint.py", "--check", "fingerprints.txt"), 1)
    inline = PythonCall(str(tmp_path), ("-c", "pass"))
    first = not_run(trace(commands=[], python_calls=(check_run, inline)), tmp_path)
    assert (first.passed, first.evidence) == (
        False,
        f"python ran: fingerprint.py --check fingerprints.txt in {tmp_path}, exit 1 and 1 more",
    )
    alone = not_run(trace(commands=[], python_calls=(inline,)), tmp_path)
    assert (alone.passed, alone.evidence) == (False, f"python ran: -c pass in {tmp_path}, exit 0")


@pytest.mark.parametrize(
    "command",
    [
        "/usr/bin/python3 fingerprint.py --check fingerprints.txt",
        "env -i python3 -m unittest",
        "PATH=/usr/bin python3 fingerprint.py",
        # The shell's words: the lexer's default would split these at ':' and '@'.
        "PATH=/usr/bin:/bin python3 fingerprint.py",
        "env PATH=/opt/homebrew/bin:/usr/bin python3 -m unittest",
        "/usr/bin/env PATH=/usr/bin python3 x.py",
        "/usr/bin/time -p /usr/bin/python3 x.py",
        "/opt/homebrew/opt/python@3.13/bin/python3.13 -m unittest",
        "exec python3 x.py",
        "command python3 x.py",
        "time python3 x.py",
        "git status && python3 -m unittest -v",
        # Ticket 18's RED Codex baseline ran this, with no path.
        "python3 -m unittest -v && python3 wordstat.py sample.txt --top 3",
        "python -m unittest",
        "python3.14 -m unittest",
        "nohup /usr/local/bin/python3.13 x.py",
    ],
)
@pytest.mark.parametrize("ok", [True, False])
def test_python_not_run_fails_on_a_command_that_runs_an_interpreter(
    tmp_path: Path, command: str, *, ok: bool
) -> None:
    # The log was lost, or the interpreter was reached past the wrapper.
    observed = trace(commands=[Command(command, ok=ok, output="")], python_calls=())
    result = not_run(observed, tmp_path)
    assert (result.passed, result.evidence) == (False, f"a command runs python: {command}")


@pytest.mark.parametrize(
    "command",
    [
        "if true; then /usr/bin/python3 x.py; fi",
        "if /usr/bin/python3 x.py; then :; fi",
        "if false; then :; elif /usr/bin/python3 x.py; then :; fi",
        "if false; then :; else /usr/bin/python3 x.py; fi",
        "for f in a; do /usr/bin/python3 x.py; done",
        "while /usr/bin/python3 x.py; do :; done",
        "until /usr/bin/python3 x.py; do :; done",
        "( /usr/bin/python3 x.py )",
        "(/usr/bin/python3 x.py)",
        "{ /usr/bin/python3 x.py; }",
        "! /usr/bin/python3 x.py",
        "if ! env -i /usr/bin/python3 x.py; then :; fi",
    ],
)
def test_python_not_run_finds_an_interpreter_after_a_keyword_or_in_a_group(
    tmp_path: Path, command: str
) -> None:
    result = not_run(quiet(command), tmp_path)
    assert (result.passed, result.evidence) == (False, f"a command runs python: {command}")


@pytest.mark.parametrize(
    "command",
    [
        "sh -c '/usr/bin/python3 fingerprint.py'",
        "bash -lc 'cd . && /opt/homebrew/bin/python3.13 -m unittest'",
        "zsh -c 'env -i python3 x.py'",
        "/bin/dash -ec '/usr/bin/python3 x.py'",
        "ksh -c 'true; /usr/bin/python3 x.py'",
        "bash -ce '/usr/bin/python3 x.py'",
        "bash -o pipefail -c '/usr/bin/python3 x.py | cat'",
        # Codex's own wrapper, had the adapter not removed it.
        '/bin/zsh -c "PATH=/usr/bin python3 x.py"',
        "sh -c \"bash -c '/usr/bin/python3 x.py'\"",
        "env -i sh -c 'exec /usr/bin/python3 x.py'",
    ],
)
def test_python_not_run_reads_the_string_a_shell_runs(tmp_path: Path, command: str) -> None:
    result = not_run(quiet(command), tmp_path)
    assert (result.passed, result.evidence) == (False, f"a command runs python: {command}")


@pytest.mark.parametrize(
    "command",
    [
        # A reset PATH takes the script's #! line past the wrapper (design review C5).
        "PATH=/usr/bin:/bin ./fingerprint.py --check fingerprints.txt",
        "env -i ./fingerprint.py --check fingerprints.txt",
        "env PATH=/usr/bin ./fingerprint.py --check fingerprints.txt",
        "sh -c 'PATH=/usr/bin:/bin ./fingerprint.py --check fingerprints.txt'",
        "./fingerprint.py --check fingerprints.txt",
        "if true; then /trial/workspace/fingerprint.py; fi",
    ],
)
def test_python_not_run_fails_on_a_python_script_run_by_path(tmp_path: Path, command: str) -> None:
    result = not_run(quiet(command), tmp_path)
    assert (result.passed, result.evidence) == (
        False,
        f"a command runs a python script: {command}",
    )


UNSPLIT = (
    "/usr/bin/python3 fingerprint.py --check fingerprints.txt; cat <<EOF\nThe branch's list\nEOF"
)


@pytest.mark.parametrize(
    ("command", "unsplit"),
    [
        # The lexer reads a here-doc body, and an apostrophe there is an odd quote to it.
        (UNSPLIT, UNSPLIT),
        ("python3.13 -m unittest; echo it's", "python3.13 -m unittest; echo it's"),
        # The outer command splits; the string its shell runs does not.
        ('sh -c "/usr/bin/python3 x.py; echo it\'s"', "/usr/bin/python3 x.py; echo it's"),
    ],
)
def test_python_not_run_fails_closed_on_a_command_the_lexer_cannot_split(
    tmp_path: Path, command: str, unsplit: str
) -> None:
    assert command_list(unsplit, whole_words=True) == []
    result = not_run(quiet(command), tmp_path)
    assert (result.passed, result.evidence) == (
        False,
        f"a command names python and could not be split: {command}",
    )


@pytest.mark.parametrize(
    "command",
    [
        "git --no-optional-locks log -S python3 --oneline",
        "git --no-optional-locks show HEAD:fingerprint.py",
        "printf '%s\\n' python3",
        "echo /usr/bin/python3",
        "cat fingerprint.py",
        "sed -n 1,20p test_fingerprint.py",
        # A .py name that is an argument, not the program, on a continued line too.
        "ls ./fingerprint.py",
        "git --no-optional-locks diff main...HEAD -- \\\n  fingerprint.py README.md",
        "grep -n python3 README.md",
        "true # python3 x.py",
        # A lookup runs nothing.
        "command -v python3",
        "command -V python3",
        "command -pv python3",
        "which python3",
        "type python3",
        # Commands the lexer cannot split, with no interpreter word: longer names are not one.
        "cat <<EOF\nThe branch's list\nEOF",
        "cat .python-version cpython-314.pyc mypython; echo it's",
    ],
)
def test_python_not_run_passes_on_commands_that_only_name_python(
    tmp_path: Path, command: str
) -> None:
    assert not_run(quiet(command), tmp_path) == AssertionResult(
        "python_not_run", True, NOTHING_RAN
    )


@pytest.mark.parametrize(
    ("command", "evidence"),
    [
        # A here-doc body is read as commands, since one fed to sh runs (a false fail, pinned).
        ("cat <<'EOF'\npython3 x.py\nEOF", "a command runs python"),
        (
            "cat <<'EOF'\nfingerprint.py now drops blank lines\nEOF",
            "a command runs a python script",
        ),
        # The fallback fails a command it cannot split that names python only as data.
        (
            "cat <<EOF\nRun it with python3 x.py, it's quick\nEOF",
            "a command names python and could not be split",
        ),
    ],
)
def test_python_not_run_fails_conservatively_on_a_here_doc_that_names_python(
    tmp_path: Path, command: str, evidence: str
) -> None:
    result = not_run(quiet(command), tmp_path)
    assert (result.passed, result.evidence) == (False, f"{evidence}: {command}")


def nested_shells(depth: int, command: str) -> str:
    for _ in range(depth):
        command = f"sh -c {shlex.quote(command)}"
    return command


def test_python_not_run_reads_three_nested_shells_and_fails_closed_past_them(
    tmp_path: Path,
) -> None:
    three = nested_shells(3, "/usr/bin/python3 x.py")
    assert not_run(quiet(three), tmp_path).evidence == f"a command runs python: {three}"
    # Past three, the string is read as one the lexer cannot split: a python word fails it.
    four = nested_shells(4, "/usr/bin/python3 x.py")
    assert not_run(quiet(four), tmp_path).evidence == (
        f"a command names python and could not be split: {four}"
    )
    assert not_run(quiet(nested_shells(4, "ls x.py")), tmp_path).passed


@pytest.mark.parametrize(
    ("planted", "found"),
    [
        ("__pycache__/fingerprint.cpython-314.pyc", "__pycache__"),
        ("x.pyc", "x.pyc"),
        ("notes/__pycache__/", "notes/__pycache__"),
    ],
)
def test_python_not_run_fails_on_bytecode_in_the_workspace(
    tmp_path: Path, planted: str, found: str
) -> None:
    path = tmp_path / planted
    path.parent.mkdir(parents=True, exist_ok=True)
    if planted.endswith("/"):
        path.mkdir()
    else:
        path.write_bytes(b"")
    result = not_run(quiet("git status"), tmp_path)
    assert (result.passed, result.evidence) == (False, f"bytecode in the workspace: {found}")


@pytest.mark.skipif(os.geteuid() == 0, reason="root lists any directory")
def test_python_not_run_fails_on_a_directory_it_cannot_read(tmp_path: Path) -> None:
    notes = tmp_path / "notes"
    notes.mkdir()
    notes.chmod(0)
    try:
        result = not_run(quiet("git status"), tmp_path)
    finally:
        notes.chmod(0o755)
    assert (result.passed, result.evidence) == (False, "could not read notes")


def test_python_not_run_does_not_follow_a_link_out_of_the_workspace(tmp_path: Path) -> None:
    outside = tmp_path / "outside"
    (outside / "__pycache__").mkdir(parents=True)
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    (workspace / "elsewhere").symlink_to(outside)
    assert not_run(quiet("git status"), workspace).passed


def test_python_not_run_still_reads_the_log_and_the_workspace_when_no_command_ran(
    tmp_path: Path,
) -> None:
    # A trace with no commands passes on the two witnesses it still has.
    assert not_run(quiet(), tmp_path).passed
    assert not not_run(trace(commands=[], python_calls=(CALL,)), tmp_path).passed
    (tmp_path / "x.pyc").write_bytes(b"")
    assert not not_run(quiet(), tmp_path).passed


@pytest.mark.parametrize("parsed", [parse, parse_codex], ids=["claude", "codex"])
def test_python_not_run_reads_each_agents_commands_as_its_parser_gives_them(
    tmp_path: Path, parsed: Callable[[str], Trace]
) -> None:
    # Recorded traces carry no wrapper log, so only the command shows the run.
    ran = parsed("live-behaviour")
    assert (ran.status, ran.python_calls) == ("ok", ())
    result = not_run(ran, tmp_path)
    assert not result.passed
    assert result.evidence.startswith("a command runs python: python3 ")
    # A trial that ran no command at all.
    answered = parsed("live-should-not-trigger")
    assert (answered.status, answered.commands) == ("ok", [])
    assert not_run(answered, tmp_path) == AssertionResult("python_not_run", True, NOTHING_RAN)


def test_an_operator_at_the_end_of_a_line_ends_the_command() -> None:
    assert command_list("a ||\n b") == [(["a"], "||"), (["b"], "")]
    assert command_list("a &&\n\n b ;\n c") == [(["a"], "&&"), (["b"], ";"), (["c"], "")]
    assert command_list("a\n\nb") == [(["a"], "\n"), (["b"], "")]
