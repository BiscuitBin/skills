"""Git fixtures: a small project with history that an eval trial starts in.

A fixture is evals/<skill>/fixtures/<name>/: a fixture.json naming the commits,
branch, index and working directory, and one full snapshot of the project per
tree under trees/<tree>/. The schema is in docs/reference/evals.md.
"""

import hashlib
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

    from skills_tooling.evals.adapter import TrialPaths

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
# mostly prints the project's own text, so no file, path, branch or commit
# message may hold one.
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

# Bumped whenever build() gives other objects, refs or files for the same
# fixture: identity, dates, plumbing. It goes into evals_sha256.
FIXTURE_FORMAT = 1
# A neutral author and committer: "Eval Harness" would tell the agent it is
# being evaluated. These override workspace.GIT_ENV's.
IDENTITY = {
    "GIT_AUTHOR_NAME": "Robin Hale",
    "GIT_AUTHOR_EMAIL": "robin@example.com",
    "GIT_COMMITTER_NAME": "Robin Hale",
    "GIT_COMMITTER_EMAIL": "robin@example.com",
}
# 2026-01-01T00:00:00Z. Commit n, counted across main and then the branch, is
# dated n hours later. Every working file's mtime is this too: a past time keeps
# Git's racy-clean check from rehashing a file.
FIRST_COMMIT = 1767225600
COMMIT_STEP = 3600
# Both arms get the same file, and the baseline has neither directory, so it
# tells the agent nothing about its arm. See docs/explanation/eval-isolation.md.
EXCLUDE = "/.claude/\n/.agents/\n"
# Git ignores reflogs for these calls, so .git/logs never exists.
NO_REFLOG = ("-c", "core.logAllRefUpdates=false")
# Added to the agent's environment in a fixture trial, in both arms. The agent's
# git reads no system or global config and no system attributes, which differ
# from machine to machine (Apple's git has a gitattributes that changes diff
# hunk headers), and takes no optional lock, which Codex's sandbox denies on
# .git. A trial with no fixture keeps the environment it had.
AGENT_GIT_ENV = {
    "GIT_OPTIONAL_LOCKS": "0",
    "GIT_CONFIG_NOSYSTEM": "1",
    "GIT_CONFIG_GLOBAL": os.devnull,
    "GIT_ATTR_NOSYSTEM": "1",
}


@dataclass(frozen=True)
class Commit:
    tree: str
    message: str


@dataclass(frozen=True)
class Fixture:
    """A validated fixture: its directory, and what its fixture.json names."""

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

    @property
    def tip_tree(self) -> str:
        return (self.commits or self.main)[-1].tree

    @property
    def index_tree(self) -> str:
        return self.staged or self.tip_tree

    @property
    def working_tree(self) -> str:
        return self.worktree or self.index_tree

    def files(self, tree: str) -> dict[str, Path]:
        """The tree's files, by their path in it."""
        base = self.path / "trees" / tree
        return {p.relative_to(base).as_posix(): p for p in sorted(base.rglob("*")) if p.is_file()}

    def mode(self, path: str) -> int:
        """The path's git mode, in every tree that has it. Modes on disk are ignored."""
        return 0o100755 if path in self.executable else 0o100644


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
        if not isinstance(tree, str) or tree not in trees:
            problems.append(f"{at}: tree {tree!r} is not a directory under trees/")
        if not _message(message):
            problems.append(
                f"{at}: message must be a nonempty string of one paragraph, "
                "with no blank line and no leading or trailing whitespace"
            )
        problems += _skill_wording(str(message), "the message", at)
        problems += _denial(str(message), "the message", at)
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
    return _skill_wording(branch, f"branch {branch!r}", where) + _denial(
        branch, f"branch {branch!r}", where
    )


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
            # benchmark.tree_sha256 skips these, so evals_sha256 would miss a
            # change to one that the build writes, whatever the ignore check says.
            if "__pycache__" in parts and path.is_file():
                problems.append(
                    f"{where}: {relative}: a fixture may hold no '__pycache__', "
                    "which evals_sha256 leaves out"
                )
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
        if key in data and (not isinstance(data[key], str) or data[key] not in names):
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


