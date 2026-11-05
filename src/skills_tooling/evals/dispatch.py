"""Plan, and check the output of, a manual live-eval dispatch from GitHub Actions.

The workflow (.github/workflows/live-evals.yml) calls these through `just eval-ci`
and `just eval-changed`. See docs/how-to/live-evals-in-ci.md.

  changed   the skills changed since the merge base with main
  plan      validate the dispatch inputs and write the runs, the flags and a summary
  runs      the finished runs of one skill under eval-results/
  scan      fail when a file under a directory holds a configured secret value
"""

import argparse
import json
import os
import sys
from dataclasses import dataclass, field
from pathlib import Path

from skills_tooling.evals import results, workspace
from skills_tooling.evals.adapter import AGENTS
from skills_tooling.evals.cases import SLUG
from skills_tooling.evals.codex import Codex
from skills_tooling.evals.history import NAME

USAGE = 2
LEAKED = 1
# Each run costs money, so the dispatch caps the trials per case.
MAX_TRIALS = 5
AGENT_CHOICES = ("both", *AGENTS)
CHANGED = "changed"
DEFAULT_BASE = "origin/main"
# The secret values the scan looks for, by environment variable. The scan also
# reads the secret fields of $CODEX_HOME/auth.json, the login Codex writes.
SCANNED_ENV = ("CLAUDE_CODE_OAUTH_TOKEN", "OPENAI_API_KEY")
# A change here can change every suite's results: the shared eval code, the
# adapters and the grader, and the pinned agent CLIs and the Node that runs them.
EVERY_SUITE_PREFIXES = ("src/skills_tooling/evals/",)
EVERY_SUITE_FILES = ("package.json", "package-lock.json", ".node-version")
LABELS = {"claude": "Claude Code", "codex": "Codex"}
# The secret each agent's runs need. The grader is Claude Code for every agent.
AGENT_SECRET = {"claude": "CLAUDE_CODE_OAUTH_TOKEN", "codex": "OPENAI_API_KEY"}


class DispatchError(Exception):
    """An input or a git call that leaves nothing safe to run."""


def suites(root: Path) -> list[str]:
    """The skills with an eval suite, evals/<name>/evals.json."""
    return sorted(
        path.parent.name
        for path in (root / "evals").glob("*/evals.json")
        if SLUG.fullmatch(path.parent.name)
    )


def select_changed(paths: list[str], known: list[str]) -> list[str]:
    """The suites the changed paths select; every one when shared eval code changed."""
    if any(p.startswith(EVERY_SUITE_PREFIXES) or p in EVERY_SUITE_FILES for p in paths):
        return sorted(known)
    named = {
        parts[1]
        for p in paths
        if len(parts := p.split("/")) > 2 and parts[0] in {"skills", "evals"}  # noqa: PLR2004 -- <top>/<name>/<file>
    }
    return sorted(named & set(known))


def _git(root: Path, *args: str) -> str:
    result = workspace.git(*args, cwd=root)
    if result.returncode != 0:
        msg = f"git {' '.join(args)} failed: {result.stderr.strip()}"
        raise DispatchError(msg)
    return result.stdout


def changed_paths(root: Path, base: str = DEFAULT_BASE) -> list[str]:
    """Paths changed since the merge base with base: commits, uncommitted edits and new files.

    A missing base raises: an empty list would read as "nothing changed".
    """
    merge_base = _git(root, "merge-base", base, "HEAD").strip()
    diffed = _git(root, "diff", "--name-only", "-z", merge_base, "--")
    untracked = _git(root, "ls-files", "-z", "--others", "--exclude-standard")
    return sorted({p for p in (diffed + untracked).split("\0") if p})


def changed(root: Path, base: str = DEFAULT_BASE) -> list[str]:
    return select_changed(changed_paths(root, base), suites(root))


