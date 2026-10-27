"""Prove that only the skill under test, and the agent's built-ins, reached a trial.

See docs/explanation/eval-isolation.md. The preflight runs before the agent
does and fails closed. The check runs over the trace afterwards.
"""

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING

from skills_tooling.evals import workspace

if TYPE_CHECKING:
    from collections.abc import Iterable, Mapping

    from skills_tooling.evals.adapter import Adapter, Homes, Trace, TrialPaths

# The user's own skills, by agent. Only directory names are read, never contents.
USER_SKILL_DIRS = (
    (".claude/skills", "user skill ~/.claude/skills"),
    (".agents/skills", "user skill ~/.agents/skills"),
    (".codex/skills", "user skill ~/.codex/skills"),
    (".pi/agent/skills", "user skill ~/.pi/agent/skills"),
)
INSTRUCTION_FILES = ("AGENTS.md", "CLAUDE.md", "CLAUDE.local.md")


@dataclass(frozen=True)
class NeverAppear:
    """Skill names (with where each came from) and instruction files that must stay out."""

    skills: Mapping[str, str]
    instruction_files: tuple[str, ...]


@dataclass
class ContaminationResult:
    passed: bool
    problems: list[str]
    notes: list[str] = field(default_factory=list)


def _names(directory: Path) -> list[str]:
    try:
        return sorted(p.name for p in directory.iterdir() if not p.name.startswith("."))
    except FileNotFoundError, NotADirectoryError, PermissionError:
        return []


def never_appear(
    repo_root: Path,
    skill: str,
    *,
    user_home: Path,
    agent_homes: Iterable[Path],
) -> NeverAppear:
    """What must never be visible in a trial of `skill`."""
    skills: dict[str, str] = {}
    for base, source in USER_SKILL_DIRS:
        skills |= dict.fromkeys(_names(user_home / base), source)
    for home in agent_homes:
        skills |= dict.fromkeys(_names(home / "skills"), f"agent home {home}")
    skills |= dict.fromkeys(
        (n for n in _names(repo_root / "skills") if n != skill), "another shipped skill"
    )
    skills |= dict.fromkeys(_names(repo_root / "dev-skills"), "dev skill")
    # The user's own instruction files sit above every trial too: with loading
    # on, the CLI reads ~/.claude/CLAUDE.md as an ancestor's project instructions.
    candidates = [repo_root / name for name in INSTRUCTION_FILES]
    candidates += [user_home / "CLAUDE.md", user_home / ".claude/CLAUDE.md"]
    instructions = tuple(str(path) for path in candidates if path.is_file())
    return NeverAppear(skills, instructions)


def default_never_appear(repo_root: Path, skill: str) -> NeverAppear:
    """The never-appear list for this machine: the real homes and the caller's agent homes."""
    homes = [
        Path(os.environ[name])
        for name in ("CLAUDE_CONFIG_DIR", "CODEX_HOME", "PI_CODING_AGENT_DIR")
        if os.environ.get(name)
    ]
    return never_appear(repo_root, skill, user_home=Path.home(), agent_homes=homes)


def preflight(
    adapter: Adapter, trial: TrialPaths, homes: Homes, repo_root: Path, skill: str | None
) -> list[str]:
    """Problems that must stop the trial before the agent starts. Empty when isolated."""
    problems = workspace.isolation_problems(trial, repo_root)
    for name in ("HOME", "TMPDIR", "XDG_CONFIG_HOME", "XDG_DATA_HOME", "XDG_CACHE_HOME"):
        value = homes.env.get(name)
        if value is None or not Path(value).resolve().is_relative_to(trial.root):
            problems.append(f"{name}={value!r} is not inside the trial {trial.root}")
    for path in (homes.agent_home, homes.user_home):
        if not path.resolve().is_relative_to(trial.root):
            problems.append(f"home {path} is not inside the trial {trial.root}")
    for name in adapter.home_env:
        value = homes.env.get(name)
        if value is None or Path(value).resolve() != homes.agent_home.resolve():
            problems.append(f"{name}={value!r} does not point at the trial's agent home")
    problems += adapter.context_isolation(homes.env)
    problems += workspace.inventory_problems(trial.workspace, adapter.skills_dir, skill)
    problems += [
        f"discovery location {location.name} ({location.path}) has no mitigation; failing closed"
        for location in adapter.discovery_locations(trial)
        if not location.mitigations
    ]
    return problems


def _plugin_problems(adapter: Adapter, trace: Trace, plugins: frozenset[str]) -> list[str]:
    if trace.visible_plugins is None:
        if adapter.reports_skills:
            return [f"{adapter.name} did not report its plugins; failing closed"]
        return []
    if trace.visible_plugins != plugins:
        unexpected = ", ".join(sorted(trace.visible_plugins ^ plugins))
        return [f"plugins differ from the built-in allowlist: {unexpected}"]
    return []


def check(  # noqa: PLR0913 -- everything one trial's check reads
    adapter: Adapter,
    trace: Trace,
    *,
    skill: str,
    baseline: bool,
    trial: TrialPaths,
    never: NeverAppear,
    system_root: Path = Path("/"),
) -> ContaminationResult:
    """Check one trial's trace. A baseline trial ran with `skill` not installed."""
    problems: list[str] = []
    notes: list[str] = []
    installed = set() if baseline else {skill}
    allowed = adapter.builtin_skills.get(trace.cli_version)
    plugins = adapter.builtin_plugins.get(trace.cli_version)
    if allowed is None or plugins is None:
        known = ", ".join(sorted(adapter.builtin_skills))
        problems.append(
            f"no recorded built-in allowlist for {adapter.name} {trace.cli_version!r} "
            f"(recorded: {known}); re-record it from the canary sweep"
        )
        allowed, plugins = frozenset(), frozenset()
    visible: set[str] = set()
    if not adapter.reports_skills:
        notes.append(
            f"{adapter.name} does not report its skills: the proof is the preflight's "
            "redirected homes and mitigated locations, and the canary sweep"
        )
    elif trace.visible_skills is None:
        problems.append(f"{adapter.name} did not report its visible skills; failing closed")
    else:
        visible = set(trace.visible_skills)
        if not baseline and skill not in visible:
            problems.append(f"the skill under test {skill!r} is not visible")
    discovered = set(trace.dynamic_commands) - (trace.initial_commands or frozenset())
    # A failed Skill call to a name that does not exist shows nothing leaked.
    seen = visible | discovered | set(trace.skills_triggered)
    if baseline and skill in seen:
        problems.append(f"the skill under test {skill!r} is visible in the baseline arm")
    extra = sorted(seen - allowed - installed - ({skill} if baseline else set()))
    if extra:
        problems.append(f"unexpected skills visible: {', '.join(extra)}")
    problems += _plugin_problems(adapter, trace, plugins)
    problems += adapter.discovery_report_problems(
        trace, trial, installed=not baseline, system_root=system_root
    )
    # The discovery report's paths are checked above: any outside the trial fail.
    for name, source in sorted(never.skills.items()):
        if name in allowed or name == skill:
            notes.append(
                f"{name!r} ({source}) shares a name with a built-in or the skill under test"
            )
        elif name in seen:
            problems.append(f"never-appear skill {name!r} ({source}) is visible")
    if never.instruction_files:
        notes.append(
            "instruction files are kept out by the preflight's context isolation, not observed: "
            + ", ".join(never.instruction_files)
        )
    return ContaminationResult(not problems, problems, notes)
