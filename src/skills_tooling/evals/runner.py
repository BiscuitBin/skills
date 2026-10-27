"""Run a skill's eval cases against one agent and write the results.

One trial per case: a fresh workspace and homes, the preflight, the headless
run, the contamination check, then scoring. A trial with an infrastructure
error is recorded but never scored.
"""

import secrets
import shutil
from dataclasses import dataclass, replace
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any

from skills_tooling.evals import results, workspace
from skills_tooling.evals.assertions import evaluate
from skills_tooling.evals.cases import load_suite
from skills_tooling.evals.contamination import check, preflight

if TYPE_CHECKING:
    from collections.abc import Mapping

    from skills_tooling.evals.adapter import Adapter, Trace, TrialPaths
    from skills_tooling.evals.cases import Case
    from skills_tooling.evals.contamination import NeverAppear


class UsageError(Exception):
    """The run was asked for something that does not exist; nothing ran."""


@dataclass(frozen=True)
class RunSettings:
    root: Path
    skill: str
    adapter: Adapter
    model: str
    timeout: float
    credentials: Mapping[str, str]
    case_ids: tuple[str, ...]
    run_id: str
    never: NeverAppear
    system_root: Path = Path("/")

    @property
    def results_dir(self) -> Path:
        return self.root / "eval-results" / self.run_id

    @property
    def workspaces_dir(self) -> Path:
        return self.root / ".eval-workspaces"

    @property
    def secrets(self) -> list[str]:
        return [value for value in self.credentials.values() if value]


def new_run_id() -> str:
    return f"{datetime.now(UTC):%Y%m%dT%H%M%SZ}-{secrets.token_hex(2)}"


def _now() -> str:
    return datetime.now(UTC).isoformat(timespec="milliseconds")


def select_cases(cases: tuple[Case, ...], case_ids: tuple[str, ...]) -> list[Case]:
    known = {case.id: case for case in cases}
    for case_id in case_ids:
        if case_id not in known:
            msg = f"unknown case {case_id!r}; known cases: {', '.join(known)}"
            raise UsageError(msg)
    return [case for case in cases if not case_ids or case.id in case_ids]


def _infra_error(trace: Trace, reason: str) -> Trace:
    return replace(trace, status="infra_error", status_reason=reason)


