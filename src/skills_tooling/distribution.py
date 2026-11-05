"""Check marketplace versions against the shipped plugin manifests."""

import argparse
import json
import subprocess
import sys
from pathlib import Path

MARKETPLACE = ".claude-plugin/marketplace.json"


def _missing(root: Path, name: str) -> str:
    """What to add for a shipped skill the marketplace does not list."""
    manifest = f"skills/{name}/.claude-plugin/plugin.json"
    exists = (root / manifest).is_file()
    try:
        plugin = json.loads((root / manifest).read_text())
        description, version = plugin["description"], plugin["version"]
        create = ""
    except (OSError, ValueError, KeyError, TypeError) as error:
        if exists:
            return (
                f"skills/{name} is not listed in {MARKETPLACE}, and its manifest cannot be read."
                f"\n  Fix {manifest} so it has a name, version and description ({error!r}),"
                " then run this check again for the entry to add."
            )
        description, version = "<one line on what the skill does>", "0.1.0"
        plugin = {
            "name": name,
            "version": version,
            "description": description,
            "author": {"name": "BiscuitBin"},
            "license": "MIT",
            "skills": ["./"],
        }
        create = f"\n  Create {manifest} (set its description):\n    {json.dumps(plugin)}"
    entry = {
        "name": name,
        "description": description,
        "source": f"./skills/{name}",
        "version": version,
    }
    return (
        f"skills/{name} is not listed in {MARKETPLACE}.{create}"
        f"\n  Add this entry to its plugins:\n    {json.dumps(entry)}"
    )


def check(root: Path, *, write: bool = False) -> None:
    """Keep the marketplace derived from the shipped plugin manifests."""
    path = root / MARKETPLACE
    marketplace = json.loads(path.read_text())
    shipped = {entry.name for entry in (root / "skills").iterdir() if entry.is_dir()}
    entries = marketplace["plugins"]
    names = [entry["name"] for entry in entries]
    problems = [
        f"{name} is listed more than once in {MARKETPLACE}; keep one entry"
        for name in sorted({name for name in names if names.count(name) > 1})
    ]
    problems += [_missing(root, name) for name in sorted(shipped - set(names))]
    problems += [
        f"remove the {name} entry from {MARKETPLACE}; skills/{name} does not exist"
        for name in sorted(set(names) - shipped)
    ]
    if problems:
        raise ValueError(
            "marketplace plugins must list exactly the shipped skills:\n" + "\n".join(problems)
        )
    for entry in entries:
        name = entry["name"]
        if entry["source"] != f"./skills/{name}":
            msg = f"{name}: plugin source must be ./skills/{name} to exclude repo files"
            raise ValueError(msg)
        plugin = json.loads((root / "skills" / name / ".claude-plugin/plugin.json").read_text())
        if (
            plugin["name"] != name
            or not isinstance(plugin["version"], str)
            or not plugin["version"]
        ):
            msg = f"{name}: plugin manifest needs a matching name and a nonempty version"
            raise ValueError(msg)
        # plugin.json is the source of both; a manifest without a description has none to copy.
        for field in ("version", "description"):
            if field not in plugin or entry.get(field) == plugin[field]:
                continue
            if not write:
                msg = f"{name}: marketplace {field} differs from plugin.json; run just format"
                raise ValueError(msg)
            entry[field] = plugin[field]
    if write:
        path.write_text(json.dumps(marketplace, indent=2, ensure_ascii=False) + "\n")


def require_committed(root: Path) -> None:
    """Reject local source changes that cannot enter committed-tree installs."""
    status = subprocess.run(
        [  # noqa: S607 -- git is a documented host prerequisite
            "git",
            "status",
            "--porcelain",
            "--untracked-files=all",
            "--",
            "skills",
            ".claude-plugin",
            "dev-skills",
            ".agents/skills",
            ".claude/skills",
        ],
        cwd=root,
        capture_output=True,
        text=True,
        check=True,
    )
    if status.stdout:
        msg = "Commit distribution source changes before install round trips:\n" + status.stdout
        raise ValueError(msg)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--write", action="store_true", help="Used only by just format.")
    parser.add_argument(
        "--committed", action="store_true", help="Require committed install sources."
    )
    args = parser.parse_args()
    try:
        check(args.root, write=args.write)
        if args.committed:
            require_committed(args.root)
    except (OSError, ValueError, KeyError, TypeError, subprocess.CalledProcessError) as error:
        print(f"distribution: {error}", file=sys.stderr)
        sys.exit(1)
    print("Marketplace sources, plugin versions and descriptions match.")


if __name__ == "__main__":
    main()
