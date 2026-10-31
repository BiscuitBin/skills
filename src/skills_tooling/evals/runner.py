"""Run a skill's eval cases against one agent and write the results.

Each case runs `trials` times with the skill installed, and as many times again
with nothing installed when the baseline arm is on. Every trial gets a fresh
workspace and homes, the preflight, the headless run, the contamination check,
then scoring. A trial with an infrastructure error is recorded but never scored.
"""

import json
import secrets
import shutil
from contextlib import suppress
from dataclasses import dataclass, replace
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any, Literal

from skills_tooling.evals import benchmark, grader, results, workspace
from skills_tooling.evals.assertions import evaluate
from skills_tooling.evals.cases import load_suite
from skills_tooling.evals.claude_code import BUDGET_USD
from skills_tooling.evals.contamination import check, preflight

if TYPE_CHECKING:
    from collections.abc import Mapping

    from skills_tooling.evals.adapter import Adapter, Trace, TrialPaths
    from skills_tooling.evals.cases import Assertion, Case
    from skills_tooling.evals.contamination import NeverAppear
    from skills_tooling.evals.grader import GraderSettings

Arm = Literal["skill", "baseline"]
# The grader runs on Claude Code, with its --max-budget-usd per call.
GRADER_BUDGET_USD = float(BUDGET_USD)


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
    trials: int = 1
    baseline: bool = False
    # Grades rubric expectations; None only when no selected case has any.
    grader: GraderSettings | None = None

    @property
    def results_dir(self) -> Path:
        return self.root / "eval-results" / self.run_id

    @property
    def workspaces_dir(self) -> Path:
        return self.root / ".eval-workspaces"

    @property
    def secrets(self) -> list[str]:
        found = self.adapter.secrets(self.credentials)
        if self.grader is not None:
            # A Codex run's grader holds a second credential.
            found += [v for v in self.grader.credentials.values() if v and v not in found]
        return found


def new_run_id() -> str:
    return f"{datetime.now(UTC):%Y%m%dT%H%M%SZ}-{secrets.token_hex(2)}"


def _now() -> str:
    return datetime.now(UTC).isoformat(timespec="milliseconds")


@dataclass(frozen=True)
class Planned:
    """One trial in the run's schedule."""

    order: int
    case: Case
    arm: Arm
    n: int

    @property
    def key(self) -> str:
        """The trial's path under the run: <case>/<arm>-<n>."""
        return f"{self.case.id}/{self.arm}-{self.n}"


def in_baseline(case: Case) -> bool:
    """Whether the case has an outcome to measure without the skill."""
    return bool(case.expectations) or any(not a.skill_use for a in case.assertions)


def schedule(cases: list[Case], trials: int, *, baseline: bool) -> list[Planned]:
    """Each round runs every case's arms back to back; the first arm alternates by round.

    Alternating balances order effects, such as a grader call landing just
    before the second trial of a pair, exactly when the trial count is even.
    """
    planned: list[Planned] = []
    for n in range(1, trials + 1):
        for case in cases:
            arms: list[Arm] = (
                ["skill", "baseline"] if baseline and in_baseline(case) else ["skill"]
            )
            if n % 2 == 0:
                arms.reverse()
            planned += [Planned(len(planned) + i, case, arm, n) for i, arm in enumerate(arms)]
    return planned


def grader_calls(case: Case) -> int:
    """The grader calls one trial of the case makes: one per nonempty group, blinded and not."""
    return sum(any(e.blinded is blinded for e in case.expectations) for blinded in (True, False))


