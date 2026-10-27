"""Deterministic assertions over a trace. See docs/reference/evals.md."""

import functools
import re
import shlex
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

from skills_tooling.evals import workspace

if TYPE_CHECKING:
    from collections.abc import Iterator

    from skills_tooling.evals.adapter import Command, PythonCall, Trace
    from skills_tooling.evals.cases import Assertion

PYTHON = re.compile(r"python(?:3(?:\.\d+)?)?")
OPERATORS = {";", "&&", "||", "|", "&", "\n"}
# Words that run the command after them; leading NAME=value assignments are skipped too.
PREFIXES = {"env", "exec", "command", "time", "nohup"}
ASSIGNMENT = re.compile(r"[A-Za-z_][A-Za-z0-9_]*=.*")
# Seconds the shipped script may take to produce the expected output.
SCRIPT_TIMEOUT = 30.0
# The interpreter's single-letter flags that take no value and still run the script.
FLAGS = set("bBdEiIOPqsSuvx")
# Single-letter options whose value is the rest of the word, or else the next word.
VALUE_FLAGS = set("WX")


@dataclass(frozen=True)
class AssertionResult:
    type: str
    passed: bool
    evidence: str


@functools.cache
def expected_script_output(skill_dir: Path, script: str, args: tuple[str, ...]) -> str:
    """Run the shipped script the way the harness trusts: isolated, outside any workspace.

    It runs in its own process group with stdin closed, like the agent, so a
    script that hangs or starts a child leaves nothing behind.
    """
    argv = [sys.executable, "-I", str(skill_dir / script), *args]
    with tempfile.TemporaryDirectory() as scratch, tempfile.TemporaryDirectory() as logs:
        out, err = Path(logs) / "stdout", Path(logs) / "stderr"
        done = workspace.run_isolated(
            argv,
            cwd=Path(scratch),
            env={"PATH": "/usr/bin:/bin", "PYTHONUTF8": "1"},
            stdout=out,
            stderr=err,
            timeout=SCRIPT_TIMEOUT,
        )
        if done.timed_out:
            raise subprocess.TimeoutExpired(argv, SCRIPT_TIMEOUT)
        if done.exit_code != 0 or done.survivors:
            raise subprocess.CalledProcessError(
                done.exit_code or -1, argv, stderr=err.read_bytes()
            )
        return out.read_bytes().decode()


def contains_lines(text: str, expected: str) -> bool:
    """Whether expected's lines appear, whole and in order, as a run of text's lines."""
    want = expected.removesuffix("\n").split("\n")
    have = [line.removesuffix("\r") for line in text.split("\n")]
    return any(have[i : i + len(want)] == want for i in range(len(have) - len(want) + 1))


def command_list(command: str) -> list[tuple[list[str], str]]:
    """Each simple command with the operator that follows it ("" for the last)."""
    lexer = shlex.shlex(command, posix=True, punctuation_chars=";&|\n")
    lexer.whitespace = " \t\r"
    found: list[tuple[list[str], str]] = []
    current: list[str] = []
    try:
        for token in lexer:
            if token in OPERATORS:
                if current:
                    found.append((current, token))
                current = []
            else:
                current.append(token)
    except ValueError:  # unbalanced quotes: the shell would not have run it either
        return []
    if current:
        found.append((current, ""))
    return found


def simple_commands(command: str) -> Iterator[list[str]]:
    for words, _ in command_list(command):
        yield words


def _script_argument(words: list[str]) -> tuple[str, list[str]] | None:
    """For `python3 <script> args…`, the script and its args; None for anything else."""
    while words and (words[0] in PREFIXES or ASSIGNMENT.fullmatch(words[0])):
        words = words[1:]
        while words and words[0].startswith("-"):  # options of env, command, time…
            words = words[1:]
    if not words or PYTHON.fullmatch(Path(words[0]).name) is None:
        return None
    rest = _past_options(words[1:])
    return (rest[0], rest[1:]) if rest else None


