"""The read rule both adapters share: whether a shell command confirmably read a skill's SKILL.md.

See docs/reference/evals.md. A read counts as a trigger only when the trace can
confirm it, so the rule is a lower bound on loads, with one exception:

- Only the shapes `outcome_is_the_read` accepts count. A read through a pipe
  (`cat …/SKILL.md | cat`), `awk`, an interpreter, or a copy read under another
  name records nothing, so a quiet case's pass means no confirmed load, not no load.
- A transforming `sed` counts: `sed` is a reader whatever its script, so
  `sed -n = …/SKILL.md` records a read although it printed none of the skill's text.
- `skills_read` matches a skill by name in any skills directory, not by its
  installed path; the location checks rule out a second copy.
"""

import os
import re
from pathlib import Path
from typing import TYPE_CHECKING

from skills_tooling.evals.assertions import ASSIGNMENT, command_list

if TYPE_CHECKING:
    from collections.abc import Iterator

# Programs that print a file's contents. A command that only names the path,
# such as ls, test or echo, is not a read. awk is not one: whether it opens an
# operand depends on its program, so an awk read does not count.
READERS = {"cat", "head", "tail", "sed", "nl", "less", "more", "bat"}
# `head` and `tail` print this header for each file when given several.
FILE_HEADER = re.compile(r"==> .* <==")
# A redirection can make a reader write the path, or send its output elsewhere.
# Quoting is gone by the time the words are checked, so a quoted < or > counts too.
REDIRECTION = re.compile(r"[<>]")
# Flags that make a reader print help or its version instead of the file.
NO_READ_FLAGS = {"--help", "--version", "-h", "-V"}
# Characters the shell expands, so the name in the text is not the directory read.
UNPLACEABLE = re.compile(r"[*?\[\]{}$~`]")
# The directory a skill directory sits in: .agents/skills, skills, dev-skills/build, .system.
SKILLS_DIR = re.compile(r"skills$|(?:^|/)dev-skills/build$|(?:^|/)\.system$")


def _read_paths(command: str) -> Iterator[Path]:
    """Each file a reader program names, after any `cd <dir>` before it.

    A path named by anything other than a reader, such as `ls`, `test` or
    `echo`, or as a `name=value` assignment, is not a read.
    """
    cwd = Path()
    for words, _ in command_list(command):
        if words[0] == "cd" and len(words) == 2:  # noqa: PLR2004 -- cd and its directory
            cwd = cwd / words[1]
            continue
        if Path(words[0]).name not in READERS:
            continue
        for word in words[1:]:
            if not word.startswith("-") and not ASSIGNMENT.fullmatch(word):
                yield Path(os.path.normpath(cwd / word))


def skills_read(command: str) -> tuple[list[str], bool]:
    """The skill of each SKILL.md in a skills directory a reader program names,
    and whether it names a SKILL.md whose skill directory the text cannot place.

    `cd <dir> && cat SKILL.md` names <dir>/SKILL.md. A path counts only when
    its grandparent is a skills directory (`.agents/skills`, `skills`,
    `dev-skills/build`, `.system`), so `/tmp/cowsay/SKILL.md` is not a skill, nor unplaceable. A
    path the text cannot place (`SKILL.md` or `cowsay/SKILL.md` run in another
    `workdir`, `../SKILL.md`, a glob, a variable) names no skill; it can still back
    Codex's own implicit event (see `codex.parse_stream`).
    """
    skills = []
    unplaceable = False
    for path in _read_paths(command):
        if path.name != "SKILL.md":
            continue
        skill = path.parent.name
        if skill in ("", "..") or UNPLACEABLE.search(skill):
            unplaceable = True
        elif SKILLS_DIR.search(path.parent.parent.as_posix()):
            skills.append(skill)
        elif UNPLACEABLE.search(path.parent.parent.name) or (
            not path.is_absolute() and path.parent.parent.name in ("", "..")
        ):
            # `$dir/cowsay/SKILL.md`, or `cowsay/SKILL.md` run in the skills
            # directory: the skill is named, its directory is not.
            unplaceable = True
    return skills, unplaceable


def pwd_lines(command: str) -> int:
    """How many lines the `pwd`s before a command's last part print."""
    return sum(words == ["pwd"] for words, _ in command_list(command)[:-1])


def outcome_is_the_read(command: str, output: str) -> bool:
    """Whether the command's exit status and output show its read printed something.

    Only `cd <dir>` and `pwd` may come before the read, joined by `&&`, and
    the read comes last. `cd` prints nothing and `pwd` one line, so the output
    must have a line more than the `pwd`s print, not counting blank lines or
    the file headers `head` and `tail` print, which are not the file's content.
    After `||`, `;`, `&` or a pipe, or after any other command, a command can
    exit 0 and print something whatever the read did. A redirection, or a help
    or version flag, can make a reader not read. Every other shape is not a read
    the trace can confirm.
    """
    parts = command_list(command)
    if not parts or any(operator not in ("&&", "") for _, operator in parts):
        return False
    *before, (read, _) = parts
    printed = [
        line for line in output.split("\n") if line.strip() and not FILE_HEADER.fullmatch(line)
    ]
    return (
        all(
            words == ["pwd"]
            # `cd -` prints the directory it changes to.
            or (words[0] == "cd" and len(words) == 2 and not words[1].startswith("-"))  # noqa: PLR2004 -- cd and its directory
            for words, _ in before
        )
        and Path(read[0]).name in READERS
        and not any(REDIRECTION.search(word) or word in NO_READ_FLAGS for word in read[1:])
        and len(printed) > pwd_lines(command)
    )
