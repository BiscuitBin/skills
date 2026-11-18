"""Git fixture trees are data: no line-ending conversion, and no linter, type checker or test run.

A fixture tree is a snapshot of a small project that the eval harness commits
into a trial's workspace (src/skills_tooling/evals/fixture.py). Its bytes are
hashed into `evals_sha256`, so Git must store them as written, and its code is
not this repo's code. Fixture trees sit in two layouts, a skill's
`evals/<skill>/fixtures/<name>/trees/` and the harness's own test fixtures under
`tests/fixtures/evals/git/<name>/trees/`, and each tool names both in its own
syntax. A reworded pattern would lint a fixture, or convert its line endings,
without any error.
"""

import json
import re
import tomllib
from pathlib import Path
from typing import Any

import pytest
import yaml

from skills_tooling.evals import workspace

ROOT = Path(__file__).parents[1]
LAYOUTS = ("evals/*/fixtures/*/trees/**", "tests/fixtures/evals/git/*/trees/**")
# Paths no skill holds yet, one per layout, so both are checked from the start.
SAMPLES = (
    "evals/x/fixtures/f/trees/t/a.py",
    "tests/fixtures/evals/git/small-tally/trees/start/tally.py",
)
NOT_A_TREE = "tests/fixtures/evals/grading/fake_claude.py"
EXCLUDED_HOOKS = (
    "check-executables-have-shebangs",
    "check-shebang-scripts-are-executable",
    "check-merge-conflict",
)


def tree_files() -> list[str]:
    found = {
        path.relative_to(ROOT).as_posix()
        for layout in LAYOUTS
        for path in ROOT.glob(layout)
        if path.is_file()
    }
    return sorted(found | set(SAMPLES))


def test_the_layout_globs_find_the_shipped_fixture_trees() -> None:
    # Otherwise every check below could pass on the two sample paths alone.
    shipped = [p for p in tree_files() if p not in SAMPLES]
    assert "tests/fixtures/evals/git/small-tally/trees/average-wip/notes.txt" in shipped
    assert "tests/fixtures/evals/git/clean-branch/trees/start/greet.py" in shipped


def hooks() -> dict[str, dict[str, Any]]:
    config = yaml.safe_load((ROOT / ".pre-commit-config.yaml").read_text())
    return {hook["id"]: hook for repo in config["repos"] for hook in repo["hooks"]}


def test_git_converts_no_line_endings_in_any_fixture_tree() -> None:
    attributes = ("text", "eol", "ident", "filter", "working-tree-encoding")
    files = tree_files()
    checked = workspace.git("check-attr", *attributes, "--", *files, cwd=ROOT)
    assert checked.returncode == 0, checked.stderr
    expected = [
        f"{path}: {name}: {'unset' if name == 'text' else 'unspecified'}"
        for path in files
        for name in attributes
    ]
    assert checked.stdout.splitlines() == expected


@pytest.mark.parametrize("source", ["mypy", *EXCLUDED_HOOKS, "markdownlint"])
def test_each_exclusion_regex_matches_both_layouts_only(source: str) -> None:
    if source == "mypy":
        pyproject = tomllib.loads((ROOT / "pyproject.toml").read_text())
        pattern = re.compile(pyproject["tool"]["mypy"]["exclude"])
    else:
        pattern = re.compile(hooks()[source]["exclude"])
    assert [path for path in tree_files() if not pattern.search(path)] == []
    assert pattern.search(NOT_A_TREE) is None


def test_markdownlint_hook_still_skips_claude_md() -> None:
    pattern = re.compile(hooks()["markdownlint"]["exclude"])
    assert pattern.search("CLAUDE.md")
    assert pattern.search("docs/CLAUDE.md") is None


def test_ruff_prettier_and_markdownlint_ignore_both_layouts() -> None:
    pyproject = tomllib.loads((ROOT / "pyproject.toml").read_text())
    prettier = (ROOT / ".prettierignore").read_text().splitlines()
    # The file is JSONC: every comment here is a whole line.
    jsonc = (ROOT / ".markdownlint-cli2.jsonc").read_text()
    markdownlint = json.loads(re.sub(r"(?m)^\s*//.*$", "", jsonc))
    for globs in (pyproject["tool"]["ruff"]["extend-exclude"], prettier, markdownlint["ignores"]):
        assert set(LAYOUTS) <= set(globs)


def test_pytest_collects_nothing_under_fixtures_and_keeps_its_default_skips() -> None:
    pyproject = tomllib.loads((ROOT / "pyproject.toml").read_text())
    skipped = pyproject["tool"]["pytest"]["ini_options"]["norecursedirs"]
    defaults = ["*.egg", ".*", "_darcs", "build", "CVS", "dist", "node_modules", "venv", "{arch}"]
    assert skipped == [*defaults, "fixtures"]
