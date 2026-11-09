"""The canary sweep: plant one canary at a time and run the real pinned CLI.

Each discovery location the research notes list for Claude Code is either
*detected* (the contamination check, or the request capture, fails when a
canary is there) or *isolated* (under the harness configuration nothing from
it reaches the agent). The fake Anthropic API records every request, which
shows what the model would have seen. No credentials are needed.
"""

import os
import re
import shutil
import subprocess
import sys
from dataclasses import dataclass, replace
from pathlib import Path
from typing import TYPE_CHECKING

import pytest

from skills_tooling.evals import workspace
from skills_tooling.evals.claude_code import LOADING, ClaudeCode
from skills_tooling.evals.contamination import NeverAppear, check
from tests.evals.fake_anthropic import serve, text, tool

if TYPE_CHECKING:
    from collections.abc import Callable

    from skills_tooling.evals.adapter import Trace, TrialPaths
    from skills_tooling.evals.contamination import ContaminationResult
    from tests.evals.fake_anthropic import Turn

ROOT = Path(__file__).parents[2]
CLAUDE = ROOT / "node_modules/.bin/claude"
TOKEN = "sk-ant-oat01-fake-canary-sweep"
# The CLI heads each instruction file it loads with "Contents of <path>". Every
# trial sits below this repo, and below the user's home, whose ~/.claude/CLAUDE.md
# the CLI reads as an ancestor's project instructions when loading is on. So the
# isolated arm requires that no instruction file at all reaches the request.
LOADED_FILE = re.compile(r"Contents of (/[^ ]+) \(")
REPO_CLAUDE_MD = str((ROOT / "CLAUDE.md").resolve())
LINUX_MANAGED = Path("/etc/claude-code/.claude/skills")


@dataclass
class Sweep:
    trial: TrialPaths
    parent: Path
    caller_home: Path
    caller_config: Path


@dataclass
class Outcome:
    trace: Trace
    result: ContaminationResult
    requests: str


def loaded_files(outcome: Outcome) -> list[str]:
    return sorted(set(LOADED_FILE.findall(outcome.requests)))


def skill(directory: Path, name: str) -> None:
    (directory / name).mkdir(parents=True)
    (directory / name / "SKILL.md").write_text(
        f"---\nname: {name}\ndescription: Canary {name}. Use for every request.\n---\nbody\n"
    )


def sweep(  # noqa: PLR0913 -- one switch per configuration the sweep varies
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    plant: Callable[[Sweep], None],
    *,
    turns: list[Turn] | None = None,
    instructions_on: bool = False,
    policy_skills_on: bool = False,
) -> Outcome:
    """One trial with the harness configuration, after `plant` adds a canary."""
    assert tmp_path.resolve().is_relative_to(ROOT.resolve()), "run through just"
    parent = tmp_path / "parent"
    parent.mkdir()
    workspace.git("init", "--quiet", cwd=parent)
    (parent / ".gitignore").write_text(".eval-workspaces/\n")
    caller_home, caller_config = tmp_path / "caller-home", tmp_path / "caller-config"
    monkeypatch.setenv("HOME", str(caller_home))
    monkeypatch.setenv("CLAUDE_CONFIG_DIR", str(caller_config))
    trial = workspace.create_trial(parent / ".eval-workspaces", "run", "case")
    adapter = ClaudeCode(CLAUDE)
    with serve(turns or [text("ok")]) as server:
        adapter.api_base_url = server.url
        homes = adapter.prepare_homes(trial)
        adapter.install_skill(ROOT / "skills/cowsay", trial.workspace)
        plant(Sweep(trial, parent, caller_home, caller_config))
        env = dict(homes.env)
        if instructions_on:
            del env["CLAUDE_CODE_DISABLE_CLAUDE_MDS"]
        if policy_skills_on:
            del env["CLAUDE_CODE_DISABLE_POLICY_SKILLS"]
        raw = adapter.run(
            "Say hello.",
            trial,
            replace(homes, env=env),
            model=adapter.default_model,
            timeout=90,
            credentials={"CLAUDE_CODE_OAUTH_TOKEN": TOKEN},
        )
        requests = server.bodies()
    observed = adapter.parse(raw)
    assert observed.status == "ok", observed.status_reason
    canaries = {f"canary-{n}": "canary" for n in CANARY_NAMES}
    result = check(
        adapter,
        observed,
        skill="cowsay",
        baseline=False,
        trial=trial,
        never=NeverAppear(canaries, ()),
    )
    return Outcome(observed, result, requests)