def describe_plan(  # noqa: PLR0913 -- every figure the plan prints
    skill: str,
    agent: str,
    cases: list[Case],
    *,
    trials: int,
    baseline: bool,
    grader_model: str,
    agent_budget_usd: float | None,
) -> str:
    """The calls a run will make, and its spend cap, before anything is spent."""
    planned = schedule(cases, trials, baseline=baseline)
    calls = {arm: sum(p.arm == arm for p in planned) for arm in ("skill", "baseline")}
    graded = sum(grader_calls(p.case) for p in planned)
    skipped = [case.id for case in cases if baseline and not in_baseline(case)]
    lines = [
        (
            f"Plan: {skill} on {agent}, {trials} trial{'' if trials == 1 else 's'} per case, "
            f"baseline {'on' if baseline else 'off'}"
        ),
        f"  skill arm: {calls['skill']} agent calls",
    ]
    if baseline:
        lines += [
            f"  baseline arm: {calls['baseline']} agent calls",
            f"  skipped in the baseline: {', '.join(skipped) or 'none'}",
        ]
    lines.append(f"  grader calls: at most {graded} ({grader_model})")
    per_call = f"${GRADER_BUDGET_USD:.2f}"
    if agent_budget_usd is None:
        cap = graded * GRADER_BUDGET_USD
        lines.append(
            f"  spend cap: ${cap:.2f} for the grader ({per_call} per call); "
            f"{agent} agent calls have no per-call cap"
        )
    else:
        cap = (calls["skill"] + calls["baseline"]) * agent_budget_usd + graded * GRADER_BUDGET_USD
        lines.append(f"  spend cap: ${cap:.2f} (each call is capped by --max-budget-usd)")
    return "\n".join(lines)


def select_cases(cases: tuple[Case, ...], case_ids: tuple[str, ...]) -> list[Case]:
    known = {case.id: case for case in cases}
    for case_id in case_ids:
        if case_id not in known:
            msg = f"unknown case {case_id!r}; known cases: {', '.join(known)}"
            raise UsageError(msg)
    return [case for case in cases if not case_ids or case.id in case_ids]


def _assertion_class(assertion: Assertion) -> str:
    return "skill_use" if assertion.skill_use else "outcome"


def _not_scored(case: Case, arm: Arm, reason: str, problems: list[str]) -> dict[str, Any]:
    """An infrastructure error: recorded, never scored, so it can never pass a case."""
    return {
        "status": "infra_error",
        "status_reason": reason,
        "trigger": {
            "expected": case.should_trigger,
            "actual": None,
            "matched": None,
            "applicable": arm == "skill",
        },
        # null: the check never ran. A failed preflight is a contamination failure.
        "contamination": {
            "passed": False if problems else None,
            "problems": problems,
            "notes": [],
        },
        "assertions": [
            {
                "type": a.type,
                "class": _assertion_class(a),
                "result": "not_scored",
                "evidence": "",
            }
            for a in case.assertions
        ],
    }


def _score(
    settings: RunSettings, case: Case, arm: Arm, trace: Trace, trial: TrialPaths
) -> dict[str, Any]:
    if trace.status != "ok":
        return _not_scored(case, arm, trace.status_reason, [])
    actual = settings.skill in trace.skills_triggered
    skill_arm = arm == "skill"
    installed = trial.workspace / settings.adapter.skills_dir / settings.skill
    scored = []
    for assertion in case.assertions:
        record = {"type": assertion.type, "class": _assertion_class(assertion)}
        if assertion.skill_use and not skill_arm:
            # Skill use means nothing without the skill; the baseline never scores it.
            scored.append({**record, "result": "not_applicable", "evidence": "baseline arm"})
            continue
        result = evaluate(
            assertion,
            trace,
            skill=settings.skill,
            skill_dir=settings.root / "skills" / settings.skill,
            installed=installed if skill_arm else None,
        )
        scored.append(
            {
                **record,
                "result": "passed" if result.passed else "failed",
                "evidence": result.evidence,
            }
        )
    return {
        "status": "ok",
        "status_reason": "",
        "trigger": {
            "expected": case.should_trigger,
            "actual": actual,
            # A trigger in the baseline is a contamination failure, not a mismatch.
            "matched": actual == case.should_trigger if skill_arm else None,
            "applicable": skill_arm,
        },
        "assertions": scored,
    }


