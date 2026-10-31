"""The benchmark: eval-results/<run-id>/benchmark.json. The schema is in docs/reference/evals.md.

aggregate() is a pure function of the run record and the grading files it
references. Every exclusion is counted and shown, never folded in as a 0.
"""

import hashlib
import statistics
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any, TypeIs

from skills_tooling.evals import workspace

if TYPE_CHECKING:
    from collections.abc import Iterable, Mapping, Sequence

# Below this many values a sample stddev is undefined, so it is null, never 0.
MIN_STDDEV_N = 2
# Below this many scored trials a spread says nothing, and the notes say so.
MIN_SPREAD_N = 3
DELTA_METRICS = ("deterministic_pass_rate", "graded_pass_rate", "outcome_pass_rate")
SKILL_ONLY = ("trigger_accuracy", "skill_use_pass_rate")
METRICS = (*SKILL_ONLY, *DELTA_METRICS)
EXCLUSIONS = ("n_infra_error", "n_contaminated", "n_secret_found")
GRADING_FAILURES = ("grader_error", "invalid_reply", "rejected")
# The statuses of a grading that holds a verdict; grader_error holds none.
VERDICT_STATUSES = ("ok", "rejected", "invalid_reply")
DESCRIPTIVE = (
    "No significance test or confidence interval: with a few trials per arm the delta"
    " and spreads are descriptive."
)


def stat(values: Sequence[float]) -> dict[str, Any] | None:
    """Mean, sample stddev, min, max and n; None when there is nothing to measure."""
    if not values:
        return None
    return {
        "mean": statistics.fmean(values),
        "stddev": statistics.stdev(values) if len(values) >= MIN_STDDEV_N else None,
        "min": min(values),
        "max": max(values),
        "n": len(values),
    }


@dataclass(frozen=True)
class _Scored:
    """One scored trial's per-metric values; None where the metric does not apply to it."""

    values: dict[str, float | None]
    # The grading's status, or None when the case has no expectations. A
    # missing or unreadable grading file is a grader_error.
    grading_status: str | None = None
    # Each expectation's verdict by its text; empty unless the trial was graded with a reply.
    verdicts: Mapping[str, bool] = field(default_factory=dict)
    # The material sent to the grader named the arm (a grader error sent nothing).
    disclosed: bool = False


def _exclusion(trial: Mapping[str, Any]) -> str | None:
    """Which count removes the trial from every metric, or None when it is scored."""
    if trial["secret_found"] is not None:
        return "n_secret_found"
    if trial["status"] != "ok":
        return "n_infra_error"
    if trial["contamination"]["passed"] is not True:
        return "n_contaminated"
    return None


def _rate(results: Sequence[str]) -> float | None:
    return sum(r == "passed" for r in results) / len(results) if results else None


def _well_formed(grading: object) -> bool:
    """Whether a grading file has the shape grader.py writes, so reading it cannot fail."""
    if not isinstance(grading, dict):
        return False
    grader, expectations = grading.get("grader"), grading.get("expectations")
    return (
        isinstance(grader, dict)
        and isinstance(grader.get("status"), str)
        and isinstance(grader.get("model"), str)
        and isinstance(grader.get("cli_version"), str)
        and isinstance(grading.get("arm_disclosed"), bool)
        and isinstance(expectations, list)
        and all(
            isinstance(e, dict)
            and isinstance(e.get("text"), str)
            and "passed" in e
            # Not `in (True, False, None)`: 1 == True would let an integer through.
            and (e["passed"] is None or isinstance(e["passed"], bool))
            for e in expectations
        )
    )


# grading comes first: TypeIs narrows only the first argument, to a non-None grading.
def _has_verdicts(
    grading: Mapping[str, Any] | None, case: Mapping[str, Any]
) -> TypeIs[Mapping[str, Any]]:
    """Whether the grading holds a verdict on exactly the case's rubric.

    A file that lists other expectations, or none, or no known status, cannot be
    scored against the case, so it is a grader error, like a missing file: it
    never changes the denominator or the expectation counts.
    """
    return (
        grading is not None
        and grading["grader"].get("status") in VERDICT_STATUSES
        and [e["text"] for e in grading["expectations"]]
        == [e["text"] for e in case["expectations"]]
    )


