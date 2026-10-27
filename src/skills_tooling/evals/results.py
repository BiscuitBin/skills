"""Results files: eval-results/<run-id>/results.json and scrubbed transcripts.

Every byte written here first passes through scrub(), and verify_clean() then
rereads it all: a file that still holds a secret is deleted and the run fails.
"""

import json
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import Iterable
    from pathlib import Path

REDACTED = "[REDACTED]"


class SecretLeakError(Exception):
    """A results file still held a secret after scrubbing; it has been deleted."""


def scrub(text: str, secrets: Iterable[str]) -> str:
    for secret in secrets:
        if secret:
            text = text.replace(secret, REDACTED)
    return text


def write_text(path: Path, text: str, secrets: Iterable[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(scrub(text, secrets))


def write_json(path: Path, data: dict[str, Any], secrets: Iterable[str]) -> None:
    write_text(path, json.dumps(data, indent=2, ensure_ascii=False) + "\n", secrets)


def files_holding(directory: Path, secrets: Iterable[str]) -> list[Path]:
    needles = [s.encode() for s in secrets if s]
    if not needles:
        return []
    found = []
    for path in sorted(directory.rglob("*")):
        if path.is_file() and not path.is_symlink():
            data = path.read_bytes()
            if any(needle in data for needle in needles):
                found.append(path)
    return found


def verify_clean(directory: Path, secrets: Iterable[str]) -> None:
    """Delete, and raise for, every file under directory that holds a secret."""
    leaked = files_holding(directory, list(secrets))
    for path in leaked:
        path.unlink()
    if leaked:
        names = ", ".join(str(path) for path in leaked)
        msg = f"secret found and deleted from {names}"
        raise SecretLeakError(msg)
