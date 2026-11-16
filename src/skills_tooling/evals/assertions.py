"""Deterministic assertions over a trace. See docs/reference/evals.md."""

import functools
import itertools
import re
import shlex
import stat
import subprocess
import sys
import tempfile
from collections import deque
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

from skills_tooling.evals import workspace

if TYPE_CHECKING:
    from collections.abc import Iterator

    from skills_tooling.evals.adapter import Command, PythonCall, Trace
    from skills_tooling.evals.cases import Assertion

PYTHON = re.compile(r"python(?:3(?:\.\d+)?)?")
PUNCTUATION = set(";&|\n")
OPERATOR_PIECE = re.compile(r"&&|\|\||;;|\|&|[;&|\n]")
# Words that run the command after them; leading NAME=value assignments are skipped too.
PREFIXES = {"env", "exec", "command", "time", "nohup"}
ASSIGNMENT = re.compile(r"[A-Za-z_][A-Za-z0-9_]*=.*")
# A shell NAME, as a named coprocess's: coproc NAME { …; }.
SHELL_NAME = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")
# Shell words that can come before a command's program, which python_not_run looks past.
KEYWORDS = {"if", "then", "elif", "else", "while", "until", "do", "!", "{", "coproc"}
# Shells whose -c string python_not_run reads as commands, this many shells deep.
SHELLS = {"sh", "bash", "zsh", "dash", "ksh"}
# Shells in which an o with letters after it names the option in the rest of its word.
ATTACHED_OPTION_SHELLS = {"zsh", "ksh"}
SHELL_DEPTH = 3
# A shell's long options that take a file; bash reads them after one dash too.
SHELL_FILE_OPTIONS = {"--rcfile", "--init-file", "-rcfile", "-init-file"}
# An interpreter's name in text that cannot be split into commands: PYTHON, bare or
# ending a path, but not part of a longer name such as cpython-314 or .python-version.
PYTHON_WORD = re.compile(r"(?<![\w.-])python(?:3(?:\.\d+)?)?(?![\w.-])")
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
            env={"PATH": "/usr/bin:/bin", "PYTHONUTF8": "1", "HOME": scratch, "TMPDIR": scratch},
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


def _operator(token: str) -> str | None:
    """The operator a punctuation token stands for, or None for a word.

    The lexer returns adjacent punctuation as one token, so `||` at the end of a
    line arrives as `||\n`. A newline after an operator only continues the line.
    """
    if not token or set(token) - PUNCTUATION:
        return None
    pieces = OPERATOR_PIECE.findall(token)
    return next((piece for piece in pieces if piece != "\n"), "\n")


def command_list(command: str, *, whole_words: bool = False) -> list[tuple[list[str], str]]:
    """Each simple command with the operator that follows it ("" for the last).

    By default the lexer also splits a word at characters such as `:`, `@` and `(`.
    whole_words splits only at blanks and operators, as the shell does, so
    `PATH=/usr/bin:/bin` stays one word, and so does a `(` that opens a word.
    """
    lexer = shlex.shlex(command, posix=True, punctuation_chars=";&|\n")
    lexer.whitespace = " \t\r"
    lexer.whitespace_split = whole_words
    found: list[tuple[list[str], str]] = []
    current: list[str] = []
    try:
        for token in lexer:
            if (operator := _operator(token)) is not None:
                if current:
                    found.append((current, operator))
                elif operator == ";;" and found:
                    # A case arm's ;; on a line of its own ends the command before it.
                    found[-1] = (found[-1][0], operator)
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
    proves the installed copy ran and exited 0; this only ties the command to the script.
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
    if call.exit_code != 0:
        return False
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
            evidence=f"the trial's python3 never ran {target} with the case's text and exit 0",
        )
    return AssertionResult("script_ran", passed=True, evidence=good[0].command)


def _logged_call(calls: tuple[PythonCall, ...]) -> str | None:
    """The first call the trial's wrapper logged, and how many more, or None."""
    if not calls:
        return None
    first = calls[0]
    more = f" and {len(calls) - 1} more" if len(calls) > 1 else ""
    return f"python ran: {' '.join(first.argv)} in {first.cwd}, exit {first.exit_code}{more}"


