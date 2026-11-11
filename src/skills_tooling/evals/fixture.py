"""Git fixtures: a small project with history that an eval trial starts in.

A fixture is evals/<skill>/fixtures/<name>/: a fixture.json naming the commits,
branch, index and working directory, and one full snapshot of the project per
tree under trees/<tree>/. The schema is in docs/reference/evals.md.
"""

import json
import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

from skills_tooling.evals import workspace
from skills_tooling.evals.grader import SKILL_WORD

if TYPE_CHECKING:
    from collections.abc import Iterable, Mapping

FIXTURE_KEYS = {"branch", "main", "commits", "staged", "worktree", "executable"}
COMMIT_KEYS = {"tree", "message"}
# Git's and the agent CLIs' own names, by their lowercase form: on a file system
# that folds case, a fixture's .Claude/ is the directory the skill is installed
# in, and its claude.md is the CLI's CLAUDE.md. A .gitattributes would outrank
# the root one that keeps fixture bytes as written.
RESERVED = {
    name.lower(): name
    for name in (
        ".claude",
        ".agents",
        ".codex",
        ".git",
        ".gitattributes",
        "CLAUDE.md",
        "CLAUDE.local.md",
        "AGENTS.md",
        "AGENTS.override.md",
        "SKILL.md",
    )
}
# What makes Codex report a failed command as denied by its sandbox, and the
# trial an infra_error (docs/reference/evals.md, Codex). A failing command
# mostly prints the project's own text, so no file or path may hold one.
DENIAL_KEYWORDS = (
    "operation not permitted",
    "permission denied",
    "read-only file system",
    "seccomp",
    "sandbox",
    "landlock",
    "failed to write file",
)
# A .gitignore line Git could read as a negation, which would outrank
# .git/info/exclude and show the installed skill's folder to Git. Wider than
# Git's own rule: a byte-order mark or leading whitespace does not hide the `!`.
NEGATION = re.compile(rb"^(?:\xef\xbb\xbf|[ \t\r\v\f])*!")


@dataclass(frozen=True)
class Commit:
    tree: str
    message: str


@dataclass(frozen=True)
class Fixture:
    name: str
    path: Path
    branch: str
    main: tuple[Commit, ...]
    commits: tuple[Commit, ...] = ()
    # The index's tree, else the branch tip's.
    staged: str | None = None
    # The working directory's tree, else the index's.
    worktree: str | None = None
    executable: frozenset[str] = frozenset()


def _unknown(data: dict[str, object], allowed: set[str], where: str) -> list[str]:
    return [f"{where}: unknown key {key!r}" for key in sorted(set(data) - allowed)]


def _tree_names(directory: Path) -> set[str]:
    trees = directory / "trees"
    if not trees.is_dir():
        return set()
    return {path.name for path in trees.iterdir() if path.is_dir()}


def _message(message: object) -> bool:
    """One nonempty paragraph, stored as written: git commit-tree keeps every byte."""
    return (
        isinstance(message, str)
        and message != ""
        and message == message.strip()
        and all(line.strip() for line in message.splitlines())
    )


def _commits(
    data: dict[str, object], key: str, trees: set[str], where: str, problems: list[str]
) -> tuple[Commit, ...]:
    raw = data.get(key, [])
    if not isinstance(raw, list) or (key == "main" and not raw):
        nonempty = "nonempty " if key == "main" else ""
        problems.append(f"{where}: {key} must be a {nonempty}list of commits")
        return ()
    found = []
    for index, item in enumerate(raw):
        at = f"{where}: {key}[{index}]"
        if not isinstance(item, dict):
            problems.append(f"{at}: a commit must be an object")
            continue
        problems += _unknown(item, COMMIT_KEYS, at)
        tree, message = item.get("tree"), item.get("message")
        if tree not in trees:
            problems.append(f"{at}: tree {tree!r} is not a directory under trees/")
        if not _message(message):
            problems.append(
                f"{at}: message must be a nonempty string of one paragraph, "
                "with no blank line and no leading or trailing whitespace"
            )
        problems += _skill_wording(str(message), "the message", at)
        found.append(Commit(str(tree), str(message)))
    return tuple(found)