def _score(
    case: Mapping[str, Any], trial: Mapping[str, Any], grading: Mapping[str, Any] | None
) -> _Scored:
    def results(cls: str) -> list[str]:
        return [
            a["result"]
            for a in trial["assertions"]
            if a["class"] == cls and a["result"] in {"passed", "failed"}
        ]

    outcome = results("outcome")
    passed = sum(r == "passed" for r in outcome)
    values: dict[str, float | None] = {
        "trigger_accuracy": 1.0 if trial["trigger"]["matched"] is True else 0.0,
        "skill_use_pass_rate": _rate(results("skill_use")),
        "deterministic_pass_rate": _rate(outcome),
        "graded_pass_rate": None,
        "outcome_pass_rate": _rate(outcome),
    }
    if not case["expectations"]:
        return _Scored(values)
    if not _has_verdicts(grading, case):
        # No reply, no file or a file off the rubric: the trial leaves only the metrics the grader
        # feeds, so every outcome_pass_rate denominator has the same mix of measures.
        values["outcome_pass_rate"] = None
        return _Scored(values, "grader_error")
    status = grading["grader"]["status"]
    # A rejected or invalid reply fails every expectation, whatever its verdicts say.
    usable = status == "ok"
    verdicts = {e["text"]: usable and e["passed"] is True for e in grading["expectations"]}
    values["graded_pass_rate"] = sum(verdicts.values()) / len(verdicts)
    values["outcome_pass_rate"] = (passed + sum(verdicts.values())) / (
        len(outcome) + len(verdicts)
    )
    return _Scored(values, status, verdicts, disclosed=grading["arm_disclosed"] is True)


def _metrics(scored: Sequence[_Scored], *, baseline: bool) -> dict[str, Any]:
    metrics: dict[str, Any] = {
        m: stat([v for s in scored if (v := s.values[m]) is not None]) for m in METRICS
    }
    if baseline:
        # Nothing is installed, so nothing could trigger or be used.
        metrics |= dict.fromkeys(SKILL_ONLY, "not_applicable")
    return metrics


def _arm(
    case: Mapping[str, Any],
    trials: Sequence[Mapping[str, Any]],
    gradings: Mapping[str, Mapping[str, Any] | None],
    planned: int,
    *,
    baseline: bool,
) -> tuple[dict[str, Any], list[_Scored]]:
    counts = dict.fromkeys(("n_scored", *EXCLUSIONS), 0)
    scored = []
    for trial in trials:
        excluded = _exclusion(trial)
        if excluded is not None:
            counts[excluded] += 1
            continue
        counts["n_scored"] += 1
        grading = gradings.get(trial["grading"]) if trial["grading"] is not None else None
        scored.append(_score(case, trial, grading))
    for status in GRADING_FAILURES:
        counts[f"n_{status}"] = sum(s.grading_status == status for s in scored)
    counts["n_arm_disclosed"] = sum(s.disclosed for s in scored)
    metrics = _metrics(scored, baseline=baseline)
    return {"n_planned": planned, **counts, "metrics": metrics}, scored


def _case(
    run: Mapping[str, Any],
    case: Mapping[str, Any],
    trials: Sequence[Mapping[str, Any]],
    gradings: Mapping[str, Mapping[str, Any] | None],
) -> tuple[dict[str, Any], dict[str, list[_Scored]]]:
    """The case's record, and its scored trials by arm for pooling."""
    mine = [t for t in trials if t["case"] == case["id"]]
    planned = run["trials_per_case"]
    skill, skill_scored = _arm(
        case, [t for t in mine if t["arm"] == "skill"], gradings, planned, baseline=False
    )
    scored = {"skill": skill_scored}
    baseline: dict[str, Any] | str = "skipped"
    delta: dict[str, Any] = {}
    if case["in_baseline"]:
        baseline, scored["baseline"] = _arm(
            case, [t for t in mine if t["arm"] == "baseline"], gradings, planned, baseline=True
        )
        delta = {m: _delta(skill["metrics"][m], baseline["metrics"][m]) for m in DELTA_METRICS}
    expectations = [
        {
            "text": e["text"],
            "blinded": e["blinded"],
            "skill": _passes(e["text"], skill_scored),
            "baseline": _passes(e["text"], scored["baseline"]) if "baseline" in scored else None,
        }
        for e in case["expectations"]
    ]
    record = {
        "skill": skill,
        "baseline": baseline,
        "delta": delta,
        "expectations": expectations,
        "notes": _notes(skill, baseline, delta, expectations),
    }
    return record, scored