@dataclass(frozen=True)
class Plan:
    """The `just eval` runs a dispatch makes, the flags they share, and what it skipped."""

    runs: list[tuple[str, str]]
    grade: bool
    flags: list[str]
    notices: list[str] = field(default_factory=list)
    skills: list[str] = field(default_factory=list)
    trials: int = 1
    baseline: bool = False

    def summary(self) -> str:
        """The job summary's plan, in Markdown. Every value in it has been validated."""
        lines = ["## Live evals", ""]
        for notice in self.notices:
            lines += [f"> {notice}", ""]
        if not self.runs:
            lines.append("No evals ran.")
            return "\n".join(lines) + "\n"
        lines += [
            (
                f"Trials per case: {self.trials}. Baseline: {'on' if self.baseline else 'off'}."
                f" Grading: {'on' if self.grade else 'skipped'}."
            ),
            "",
            "| skill | agent |",
            "| --- | --- |",
            *(f"| {skill} | {LABELS[agent]} |" for skill, agent in self.runs),
        ]
        return "\n".join(lines) + "\n"


def _boolean(name: str, value: str) -> bool:
    if value not in {"true", "false"}:
        msg = f"{name} must be true or false, got {value!r}"
        raise DispatchError(msg)
    return value == "true"


def _trials(value: str) -> int:
    # isdigit alone: int() would also take " 1", "+1" and "1_0".
    if not (value.isascii() and value.isdigit()) or not 1 <= int(value) <= MAX_TRIALS:
        msg = f"trials must be a whole number from 1 to {MAX_TRIALS}, got {value!r}"
        raise DispatchError(msg)
    return int(value)


def _skills(value: str, root: Path, base: str) -> tuple[list[str], list[str]]:
    """The selected skills, and a notice when "changed" selected none."""
    if value == CHANGED:
        selected = changed(root, base)
        notices = [] if selected else [f"Nothing changed since {base}: no skill selected."]
        return selected, notices
    if not SLUG.fullmatch(value) or value not in suites(root):
        msg = f"skill must be {CHANGED!r} or a skill with evals/<skill>/evals.json, got {value!r}"
        raise DispatchError(msg)
    return [value], []


def plan(  # noqa: PLR0913 -- one argument per dispatch input and secret
    skills: str,
    agents: str,
    trials: str,
    baseline: str,
    *,
    have_claude: bool,
    have_openai: bool,
    root: Path,
    base: str = DEFAULT_BASE,
) -> Plan:
    """Validate the dispatch inputs, as strings, and plan the runs the secrets allow."""
    if agents not in AGENT_CHOICES:
        msg = f"agents must be one of {', '.join(AGENT_CHOICES)}, got {agents!r}"
        raise DispatchError(msg)
    count = _trials(trials)
    with_baseline = _boolean("baseline", baseline)
    selected, notices = _skills(skills, root, base)
    have = {"claude": have_claude, "codex": have_openai}
    chosen = list(AGENTS) if agents == "both" else [agents]
    runnable = [a for a in chosen if have[a]]
    notices += [
        f"{LABELS[a]} skipped: the {AGENT_SECRET[a]} secret is not set in the live-evals"
        " environment."
        for a in chosen
        if not have[a]
    ]
    runs = [(skill, agent) for skill in selected for agent in runnable]
    if runs and not have_claude:
        notices.append(
            "Grading skipped: the CLAUDE_CODE_OAUTH_TOKEN secret the grader needs is not set,"
            " so cases with expectations are scored on their deterministic assertions only."
        )
    flags = ["--trials", str(count)]
    flags += ["--baseline"] if with_baseline else []
    flags += [] if have_claude else ["--no-grader"]
    return Plan(runs, have_claude, flags, notices, selected, count, with_baseline)


def finished_runs(root: Path, skill: str) -> list[str]:
    """The run ids under eval-results/ that tested skill and wrote their benchmark."""
    found = []
    for path in sorted((root / "eval-results").glob("*/results.json")):
        directory = path.parent
        if not NAME.fullmatch(directory.name) or not (directory / "benchmark.json").is_file():
            continue
        try:
            data = json.loads(path.read_text())
        except OSError, ValueError:
            continue
        if isinstance(data, dict) and data.get("skill") == skill:
            found.append(directory.name)
    return found


def scanned_secrets(environ: dict[str, str]) -> list[str]:
    """The secret values the scan looks for: SCANNED_ENV and the Codex login's secret fields."""
    found = [environ[name] for name in SCANNED_ENV if environ.get(name)]
    if home := environ.get("CODEX_HOME"):
        try:
            text = (Path(home) / "auth.json").read_text()
        except OSError:
            text = ""
        if text:
            # Only the login is read; the executable is never started.
            found += Codex(Path(os.devnull)).secrets({"auth.json": text})
    return list(dict.fromkeys(found))