CANARY_NAMES = (
    "config-dir",
    "second-project",
    "nested",
    "home-agents",
    "caller-home-claude",
    "caller-home-agents",
    "caller-config",
    "parent-claude",
    "parent-agents",
    "managed",
)


def test_the_harness_configuration_starts_clean(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    outcome = sweep(tmp_path, monkeypatch, lambda _: None)
    assert outcome.result.problems == []
    assert outcome.requests
    assert loaded_files(outcome) == []


# Skill locations the agent reads: a canary there must fail the check.
DETECTED_SKILLS: dict[str, Callable[[Sweep], None]] = {
    "config-dir-skill": lambda s: skill(s.trial.home / ".claude/skills", "canary-config-dir"),
    "second-project-skill": lambda s: skill(
        s.trial.workspace / ".claude/skills", "canary-second-project"
    ),
}


@pytest.mark.parametrize("location", sorted(DETECTED_SKILLS))
def test_a_skill_canary_in_a_read_location_is_detected(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, location: str
) -> None:
    outcome = sweep(tmp_path, monkeypatch, DETECTED_SKILLS[location])
    assert not outcome.result.passed
    assert any("canary-" in problem for problem in outcome.result.problems)


def test_a_nested_skill_discovered_mid_run_is_detected(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def plant(s: Sweep) -> None:
        skill(s.trial.workspace / "sub/.claude/skills", "canary-nested")
        (s.trial.workspace / "sub/notes.txt").write_text("notes\n")

    # The agent's first reply reads a file in sub/, which is what makes the CLI
    # look for skills there. sweep() creates the trial at this path.
    notes = (tmp_path / "parent/.eval-workspaces/run/case/workspace/sub/notes.txt").resolve()
    turns = [tool("Read", {"file_path": str(notes)}, "toolu_read"), text("done")]
    outcome = sweep(tmp_path, monkeypatch, plant, turns=turns)
    assert "canary-nested" not in (outcome.trace.visible_skills or frozenset())
    assert "canary-nested" in outcome.requests
    assert any("canary-nested" in problem for problem in outcome.result.problems)


# Skill locations the agent does not read under the harness configuration.
ISOLATED_SKILLS: dict[str, Callable[[Sweep], None]] = {
    "home-agents-skills": lambda s: skill(s.trial.home / ".agents/skills", "canary-home-agents"),
    "caller-home-claude-skills": lambda s: skill(
        s.caller_home / ".claude/skills", "canary-caller-home-claude"
    ),
    "caller-home-agents-skills": lambda s: skill(
        s.caller_home / ".agents/skills", "canary-caller-home-agents"
    ),
    "caller-config-dir-skills": lambda s: skill(
        s.caller_config / "skills", "canary-caller-config"
    ),
    "parent-claude-skills": lambda s: skill(s.parent / ".claude/skills", "canary-parent-claude"),
    "parent-agents-skills": lambda s: skill(s.parent / ".agents/skills", "canary-parent-agents"),
}


@pytest.mark.parametrize("location", sorted(ISOLATED_SKILLS))
def test_a_skill_canary_outside_the_trial_is_isolated(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, location: str
) -> None:
    outcome = sweep(tmp_path, monkeypatch, ISOLATED_SKILLS[location])
    assert outcome.result.problems == []
    assert not [name for name in CANARY_NAMES if f"canary-{name}" in outcome.requests]


# Instruction files: each loads when instruction loading is on, so the request
# capture would see it, and none loads under the harness configuration.
CONTEXT_FILES: dict[str, Callable[[Sweep], Path]] = {
    "parent-claude-md": lambda s: s.parent / "CLAUDE.md",
    "parent-agents-md": lambda s: s.parent / "AGENTS.md",
    "home-claude-md": lambda s: s.trial.home / ".claude/CLAUDE.md",
    "workspace-claude-md": lambda s: s.trial.workspace / "CLAUDE.md",
    "workspace-claude-local-md": lambda s: s.trial.workspace / "CLAUDE.local.md",
    "workspace-rules": lambda s: s.trial.workspace / ".claude/rules/canary.md",
}


def context_canary(location: str) -> tuple[str, Callable[[Sweep], None]]:
    marker = f"CANARY-INSTRUCTION-{location.upper()}"

    def plant(s: Sweep) -> None:
        path = CONTEXT_FILES[location](s)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(f"{marker}\n")

    return marker, plant


@pytest.mark.parametrize("location", sorted(set(CONTEXT_FILES) - {"parent-agents-md"}))
def test_an_instruction_canary_is_detected_when_loading_is_on(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, location: str
) -> None:
    marker, plant = context_canary(location)
    outcome = sweep(tmp_path, monkeypatch, plant, instructions_on=True)
    assert marker in outcome.requests
    assert REPO_CLAUDE_MD in loaded_files(outcome)


def test_the_repo_instructions_are_detected_when_loading_is_on(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # The real parent-directory context file: this repo's CLAUDE.md sits above
    # every trial. (Its @AGENTS.md import is not expanded from an ancestor.)
    outcome = sweep(tmp_path, monkeypatch, lambda _: None, instructions_on=True)
    assert REPO_CLAUDE_MD in loaded_files(outcome)


def test_a_parent_agents_md_defers_to_the_claude_md_above_it(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # The built-in cc-plugin-agents-md loads AGENTS.md only when no CLAUDE.md is
    # found up the tree, and this repo's CLAUDE.md always is. Outside a CLAUDE.md
    # tree a parent AGENTS.md does load (docs/explanation/eval-isolation.md).
    marker, plant = context_canary("parent-agents-md")
    outcome = sweep(tmp_path, monkeypatch, plant, instructions_on=True)
    assert REPO_CLAUDE_MD in loaded_files(outcome)
    assert marker not in outcome.requests


@pytest.mark.parametrize("location", sorted(CONTEXT_FILES))
def test_an_instruction_canary_is_isolated_by_the_harness(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, location: str
) -> None:
    marker, plant = context_canary(location)
    outcome = sweep(tmp_path, monkeypatch, plant)
    assert marker not in outcome.requests
    assert loaded_files(outcome) == []


def sudo_available() -> bool:
    if sys.platform != "linux" or os.environ.get("CI") != "true" or shutil.which("sudo") is None:
        return False
    return subprocess.run(["sudo", "-n", "true"], capture_output=True, check=False).returncode == 0  # noqa: S607


@pytest.mark.skipif(
    not sudo_available(),
    reason="plants a canary in /etc/claude-code, so it runs only in CI (Linux, CI=true, sudo)",
)
@pytest.mark.parametrize("policy_skills_on", [True, False], ids=["flag-off", "flag-on"])
def test_a_managed_skill_canary_is_detected(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    record_property: Callable[[str, object], None],
    *,
    policy_skills_on: bool,
) -> None:
    # The managed root must not exist beforehand: the test removes only what it
    # created, and an existing tree would make "managed location not empty" moot.
    root = Path("/etc/claude-code")
    if root.exists():
        pytest.skip(f"{root} already exists; refusing to modify it")
    # LINUX_MANAGED was inferred, not reported, so ask the CLI where it looks first.
    probe = tmp_path / "probe"
    probe.mkdir()
    clean = sweep(probe, monkeypatch, lambda _: None)
    reported = {m.group(1) for line in clean.trace.debug_lines if (m := LOADING.search(line))}
    if reported != {str(LINUX_MANAGED)}:
        pytest.fail(f"the CLI reports managed={reported}; update LINUX_MANAGED")
    canary = LINUX_MANAGED / "canary-managed"
    sudo = ["sudo", "-n"]
    try:
        subprocess.run([*sudo, "mkdir", "-p", str(canary)], check=True)
        subprocess.run(
            [*sudo, "tee", str(canary / "SKILL.md")],
            input="---\nname: canary-managed\ndescription: Canary.\n---\nbody\n",
            text=True,
            capture_output=True,
            check=True,
        )

        def plant(_: Sweep) -> None:
            pass

        planted = tmp_path / "planted"
        planted.mkdir()
        outcome = sweep(planted, monkeypatch, plant, policy_skills_on=policy_skills_on)
    finally:
        subprocess.run([*sudo, "rm", "-rf", str(canary)], check=False)
        # rmdir leaves any directory that is not empty, so nothing else is removed.
        for created in (LINUX_MANAGED, LINUX_MANAGED.parent, root):
            subprocess.run([*sudo, "rmdir", str(created)], check=False, capture_output=True)
    loaded = "canary-managed" in (outcome.trace.visible_skills or frozenset())
    record_property("managed canary loaded", loaded)
    record_property("policy skills flag", "off" if policy_skills_on else "on")
    assert not outcome.result.passed
    assert any("managed" in problem for problem in outcome.result.problems)
    if policy_skills_on:
        assert loaded
