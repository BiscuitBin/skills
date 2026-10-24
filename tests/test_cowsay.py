"""Exercise the shipped script exactly as an agent runs it."""

import subprocess
import sys
from pathlib import Path

SCRIPT = Path(__file__).parents[1] / "skills/cowsay/scripts/cowsay.py"
COW = "    \\   ^__^\n     \\  (oo)\\_______\n        (__)\\       )\\/\\\n            ||----w |\n            ||     ||\n"


def say(text: str, *, stdin: bool = False) -> str:
    result = subprocess.run(
        [sys.executable, str(SCRIPT), *([] if stdin else ["--", text])],
        input=text if stdin else None,
        capture_output=True,
        text=True,
        check=True,
    )
    return result.stdout


def test_single_word() -> None:
    assert say("hello") == " _______\n< hello >\n -------\n" + COW


def test_long_text_wraps_at_word_boundary() -> None:
    assert say("one two three four five six seven eight nine ten") == (
        " _________________________________________\n"
        "/ one two three four five six seven eight \\\n"
        "\\ nine ten                                /\n"
        " -----------------------------------------\n" + COW
    )


def test_long_word_is_split() -> None:
    assert say("x" * 41).splitlines()[1:3] == ["/ " + "x" * 40 + " \\", "\\ x" + " " * 40 + "/"]


def test_multiline_keeps_blank_lines_and_stdin_matches_argument() -> None:
    expected = " ___\n/ a \\\n|   |\n\\ b /\n ---\n" + COW
    assert say("a\n\nb") == expected
    assert say("a\n\nb", stdin=True) == expected


def test_empty_input() -> None:
    assert say("") == " __\n<  >\n --\n" + COW
    assert say("", stdin=True) == say("")


def test_unicode_input() -> None:
    assert say("你好 🐄 café") == " ___________\n< 你好 🐄 café >\n -----------\n" + COW


def test_stdin_and_argument_preserve_the_same_trailing_newline() -> None:
    assert say("hi\n", stdin=True) == say("hi\n")
    assert say("hi\n") == " ____\n/ hi \\\n\\    /\n ----\n" + COW


def test_leading_hyphen_is_text() -> None:
    assert say("-x") == " ____\n< -x >\n ----\n" + COW
