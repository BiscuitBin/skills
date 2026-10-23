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
      any file outside ai_tmp/ and .git/ changed during the review, saving
      the output as ai_tmp/rejected-<timestamp>-<reviewer>.md instead.

Exit codes: 0 ok, 1 error before any review ran (including unreadable paths), 2 usage error (argparse),
3 cross-model review unavailable, 4 worktree changed during the review.
Python 3 standard library only.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import stat
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
EXIT_ERROR = 1
EXIT_UNAVAILABLE = 3  # 2 is argparse's usage-error code
EXIT_MODIFIED = 4


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
            "--ignore-rules",  # execpolicy rules can allow commands outside the sandbox
            "--skip-git-repo-check",
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
        "--no-session-persistence",
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


# A family marker at the start or after a provider/region separator, so
# openai/gpt-6-astra, us.anthropic.claude-opus-5-5 and bare aliases match.
_SEP = r"(?:^|[/:.@_-])"
_ANTHROPIC_MODEL = re.compile(_SEP + r"(?:anthropic|claude|opus|sonnet|haiku|fable)")
_OPENAI_MODEL = re.compile(_SEP + r"(?:openai|chatgpt|gpt|codex|astra|o\d)")
# Known third families. An "other" model matching none of the three patterns
# has an unconfirmed family, so no reviewer can be a confirmed fallback for it.
_THIRD_FAMILY_MODEL = re.compile(
    _SEP + r"(?:google|gemini|gemma|llama|mistral|mixtral|qwen|deepseek|grok|xai)"
)


def model_family(model: str) -> Family:
    name = model.strip().lower()
    if _ANTHROPIC_MODEL.search(name):
        return "anthropic"
    if _OPENAI_MODEL.search(name):
        return "openai"
    return "other"


def implementer_family(implementer: Implementer, model: str | None) -> Family:
    """The family the implementer is running. A known implementer keeps its
    default family when its stated model is unrecognised."""
    family = model_family(model) if model else None
    if family is not None and family != "other":
        return family
    if implementer in IMPLEMENTER_DEFAULT_FAMILY:
        return IMPLEMENTER_DEFAULT_FAMILY[implementer]
    if family is not None:
        return family
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
    unconfirmed = family == "other" and not _THIRD_FAMILY_MODEL.search(
        (model or "").strip().lower()
    )
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
        if candidate != preferred and unconfirmed:
            notes.append(
                f"{candidate} ({spec.model}) refused: model {model!r} is not a recognised "
                "family, so a different family cannot be confirmed; pass the underlying model ID"
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
    """Map every path under root (except .git/ and ai_tmp/) to its content hash
    and permission bits. The root itself is recorded as ".".

    Walks the filesystem rather than asking git, so ignored and untracked files
    count too. Symlinks are recorded by target and never followed. Paths that
    cannot be read are recorded as "error:<errno>": a path that becomes
    unreadable shows as modified, and `run` refuses to start if any already is.
    """
    entries: dict[str, str] = {}
    try:
        entries["."] = f"dir mode:{stat.S_IMODE(root.stat().st_mode):o}"
    except OSError as error:
        entries["."] = f"error:{error.errno}"

    def unreadable(error: OSError) -> None:
        if error.filename is not None:
            rel = Path(error.filename).relative_to(root).as_posix()
            entries[rel] = f"error:{error.errno}"

    for current, dirs, files in os.walk(root, onerror=unreadable):
        here = Path(current)
        if here == root:
            dirs[:] = [d for d in dirs if d not in SNAPSHOT_SKIP]
        for name in [*dirs, *files]:
            path = here / name
            rel = path.relative_to(root).as_posix()
            try:
                info = path.lstat()
                mode = f"mode:{stat.S_IMODE(info.st_mode):o}"
                if stat.S_ISLNK(info.st_mode):
                    entries[rel] = "link:" + os.readlink(path)
                elif stat.S_ISREG(info.st_mode):
                    entries[rel] = f"sha256:{_file_digest(path)} {mode}"
                elif stat.S_ISDIR(info.st_mode):
                    entries.setdefault(rel, f"dir {mode}")
            except OSError as error:
                entries[rel] = f"error:{error.errno}"
    return entries


def _file_digest(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def diff_snapshots(before: Mapping[str, str], after: Mapping[str, str]) -> list[str]:
    modified = [f"modified: {p}" for p in before if p in after and before[p] != after[p]]
    added = [f"added: {p}" for p in after if p not in before]
    removed = [f"removed: {p}" for p in before if p not in after]
    return modified + added + removed


class WorktreeModified(Exception):
    """Files changed during the review, by the reviewer or a concurrent process."""


class SetupError(Exception):
    """The run could not start; no reviewer ran."""


def _output_path(root: Path, kind: str, reviewer: Reviewer) -> Path:
    scratch = root / SCRATCH_DIR
    scratch.mkdir(exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    path = scratch / f"{kind}-{stamp}-{reviewer}.md"
    suffix = 1
    while True:
        try:
            path.touch(exist_ok=False)  # reserve atomically; a concurrent run gets the next suffix
            return path
        except FileExistsError:
            suffix += 1
            path = scratch / f"{kind}-{stamp}-{reviewer}-{suffix}.md"


def run_review(
    implementer: Implementer,
    model: str | None,
    brief: str,
    root: Path,
    probe: Probe,
    timeout: float,
) -> tuple[Path, Selection]:
    failed: dict[Reviewer, str] = {}
    before = snapshot(root)
    unreadable = sorted(p for p, v in before.items() if v.startswith("error:"))
    if unreadable:
        raise SetupError(
            "cannot verify the review leaves the worktree unchanged; "
            "make these paths readable or remove them:\n- " + "\n- ".join(unreadable)
        )
    while True:
        selection = select_reviewer(implementer, model, probe, failed)
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
        after = snapshot(root)
        changes = diff_snapshots(before, after)
        if changes:
            message = (
                f"the worktree changed while {selection.reviewer} was reviewing "
                "(by the reviewer or a concurrent process); this is not a valid review:\n- "
                + "\n- ".join(changes)
            )
            if result is not None and result.stdout.strip():
                rejected = _output_path(root, "rejected", selection.reviewer)
                rejected.write_text(result.stdout)
                message += f"\nreviewer output kept for inspection only: {rejected}"
            raise WorktreeModified(message)
        before = after
        if result is not None:
            if result.returncode == 0 and result.stdout.strip():
                break
            stderr_tail = " ".join(result.stderr.strip().splitlines()[-3:])
            failure = f"exited {result.returncode}: {stderr_tail or 'no output'}"
        failed[selection.reviewer] = f"failed at runtime ({failure})"
    assert result is not None
    path = _output_path(root, "review", selection.reviewer)
    path.write_text(result.stdout)
    return path, selection


def _git_root() -> Path:
    out = subprocess.run(
        ["git", "rev-parse", "--show-toplevel"], capture_output=True, text=True, check=False
    )
    if out.returncode != 0:
        raise SetupError("not inside a git repository; pass --root")
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
        try:
            brief = args.brief.read_text()
        except OSError as error:
            raise SetupError(f"cannot read brief: {error}") from error
        path, selection = run_review(
            args.implementer, args.model, brief, root, default_probe, args.timeout
        )
    except SetupError as error:
        print(f"error: {error}", file=sys.stderr)
        return EXIT_ERROR
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