def scan(directory: Path, environ: dict[str, str]) -> int:
    """Exit 1, naming each file scrubbed, when a file's contents or path holds a secret."""
    secrets = scanned_secrets(environ)
    if not secrets:
        print("scan: no secret is configured, so there is nothing to look for.")
        return 0
    if not directory.is_dir():
        print(f"scan: {directory} is not a directory.", file=sys.stderr)
        return USAGE
    leaked = results.files_holding(directory, secrets)
    for path in leaked:
        name = results.scrub(path.relative_to(directory).as_posix(), secrets)
        print(f"scan: a configured secret is in {name}", file=sys.stderr)
    if leaked:
        print(f"scan: {len(leaked)} file(s) hold a secret; do not upload {directory}.")
        return LEAKED
    count = sum(1 for p in directory.rglob("*") if p.is_file())
    print(f"scan: no configured secret in the {count} file(s) under {directory}.")
    return 0


def _write_plan(args: argparse.Namespace) -> int:
    root: Path = args.root.resolve()
    out: Path = args.out.resolve()
    if not out.is_relative_to(root / "eval-results"):
        print(f"plan: --out must be under {root / 'eval-results'}.", file=sys.stderr)
        return USAGE
    try:
        planned = plan(
            args.skills,
            args.agents,
            args.trials,
            args.baseline,
            have_claude=_boolean("--has-claude", args.has_claude),
            have_openai=_boolean("--has-openai", args.has_openai),
            root=root,
            base=args.base,
        )
    except DispatchError as error:
        print(f"plan: {error}", file=sys.stderr)
        return USAGE
    out.mkdir(parents=True, exist_ok=True)
    (out / "runs.txt").write_text("".join(f"{s} {a}\n" for s, a in planned.runs))
    (out / "flags").write_text(" ".join(planned.flags) + "\n")
    (out / "summary.md").write_text(planned.summary())
    print(planned.summary(), end="")
    return 0


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="python -m skills_tooling.evals.dispatch",
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    commands = parser.add_subparsers(dest="command", required=True)
    diff = commands.add_parser("changed", help="Print the skills changed since the merge base.")
    diff.add_argument("--base", default=DEFAULT_BASE, help=f"Default: {DEFAULT_BASE}.")
    diff.add_argument("--root", type=Path, default=Path.cwd())
    planner = commands.add_parser("plan", help="Validate the dispatch inputs and plan the runs.")
    planner.add_argument("--skills", required=True, help=f"A skill name, or {CHANGED!r}.")
    planner.add_argument("--agents", required=True, help=" | ".join(AGENT_CHOICES))
    planner.add_argument("--trials", required=True, help=f"1 to {MAX_TRIALS}.")
    planner.add_argument("--baseline", required=True, help="true | false")
    planner.add_argument("--has-claude", required=True, help="true | false")
    planner.add_argument("--has-openai", required=True, help="true | false")
    planner.add_argument("--base", default=DEFAULT_BASE, help=f"Default: {DEFAULT_BASE}.")
    planner.add_argument(
        "--out", type=Path, required=True, help="A directory under eval-results/."
    )
    planner.add_argument("--root", type=Path, default=Path.cwd())
    finished = commands.add_parser("runs", help="Print the finished runs of one skill.")
    finished.add_argument("skill")
    finished.add_argument("--root", type=Path, default=Path.cwd())
    check = commands.add_parser("scan", help="Fail when a file holds a configured secret.")
    check.add_argument("directory", type=Path)
    args = parser.parse_args()
    if args.command == "changed":
        try:
            print(
                "".join(f"{skill}\n" for skill in changed(args.root.resolve(), args.base)), end=""
            )
        except DispatchError as error:
            print(f"changed: {error}", file=sys.stderr)
            sys.exit(USAGE)
        sys.exit(0)
    if args.command == "runs":
        print("".join(f"{r}\n" for r in finished_runs(args.root.resolve(), args.skill)), end="")
        sys.exit(0)
    if args.command == "scan":
        sys.exit(scan(args.directory, dict(os.environ)))
    sys.exit(_write_plan(args))


if __name__ == "__main__":
    main()