def _attempt(
    settings: RunSettings,
    planned: Planned,
    trial: TrialPaths,
    secrets: list[str],
    credentials: Mapping[str, str],
) -> tuple[dict[str, Any], Trace | None]:
    """Preflight, run, check and score one trial. Adds the run's new secrets to `secrets`.

    Returns the record and the trace, which grading reads after teardown; no
    trace when the preflight stopped the trial.
    """
    adapter, case = settings.adapter, planned.case
    baseline = planned.arm == "baseline"
    skill = None if baseline else settings.skill
    homes = adapter.prepare_homes(trial)
    adapter.install_skill(
        None if baseline else settings.root / "skills" / settings.skill, trial.workspace
    )
    problems = preflight(adapter, trial, homes, settings.root, skill)
    if problems:
        reason = "preflight failed: " + "; ".join(problems)
        return _not_scored(case, planned.arm, reason, problems), None
    raw = adapter.run(
        case.prompt,
        trial,
        homes,
        model=settings.model,
        timeout=settings.timeout,
        credentials=credentials,
    )
    _add_trial_secrets(adapter, trial, secrets)
    trace = adapter.parse(raw)
    contamination = check(
        adapter,
        trace,
        skill=settings.skill,
        baseline=baseline,
        trial=trial,
        never=settings.never,
        system_root=settings.system_root,
    )
    transcript = settings.results_dir / "transcripts" / f"{planned.key}.jsonl"
    results.write_text(transcript, raw.transcript.read_text(errors="replace"), secrets)
    try:
        scored = _score(settings, case, planned.arm, trace, trial)
    except Exception as error:  # noqa: BLE001 -- keep the run's evidence when scoring breaks
        reason = f"harness error while scoring: {type(error).__name__}: {error}"
        scored = _not_scored(case, planned.arm, results.scrub(reason, secrets), [])
    record = {
        "cli_version": trace.cli_version,
        # The model the agent reports running, which a --model alias resolves to.
        "model": trace.model,
        **scored,
        # Listed after `scored`, so the real result replaces _not_scored's null.
        "contamination": {
            "passed": contamination.passed,
            "problems": contamination.problems,
            "notes": contamination.notes,
        },
        "transcript": transcript.relative_to(settings.root).as_posix(),
        "stderr": results.scrub(raw.stderr[-2000:], secrets),
    }
    return record, trace


def _add_trial_secrets(adapter: Adapter, trial: TrialPaths, secrets: list[str]) -> None:
    secrets += [value for value in adapter.trial_secrets(trial) if value not in secrets]


def _collect_credentials(
    adapter: Adapter, trial: TrialPaths, secrets: list[str], credentials: dict[str, str]
) -> str:
    """Add the trial's secrets and carry its login forward; why they could not be read, or ""."""
    try:
        _add_trial_secrets(adapter, trial, secrets)
    except Exception as error:  # noqa: BLE001 -- the trial fails closed; the run goes on
        # The type only: the message could quote the file.
        return f"could not read the trial's credentials: {type(error).__name__}"
    credentials |= adapter.trial_credentials(trial, credentials)
    return ""


def _scorable(record: Mapping[str, Any]) -> bool:
    """No secret found, the run was ok and uncontaminated: its scores count."""
    return benchmark.exclusion(record) is None


def run_trial(
    settings: RunSettings,
    planned: Planned,
    secrets: list[str] | None = None,
    credentials: dict[str, str] | None = None,
) -> dict[str, Any]:
    """One trial. A harness failure is recorded as an infrastructure error, not raised.

    `secrets` starts as the run's credential values and gains any the trial's
    run reports, such as a refreshed login, so the caller can scrub for them too.
    `credentials` starts as the run's credential and becomes the trial's own
    copy, so the next trial starts from a refreshed login.
    """
    if secrets is None:
        secrets = list(settings.secrets)
    if credentials is None:
        credentials = dict(settings.credentials)
    case = planned.case
    record: dict[str, Any] = {
        "case": case.id,
        "kind": case.kind,
        "agent": settings.adapter.name,
        "arm": planned.arm,
        "trial": planned.n,
        "order": planned.order,
        "started_at": _now(),
        "cli_version": None,
        "model": None,
        "transcript": None,
        "secret_found": None,
        "grading": None,
        "graded": None,
    }
    trial: TrialPaths | None = None
    trace: Trace | None = None
    try:
        trial = workspace.create_trial(settings.workspaces_dir, settings.run_id, planned.key)
        scored, trace = _attempt(settings, planned, trial, secrets, credentials)
        record |= scored
    except Exception as error:  # noqa: BLE001 -- one trial's failure must not lose the run
        if trial is not None:
            _collect_credentials(settings.adapter, trial, secrets, credentials)
        reason = results.scrub(f"harness error: {type(error).__name__}: {error}", secrets)
        record |= _not_scored(case, planned.arm, reason, [])
    finally:
        if trial is not None:
            # Before teardown removes the trial's home, on every path.
            unreadable = _collect_credentials(settings.adapter, trial, secrets, credentials)
            workspace.teardown(trial)
            leaked = results.files_holding(trial.root, secrets)
            if leaked or unreadable:
                # Anywhere in the trial, not only the workspace, so all of it goes.
                shutil.rmtree(trial.root, ignore_errors=True)
            if leaked:
                record["secret_found"] = {
                    "files": [path.relative_to(trial.root).as_posix() for path in leaked],
                    "deleted": not trial.root.exists(),
                }
            if unreadable:
                # A token the sweep cannot know of may be in the evidence, so none is kept.
                if record["transcript"] is not None:
                    (settings.root / record["transcript"]).unlink(missing_ok=True)
                record.pop("stderr", None)
                record |= _not_scored(case, planned.arm, unreadable, [])
                record["transcript"] = None
        record["finished_at"] = _now()
    # After the sweep, so a workspace that held a credential never reaches the
    # grader, and with the trace scrubbed: the sweep never sees the transcript.
    if trial is not None and trace is not None and case.expectations and _scorable(record):
        record |= _grade(settings, planned, _scrubbed(trace, secrets), trial, secrets)
    graded = record["graded"]
    record["valid"] = _scorable(record) and (graded is None or graded["status"] != "grader_error")
    record["passed"] = (
        record["valid"]
        and record["trigger"]["matched"] is True
        and all(a["result"] == "passed" for a in record["assertions"])
        and (graded is None or (graded["status"] == "ok" and graded["failed"] == 0))
        if planned.arm == "skill"
        else None
    )
    return record