def _program(words: list[str]) -> list[str]:
    """A simple command from its program on, past keywords, prefix words and assignments.

    [] when there is no program, or when `command -v` or `-V` only looks a name up.
    A subshell's `(` may open the program's word.
    """
    while words:
        word, rest = words[0], words[1:]
        name = Path(word).name  # /usr/bin/env is env
        if word.startswith("("):
            words = [word[1:], *rest] if word != "(" else rest
        elif word == "coproc" and _named_coprocess(rest):
            words = rest[1:]  # NAME is the coprocess's, not a program
        elif word in KEYWORDS:
            words = rest
        elif name in PREFIXES or ASSIGNMENT.fullmatch(word):
            options = list(itertools.takewhile(lambda w: w.startswith("-"), rest))
            if name == "command" and any(set(o) & {"v", "V"} for o in options):
                return []
            words = rest[len(options) :]  # options of env, command, time…
        else:
            break
    return words


def _named_coprocess(rest: list[str]) -> bool:
    """Whether coproc's words name the coprocess: NAME, then a bare `{` or a subshell's `(`.

    A `{` that opens a longer word is brace expansion, as in `coproc python3 {a,b}`.
    """
    return (
        len(rest) > 1
        and SHELL_NAME.fullmatch(rest[0]) is not None
        and (rest[1] == "{" or rest[1].startswith("("))
    )


def _past_pattern(words: list[str]) -> list[str] | None:
    """The words after the `)` that closes a case pattern, or None when the pattern goes on."""
    end = next((i for i, word in enumerate(words) if ")" in word), None)
    if end is None:
        return None
    tail = words[end].split(")", 1)[1]  # an arm's command may be glued to it: a)cmd
    return ([tail] if tail else []) + words[end + 1 :]


def _programs(found: list[tuple[list[str], str]]) -> Iterator[list[str]]:
    """Each simple command from its program on, as _program gives it, past case patterns.

    After `case WORD in`, and after `;;` while a case is open, the words through the
    one holding the pattern's closing `)` are the pattern, which the lexer may have split
    at `|` or a newline; the rest is the arm's command. `esac` closes the case.
    """
    pattern = False  # in a case pattern, before its closing )
    cases = 0  # open cases: a ;; outside one, as in a here-doc body, starts no pattern
    for words, operator in found:
        command = words
        if pattern and words[0] == "esac":
            pattern, cases, command = False, max(cases - 1, 0), words[1:]
        elif pattern:
            arm = _past_pattern(words)
            if arm is None:
                continue  # an alternative split off at |, or a pattern on its own line
            pattern, command = False, arm
        program = _program(command)
        if program[:1] == ["esac"]:
            cases = max(cases - 1, 0)
        elif program[:1] == ["case"] and "in" in program[2:]:
            after = program[program.index("in", 2) + 1 :]
            arm = _past_pattern(after)
            # A pattern follows `in`: on the next line, closed by a ), or split off at |.
            # Otherwise the line is not a case, such as prose in a here-doc body.
            if not after or arm is not None or operator == "|":
                cases += 1
                pattern, program = arm is None, _program(arm or [])
        if operator == ";;" and cases:
            pattern = True
        yield program


def _shell_string(shell: str, options: list[str]) -> str | None:
    """For a shell's words after its name, the string its -c runs; None when it has none.

    The c may sit in a cluster (-lc, -ce), and the string is the first word past the options.
    """
    reads = False
    while options and options[0][:1] in ("-", "+") and options[0] not in ("-", "--"):
        word, options = options[0], options[1:]
        if word in ("-o", "+o", "-O", "+O") or word in SHELL_FILE_OPTIONS:  # these take a value
            options = options[1:]
        elif not word.startswith("--"):
            flags = word[1:]
            if shell in ATTACHED_OPTION_SHELLS and "o" in flags[:-1]:
                # zsh and ksh: -oerrexit names the option itself, so it takes no word,
                # and the letters after the o are its name, not flags.
                flags, takes = flags[: flags.index("o")], 0
            else:
                # In a cluster each o or O takes the next word (-euo pipefail).
                takes = sum(flag in "oO" for flag in flags)
            # Unless that word is an option, as after bash's one-dash long options (-noprofile -c).
            for _ in range(takes):
                if options and options[0][:1] not in ("-", "+"):
                    options = options[1:]
            if word.startswith("-") and "c" in flags:
                reads = True
    if options[:1] == ["--"]:
        options = options[1:]
    return options[0] if reads and options else None