def _branch(branch: object, root: Path, where: str) -> list[str]:
    if not isinstance(branch, str):
        return [f"{where}: branch must be a string"]
    # --branch refuses names `git branch` would, such as HEAD and -x, but expands
    # @{-1}; the plain form refuses @{ outright. Both must pass.
    valid = all(
        workspace.git("check-ref-format", *form, cwd=root).returncode == 0
        for form in (("--branch", branch), (f"refs/heads/{branch}",))
    )
    if not valid:
        return [f"{where}: branch {branch!r} is not a valid branch name"]
    # The builder creates refs/heads/main first, and a loose ref is a file, so
    # main/<x> cannot sit beside it; a file system that folds case makes Main main.
    folded = branch.lower()
    if folded == "main" or folded.startswith("main/"):
        return [f"{where}: branch {branch!r} clashes with main, which every fixture has"]
    return _skill_wording(branch, f"branch {branch!r}", where)


def case_clashes(paths: Iterable[str]) -> list[tuple[str, str]]:
    """Each path or directory that differs only in case from an earlier one, with that one.

    A file system that folds case, as macOS's and Windows' do, holds the two as one.
    """
    seen: dict[str, str] = {}
    clashes: list[tuple[str, str]] = []
    for path in sorted(paths):
        parts = path.split("/")
        for end in range(1, len(parts) + 1):
            prefix = "/".join(parts[:end])
            first = seen.setdefault(prefix.lower(), prefix)
            if first != prefix and (prefix, first) not in clashes:
                clashes.append((prefix, first))
    return clashes


def _skill_wording(text: str, what: str, where: str) -> list[str]:
    """The grader's arm-disclosure check would read the word as the skill arm's."""
    return [f"{where}: {what} holds 'skill' wording"] if SKILL_WORD.search(text) else []


def _denial(text: str, what: str, where: str) -> list[str]:
    folded = text.lower()
    return [
        f"{where}: {what} holds the sandbox denial keyword {keyword!r}"
        for keyword in DENIAL_KEYWORDS
        if keyword in folded
    ]


def _tree_file(path: str, file: Path, where: str) -> list[str]:
    """The problems with one file in a tree: its path, and its bytes."""
    problems = _tree_path(path, where)
    data = file.read_bytes()
    # Binary files too: the word reaches the agent whatever surrounds it.
    text = data.decode(errors="replace")
    problems += _skill_wording(text, "the file", where) + _denial(text, "the file", where)
    # Only the root file: the installed skill sits at the root, and a nested
    # .gitignore applies only below its own directory.
    if path.lower() == ".gitignore":
        problems += [
            f"{where}: line {number} is a negation ('!'), which would outrank "
            ".git/info/exclude; a fixture keeps a negation in a subdirectory's .gitignore"
            for number, line in enumerate(data.split(b"\n"), 1)
            if NEGATION.match(line)
        ]
    return problems


def _tree_path(path: str, where: str) -> list[str]:
    """The problems with one file's path inside its tree."""
    if not path.isascii():
        return [f"{where}: is not ASCII"]
    parts = path.split("/")
    problems = _skill_wording(path, "the path", where) + _denial(path, "the path", where)
    problems += [
        f"{where}: reserved name {RESERVED[part.lower()]!r}, ignoring case"
        for part in parts
        if part.lower() in RESERVED
    ]
    problems += [
        f"{where}: directory {part!r} ends in 'skills', ignoring case"
        for part in parts[:-1]
        if part.lower().endswith("skills")
    ]
    return problems


def _walk(directory: Path, where: str, problems: list[str]) -> dict[str, dict[str, Path]]:
    """Each tree's files by their path in it. Links are reported, never followed."""
    trees: dict[str, dict[str, Path]] = {}
    for current, dirnames, filenames in os.walk(directory):
        for name in sorted(dirnames + filenames):
            path = Path(current, name)
            relative = path.relative_to(directory).as_posix()
            if path.is_symlink():
                problems.append(f"{where}: {relative}: is a symlink")
                continue
            parts = relative.split("/")
            if parts[0] != "trees" or len(parts) < 3:  # noqa: PLR2004 -- trees/<tree>/<path>
                if name.lower() == ".gitattributes":
                    problems.append(f"{where}: {relative}: a fixture may hold no '.gitattributes'")
                continue
            if path.is_file():
                inner = "/".join(parts[2:])
                problems += _tree_file(inner, path, f"{where}: {relative}")
                trees.setdefault(parts[1], {})[inner] = path
    for tree, files in sorted(trees.items()):
        problems += [
            f"{where}: trees/{tree}/{path} clashes with trees/{tree}/{first}, ignoring case"
            for path, first in case_clashes(files)
        ]
    return trees