def _notes(
    skill: Mapping[str, Any],
    baseline: Mapping[str, Any] | str,
    delta: Mapping[str, Any],
    expectations: Sequence[Mapping[str, Any]],
) -> list[str]:
    notes = [
        f"n < 3: spread not meaningful ({name}, n = {n})"
        for name, arm in (("skill", skill), ("baseline", baseline))
        if not isinstance(arm, str) and (n := _thinnest(arm["metrics"])) is not None
    ]
    trigger = skill["metrics"]["trigger_accuracy"]
    if trigger is not None and 0 < trigger["mean"] < 1:
        notes.append(f"flaky trigger: accuracy {trigger['mean']:.2f} over {trigger['n']} trials")
    notes += [
        f"non-discriminating: {row['text']!r} passed in every graded trial of both arms"
        for row in expectations
        if row["baseline"] is not None
        and all(0 < arm["n"] == arm["passed"] for arm in (row["skill"], row["baseline"]))
    ]
    if isinstance(baseline, str):
        return notes
    notes += [
        f"unequal n on {m}: {d['n_skill']} (skill) / {d['n_baseline']} (baseline)"
        for m, d in delta.items()
        if d["value"] is not None and d["n_skill"] != d["n_baseline"]
    ]
    if skill["n_grader_error"] or baseline["n_grader_error"]:
        notes.append(
            f"grader errors excluded: {skill['n_grader_error']} (skill)"
            f" / {baseline['n_grader_error']} (baseline)"
        )
    if skill["n_arm_disclosed"] or baseline["n_arm_disclosed"]:
        graded = delta["graded_pass_rate"]
        notes.append(
            f"arm disclosed to the grader in {skill['n_arm_disclosed']} of"
            f" {graded['n_skill']} trials (skill) / {baseline['n_arm_disclosed']} of"
            f" {graded['n_baseline']} (baseline)"
        )
    return notes


def _thinnest(metrics: Mapping[str, Any]) -> int | None:
    """The smallest n, below MIN_SPREAD_N, of any measured metric; None when none is that thin."""
    thin = [m["n"] for m in metrics.values() if isinstance(m, dict) and 1 <= m["n"] < MIN_SPREAD_N]
    return min(thin, default=None)


def _passes(text: str, scored: Sequence[_Scored]) -> dict[str, int]:
    """How many graded trials passed one expectation, out of those with a verdict on it."""
    verdicts = [s.verdicts[text] for s in scored if text in s.verdicts]
    return {"passed": sum(verdicts), "n": len(verdicts)}


def _delta(skill: Mapping[str, Any] | None, baseline: Mapping[str, Any] | None) -> dict[str, Any]:
    """Skill mean minus baseline mean; null when either side has nothing to measure."""
    n_skill = skill["n"] if skill else 0
    n_baseline = baseline["n"] if baseline else 0
    value = skill["mean"] - baseline["mean"] if skill and baseline else None
    return {"value": value, "n_skill": n_skill, "n_baseline": n_baseline}


