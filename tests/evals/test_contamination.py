"""The contamination check over a trace, and the preflight before a run."""

from dataclasses import replace
from pathlib import Path

import pytest

from skills_tooling.evals import workspace
from skills_tooling.evals.adapter import Location, Trace, TrialPaths
from skills_tooling.evals.claude_code import BUILTIN_PLUGINS, BUILTIN_SKILLS, ClaudeCode
from skills_tooling.evals.contamination import NeverAppear, check, never_appear, preflight

ROOT = Path(__file__).parents[2]
ADAPTER = ClaudeCode(ROOT / "node_modules/.bin/claude")
BUILTINS = BUILTIN_SKILLS["2.1.309"]
MANAGED = "/Library/Application Support/ClaudeCode/.claude/skills"


def discovery(
    trial: TrialPaths, *, user: int = 0, project: int = 1, managed: int = 0
) -> tuple[str, ...]:
    return (
        (
            f"Loading skills from: managed={MANAGED}, user={trial.home}/.claude/skills, "
            f"project=[{trial.workspace}/.claude/skills]"
        ),
        (
            f"Loaded {user + project} unique skills ({user + project} unconditional, "
            f"0 conditional, managed: {managed}, user: {user}, project: {project}, "
            "additional: 0, legacy commands: 0)"
        ),
    )


def trace(trial: TrialPaths, *, skill: str | None = "cowsay", **overrides: object) -> Trace:
    visible = BUILTINS | ({skill} if skill else set())
    base = Trace(
        skills_triggered=[],
        skills_invoked=[],
        commands=[],
        final_message="",
        cli_version="2.1.309",
        model="claude-sonnet-5-5",
        exit_code=0,
        timed_out=False,
        stream_completed=True,
        status="ok",
        status_reason="",
        visible_skills=frozenset(visible),
        visible_plugins=BUILTIN_PLUGINS["2.1.309"],
        initial_commands=frozenset(visible | {"compact"}),
        dynamic_commands=[],
        debug_lines=discovery(trial, project=1 if skill else 0),
    )
    return replace(base, **overrides)  # type: ignore[arg-type]


NOTHING = NeverAppear(skills={}, instruction_files=())


def problems(
    trial: TrialPaths,
    observed: Trace,
    *,
    baseline: bool = False,
    forbidden: NeverAppear = NOTHING,
    system_root: Path = Path("/nonexistent-system-root"),
) -> list[str]:
    return check(
        ADAPTER,
        observed,
        skill="cowsay",
        baseline=baseline,
        trial=trial,
        never=forbidden,
        system_root=system_root,
    ).problems


@pytest.fixture
def trial(tmp_path: Path) -> TrialPaths:
    return workspace.create_trial(tmp_path, "run", "case")


def test_a_clean_trial_passes_in_both_arms(trial: TrialPaths) -> None:
    assert problems(trial, trace(trial)) == []
    assert problems(trial, trace(trial, skill=None), baseline=True) == []


def test_an_extra_reported_skill_fails(trial: TrialPaths) -> None:
    observed = trace(trial, visible_skills=frozenset(BUILTINS | {"cowsay", "user-canary"}))
    assert any("user-canary" in p for p in problems(trial, observed))


def test_the_skill_under_test_must_be_visible_only_in_the_with_skill_arm(
    trial: TrialPaths,
) -> None:
    missing = trace(trial, visible_skills=frozenset(BUILTINS))
    assert any("not visible" in p for p in problems(trial, missing))
    assert any("baseline" in p for p in problems(trial, trace(trial), baseline=True))


def test_an_unrecorded_cli_version_fails_with_a_rerecord_hint(trial: TrialPaths) -> None:
    found = problems(trial, trace(trial, cli_version="9.9.9"))
    assert any("re-record" in p and "9.9.9" in p for p in found)


def test_an_unexpected_plugin_fails(trial: TrialPaths) -> None:
    plugins = BUILTIN_PLUGINS["2.1.309"] | {"leaked@user-marketplace"}
    assert any(
        "leaked@user-marketplace" in p
        for p in problems(trial, trace(trial, visible_plugins=plugins))
    )


def test_a_skill_discovered_mid_run_fails(trial: TrialPaths) -> None:
    observed = trace(trial, dynamic_commands=["compact", "cowsay", "nested-canary"])
    assert any("nested-canary" in p for p in problems(trial, observed))
    rescanned = trace(trial, dynamic_commands=["compact", "cowsay"])
    assert problems(trial, rescanned) == []


def test_calling_an_unlisted_skill_fails(trial: TrialPaths) -> None:
    observed = trace(trial, skills_triggered=["secret-skill"], skills_invoked=["secret-skill"])
    assert any("secret-skill" in p for p in problems(trial, observed))


def test_a_failed_call_to_a_missing_skill_is_not_contamination(trial: TrialPaths) -> None:
    assert problems(trial, trace(trial, skills_invoked=["ascii-art"])) == []


def test_an_empty_project_list_is_not_a_location(trial: TrialPaths) -> None:
    lines = (
        f"Loading skills from: managed={MANAGED}, user={trial.home}/.claude/skills, project=[]",
        discovery(trial, project=0)[1],
    )
    observed = trace(trial, skill=None, debug_lines=lines)
    assert problems(trial, observed, baseline=True) == []


def test_never_appear_names_do_not_match_the_trials_own_paths(tmp_path: Path) -> None:
    trial = workspace.create_trial(tmp_path / "ticket", "run", "trigger-talking-cow")
    forbidden = NeverAppear(
        skills={"trigger": "user skill", "ticket": "user skill"}, instruction_files=()
    )
    assert problems(trial, trace(trial), forbidden=forbidden) == []