def _git(workspace_dir: Path, *args: str, env: Mapping[str, str] | None = None) -> str:
    result = workspace.git(*args, cwd=workspace_dir, env=env)
    if result.returncode != 0:
        msg = f"git {' '.join(args)} failed in {workspace_dir}: {result.stderr.strip()}"
        raise RuntimeError(msg)
    return result.stdout.strip()


def _write_tree(fixture: Fixture, tree: str, trial: TrialPaths) -> str:
    """Store the tree's files as blobs, by path, with no filters, and return the tree's id."""
    files = fixture.files(tree)
    # A temporary index, so the trial's own index is written once, by read-tree.
    index = trial.tmp / "fixture-index"
    env = {"GIT_INDEX_FILE": str(index)}
    try:
        if files:
            # The ids come back one per line, in argument order. The files sit outside
            # the work tree, and --no-filters stores their bytes as they are.
            stored = _git(
                trial.workspace,
                "hash-object",
                "-w",
                "--no-filters",
                "--",
                *map(str, files.values()),
            )
            entries = [
                argument
                for (path, blob) in zip(files, stored.splitlines(), strict=True)
                for argument in ("--cacheinfo", f"{fixture.mode(path):o},{blob},{path}")
            ]
            _git(trial.workspace, "update-index", "--add", *entries, env=env)
        return _git(trial.workspace, "write-tree", env=env)
    finally:
        index.unlink(missing_ok=True)


def build(fixture: Fixture, trial: TrialPaths) -> workspace.FixtureFiles:
    """Give a fresh trial workspace the fixture's history, index and working directory.

    Plumbing only, with a fixed identity and dates, so a fixture's commits are
    the same in every trial, run and machine. Nothing but the fixture's files
    and .git is written to the workspace, and nothing is left in trial.tmp.
    Returns the working directory as written, from the fixture's own bytes:
    the preflight and the grader compare the workspace with it.
    """
    work = trial.workspace
    object_format = _git(work, "rev-parse", "--show-object-format")
    if object_format != "sha1":
        msg = f"a fixture is built in a sha1 repository; {work} uses {object_format}"
        raise RuntimeError(msg)
    trees: dict[str, str] = {}

    def tree_id(tree: str) -> str:
        if tree not in trees:
            trees[tree] = _write_tree(fixture, tree, trial)
        return trees[tree]

    tips: list[str] = []
    for number, commit in enumerate((*fixture.main, *fixture.commits)):
        date = f"@{FIRST_COMMIT + number * COMMIT_STEP} +0000"
        parent = ("-p", tips[-1]) if tips else ()
        env = {**IDENTITY, "GIT_AUTHOR_DATE": date, "GIT_COMMITTER_DATE": date}
        tips.append(
            _git(work, "commit-tree", tree_id(commit.tree), *parent, "-m", commit.message, env=env)
        )
    _git(work, *NO_REFLOG, "update-ref", "refs/heads/main", tips[len(fixture.main) - 1])
    _git(work, *NO_REFLOG, "update-ref", f"refs/heads/{fixture.branch}", tips[-1])
    _git(work, *NO_REFLOG, "symbolic-ref", "HEAD", f"refs/heads/{fixture.branch}")
    _git(work, "read-tree", tree_id(fixture.index_tree))
    written: dict[str, tuple[str, int]] = {}
    for path, source in fixture.files(fixture.working_tree).items():
        target = work / path
        target.parent.mkdir(parents=True, exist_ok=True)
        data = source.read_bytes()
        target.write_bytes(data)
        target.chmod(fixture.mode(path) & 0o777)
        os.utime(target, (FIRST_COMMIT, FIRST_COMMIT))
        written[path] = (hashlib.sha256(data).hexdigest(), fixture.mode(path))
    # The index takes each file's stat data now, so a later `git status` has
    # nothing to write. -q: a file that differs from the index is not an error.
    _git(work, "update-index", "-q", "--refresh")
    (work / ".git/info").mkdir(exist_ok=True)
    (work / ".git/info/exclude").write_text(EXCLUDE)
    return written