def _score(
    settings: RunSettings, case: Case, trace: Trace, trial: TrialPaths
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    if trace.status != "ok":
        trigger = {"expected": case.should_trigger, "actual": None, "matched": None}
        skipped = [
            {"type": a.type, "result": "not_scored", "evidence": ""} for a in case.assertions
        ]
        return trigger, skipped
    actual = settings.skill in trace.skills_triggered
    trigger = {
        "expected": case.should_trigger,
        "actual": actual,
        "matched": actual == case.should_trigger,
    }
    installed = trial.workspace / settings.adapter.skills_dir / settings.skill
    scored = []
    for assertion in case.assertions:
        result = evaluate(
            assertion,
            trace,
            skill=settings.skill,
            skill_dir=settings.root / "skills" / settings.skill,
            installed=installed,
        )
        scored.append(
            {
                "type": result.type,
                "result": "passed" if result.passed else "failed",
                "evidence": result.evidence,
            }
        )
    return trigger, scored


def run_trial(settings: RunSettings, case: Case) -> dict[str, Any]:
    adapter = settings.adapter
    record: dict[str, Any] = {
        "case": case.id,
        "kind": case.kind,
        "agent": adapter.name,
        "started_at": _now(),
    }
    trial = workspace.create_trial(settings.workspaces_dir, settings.run_id, case.id)
    try:
        homes = adapter.prepare_homes(trial)
        adapter.install_skill(settings.root / "skills" / settings.skill, trial.workspace)
        problems = preflight(adapter, trial, homes, settings.root, settings.skill)
        if problems:
            record |= {
                "cli_version": None,
                "model": None,
                "status": "infra_error",
                "status_reason": "preflight failed: " + "; ".join(problems),
                "trigger": {"expected": case.should_trigger, "actual": None, "matched": None},
                "contamination": {"passed": False, "problems": problems, "notes": []},
                "assertions": [
                    {"type": a.type, "result": "not_scored", "evidence": ""}
                    for a in case.assertions
                ],
                "transcript": None,
            }
            return record
        raw = adapter.run(
            case.prompt,
            trial,
            homes,
            model=settings.model,
            timeout=settings.timeout,
            credentials=settings.credentials,
        )
        trace = adapter.parse(raw)
        if trace.status == "ok" and trace.model != settings.model:
            trace = _infra_error(trace, f"ran {trace.model!r}, not {settings.model!r}")
        contamination = check(
            adapter,
            trace,
            skill=settings.skill,
            baseline=False,
            trial=trial,
            never=settings.never,
            system_root=settings.system_root,
        )
        transcript = settings.results_dir / "transcripts" / f"{case.id}.jsonl"
        results.write_text(
            transcript, raw.transcript.read_text(errors="replace"), settings.secrets
        )
        trigger, scored = _score(settings, case, trace, trial)
        record |= {
            "cli_version": trace.cli_version,
            "model": trace.model,
            "status": trace.status,
            "status_reason": trace.status_reason,
            "trigger": trigger,
            "contamination": {
                "passed": contamination.passed,
                "problems": contamination.problems,
                "notes": contamination.notes,
            },
            "assertions": scored,
            "transcript": transcript.relative_to(settings.root).as_posix(),
            "stderr": results.scrub(raw.stderr[-2000:], settings.secrets),
        }
        return record
    finally:
        workspace.teardown(trial)
        if results.files_holding(trial.root, settings.secrets):
            shutil.rmtree(trial.workspace, ignore_errors=True)
            record["workspace_deleted"] = "a secret was found in the workspace"
        record["finished_at"] = _now()
        record["passed"] = (
            record.get("status") == "ok"
            and record.get("contamination", {}).get("passed") is True
            and record.get("trigger", {}).get("matched") is True
            and all(a["result"] == "passed" for a in record.get("assertions", []))
        )


def run_suite(settings: RunSettings) -> int:
    """Run the selected cases; 0 when every trial passed, 1 otherwise."""
    suite = load_suite(settings.root, settings.skill)
    cases = select_cases(suite.cases, settings.case_ids)
    started = _now()
    trials = [run_trial(settings, case) for case in cases]
    passed = all(trial["passed"] for trial in trials)
    data = {
        "run_id": settings.run_id,
        "skill": settings.skill,
        "agent": settings.adapter.name,
        "requested_model": settings.model,
        "credential_env": list(settings.adapter.credential_env),
        "started_at": started,
        "finished_at": _now(),
        "passed": passed,
        "trials": trials,
    }
    path = settings.results_dir / "results.json"
    results.write_json(path, data, settings.secrets)
    try:
        results.verify_clean(settings.results_dir, settings.secrets)
    except results.SecretLeakError as error:
        print(f"eval: {error}")
        return 1
    for trial in trials:
        verdict = "PASS" if trial["passed"] else "FAIL"
        reason = "" if trial["passed"] else f": {_why(trial)}"
        print(f"{verdict} {trial['case']}{reason}")
    print(f"Results: {path.relative_to(settings.root)}")
    return 0 if passed else 1


def _why(trial: Mapping[str, Any]) -> str:
    if trial.get("status") != "ok":
        return f"infrastructure error, {trial.get('status_reason')}"
    reasons = []
    if not trial["contamination"]["passed"]:
        reasons.append("contamination: " + "; ".join(trial["contamination"]["problems"]))
    if trial["trigger"]["matched"] is not True:
        reasons.append(
            f"trigger expected {trial['trigger']['expected']}, got {trial['trigger']['actual']}"
        )
    reasons += [
        f"{a['type']} failed ({a['evidence']})"
        for a in trial["assertions"]
        if a["result"] != "passed"
    ]
    return "; ".join(reasons)