def _names_python(text: str) -> str | None:
    """For text rule 2 cannot read as commands: whether it holds an interpreter's name."""
    if PYTHON_WORD.search(text) is None:
        return None
    return "a command names python and could not be split"


def _runs_python(command: str, depth: int = 0) -> str | None:
    """How the command's text starts python, as the evidence's opening; None if it does not."""
    # A backslash-newline continues the line, as in the shell; the lexer would end it there.
    # An escaped backslash before the newline ends the line, so only an odd run joins.
    command = re.sub(r"(?<!\\)((?:\\\\)*)\\\n", r"\1", command)
    found = command_list(command, whole_words=True)
    if not found and command.strip():
        # Unbalanced quotes, as in a here-doc body with an apostrophe: fail closed.
        return _names_python(command)
    for program in _programs(found):
        if not program:
            continue
        # A redirection may be glued to the program's word: python3<<EOF, ./x.py>out.
        name = Path(re.split(r"[<>]", program[0], maxsplit=1)[0]).name
        if PYTHON.fullmatch(name):
            return "a command runs python"
        # Its #! line starts the interpreter, past the wrapper once PATH is reset.
        # A Command has no cwd, so this goes by name.
        if name.endswith(".py"):
            return "a command runs a python script"
        string = _shell_string(name, program[1:]) if name in SHELLS else None
        if string is not None:
            # Past SHELL_DEPTH shells, the string is read like one the lexer cannot split.
            how = _runs_python(string, depth + 1) if depth < SHELL_DEPTH else _names_python(string)
            if how is not None:
                return how
    return None


def _named_in_command(commands: list[Command]) -> str | None:
    """The first command, ok or not, whose text starts python, or None."""
    for command in commands:
        if (how := _runs_python(command.command)) is not None:
            return f"{how}: {command.command}"
    return None


def _bytecode(root: Path) -> str | None:
    """Bytecode under root, outside its .git/, or a path the walk cannot read; None for neither.

    The walk never follows a link. It fails closed, because scoring runs before the
    runner restores access, so a directory the agent locked could hide bytecode.
    """
    pending = deque([root])
    while pending:
        directory = pending.popleft()
        try:
            entries = sorted(directory.iterdir())
        except OSError:
            return f"could not read {directory.relative_to(root).as_posix()}"
        for entry in entries:
            if directory == root and entry.name == ".git":
                continue
            relative = entry.relative_to(root).as_posix()
            if entry.name == "__pycache__" or entry.name.endswith(".pyc"):
                return f"bytecode in the workspace: {relative}"
            try:
                mode = entry.lstat().st_mode
            except OSError:
                return f"could not read {relative}"
            if stat.S_ISDIR(mode):
                pending.append(entry)
    return None


def _python_not_run(trace: Trace, root: Path) -> AssertionResult:
    """No witness shows python ran: the wrapper's log, the commands, the workspace's bytecode.

    A pass is a lower bound: no recorded run, by these witnesses. See docs/reference/evals.md.
    """
    found = (
        _logged_call(trace.python_calls) or _named_in_command(trace.commands) or _bytecode(root)
    )
    if found is not None:
        return AssertionResult("python_not_run", passed=False, evidence=found)
    return AssertionResult(
        "python_not_run",
        passed=True,
        evidence="no python call logged, none named in a command, no bytecode in the workspace",
    )


def evaluate(  # noqa: PLR0913 -- one keyword per part of the trial an assertion reads
    assertion: Assertion,
    trace: Trace,
    *,
    skill: str,
    skill_dir: Path,
    installed: Path | None,
    trial_workspace: Path | None = None,
) -> AssertionResult:
    final = trace.final_message
    kind = assertion.type
    if kind == "skill_triggered":
        passed = skill in trace.skills_triggered
        return AssertionResult(kind, passed, f"triggered: {trace.skills_triggered}")
    if kind == "script_ran":
        return _script_ran(assertion, trace, skill_dir, installed)
    if kind == "python_not_run":
        # Required, so no caller can skip the bytecode check by leaving it out.
        if trial_workspace is None:
            msg = "python_not_run needs the trial's workspace (trial_workspace)"
            raise ValueError(msg)
        return _python_not_run(trace, trial_workspace)
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
