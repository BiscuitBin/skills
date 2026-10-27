"""Validate eval cases, or run them against an agent. See docs/reference/evals.md."""

import argparse
import os
import sys
from pathlib import Path

from skills_tooling.evals.cases import CaseError, load_suite, validate_all
from skills_tooling.evals.claude_code import ClaudeCode
from skills_tooling.evals.contamination import default_never_appear
from skills_tooling.evals.runner import (
    RunSettings,
    UsageError,
    new_run_id,
    run_suite,
    select_cases,
)

USAGE = 2


def validate(root: Path) -> int:
    problems = validate_all(root)
    for problem in problems:
        print(problem, file=sys.stderr)
    if problems:
        return 1
    count = len(list((root / "evals").glob("*/evals.json")))
    print(f"{count} eval suite{'' if count == 1 else 's'} valid.")
    return 0


def run(args: argparse.Namespace) -> int:
    root: Path = args.root.resolve()
    adapter = ClaudeCode(root / "node_modules/.bin/claude")
    # The token is read here and handed only to the child's environment.
    credentials = {name: os.environ.get(name, "") for name in adapter.credential_env}
    missing = [name for name, value in credentials.items() if not value]
    if missing:
        print(
            f"eval: {', '.join(missing)} is not set. Live evals need an authenticated agent: "
            "run `claude setup-token` and export the token. See docs/reference/evals.md.",
            file=sys.stderr,
        )
        return USAGE
    try:
        suite = load_suite(root, args.skill)
        select_cases(suite.cases, tuple(args.case))
    except (CaseError, UsageError, FileNotFoundError) as error:
        print(f"eval: {error}", file=sys.stderr)
        return USAGE
    if not adapter.executable.is_file():
        print(
            f"eval: the pinned CLI {root / 'node_modules/.bin/claude'} is missing; "
            "run just initialize.",
            file=sys.stderr,
        )
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
    )
    return run_suite(settings)


def main() -> None:
    parser = argparse.ArgumentParser(prog="python -m skills_tooling.evals", description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    check = commands.add_parser("validate", help="Validate every evals/*/evals.json.")
    check.add_argument("--root", type=Path, default=Path.cwd())
    live = commands.add_parser("run", help="Run a skill's eval cases against an agent.")
    live.add_argument("skill", help="The skill under test, as in evals/<skill>/.")
    live.add_argument("--agent", choices=["claude"], required=True)
    live.add_argument(
        "--case", action="append", default=[], help="Run only this case (repeatable)."
    )
    live.add_argument("--model", help=f"Default: {ClaudeCode.default_model}.")
    live.add_argument("--timeout", type=float, default=300.0, help="Seconds per trial.")
    live.add_argument("--root", type=Path, default=Path.cwd())
    args = parser.parse_args()
    sys.exit(validate(args.root) if args.command == "validate" else run(args))


if __name__ == "__main__":
    main()