def _ignored(root: Path, directory: Path, where: str) -> list[str]:
    """Files the repository ignores, which are on the author's disk but in no checkout.

    Only when root is a repository's top level. Anywhere else, such as a test's
    temporary root inside this repository's ignored .tools/, no repository holds
    the suite, so no file of it is left out of a checkout.
    """
    toplevel = workspace.git("rev-parse", "--show-toplevel", cwd=root)
    if toplevel.returncode != 0 or Path(toplevel.stdout.strip()).resolve() != root.resolve():
        return []
    paths = sorted(
        path.relative_to(root).as_posix()
        for path in directory.rglob("*")
        if path.is_file() and not path.is_symlink()
    )
    if not paths:
        return []
    checked = workspace.git("check-ignore", "--no-index", "--", *paths, cwd=root)
    if checked.returncode not in (0, 1):
        return [f"{where}: git check-ignore failed: {checked.stderr.strip()}"]
    return [
        f"{where}: {path.removeprefix(where + '/')}: the repository ignores it, "
        "so a checkout would not have it"
        for path in checked.stdout.splitlines()
    ]


def _spec(
    root: Path, directory: Path, trees: Mapping[str, Mapping[str, Path]], problems: list[str]
) -> Fixture | None:
    path = directory / "fixture.json"
    where = path.relative_to(root).as_posix()
    if not path.is_file():
        problems.append(f"{directory.relative_to(root).as_posix()}: missing fixture.json")
        return None
    try:
        data = json.loads(path.read_text())
    except json.JSONDecodeError as error:
        problems.append(f"{where}: not valid JSON: {error}")
        return None
    if not isinstance(data, dict):
        problems.append(f"{where}: the fixture must be a JSON object")
        return None
    before = len(problems)
    problems += _unknown(data, FIXTURE_KEYS, where)
    names = _tree_names(directory)
    branch = data.get("branch")
    problems += _branch(branch, root, where)
    main = _commits(data, "main", names, where, problems)
    commits = _commits(data, "commits", names, where, problems)
    for key in ("staged", "worktree"):
        if key in data and data[key] not in names:
            problems.append(f"{where}: {key} {data[key]!r} is not a directory under trees/")
    executable = data.get("executable", [])
    if not isinstance(executable, list) or not all(isinstance(p, str) for p in executable):
        problems.append(f"{where}: executable must be a list of paths")
        executable = []
    problems += [
        f"{where}: executable {path!r} is not a file in any tree"
        for path in executable
        if not any(path in files for files in trees.values())
    ]
    if len(problems) > before:
        return None
    staged, worktree = data.get("staged"), data.get("worktree")
    return Fixture(
        name=directory.name,
        path=directory,
        branch=str(branch),
        main=main,
        commits=commits,
        staged=str(staged) if staged is not None else None,
        worktree=str(worktree) if worktree is not None else None,
        executable=frozenset(executable),
    )


def load_fixture(root: Path, directory: Path, problems: list[str]) -> Fixture | None:
    """Load and validate one fixture directory, adding every problem to problems."""
    where = directory.relative_to(root).as_posix()
    if directory.is_symlink():
        problems.append(f"{where}: is a symlink")
        return None
    before = len(problems)
    trees = _walk(directory, where, problems)
    problems += _ignored(root, directory, where)
    fixture = _spec(root, directory, trees, problems)
    return fixture if len(problems) == before else None


@dataclass(frozen=True)
class Fixtures:
    """A suite's fixtures directory, relative to the root, and every fixture in it by name."""

    where: str
    # None for a fixture that failed validation.
    found: Mapping[str, Fixture | None]


def load_fixtures(root: Path, skill: str, problems: list[str]) -> Fixtures:
    """Validate every fixture of evals/<skill>/, named by a case or not."""
    directory = root / "evals" / skill / "fixtures"
    found = {
        path.name: load_fixture(root, path, problems) for path in sorted(directory.glob("*/"))
    }
    return Fixtures(directory.relative_to(root).as_posix(), found)
