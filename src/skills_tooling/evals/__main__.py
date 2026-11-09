"""Validate eval cases, run them against an agent, record benchmarks and report on them.

See docs/reference/evals.md.
"""

import argparse
import json
import os
import sys
from pathlib import Path
from typing import TYPE_CHECKING, Any

from skills_tooling.distribution import MARKETPLACE
from skills_tooling.evals import history, workspace
from skills_tooling.evals import report as reporting
from skills_tooling.evals.adapter import AGENTS, CredentialError
from skills_tooling.evals.cases import CaseError, load_suite, validate_all
from skills_tooling.evals.claude_code import BUDGET_USD, ClaudeCode
from skills_tooling.evals.codex import Codex, pinned_executable
from skills_tooling.evals.contamination import default_never_appear
from skills_tooling.evals.grader import GraderSettings
from skills_tooling.evals.runner import (
    RunSettings,
    UsageError,
    describe_plan,
    new_run_id,
    run_suite,
    select_cases,
)
from skills_tooling.validator import PLACEHOLDER

if TYPE_CHECKING:
    from skills_tooling.evals.adapter import Adapter
    from skills_tooling.evals.cases import Case

USAGE = 2
REGRESSED = 1
GRADER_MODEL = "claude-opus-5-5"


def unwritten_distributed(root: Path) -> dict[str, list[str]]:
    """Distributed skills with placeholder cases: their ids, or [] when every case is one."""
    try:
        plugins = json.loads((root / MARKETPLACE).read_text())["plugins"]
        listed = sorted({entry["name"] for entry in plugins})
    except OSError, ValueError, KeyError, TypeError:
        return {}  # validate-distribution reports a missing or malformed marketplace.
    found: dict[str, list[str]] = {}
    for name in listed:
        try:
            suite = load_suite(root, name)
        except CaseError, OSError:
            continue
        placeholders = [case.id for case in suite.cases if case.placeholder]
        if placeholders:
            found[name] = placeholders if len(placeholders) < len(suite.cases) else []
    return found


def validate(root: Path) -> int:
    problems = validate_all(root)
    for problem in problems:
        print(problem, file=sys.stderr)
    if problems:
        return 1
    for name, some in unwritten_distributed(root).items():
        which = (
            f"still has placeholder cases: {', '.join(some)}"
            if some
            else "has only placeholder cases"
        )
        print(
            f"warning: {name} is in {MARKETPLACE} but evals/{name}/evals.json {which}; "
            "write them (see CONTRIBUTING.md)",
            file=sys.stderr,
        )
    count = len(list((root / "evals").glob("*/evals.json")))
    print(f"{count} eval suite{'' if count == 1 else 's'} valid.")
    return 0


def refuse_unwritten(args: argparse.Namespace, root: Path) -> bool:
    """Report selected placeholder cases, which have nothing to measure yet; True if any."""
    try:
        cases = select_cases(load_suite(root, args.skill).cases, tuple(args.case))
    except CaseError, UsageError, FileNotFoundError:
        return False  # The run reports these itself.
    unwritten = [case for case in cases if case.placeholder]
    for case in unwritten:
        print(
            f"UNWRITTEN {args.skill}/{case.id}: a starter case from just new-skill; "
            f'replace its {PLACEHOLDER} text and delete "placeholder": true',
            file=sys.stderr,
        )
    if unwritten:
        print("eval: nothing ran; write those cases or pick others with --case.", file=sys.stderr)
    return bool(unwritten)


def adapter_for(agent: str, root: Path) -> Adapter:
    if agent == "codex":
        return Codex(pinned_executable(root))
    return ClaudeCode(root / "node_modules/.bin/claude")


def describe(args: argparse.Namespace, cases: list[Case]) -> str:
    return describe_plan(
        args.skill,
        args.agent,
        cases,
        trials=args.trials,
        baseline=args.baseline,
        grader_model=args.grader_model,
        # Only Claude Code takes a per-call budget.
        agent_budget_usd=float(BUDGET_USD) if args.agent == "claude" else None,
        grading_skipped=args.no_grader,
    )


