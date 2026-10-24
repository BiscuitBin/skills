"""Check marketplace versions against the shipped plugin manifests."""

import argparse
import json
import subprocess
import sys
from pathlib import Path


def check(root: Path, *, write: bool = False) -> None:
    """Keep the marketplace derived from the shipped plugin manifests."""
    path = root / ".claude-plugin/marketplace.json"
    marketplace = json.loads(path.read_text())
    shipped = {entry.name for entry in (root / "skills").iterdir() if entry.is_dir()}
    entries = marketplace["plugins"]
    if len(entries) != len(shipped) or {entry["name"] for entry in entries} != shipped:
        msg = "marketplace plugins must list exactly the shipped skills"
        raise ValueError(msg)
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
        if entry.get("version") != plugin["version"]:
            if not write:
                msg = f"{name}: marketplace version differs from plugin.json; run just format"
                raise ValueError(msg)
            entry["version"] = plugin["version"]
    if write:
        path.write_text(json.dumps(marketplace, indent=2) + "\n")


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
    print("Marketplace sources and plugin versions match.")


if __name__ == "__main__":
    main()