def _past_options(rest: list[str]) -> list[str] | None:
    """The words after the interpreter's options, or None when they run no script.

    Inline code (-c), a module (-m), stdin (-), help, version, and any option
    not known here all mean no script ran, attached or clustered as in -Ic'…'.
    """
    while rest and rest[0].startswith("-"):
        word, rest = rest[0], rest[1:]
        if word == "--check-hash-based-pycs":
            rest = rest[1:]
            continue
        if word.startswith("--") or word == "-":
            return None
        for position, flag in enumerate(word[1:], start=2):
            if flag in VALUE_FLAGS:
                if position == len(word):
                    rest = rest[1:]
                break
            if flag not in FLAGS:
                return None
    return rest


def _same_script(argument: str, script: str) -> bool:
    """Whether the two paths agree on their trailing parts, as after `cd scripts`.

    The wrapper's log, resolved against the real working directory, is what
    proves the installed copy ran; this only ties the command to the script.
    """
    have, want = Path(argument).parts, Path(script).parts
    shorter = min(len(have), len(want))
    return have[-shorter:] == want[-shorter:]


def _runs_script(command: Command, script: str) -> bool:
    for words in simple_commands(command.command):
        found = _script_argument(words)
        if found is not None and _same_script(found[0], script):
            return True
    return False


def _called(call: PythonCall, target: Path, args: tuple[str, ...] | None) -> bool:
    found = _script_argument(["python3", *call.argv])
    if found is None or (Path(call.cwd) / found[0]).resolve() != target:
        return False
    # The text may arrive as arguments or, per the skill, on stdin.
    return args is None or found[1] in ([], list(args))


def _script_ran(
    assertion: Assertion, trace: Trace, skill_dir: Path, installed: Path | None
) -> AssertionResult:
    script = assertion.script or ""
    if installed is None:
        return AssertionResult("script_ran", passed=False, evidence="no skill installed")
    shaped = [c for c in trace.commands if _runs_script(c, script)]
    if not shaped:
        return AssertionResult(
            "script_ran", passed=False, evidence=f"no Bash command runs python on {script}"
        )
    if assertion.args is not None:
        expected = expected_script_output(skill_dir, script, assertion.args)
        good = [c for c in shaped if c.ok and contains_lines(c.output, expected)]
        missing = "whose tool result holds the script's output for the case's args"
    else:
        good = [c for c in shaped if c.ok and c.output.strip()]
        missing = "with a successful, nonempty tool result"
    if not good:
        return AssertionResult(
            "script_ran", passed=False, evidence=f"no command running {script} {missing}"
        )
    target = (installed / script).resolve()
    if not any(_called(call, target, assertion.args) for call in trace.python_calls):
        return AssertionResult(
            "script_ran",
            passed=False,
            evidence=f"the trial's python3 never ran {target} with the case's text",
        )
    return AssertionResult("script_ran", passed=True, evidence=good[0].command)


def evaluate(
    assertion: Assertion,
    trace: Trace,
    *,
    skill: str,
    skill_dir: Path,
    installed: Path | None,
) -> AssertionResult:
    final = trace.final_message
    kind = assertion.type
    if kind == "skill_triggered":
        passed = skill in trace.skills_triggered
        return AssertionResult(kind, passed, f"triggered: {trace.skills_triggered}")
    if kind == "script_ran":
        return _script_ran(assertion, trace, skill_dir, installed)
    if kind == "final_contains_script_output":
        expected = expected_script_output(skill_dir, assertion.script or "", assertion.args or ())
        passed = contains_lines(final, expected)
        return AssertionResult(
            kind, passed, "exact output found" if passed else "exact output not in final message"
        )
    if kind == "output_contains":
        value = assertion.value or ""
        return AssertionResult(kind, value in final, f"looked for {value!r}")
    if kind == "output_matches":
        pattern = assertion.pattern or ""
        return AssertionResult(kind, re.search(pattern, final) is not None, f"pattern {pattern!r}")
    msg = f"unknown assertion type {kind!r}"
    raise ValueError(msg)