def plan(args: argparse.Namespace) -> int:
    """Print the calls a run would make. Reads no credential and writes nothing."""
    root: Path = args.root.resolve()
    if refuse_unwritten(args, root):
        return USAGE
    try:
        suite = load_suite(root, args.skill)
        cases = select_cases(suite.cases, tuple(args.case))
    except (CaseError, UsageError, FileNotFoundError) as error:
        print(f"eval: {error}", file=sys.stderr)
        return USAGE
    print(describe(args, cases))
    return 0


def grader_settings(
    args: argparse.Namespace, root: Path, cases: list[Case]
) -> GraderSettings | None:
    """The grader, when a selected case has expectations; raises CredentialError without its token.

    The grader is always Claude, so a Codex run reads CLAUDE_CODE_OAUTH_TOKEN too.
    With --no-grader there is no grader and no token is read for one.
    """
    if args.no_grader or not any(case.expectations for case in cases):
        return None
    claude = ClaudeCode(root / "node_modules/.bin/claude")
    try:
        credentials = claude.read_credentials(os.environ)
    except CredentialError as error:
        msg = f"the grader runs on Claude Code for every agent: {error}"
        raise CredentialError(msg) from error
    return GraderSettings(claude.executable, args.grader_model, credentials)


def run(args: argparse.Namespace) -> int:
    if args.dry_run:
        return plan(args)
    root: Path = args.root.resolve()
    if refuse_unwritten(args, root):
        return USAGE
    # The credential is read here and handed only to the trial.
    try:
        adapter = adapter_for(args.agent, root)
        credentials = adapter.read_credentials(os.environ)
    except (CredentialError, FileNotFoundError) as error:
        print(f"eval: {error}", file=sys.stderr)
        return USAGE
    try:
        suite = load_suite(root, args.skill)
        cases = select_cases(suite.cases, tuple(args.case))
        grader = grader_settings(args, root, cases)
    except (CaseError, UsageError, FileNotFoundError, CredentialError) as error:
        print(f"eval: {error}", file=sys.stderr)
        return USAGE
    pinned = [adapter.executable] + ([grader.executable] if grader is not None else [])
    for path in pinned:
        if not path.is_file():
            print(f"eval: the pinned CLI {path} is missing; run just initialize.", file=sys.stderr)
            return USAGE
    settings = RunSettings(
        root=root,
        skill=args.skill,
        adapter=adapter,
        model=args.model or adapter.default_model,
        timeout=args.timeout,
        credentials=credentials,
        case_ids=tuple(args.case),
        run_id=new_run_id(),
        never=default_never_appear(root, args.skill),
        trials=args.trials,
        baseline=args.baseline,
        grader=grader,
        grading_skipped=args.no_grader,
    )
    print(describe(args, cases))
    with workspace.end_on_termination():
        return run_suite(settings)


def record(args: argparse.Namespace) -> int:
    """Write finished runs as a named iteration under benchmarks/<skill>/."""
    root: Path = args.root.resolve()
    try:
        path = history.record(root, args.name, args.run_ids)
    except history.HistoryError as error:
        print(f"eval: {error}", file=sys.stderr)
        return USAGE
    print(f"Recorded {path.relative_to(root)}")
    return 0


def _reports(args: argparse.Namespace, root: Path) -> list[dict[str, Any]]:
    """Each skill's report: its recorded iterations, then any --run runs as one more."""
    provisional = history.assemble(root, None, args.run) if args.run else None
    if provisional is not None and args.skill not in (None, provisional["skill"]):
        msg = f"the --run runs test {provisional['skill']}, not {args.skill}"
        raise history.HistoryError(msg)
    skills = [args.skill] if args.skill else history.recorded_skills(root)
    if provisional is not None and provisional["skill"] not in skills:
        skills.append(provisional["skill"])
    reports = []
    for skill in skills:
        iterations = history.load(root, skill)
        if provisional is not None and provisional["skill"] == skill:
            iterations.append(provisional)
        if iterations:
            reports.append(reporting.build(iterations, threshold=args.threshold))
    return reports