def test_discovery_paths_outside_the_trial_fail(trial: TrialPaths) -> None:
    lines = (
        (
            f"Loading skills from: managed={MANAGED}, user=/Users/someone/.claude/skills, "
            f"project=[{trial.workspace}/.claude/skills, /repo/.claude/skills]"
        ),
        discovery(trial)[1],
    )
    found = problems(trial, trace(trial, debug_lines=lines))
    assert any("/Users/someone/.claude/skills" in p for p in found)
    assert any("/repo/.claude/skills" in p for p in found)


def test_skills_counted_outside_the_project_fail(trial: TrialPaths) -> None:
    found = problems(trial, trace(trial, debug_lines=discovery(trial, user=1)))
    assert any("user: 1" in p for p in found)
    found = problems(trial, trace(trial, debug_lines=discovery(trial, project=2)))
    assert any("project: 2" in p for p in found)


def test_a_missing_discovery_report_fails_closed(trial: TrialPaths) -> None:
    assert any("discovery report" in p for p in problems(trial, trace(trial, debug_lines=())))
    assert any("did not report" in p for p in problems(trial, trace(trial, visible_skills=None)))


def test_a_populated_managed_location_fails(trial: TrialPaths, tmp_path: Path) -> None:
    system = tmp_path / "system"
    (system / MANAGED.lstrip("/") / "managed-canary").mkdir(parents=True)
    assert any("managed" in p for p in problems(trial, trace(trial), system_root=system))


def test_never_appear_names_fail_and_builtin_collisions_are_noted(trial: TrialPaths) -> None:
    forbidden = NeverAppear(
        skills={"cross-model-review": "dev skill", "debug": "user skill ~/.claude/skills"},
        instruction_files=(),
    )
    observed = trace(trial, visible_skills=frozenset(BUILTINS | {"cowsay", "cross-model-review"}))
    result = check(
        ADAPTER,
        observed,
        skill="cowsay",
        baseline=False,
        trial=trial,
        never=forbidden,
        system_root=Path("/nonexistent"),
    )
    assert any("never-appear" in p and "cross-model-review" in p for p in result.problems)
    assert any("debug" in note and "built-in" in note for note in result.notes)
    assert not any("'debug'" in p for p in result.problems)


def test_never_appear_lists_dev_skills_other_skills_user_skills_and_instructions(
    tmp_path: Path,
) -> None:
    repo, home = tmp_path / "repo", tmp_path / "home"
    for path in (
        repo / "dev-skills/cross-model-review",
        repo / "skills/cowsay",
        repo / "skills/other-skill",
        home / ".claude/skills/my-claude-skill",
        home / ".agents/skills/my-agents-skill",
        home / ".codex/skills/my-codex-skill",
        home / ".codex/skills/.system",
        home / ".pi/agent/skills/my-pi-skill",
    ):
        path.mkdir(parents=True)
    (repo / "AGENTS.md").write_text("x\n")
    (repo / "CLAUDE.md").write_text("@AGENTS.md\n")
    (home / ".claude/CLAUDE.md").write_text("global instructions\n")
    found = never_appear(repo, "cowsay", user_home=home, agent_homes=())
    assert set(found.skills) == {
        "cross-model-review",
        "other-skill",
        "my-claude-skill",
        "my-agents-skill",
        "my-codex-skill",
        "my-pi-skill",
    }
    assert found.skills["cross-model-review"] == "dev skill"
    assert found.instruction_files == (
        str(repo / "AGENTS.md"),
        str(repo / "CLAUDE.md"),
        str(home / ".claude/CLAUDE.md"),
    )


def test_preflight_passes_for_a_prepared_trial(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    workspace.git("init", "--quiet", cwd=repo)
    (repo / ".gitignore").write_text(".eval-workspaces/\n")
    trial = workspace.create_trial(repo / ".eval-workspaces", "run", "case")
    homes = ADAPTER.prepare_homes(trial)
    ADAPTER.install_skill(ROOT / "skills/cowsay", trial.workspace)
    assert preflight(ADAPTER, trial, homes, repo, "cowsay") == []
    env = {k: v for k, v in homes.env.items() if k != "CLAUDE_CODE_DISABLE_CLAUDE_MDS"}
    assert any(
        "CLAUDE_CODE_DISABLE_CLAUDE_MDS" in p
        for p in preflight(ADAPTER, trial, replace(homes, env=env), repo, "cowsay")
    )
    outside = replace(homes, env={**homes.env, "CLAUDE_CONFIG_DIR": str(tmp_path / "shared")})
    assert any(
        "CLAUDE_CONFIG_DIR" in p for p in preflight(ADAPTER, trial, outside, repo, "cowsay")
    )
    (trial.workspace / "expected.txt").write_text("answer\n")
    assert any("expected.txt" in p for p in preflight(ADAPTER, trial, homes, repo, "cowsay"))


def test_preflight_fails_closed_on_an_unmitigated_location(tmp_path: Path) -> None:
    class Unmitigated(ClaudeCode):
        def discovery_locations(self, trial: TrialPaths) -> list[Location]:
            return [*super().discovery_locations(trial), Location("mystery", "/opt/x", (), "")]

    repo = tmp_path / "repo"
    repo.mkdir()
    workspace.git("init", "--quiet", cwd=repo)
    (repo / ".gitignore").write_text(".eval-workspaces/\n")
    trial = workspace.create_trial(repo / ".eval-workspaces", "run", "case")
    adapter = Unmitigated(ROOT / "node_modules/.bin/claude")
    homes = adapter.prepare_homes(trial)
    adapter.install_skill(ROOT / "skills/cowsay", trial.workspace)
    found = preflight(adapter, trial, homes, repo, "cowsay")
    assert any("mystery" in p and "no mitigation" in p for p in found)
