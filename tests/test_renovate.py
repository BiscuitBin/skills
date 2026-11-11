"""Renovate's custom managers still find every coupled pin, and the copies agree.

Renovate's built-in managers do not read the README, the Justfile or package.json's
allowScripts key, and read the workflows' tool versions under other dependency
names, so renovate.json tracks all of them with regex managers. A reworded line
would drop a pin from Renovate's view without any error, and a bump would then
miss that copy. See docs/adr/0016-dependency-updates-via-renovate.md.
"""

import json
import re
import shutil
import subprocess
import tomllib
from collections import defaultdict
from pathlib import Path
from typing import Any

import pytest

ROOT = Path(__file__).parents[1]
CONFIG: dict[str, Any] = json.loads((ROOT / "renovate.json").read_text())
MANAGERS: list[dict[str, Any]] = CONFIG["customManagers"]
# A JavaScript named group, `(?<name>`, but not a lookbehind, `(?<=` or `(?<!`.
JS_GROUP = re.compile(r"\(\?<(?![=!])")


def tracked_files() -> list[str]:
    git = shutil.which("git")
    assert git
    listing = subprocess.run(
        [git, "ls-files", "-z"], cwd=ROOT, capture_output=True, text=True, check=True
    )
    return [path for path in listing.stdout.split("\0") if path]


def file_pattern(pattern: str) -> re.Pattern[str]:
    # Every pattern here is a /regex/ anchored at the repo root, so a glob or an
    # unanchored regex fails here rather than matching files the test never reads.
    assert pattern.startswith("/^") and pattern.endswith("$/"), pattern
    return re.compile(pattern[1:-1])


def captures(manager: dict[str, Any]) -> dict[str, list[str]]:
    """Every `currentValue` the manager captures, by the tracked file it came from."""
    patterns = [file_pattern(p) for p in manager["managerFilePatterns"]]
    files = [f for f in tracked_files() if any(p.fullmatch(f) for p in patterns)]
    assert files, f"{manager['description']}: no tracked file matches"
    found: dict[str, list[str]] = {}
    for name in files:
        text = (ROOT / name).read_text()
        found[name] = [
            match["currentValue"]
            for string in manager["matchStrings"]
            for match in re.finditer(JS_GROUP.sub("(?P<", string), text)
        ]
    return found


@pytest.fixture(scope="module")
def by_dep() -> dict[str, list[str]]:
    values: dict[str, list[str]] = defaultdict(list)
    for manager in MANAGERS:
        for found in captures(manager).values():
            values[manager["depNameTemplate"]].extend(found)
    return values


@pytest.mark.parametrize("manager", MANAGERS, ids=[m["description"] for m in MANAGERS])
def test_every_custom_manager_matches_in_every_file_it_targets(manager: dict[str, Any]) -> None:
    assert manager["customType"] == "regex"
    assert all("(?<currentValue>" in s for s in manager["matchStrings"])
    empty = [name for name, found in captures(manager).items() if not found]
    assert empty == [], f"{manager['description']}: no match in {empty}"


def test_the_uv_copies_agree(by_dep: dict[str, list[str]]) -> None:
    pyproject = tomllib.loads((ROOT / "pyproject.toml").read_text())
    required = pyproject["tool"]["uv"]["required-version"].removeprefix("==")
    # The README, the pyproject and both workflows.
    assert len(by_dep["uv"]) >= 4
    assert set(by_dep["uv"]) == {required}
    assert pyproject["build-system"]["requires"] == [f"uv_build=={required}"]


def test_the_just_copies_agree(by_dep: dict[str, list[str]]) -> None:
    justfile = re.search(r"required='just ([^']+)'", (ROOT / "Justfile").read_text())
    assert justfile
    assert len(by_dep["casey/just"]) >= 4
    assert set(by_dep["casey/just"]) == {justfile[1]}


def test_the_readme_node_and_npm_match_the_pins(by_dep: dict[str, list[str]]) -> None:
    package = json.loads((ROOT / "package.json").read_text())
    node = (ROOT / ".node-version").read_text().strip()
    assert package["engines"] == {"node": node, "npm": package["engines"]["npm"]}
    assert package["packageManager"] == f"npm@{package['engines']['npm']}"
    assert by_dep["node"] == [node]
    assert by_dep["npm"] == [package["engines"]["npm"]]


def test_the_allow_scripts_key_names_the_installed_claude_code(
    by_dep: dict[str, list[str]],
) -> None:
    package = json.loads((ROOT / "package.json").read_text())
    pinned = package["devDependencies"]["@anthropic-ai/claude-code"]
    assert by_dep["@anthropic-ai/claude-code"] == [pinned]
    assert list(package["allowScripts"]) == [f"@anthropic-ai/claude-code@{pinned}"]


def rules_for(**match: list[str]) -> list[dict[str, Any]]:
    rules: list[dict[str, Any]] = CONFIG["packageRules"]
    return [r for r in rules if all(r.get(k) == v for k, v in match.items())]


def test_uv_groups_with_its_build_backend_by_normalized_name() -> None:
    # Renovate matches matchPackageNames against the PEP 503-normalized name, so
    # `uv_build` would match nothing and the backend would get a PR of its own.
    [rule] = [r for r in CONFIG["packageRules"] if r.get("groupName") == "uv"]
    assert rule["matchPackageNames"] == ["uv", "uv-build"]


def test_the_actions_manager_leaves_the_workflow_tool_versions_to_the_regex_managers() -> None:
    # The github-actions manager also reads setup-uv's `version` and setup-just's
    # `just-version` (dep type uses-with). Left on, it would bump the CI copies alone.
    [rule] = rules_for(matchManagers=["github-actions"], matchDepTypes=["uses-with"])
    assert rule["enabled"] is False
    [group] = [r for r in CONFIG["packageRules"] if r.get("groupName") == "GitHub Actions"]
    assert group["matchDepTypes"] == ["action"]


def test_uv_resolves_only_releases_as_old_as_renovate_proposes() -> None:
    # Renovate passes no age limit to uv, so lockfile maintenance's `uv lock
    # --upgrade` would take a transitive release published that morning.
    pyproject = tomllib.loads((ROOT / "pyproject.toml").read_text())
    assert pyproject["tool"]["uv"]["exclude-newer"] == CONFIG["minimumReleaseAge"]


def walk(node: object) -> list[tuple[str, object]]:
    if isinstance(node, dict):
        return [pair for k, v in node.items() for pair in [(k, v), *walk(v)]]
    if isinstance(node, list):
        return [pair for item in node for pair in walk(item)]
    return []


def test_nothing_is_ever_automerged() -> None:
    pairs = walk(CONFIG)
    assert CONFIG["automerge"] is False
    assert [v for k, v in pairs if k == "automerge" and v is not False] == []
    presets = [v for k, v in pairs if k == "extends"]
    assert [p for p in presets if "automerge" in str(p).lower()] == []