def report(args: argparse.Namespace) -> int:
    """Build the offline report from recorded iterations. Calls no agent and no network."""
    root: Path = args.root.resolve()
    try:
        reports = _reports(args, root)
    except history.HistoryError as error:
        print(f"eval: {error}", file=sys.stderr)
        return USAGE
    if not reports:
        scope = f"for {args.skill} " if args.skill else ""
        print(
            f"eval: no benchmark recorded {scope}in benchmarks/; record one with just eval-record.",
            file=sys.stderr,
        )
        return USAGE
    out: Path = args.out if args.out is not None else root / "eval-results/report.html"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(reporting.render_html(reports))
    if args.markdown is not None:
        args.markdown.parent.mkdir(parents=True, exist_ok=True)
        args.markdown.write_text("\n".join(reporting.markdown(each) for each in reports))
    for each in reports:
        print(reporting.summary(each), end="")
    print(f"Report: {out}")
    regressed = any(each["regressions"] for each in reports)
    return REGRESSED if regressed and args.fail_on_regression else 0


def threshold(value: str) -> float:
    number = float(value)
    if not 0 <= number <= 1:
        msg = f"must be between 0 and 1, got {number}"
        raise argparse.ArgumentTypeError(msg)
    return number


def trials(value: str) -> int:
    count = int(value)
    if count < 1:
        msg = f"must be at least 1, got {count}"
        raise argparse.ArgumentTypeError(msg)
    return count


def main() -> None:
    parser = argparse.ArgumentParser(prog="python -m skills_tooling.evals", description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    check = commands.add_parser("validate", help="Validate every evals/*/evals.json.")
    check.add_argument("--root", type=Path, default=Path.cwd())
    live = commands.add_parser("run", help="Run a skill's eval cases against an agent.")
    live.add_argument("skill", help="The skill under test, as in evals/<skill>/.")
    live.add_argument("--agent", choices=AGENTS, required=True)
    live.add_argument(
        "--case", action="append", default=[], help="Run only this case (repeatable)."
    )
    live.add_argument(
        "--model",
        help=f"Default: {ClaudeCode.default_model} (claude), {Codex.default_model} (codex).",
    )
    live.add_argument("--timeout", type=float, default=300.0, help="Seconds per trial.")
    live.add_argument(
        "--trials", type=trials, default=1, help="Trials per case per arm (default 1)."
    )
    live.add_argument(
        "--baseline",
        action="store_true",
        help="Also run each case that has an outcome to measure with no skill installed.",
    )
    live.add_argument(
        "--grader-model",
        default=GRADER_MODEL,
        help=f"The grader's model. Default: {GRADER_MODEL}.",
    )
    live.add_argument(
        "--no-grader",
        action="store_true",
        help="Skip grading: cases with expectations rest on their assertions alone.",
    )
    live.add_argument(
        "--dry-run",
        action="store_true",
        help="Print the planned agent and grader calls and the spend cap, then exit.",
    )
    live.add_argument("--root", type=Path, default=Path.cwd())
    keep = commands.add_parser("record", help="Record finished runs as a named iteration.")
    keep.add_argument("name", help="The iteration's name, such as a version or a change.")
    keep.add_argument("run_ids", nargs="+", metavar="run-id", help="One run per agent.")
    keep.add_argument("--root", type=Path, default=Path.cwd())
    show = commands.add_parser("report", help="Build the offline benchmark report.")
    show.add_argument("skill", nargs="?", help="Report only this skill.")
    show.add_argument(
        "--run",
        action="append",
        default=[],
        metavar="RUN_ID",
        help="Add an unrecorded run as the last iteration (repeatable, one per agent).",
    )
    show.add_argument(
        "--threshold",
        type=threshold,
        default=reporting.DEFAULT_THRESHOLD,
        help=f"Flag a metric that fell by more than this. Default: {reporting.DEFAULT_THRESHOLD}.",
    )
    show.add_argument(
        "--fail-on-regression",
        action="store_true",
        help=f"Exit {REGRESSED} when any metric is flagged.",
    )
    show.add_argument("--out", type=Path, help="Default: eval-results/report.html.")
    show.add_argument(
        "--markdown",
        type=Path,
        help="Also write the headline matrix and regressions as Markdown, for a job summary.",
    )
    show.add_argument("--root", type=Path, default=Path.cwd())
    args = parser.parse_args()
    handlers = {"run": run, "record": record, "report": report}
    sys.exit(validate(args.root) if args.command == "validate" else handlers[args.command](args))


if __name__ == "__main__":
    main()
