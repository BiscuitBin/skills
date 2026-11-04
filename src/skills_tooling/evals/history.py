"""Benchmark history: named iterations in benchmarks/<skill>/<iteration>.json.

An iteration is a snapshot of one run per agent: each run's benchmark.json and
the case list from its results.json. It holds no transcript and no grading
file. Where it lives and why it is committed: docs/adr/0014-benchmark-history.md.
"""

import itertools
import json
import re
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from skills_tooling.evals import results

if TYPE_CHECKING:
    from collections.abc import Sequence
    from pathlib import Path

SCHEMA = 1
# The report's name for runs shown with --run and not recorded.
UNRECORDED = "unrecorded"
NAME = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]*")
# The runs of one iteration measured one version of the skill against one set of cases.
SHARED = ("skill_sha256", "evals_sha256")


class HistoryError(Exception):
    """A run cannot be recorded, or a recorded iteration cannot be read."""


def history_dir(root: Path, skill: str) -> Path:
    return root / "benchmarks" / skill


def _read(path: Path, what: str) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text())
    except (OSError, ValueError) as error:
        msg = f"cannot read the {what} {path}: {error}"
        raise HistoryError(msg) from error
    if not isinstance(data, dict):
        msg = f"the {what} {path} is not a JSON object"
        raise HistoryError(msg)
    return data


def _run(root: Path, run_id: str) -> dict[str, Any]:
    directory = root / "eval-results" / run_id
    if not NAME.fullmatch(run_id) or not (directory / "results.json").is_file():
        msg = f"no run {run_id!r} in eval-results/"
        raise HistoryError(msg)
    if not (directory / "benchmark.json").is_file():
        msg = f"run {run_id} has no benchmark.json; it predates graded trials"
        raise HistoryError(msg)
    run = _read(directory / "results.json", "run record")
    bench = _read(directory / "benchmark.json", "benchmark")
    try:
        agent = run["agent"]
        return {
            "run_id": run_id,
            "agent": agent,
            "skill": run["skill"],
            "started_at": run["started_at"],
            "trials_per_case": bench["trials_per_case"],
            "baseline": bench["baseline"],
            "provenance": bench["provenance"],
            "cases": run["cases"],
            "benchmark": bench["agents"][agent],
            "notes": bench["notes"],
        }
    except (KeyError, TypeError) as error:
        msg = f"run {run_id} is not a complete run of the current format: missing {error}"
        raise HistoryError(msg) from error


def snapshot(
    root: Path, name: str | None, run_ids: Sequence[str], *, now: datetime | None = None
) -> dict[str, Any]:
    """The iteration the runs make; name is None for runs shown but not recorded."""
    if not run_ids:
        msg = "name at least one run"
        raise HistoryError(msg)
    runs = sorted((_run(root, run_id) for run_id in run_ids), key=lambda r: r["agent"])
    skills = sorted({r["skill"] for r in runs})
    if len(skills) > 1:
        msg = f"the runs test different skills: {', '.join(skills)}"
        raise HistoryError(msg)
    for earlier, later in itertools.pairwise(runs):
        if earlier["agent"] == later["agent"]:
            msg = (
                f"two runs of {later['agent']} ({earlier['run_id']}, {later['run_id']});"
                " an iteration holds one run per agent"
            )
            raise HistoryError(msg)
    for key in SHARED:
        if len({r["provenance"].get(key) for r in runs}) > 1:
            msg = f"the runs disagree on {key}, so they did not measure one skill version"
            raise HistoryError(msg)
    return {
        "schema": SCHEMA,
        "iteration": name,
        "skill": skills[0],
        "recorded_at": (now or datetime.now(UTC)).isoformat(),
        "runs": runs,
    }


def record(root: Path, name: str, run_ids: Sequence[str], *, now: datetime | None = None) -> Path:
    """Write the runs as iteration `name` of their skill; never overwrites one."""
    if not NAME.fullmatch(name) or name == UNRECORDED:
        msg = f"iteration name {name!r}: use letters, digits, '.', '_' and '-'"
        raise HistoryError(msg)
    iteration = snapshot(root, name, run_ids, now=now)
    path = history_dir(root, iteration["skill"]) / f"{name}.json"
    if path.exists():
        msg = f"iteration {name!r} is already recorded at {path.relative_to(root)}"
        raise HistoryError(msg)
    # The run files were scrubbed when written; nothing new is added here.
    results.write_json(path, iteration, [])
    return path


def load(root: Path, skill: str) -> list[dict[str, Any]]:
    """A skill's recorded iterations, oldest first."""
    directory = history_dir(root, skill)
    found = [_read(p, "iteration") for p in sorted(directory.glob("*.json"))]
    for path, iteration in zip(sorted(directory.glob("*.json")), found, strict=True):
        if iteration.get("schema") != SCHEMA or iteration.get("skill") != skill:
            msg = f"{path} is not a schema-{SCHEMA} iteration of {skill}"
            raise HistoryError(msg)
    return sorted(found, key=lambda i: (i["recorded_at"], i["iteration"]))


def recorded_skills(root: Path) -> list[str]:
    return sorted(p.name for p in (root / "benchmarks").glob("*") if p.is_dir())
