"""Scaffold a shipped skill, its eval suite and its marketplace entry: `just new-skill <name>`.

The skill passes the validator straight away, but every part the author still has
to write holds the validator's placeholder marker, and every starter eval case is
a placeholder that `just eval` refuses to run. See CONTRIBUTING.md.
"""

import argparse
import contextlib
import json
import shutil
import sys
import tempfile
from pathlib import Path
from typing import Any

import yaml

from skills_tooling.distribution import MARKETPLACE
from skills_tooling.validator import PLACEHOLDER, name_error

VERSION = "0.1.0"


class ScaffoldError(Exception):
    """The skill was not created; nothing was written."""


def _title(name: str) -> str:
    return " ".join(word.capitalize() for word in name.split("-"))


def _yaml_scalar(text: str) -> str:
    """The text as YAML reads it back: plain, or quoted when YAML would take another type.

    A name is only [a-z0-9-], so single quotes never need escaping.
    """
    try:
        plain = yaml.safe_load(text) == text
    except yaml.YAMLError, ValueError:  # An impossible date, such as 2026-99-99.
        plain = False
    return text if plain else f"'{text}'"


def _skill_md(name: str, description: str) -> str:
    return f"""---
name: {_yaml_scalar(name)}
description: {description}
license: MIT
---

# {_title(name)}

{PLACEHOLDER} Replace this stub with the instructions an agent follows once the
skill loads. Write the eval cases first and run a baseline without the skill;
CONTRIBUTING.md describes the loop.

## Steps

1. {PLACEHOLDER} The first thing the agent does.
"""


def _openai_yaml(name: str) -> str:
    return f"""interface:
  display_name: '{_title(name)}'
  short_description: '{PLACEHOLDER} A label for the skill picker'
"""


def _plugin_json(name: str, description: str) -> str:
    # A literal, not json.dumps, so the file is already in Prettier's format.
    return f"""{{
  "name": {json.dumps(name)},
  "version": {json.dumps(VERSION)},
  "description": {json.dumps(description)},
  "author": {{
    "name": "BiscuitBin"
  }},
  "license": "MIT",
  "skills": ["./"]
}}
"""


def _evals_json(name: str) -> str:
    def case(case_id: str, kind: str, prompt: str, *, should: bool) -> dict[str, object]:
        return {
            "id": case_id,
            "kind": kind,
            "prompt": f"{PLACEHOLDER} {prompt}",
            "should_trigger": should,
            "placeholder": True,
        }

    behaviour = case(
        "behaviour-placeholder",
        "behaviour",
        f"A task whose answer {name} should change.",
        should=True,
    )
    behaviour["expected_output"] = f"{PLACEHOLDER} What a good answer contains."
    behaviour["assertions"] = [
        {"type": "skill_triggered"},
        {"type": "output_contains", "value": f"{PLACEHOLDER} Text the answer must contain."},
    ]
    suite = {
        "skill_name": name,
        "evals": [
            case(
                "trigger-placeholder",
                "trigger",
                f"A request that should load {name}.",
                should=True,
            ),
            case(
                "no-trigger-placeholder",
                "trigger",
                f"A nearby request that should not load {name}.",
                should=False,
            ),
            behaviour,
        ],
    }
    return json.dumps(suite, indent=2) + "\n"


def _marketplace(root: Path, name: str) -> tuple[Path, str, dict[str, Any]]:
    path = root / MARKETPLACE
    try:
        text = path.read_text()
        marketplace = json.loads(text)
        if not isinstance(marketplace["plugins"], list):
            msg = "plugins is not a list"
            raise TypeError(msg)  # noqa: TRY301 -- reported with the parse errors below
        listed = {entry["name"] for entry in marketplace["plugins"]}
    except (OSError, ValueError, KeyError, TypeError) as error:
        msg = f"cannot read the plugin list in {MARKETPLACE}: {error}"
        raise ScaffoldError(msg) from error
    if name in listed:
        msg = f"{name} is already listed in {MARKETPLACE}"
        raise ScaffoldError(msg)
    return path, text, marketplace


def scaffold(root: Path, name: str) -> list[Path]:
    """Create the skill, its evals and its marketplace entry; return the files written."""
    problem = name_error(name)
    if problem is not None:
        msg = f"{problem}; use 1-64 lowercase letters and digits with single inner hyphens"
        raise ScaffoldError(msg)
    for parent in ("skills", "evals", "dev-skills/build"):
        if (root / parent / name).exists() or (root / parent / name).is_symlink():
            msg = f"{parent}/{name} already exists; pick another name"
            raise ScaffoldError(msg)
    path, original, marketplace = _marketplace(root, name)
    description = f"{PLACEHOLDER} Say what {name} does and when an agent should use it."
    files = {
        f"skills/{name}/SKILL.md": _skill_md(name, description),
        f"skills/{name}/agents/openai.yaml": _openai_yaml(name),
        f"skills/{name}/.claude-plugin/plugin.json": _plugin_json(name, description),
        f"evals/{name}/evals.json": _evals_json(name),
    }
    moved: list[Path] = []
    # Built inside the project, so each move is a rename on one filesystem; .tools/
    # is gitignored, so a staging directory left by a killed process stays out of Git.
    tools = root / ".tools/tmp"
    staging_parent = tools if tools.is_dir() else root
    with tempfile.TemporaryDirectory(dir=staging_parent, prefix=".new-skill-") as staging:
        try:
            for relative, text in files.items():
                target = Path(staging) / relative
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text(text)
            for parent in ("skills", "evals"):
                destination = root / parent / name
                (Path(staging) / parent / name).rename(destination)
                moved.append(destination)
            marketplace["plugins"].append(
                {
                    "name": name,
                    "description": description,
                    "source": f"./skills/{name}",
                    "version": VERSION,
                }
            )
            path.write_text(json.dumps(marketplace, indent=2, ensure_ascii=False) + "\n")
        except BaseException as error:
            # Interrupts too: a skill left without its marketplace entry fails just check.
            for directory in moved:
                shutil.rmtree(directory, ignore_errors=True)
            # Written back unconditionally: a write that failed part way can leave bytes
            # that no longer decode, so the file is never read to compare.
            with contextlib.suppress(OSError):
                path.write_text(original)
            if not isinstance(error, OSError):
                raise
            msg = f"could not write the skill, so nothing was kept: {error}"
            raise ScaffoldError(msg) from error
    return [root / relative for relative in files] + [path]


def main() -> None:
    parser = argparse.ArgumentParser(prog="just new-skill", description=__doc__)
    parser.add_argument("name", help="The skill's name: lowercase letters, digits and hyphens.")
    parser.add_argument("--root", type=Path, default=Path.cwd())
    args = parser.parse_args()
    root: Path = args.root.resolve()
    try:
        written = scaffold(root, args.name)
    except ScaffoldError as error:
        print(f"new-skill: {error}", file=sys.stderr)
        sys.exit(1)
    print(f"Created {args.name}:")
    for path in written:
        print(f"  {path.relative_to(root)}")
    print(
        f"Every {PLACEHOLDER} and every placeholder eval case is yours to write. "
        "CONTRIBUTING.md has the steps."
    )


if __name__ == "__main__":
    main()
