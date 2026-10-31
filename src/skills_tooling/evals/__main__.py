"""Validate eval cases, or run them against an agent. See docs/reference/evals.md."""

import argparse
import os
import sys
from pathlib import Path
from typing import TYPE_CHECKING

from skills_tooling.evals.adapter import CredentialError
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

if TYPE_CHECKING:
    from skills_tooling.evals.adapter import Adapter
    from skills_tooling.evals.cases import Case

USAGE = 2
GRADER_MODEL = "claude-opus-5-5"


def validate(root: Path) -> int:
    problems = validate_all(root)
    for problem in problems:
        print(problem, file=sys.stderr)
    if problems:
        return 1
    count = len(list((root / "evals").glob("*/evals.json")))
    print(f"{count} eval suite{'' if count == 1 else 's'} valid.")
    return 0


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
    )


def plan(args: argparse.Namespace) -> int:
    """Print the calls a run would make. Reads no credential and writes nothing."""
    root: Path = args.root.resolve()
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
    """
    if not any(case.expectations for case in cases):
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
    )
    print(describe(args, cases))
    return run_suite(settings)


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
    live.add_argument("--agent", choices=["claude", "codex"], required=True)
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
        "--dry-run",
        action="store_true",
        help="Print the planned agent and grader calls and the spend cap, then exit.",
    )
    live.add_argument("--root", type=Path, default=Path.cwd())
    args = parser.parse_args()
    sys.exit(validate(args.root) if args.command == "validate" else run(args))


if __name__ == "__main__":
    main()