def _scrubbed(trace: Trace, secrets: list[str]) -> Trace:
    """The trace with the run's secrets removed from everything the grader may see."""
    return replace(
        trace,
        final_message=results.scrub(trace.final_message, secrets),
        commands=[
            replace(
                command,
                command=results.scrub(command.command, secrets),
                output=results.scrub(command.output, secrets),
            )
            for command in trace.commands
        ],
    )


def _grade(
    settings: RunSettings,
    planned: Planned,
    trace: Trace,
    trial: TrialPaths,
    secrets: list[str],
) -> dict[str, Any]:
    """Grade the trial's expectations and write its grading file. Never raises."""
    total = len(planned.case.expectations)
    no_grading = {
        "status": "grader_error",
        "passed": 0,
        "failed": 0,
        "total": total,
        "pass_rate": None,
        "arm_disclosed": False,
    }
    if settings.grader is None:
        return {"grading": None, "graded": no_grading}
    try:
        grading = grader.grade(
            settings.grader,
            case=planned.case,
            trace=trace,
            trial=trial,
            workspaces_dir=settings.workspaces_dir,
            run_id=settings.run_id,
            skill=settings.skill,
            skills_dir=settings.adapter.skills_dir,
            skill_dir=settings.root / "skills" / settings.skill,
            run_secrets=secrets,
        )
    except Exception:  # noqa: BLE001 -- a harness bug in grading must not lose the run
        # No grading file: the benchmark counts the trial as a grader error.
        return {"grading": None, "graded": no_grading}
    path = settings.results_dir / "grading" / f"{planned.key}.json"
    try:
        results.write_json(path, grading, secrets)
    except OSError, ValueError:
        # No grading file, as above. A partial one is removed if it can be;
        # either way the trial no longer points at it.
        with suppress(OSError):
            path.unlink(missing_ok=True)
        return {"grading": None, "graded": no_grading}
    summary = grading["summary"]
    return {
        "grading": path.relative_to(settings.root).as_posix(),
        "graded": {
            "status": grading["grader"]["status"],
            "passed": summary["passed"],
            "failed": summary["failed"],
            "total": summary["total"],
            "pass_rate": summary["pass_rate"],
            "arm_disclosed": grading["arm_disclosed"],
        },
    }


def _load_gradings(root: Path, trials: list[dict[str, Any]]) -> dict[str, Any]:
    """Each trial's grading file, read back; None for one that is missing or unreadable."""
    gradings: dict[str, Any] = {}
    for trial in trials:
        if (path := trial["grading"]) is not None:
            try:
                gradings[path] = json.loads((root / path).read_text())
            except OSError, ValueError:
                gradings[path] = None
    return gradings


