#!/usr/bin/env python3
"""Pick a cross-model reviewer and run it read-only.

Subcommands:

  select --implementer {claude-code,codex,other} [--model ID]
      Print the reviewer the cross-model rule picks, as JSON.
  run --implementer ... [--model ID] --brief FILE [--root DIR] [--timeout SECONDS]
      Run that reviewer on the brief (sent on stdin), save its final output
      to <root>/ai_tmp/review-<timestamp>-<reviewer>.md, and print JSON with
      the findings path and the selection. If the reviewer fails at runtime,
      try the other reviewer when the cross-model rule allows it. Fails if
      any file outside ai_tmp/ and .git/ changed during the review.

Exit codes: 0 ok, 1 reviewer modified the worktree or other error,
2 cross-model review unavailable. Python 3 standard library only.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
from collections.abc import Callable, Mapping
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal, get_args

Family = Literal["anthropic", "openai", "other"]
Implementer = Literal["claude-code", "codex", "other"]
Reviewer = Literal["codex", "claude"]

# A probe returns None when the reviewer is usable, or the reason it is not.
Probe = Callable[[Reviewer], "str | None"]

SCRATCH_DIR = "ai_tmp"
SNAPSHOT_SKIP = {".git", SCRATCH_DIR}
EXIT_MODIFIED = 1
EXIT_UNAVAILABLE = 2


@dataclass(frozen=True)
class ReviewerSpec:
    model: str
    family: Family
    auth_args: tuple[str, ...]


REVIEWERS: dict[Reviewer, ReviewerSpec] = {
    "codex": ReviewerSpec(model="gpt-6-astra", family="openai", auth_args=("login", "status")),
    "claude": ReviewerSpec(model="claude-opus-5-5", family="anthropic", auth_args=("auth", "status")),
}

PREFERRED: dict[Family, Reviewer] = {"anthropic": "codex", "openai": "claude", "other": "codex"}

IMPLEMENTER_DEFAULT_FAMILY: dict[Implementer, Family] = {
    "claude-code": "anthropic",
    "codex": "openai",
}


def reviewer_command(reviewer: Reviewer, root: Path) -> list[str]:
    """The read-only invocation. Read-only comes from these flags, not from the brief."""
    if reviewer == "codex":
        return [
            "codex", "exec",
            "-m", REVIEWERS["codex"].model,
            "--sandbox", "read-only",
            "--ephemeral",
            "--ignore-user-config",  # user hooks and MCP servers run outside the sandbox
            "-C", str(root),
            "-",
        ]  # fmt: skip
    return [
        "claude", "-p",
        "--model", REVIEWERS["claude"].model,
        "--tools", "Read,Grep,Glob",
        "--restricted",
        "--strict-mcp-config",
        "--permission-prompts", "none",
        "--output-format", "text",
    ]  # fmt: skip


class ReviewUnavailable(Exception):
    """No reviewer from a different model family can be used."""


@dataclass(frozen=True)
class Selection:
    reviewer: Reviewer
    model: str
    implementer: Implementer
    implementer_model: str | None
    implementer_family: Family
    fallback_used: bool
    notes: list[str] = field(default_factory=list)


def model_family(model: str) -> Family:
    name = model.strip().lower()
    if name.startswith("claude-"):
        return "anthropic"
    if name.startswith(("gpt-", "codex")) or re.match(r"o\d", name):
        return "openai"
    return "other"


def implementer_family(implementer: Implementer, model: str | None) -> Family:
    if model:
        return model_family(model)
    if implementer in IMPLEMENTER_DEFAULT_FAMILY:
        return IMPLEMENTER_DEFAULT_FAMILY[implementer]
    raise ReviewUnavailable(
        "cross-model review unavailable: an 'other' implementer must pass --model "
        "with the model it is actually running"
    )


def select_reviewer(
    implementer: Implementer,
    model: str | None,
    probe: Probe,
    failed: Mapping[Reviewer, str] | None = None,
) -> Selection:
    """Apply the cross-model rule. `failed` holds reviewers that already failed at runtime."""
    family = implementer_family(implementer, model)
    preferred = PREFERRED[family]
    candidates: list[Reviewer] = [preferred, *(r for r in REVIEWERS if r != preferred)]
    notes: list[str] = []
    for candidate in candidates:
        spec = REVIEWERS[candidate]
        if spec.family == family:
            notes.append(
                f"{candidate} ({spec.model}) refused: same model family as the implementer ({family})"
            )
            continue
        reason = (failed or {}).get(candidate) or probe(candidate)
        if reason:
            notes.append(f"{candidate} unavailable: {reason}")
            continue
        if candidate != preferred:
            notes.append(f"fell back from {preferred} to {candidate}")
        return Selection(
            reviewer=candidate,
            model=spec.model,
            implementer=implementer,
            implementer_model=model,
            implementer_family=family,
            fallback_used=candidate != preferred,
            notes=notes,
        )
    raise ReviewUnavailable("cross-model review unavailable:\n- " + "\n- ".join(notes))


def default_probe(reviewer: Reviewer) -> str | None:
    """Check the reviewer CLI is on PATH and logged in."""
    spec = REVIEWERS[reviewer]
    binary = shutil.which(reviewer)
    if binary is None:
        return f"{reviewer} not found on PATH"
    shown = " ".join((reviewer, *spec.auth_args))
    try:
        result = subprocess.run(
            [binary, *spec.auth_args], capture_output=True, text=True, timeout=60, check=False
        )
    except (OSError, subprocess.TimeoutExpired) as error:
        return f"`{shown}` failed: {error}"
    if result.returncode != 0:
        return f"{reviewer} is not authenticated (`{shown}` exited {result.returncode})"
    if reviewer == "claude":
        try:
            status = json.loads(result.stdout)
        except json.JSONDecodeError:
            status = None
        if isinstance(status, dict) and status.get("loggedIn") is False:
            return f"{reviewer} is not authenticated (`{shown}` reports loggedIn: false)"
    return None


def snapshot(root: Path) -> dict[str, str]:
    """Map every path under root (except .git/ and ai_tmp/) to a content hash.

    Walks the filesystem rather than asking git, so ignored and untracked files
    count too. Symlinks are recorded by target and never followed.
    """
    entries: dict[str, str] = {}
    for current, dirs, files in os.walk(root):
        here = Path(current)
        if here == root:
            dirs[:] = [d for d in dirs if d not in SNAPSHOT_SKIP]
        for name in [*dirs, *files]:
            path = here / name
            rel = path.relative_to(root).as_posix()
            if path.is_symlink():
                entries[rel] = "link:" + os.readlink(path)
            elif path.is_file():
                entries[rel] = "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()
            elif path.is_dir():
                entries[rel] = "dir"
    return entries


def diff_snapshots(before: Mapping[str, str], after: Mapping[str, str]) -> list[str]:
    modified = [f"modified: {p}" for p in before if p in after and before[p] != after[p]]
    added = [f"added: {p}" for p in after if p not in before]
    removed = [f"removed: {p}" for p in before if p not in after]
    return modified + added + removed


class WorktreeModified(Exception):
    """The reviewer changed files it must not touch."""


def _findings_path(root: Path, reviewer: Reviewer) -> Path:
    scratch = root / SCRATCH_DIR
    scratch.mkdir(exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    path = scratch / f"review-{stamp}-{reviewer}.md"
    suffix = 1
    while path.exists():
        suffix += 1
        path = scratch / f"review-{stamp}-{reviewer}-{suffix}.md"
    return path


def run_review(
    implementer: Implementer,
    model: str | None,
    brief: str,
    root: Path,
    probe: Probe,
    timeout: float,
) -> tuple[Path, Selection]:
    failed: dict[Reviewer, str] = {}
    while True:
        selection = select_reviewer(implementer, model, probe, failed)
        before = snapshot(root)
        result: subprocess.CompletedProcess[str] | None = None
        try:
            result = subprocess.run(
                reviewer_command(selection.reviewer, root),
                input=brief,
                capture_output=True,
                text=True,
                cwd=root,
                timeout=timeout,
                check=False,
            )
        except (OSError, subprocess.TimeoutExpired) as error:
            failure = str(error)
        changes = diff_snapshots(before, snapshot(root))
        if changes:
            raise WorktreeModified(
                f"{selection.reviewer} modified the worktree during review; findings discarded:\n- "
                + "\n- ".join(changes)
            )
        if result is not None:
            if result.returncode == 0 and result.stdout.strip():
                break
            stderr_tail = " ".join(result.stderr.strip().splitlines()[-3:])
            failure = f"exited {result.returncode}: {stderr_tail or 'no output'}"
        failed[selection.reviewer] = f"failed at runtime ({failure})"
    assert result is not None
    path = _findings_path(root, selection.reviewer)
    path.write_text(result.stdout)
    return path, selection


def _git_root() -> Path:
    out = subprocess.run(
        ["git", "rev-parse", "--show-toplevel"], capture_output=True, text=True, check=True
    )
    return Path(out.stdout.strip())


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    sub = parser.add_subparsers(dest="command", required=True)
    for name in ("select", "run"):
        cmd = sub.add_parser(name)
        cmd.add_argument("--implementer", required=True, choices=get_args(Implementer))
        cmd.add_argument("--model", help="model the implementer is actually running")
        if name == "run":
            cmd.add_argument("--brief", required=True, type=Path, help="review brief file")
            cmd.add_argument("--root", type=Path, help="worktree root (default: git toplevel)")
            cmd.add_argument("--timeout", type=float, default=1800, help="seconds per reviewer")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        if args.command == "select":
            selection = select_reviewer(args.implementer, args.model, default_probe)
            print(json.dumps(asdict(selection), indent=2))
            return 0
        root = (args.root or _git_root()).resolve()
        path, selection = run_review(
            args.implementer,
            args.model,
            args.brief.read_text(),
            root,
            default_probe,
            args.timeout,
        )
    except ReviewUnavailable as error:
        print(error, file=sys.stderr)
        return EXIT_UNAVAILABLE
    except WorktreeModified as error:
        print(error, file=sys.stderr)
        return EXIT_MODIFIED
    print(json.dumps({"findings_path": str(path), "selection": asdict(selection)}, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
