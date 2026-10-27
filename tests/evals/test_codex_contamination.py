"""The contamination check for Codex, with a canary in each discovery location.

Codex does not report the skills it loaded, so the check reads the locations
themselves after the run. Each test plants one canary and shows the check fails.
"""

from dataclasses import replace
from pathlib import Path
from typing import TYPE_CHECKING

import pytest

from skills_tooling.evals import workspace
from skills_tooling.evals.codex import BUILTIN_SKILLS, SYSTEM_MARKER, Codex, pinned_executable
from skills_tooling.evals.contamination import NeverAppear, check, preflight
from tests.evals.test_codex_parser import parse

if TYPE_CHECKING:
    from collections.abc import Callable

    from skills_tooling.evals.adapter import TrialPaths

ROOT = Path(__file__).parents[2]
ADAPTER = Codex(pinned_executable(ROOT))
NOTHING = NeverAppear(skills={}, instruction_files=())


@pytest.fixture
def trial(tmp_path: Path) -> TrialPaths:
    """A trial as Codex leaves it: the skill installed and the bundled skills written."""
    repo = tmp_path / "repo"
    repo.mkdir()
    workspace.git("init", "--quiet", cwd=repo)
    (repo / ".gitignore").write_text(".eval-workspaces/\n")
    created = workspace.create_trial(repo / ".eval-workspaces", "run", "case")
    homes = ADAPTER.prepare_homes(created)
    ADAPTER.install_skill(ROOT / "skills/cowsay", created.workspace)
    system = homes.agent_home / "skills/.system"
    for name in BUILTIN_SKILLS["0.163.0"]:
        skill(system, name)
    (system / SYSTEM_MARKER).write_text("marker\n")
    return created


def skill(directory: Path, name: str) -> None:
    (directory / name).mkdir(parents=True)
    (directory / name / "SKILL.md").write_text(
        f"---\nname: {name}\ndescription: Canary {name}.\n---\nbody\n"
    )


def problems(
    trial: TrialPaths,
    name: str = "fake-should-trigger",
    *,
    forbidden: NeverAppear = NOTHING,
    system_root: Path | None = None,
    baseline: bool = False,
) -> list[str]:
    return check(
        ADAPTER,
        parse(name),
        skill="cowsay",
        baseline=baseline,
        trial=trial,
        never=forbidden,
        system_root=system_root or trial.root / "system-root",
    ).problems


def test_a_clean_trial_passes_and_notes_that_codex_reports_no_skills(trial: TrialPaths) -> None:
    result = check(
        ADAPTER,
        parse("fake-should-trigger"),
        skill="cowsay",
        baseline=False,
        trial=trial,
        never=NOTHING,
        system_root=trial.root / "system-root",
    )
    assert result.problems == []
    assert any("does not report its skills" in note for note in result.notes)


def test_an_explicit_trigger_passes(trial: TrialPaths) -> None:
    assert problems(trial, "fake-explicit") == []


# One canary per location Codex reads (docs/explanation/eval-isolation.md).
CODEX_HOME = ".codex"
CANARIES: dict[str, Callable[[TrialPaths, Path], object]] = {
    "repo-skills": lambda t, _: skill(t.workspace / ".agents/skills", "canary-repo"),
    "home-agents-skills": lambda t, _: skill(t.home / ".agents/skills", "canary-home"),
    "codex-home-skills": lambda t, _: skill(t.home / CODEX_HOME / "skills", "canary-codex-home"),
    "system-skills": lambda t, _: skill(t.home / CODEX_HOME / "skills/.system", "canary-system"),
    "etc-codex": lambda _, system: skill(system / "etc/codex/skills", "canary-etc"),
    "plugins": lambda t, _: (t.home / CODEX_HOME / "plugins/cache/canary").mkdir(parents=True),
    "plugin-sync": lambda t, _: (t.home / CODEX_HOME / ".tmp/plugins").mkdir(parents=True),
    "global-agents-md": lambda t, _: (t.home / CODEX_HOME / "AGENTS.md").write_text("CANARY\n"),
    "global-agents-override-md": lambda t, _: (
        t.home / CODEX_HOME / "AGENTS.override.md"
    ).write_text("CANARY\n"),
}


@pytest.mark.parametrize("location", sorted(CANARIES))
def test_a_canary_in_each_discovery_location_fails_the_check(
    trial: TrialPaths, location: str
) -> None:
    system_root = trial.root / "system-root"
    CANARIES[location](trial, system_root)
    found = problems(trial, system_root=system_root)
    assert found, f"a canary in {location} passed the check"


def test_the_user_shared_skills_canary_is_named(trial: TrialPaths) -> None:
    CANARIES["home-agents-skills"](trial, trial.root)
    assert problems(trial) == [f"user skills in {trial.home}/.agents/skills: ['canary-home']"]


def test_a_baseline_with_the_skill_installed_fails(trial: TrialPaths) -> None:
    assert problems(trial, "fake-should-not-trigger", baseline=True) == [
        "repo skills: ['cowsay'] (expected 0 skill)"
    ]


def test_reading_a_never_appear_skill_fails(trial: TrialPaths) -> None:
    observed = replace(parse("fake-should-trigger"), skills_triggered=["cowsay", "review"])
    forbidden = NeverAppear(skills={"review": "dev skill"}, instruction_files=())
    found = check(
        ADAPTER,
        observed,
        skill="cowsay",
        baseline=False,
        trial=trial,
        never=forbidden,
        system_root=trial.root / "system-root",
    ).problems
    assert "never-appear skill 'review' (dev skill) is visible" in found


def test_an_unrecorded_cli_version_fails(trial: TrialPaths) -> None:
    observed = replace(parse("fake-should-trigger"), cli_version="9.9.9")
    found = check(
        ADAPTER,
        observed,
        skill="cowsay",
        baseline=False,
        trial=trial,
        never=NOTHING,
        system_root=trial.root / "system-root",
    ).problems
    assert any("no recorded built-in allowlist for codex '9.9.9'" in p for p in found)


def test_the_preflight_passes_a_prepared_trial(trial: TrialPaths) -> None:
    homes = ADAPTER.prepare_homes(trial)
    # The bundled skills are written by Codex at startup, not before the run.
    for path in (trial.home / CODEX_HOME / "skills").iterdir():
        assert path.name == ".system"
    assert preflight(ADAPTER, trial, homes, ROOT, "cowsay") == []


def test_the_preflight_fails_without_instruction_suppression(trial: TrialPaths) -> None:
    adapter = Codex(pinned_executable(ROOT))
    adapter.config = tuple(c for c in adapter.config if not c.startswith("project_doc_max_bytes"))
    homes = adapter.prepare_homes(trial)
    assert preflight(adapter, trial, homes, ROOT, "cowsay") == [
        "project_doc_max_bytes=0 is not set, so AGENTS.md files load"
    ]