def run_suite(settings: RunSettings) -> int:
    """Run the planned trials; 0 when every skill trial passed and every baseline trial is valid."""
    suite = load_suite(settings.root, settings.skill)
    cases = select_cases(suite.cases, settings.case_ids)
    started = _now()
    secrets = list(settings.secrets)
    credentials = dict(settings.credentials)
    # Recorded before any trial runs, so it describes what the run started from.
    provenance = {
        **benchmark.provenance(settings.root, settings.skill),
        "grader_prompt_sha256": grader.prompt_sha256(),
    }
    planned = schedule(cases, settings.trials, baseline=settings.baseline)
    trials = [run_trial(settings, p, secrets, credentials) for p in planned]
    passed = all(t["passed"] if t["arm"] == "skill" else t["valid"] for t in trials)
    skipped = [case.id for case in cases if settings.baseline and not in_baseline(case)]
    # The grader that ran, if any case had expectations to grade.
    used = settings.grader if any(case.expectations for case in cases) else None
    credential_env = list(settings.adapter.credential_env)
    if used is not None:
        # The grader is Claude for every agent, so a Codex run reads its token too.
        credential_env += [n for n in used.credentials if n not in credential_env]
    data = {
        "run_id": settings.run_id,
        "skill": settings.skill,
        "agent": settings.adapter.name,
        "requested_model": settings.model,
        "credential_env": credential_env,
        "started_at": started,
        "finished_at": _now(),
        "passed": passed,
        "trials_per_case": settings.trials,
        "baseline": settings.baseline,
        "grader_model_requested": used.model if used is not None else None,
        "cases": [
            {
                "id": case.id,
                "kind": case.kind,
                "should_trigger": case.should_trigger,
                "expectations": [
                    {"text": e.text, "blinded": e.blinded} for e in case.expectations
                ],
                "in_baseline": settings.baseline and in_baseline(case),
            }
            for case in cases
        ],
        "skipped_in_baseline": skipped,
        "provenance": provenance,
        "trials": trials,
    }
    path = settings.results_dir / "results.json"
    results.write_json(path, data, secrets)
    summary = benchmark.aggregate(data, _load_gradings(settings.root, trials))
    results.write_json(settings.results_dir / "benchmark.json", summary, secrets)
    try:
        results.verify_clean(settings.results_dir, secrets)
    except results.SecretLeakError as error:
        print(f"eval: {error}")
        return 1
    for trial in trials:
        label = f"{trial['case']}/{trial['arm']}-{trial['trial']}"
        if trial["arm"] == "skill":
            verdict = "PASS" if trial["passed"] else "FAIL"
            ok = trial["passed"]
        else:
            verdict = "VALID" if trial["valid"] else "INVALID"
            ok = trial["valid"]
        reason = "" if ok else f": {_why(trial)}"
        # The record holds the agent's own error text, so it is scrubbed like the files.
        print(results.scrub(f"{verdict} {label}{reason}", secrets))
    print(results.scrub(benchmark.table(summary), secrets))
    print(f"Results: {path.relative_to(settings.root)}")
    print(f"Benchmark: {(settings.results_dir / 'benchmark.json').relative_to(settings.root)}")
    return 0 if passed else 1


def _why(trial: Mapping[str, Any]) -> str:
    reasons = []
    if leak := trial.get("secret_found"):
        state = "deleted" if leak["deleted"] else "NOT deleted"
        reasons.append(
            f"secret found in the trial directory ({', '.join(leak['files'])}), {state}"
        )
    if trial.get("status") != "ok":
        return "; ".join([*reasons, f"infrastructure error, {trial.get('status_reason')}"])
    if not trial["contamination"]["passed"]:
        reasons.append("contamination: " + "; ".join(trial["contamination"]["problems"]))
    if trial["trigger"]["applicable"] and trial["trigger"]["matched"] is not True:
        reasons.append(
            f"trigger expected {trial['trigger']['expected']}, got {trial['trigger']['actual']}"
        )
    if trial["arm"] == "skill":
        reasons += [
            f"{a['type']} failed ({a['evidence']})"
            for a in trial["assertions"]
            if a["result"] not in ("passed", "not_applicable")
        ]
    if (graded := trial.get("graded")) is not None:
        where = f"see {trial['grading']}" if trial.get("grading") else "no grading file"
        if graded["status"] != "ok":
            reasons.append(f"grading {graded['status']} ({where})")
        elif trial["arm"] == "skill" and graded["failed"]:
            reasons.append(f"{graded['failed']} of {graded['total']} expectations failed")
    return "; ".join(reasons)