def _agent(
    run: Mapping[str, Any],
    trials: Sequence[Mapping[str, Any]],
    gradings: Mapping[str, Mapping[str, Any] | None],
) -> dict[str, Any]:
    cases: dict[str, Any] = {}
    pooled: dict[str, list[_Scored]] = {"skill": [], "baseline": []}
    for case in run["cases"]:
        cases[case["id"]], scored = _case(run, case, trials, gradings)
        for arm, arm_scored in scored.items():
            pooled[arm] += arm_scored
    # Each case counts once in the agent's delta, whatever its trial count.
    delta = {}
    for m in DELTA_METRICS:
        values = [
            d["value"]
            for c in cases.values()
            if c["delta"] and (d := c["delta"][m])["value"] is not None
        ]
        delta[m] = {"value": statistics.fmean(values) if values else None, "n_cases": len(values)}
    metrics = {
        "skill": _metrics(pooled["skill"], baseline=False),
        "baseline": _metrics(pooled["baseline"], baseline=True) if run["baseline"] else None,
    }
    return {
        "cases": cases,
        "pooled": metrics,
        "delta": delta,
        "notes": [
            f"n < 3: spread not meaningful (pooled {arm}, n = {n})"
            for arm, arm_metrics in metrics.items()
            if arm_metrics is not None and (n := _thinnest(arm_metrics)) is not None
        ],
    }


def _distinct(values: Iterable[Any]) -> list[Any]:
    """The distinct values reported, sorted; a value nobody reported is left out."""
    return sorted({v for v in values if v})


def aggregate(
    run: Mapping[str, Any], gradings: Mapping[str, Mapping[str, Any] | None]
) -> dict[str, Any]:
    """The benchmark of one run: per agent, per case and arm, then pooled per agent."""
    # A file of any other shape is read as missing: a grader error, never a crash.
    gradings = {path: g if _well_formed(g) else None for path, g in gradings.items()}
    agents = sorted({t["agent"] for t in run["trials"]}) or [run["agent"]]
    graders = [g["grader"] for g in gradings.values() if g is not None]
    return {
        "run_id": run["run_id"],
        "skill": run["skill"],
        "trials_per_case": run["trials_per_case"],
        "baseline": run["baseline"],
        "skipped_in_baseline": run["skipped_in_baseline"],
        "provenance": {
            **run["provenance"],
            "agent": run["agent"],
            "requested_model": run["requested_model"],
            "agent_cli_versions": _distinct(t["cli_version"] for t in run["trials"]),
            "agent_models": _distinct(t["model"] for t in run["trials"]),
            "grader_model_requested": run["grader_model_requested"],
            "grader_models": _distinct(g["model"] for g in graders),
            "grader_cli_versions": _distinct(g["cli_version"] for g in graders),
        },
        "agents": {
            agent: _agent(run, [t for t in run["trials"] if t["agent"] == agent], gradings)
            for agent in agents
        },
        "notes": [DESCRIPTIVE],
    }


COLUMNS = (
    ("trigger_accuracy", "trigger"),
    ("skill_use_pass_rate", "skill use"),
    ("deterministic_pass_rate", "deterministic"),
    ("graded_pass_rate", "graded"),
    ("outcome_pass_rate", "outcome"),
)


def _cell(metric: Mapping[str, Any] | str | None) -> str:
    if metric == "not_applicable":
        return "n/a"
    if metric is None or isinstance(metric, str):
        return "no data"
    if metric["stddev"] is None:
        return f"{metric['mean']:.2f} (n={metric['n']})"
    return f"{metric['mean']:.2f} ± {metric['stddev']:.2f} (n={metric['n']})"


def _delta_cell(delta: Mapping[str, Any] | None) -> str:
    if delta is None:
        return "n/a"
    if delta["value"] is None:
        return "no data"
    n = f"{delta['n_skill']}/{delta['n_baseline']}" if "n_skill" in delta else delta["n_cases"]
    label = "n" if "n_skill" in delta else "cases"
    return f"{delta['value']:+.2f} ({label}={n})"


def _arm_counts(arm: Mapping[str, Any]) -> str:
    counted = [
        f"{key.removeprefix('n_').replace('_', ' ')} {arm[key]}"
        for key in (*EXCLUSIONS, *(f"n_{s}" for s in GRADING_FAILURES), "n_arm_disclosed")
        if arm[key]
    ]
    return f"scored {arm['n_scored']}/{arm['n_planned']}" + "".join(f", {c}" for c in counted)


