"""Results files: eval-results/<run-id>/results.json and scrubbed transcripts.

Every byte written here first passes through scrub(), and verify_clean() then
rereads it all: a file that still holds a secret is deleted and the run fails.
"""

import json
import os
import stat
from pathlib import Path
from typing import TYPE_CHECKING, Any, NoReturn

if TYPE_CHECKING:
    from collections.abc import Iterable

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


def _raise(error: OSError) -> NoReturn:
    raise error


def files_holding(directory: Path, secrets: Iterable[str]) -> list[Path]:
    """Files and symlinks under directory whose contents or path hold a secret.

    The path too: the grader lists every output file by its path. Raises OSError
    for anything it cannot enter or read, so a locked directory never passes as clean.
    """
    needles = [s.encode() for s in secrets if s]
    if not needles:
        return []
    found = []
    # dirnames too: the walk lists a symlink to a directory there.
    for parent, dirnames, filenames in os.walk(directory, onerror=_raise):
        for entry in [*dirnames, *filenames]:
            path = Path(parent, entry)
            # lstat, not is_file: is_file hides a denied stat, and reports a link's target.
            mode = path.lstat().st_mode
            if stat.S_ISLNK(mode) or stat.S_ISREG(mode):
                name = os.fsencode(path.relative_to(directory))
                # A link is never read, nor a FIFO, which would hang.
                data = path.read_bytes() if stat.S_ISREG(mode) else b""
                if any(needle in name or needle in data for needle in needles):
                    found.append(path)
    return sorted(found)


def verify_clean(directory: Path, secrets: Iterable[str]) -> None:
    """Delete, and raise for, every file under directory that holds a secret."""
    secrets = list(secrets)
    leaked = files_holding(directory, secrets)
    for path in leaked:
        path.unlink()
    if leaked:
        names = scrub(", ".join(str(path) for path in leaked), secrets)
        msg = f"secret found and deleted from {names}"
        raise SecretLeakError(msg)