def _rows(
    label: str,
    skill: Mapping[str, Any],
    baseline: Mapping[str, Any] | str | None,
    delta: Mapping[str, Any],
) -> list[list[str]]:
    rows = [[label, "skill", *(_cell(skill[m]) for m, _ in COLUMNS)]]
    if baseline is None or isinstance(baseline, str):
        # None: the run had no baseline arm at all.
        rows.append(["", "baseline", "off" if baseline is None else "skipped", "", "", "", ""])
        return rows
    rows.append(["", "baseline", *(_cell(baseline[m]) for m, _ in COLUMNS)])
    rows.append(["", "delta", "", "", *(_delta_cell(delta.get(m)) for m, _ in COLUMNS[2:])])
    return rows


def _layout(rows: Sequence[Sequence[str]]) -> list[str]:
    widths = [max(len(row[i]) for row in rows) for i in range(len(rows[0]))]
    return [
        "  ".join(c.ljust(w) for c, w in zip(row, widths, strict=True)).rstrip() for row in rows
    ]


def table(benchmark: Mapping[str, Any]) -> str:
    """The printed summary: mean ± stddev (n) per case and arm, the deltas, then the notes."""
    lines = [f"Benchmark {benchmark['run_id']}: {benchmark['skill']}"]
    header = ["case", "arm", *(name for _, name in COLUMNS)]
    for agent, result in benchmark["agents"].items():
        rows = [header]
        notes: list[str] = []
        for case_id, case in result["cases"].items():
            baseline = case["baseline"]
            counts = [f"skill {_arm_counts(case['skill'])}"]
            if isinstance(baseline, dict):
                counts.append(f"baseline {_arm_counts(baseline)}")
                baseline = baseline["metrics"]
            elif not benchmark["baseline"]:
                # Every case is "skipped" in the record; none was left out of a baseline that ran.
                baseline = None
            rows += _rows(case_id, case["skill"]["metrics"], baseline, case["delta"])
            notes += [f"{case_id}: {'; '.join(counts)}"]
            notes += [f"{case_id}: {note}" for note in case["notes"]]
        rows += _rows(
            "all cases", result["pooled"]["skill"], result["pooled"]["baseline"], result["delta"]
        )
        notes += [f"all cases: {note}" for note in result["notes"]]
        lines += ["", f"Agent {agent}", *_layout(rows), "", *notes]
    lines += ["", *benchmark["notes"]]
    return "\n".join(lines) + "\n"


def file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def tree_sha256(directory: Path) -> str:
    """SHA-256 over each file's relative path and bytes, in path order, skipping __pycache__."""
    if not directory.is_dir():
        # rglob finds nothing there, and the hash of nothing looks like any other.
        msg = f"not a directory: {directory}"
        raise FileNotFoundError(msg)
    files = sorted(
        (path.relative_to(directory).as_posix(), path)
        for path in directory.rglob("*")
        if path.is_file() and "__pycache__" not in path.relative_to(directory).parts
    )
    digest = hashlib.sha256()
    for name, path in files:
        # A NUL ends the name and the content's own fixed-length digest follows,
        # so no two trees hash the same input.
        digest.update(name.encode() + b"\0" + hashlib.sha256(path.read_bytes()).digest())
    return digest.hexdigest()


def git_state(root: Path) -> dict[str, Any]:
    """HEAD and whether the worktree has changes; both None unless root is a git root.

    A root inside some other repository, such as a copy under a dotfiles
    checkout, would otherwise record that repository's commit.
    """
    toplevel = workspace.git("rev-parse", "--show-toplevel", cwd=root)
    if toplevel.returncode != 0 or Path(toplevel.stdout.strip()).resolve() != root.resolve():
        return {"git_commit": None, "git_dirty": None}
    head = workspace.git("rev-parse", "HEAD", cwd=root)
    status = workspace.git("status", "--porcelain", cwd=root)
    return {
        "git_commit": head.stdout.strip() if head.returncode == 0 else None,
        "git_dirty": bool(status.stdout.strip()) if status.returncode == 0 else None,
    }


def provenance(root: Path, skill: str) -> dict[str, Any]:
    """What the run measured: the commit, the skill's files and its cases and rubric."""
    return {
        **git_state(root),
        "skill_sha256": tree_sha256(root / "skills" / skill),
        "evals_sha256": file_sha256(root / "evals" / skill / "evals.json"),
    }
