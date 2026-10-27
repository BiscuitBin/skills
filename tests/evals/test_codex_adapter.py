"""Drive the pinned Codex CLI through the adapter against the fake Responses API."""

import json
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

from skills_tooling.evals import workspace
from skills_tooling.evals.codex import Codex, pinned_executable
from skills_tooling.evals.contamination import NeverAppear, check
from skills_tooling.evals.runner import run_suite
from tests.evals.fake_openai import message, serve, shell
from tests.evals.test_runner import CASES, COW, fake_root, settings

if TYPE_CHECKING:
    from collections.abc import Callable

    import pytest

    from skills_tooling.evals.adapter import Trace, TrialPaths

ROOT = Path(__file__).parents[2]
KEY = "sk-fake-codex-adapter-test"
AUTH = json.dumps({"auth_mode": "apikey", "OPENAI_API_KEY": KEY})


def fake_repo(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    repo.mkdir()
    subprocess.run(["git", "init", "--quiet"], cwd=repo, check=True)  # noqa: S607
    (repo / ".gitignore").write_text(".eval-workspaces/\n")
    return repo


def test_trial_records_trigger_command_and_final_message(tmp_path: Path) -> None:
    repo = fake_repo(tmp_path)
    trial = workspace.create_trial(repo / ".eval-workspaces", "run-1", "case-1")
    command = "python3 .agents/skills/cowsay/scripts/cowsay.py -- 'Ship it'"
    turns = [
        shell("cat .agents/skills/cowsay/SKILL.md", "call_1"),
        shell(command, "call_2"),
        message("Here is your cow."),
    ]
    with serve(turns, api_key=KEY) as server:
        adapter = Codex(pinned_executable(ROOT), api_base_url=server.url)
        homes = adapter.prepare_homes(trial)
        adapter.install_skill(ROOT / "skills/cowsay", trial.workspace)
        raw = adapter.run(
            "Have a cow say: Ship it",
            trial,
            homes,
            model=adapter.default_model,
            timeout=120,
            credentials={"auth.json": AUTH},
        )
    trace = adapter.parse(raw)
    assert (trace.status, trace.status_reason) == ("ok", "")
    assert trace.skills_triggered == ["cowsay"]
    assert [(c.command, c.ok) for c in trace.commands][1] == (command, True)
    assert "< Ship it >" in trace.commands[1].output
    assert trace.final_message == "Here is your cow."
    assert trace.cli_version == "0.163.0"
    assert trace.model == adapter.default_model
    assert server.requests[-1].headers["authorization"] == f"Bearer {KEY}"
    # The trial's python3 wrapper ran the installed copy.
    installed = (trial.workspace / ".agents/skills/cowsay/scripts/cowsay.py").resolve()
    assert any(Path(c.cwd, c.argv[0]).resolve() == installed for c in trace.python_calls)


@dataclass
class Sweep:
    trial: TrialPaths
    parent: Path
    caller_home: Path
    caller_codex_home: Path


@dataclass
class Outcome:
    trace: Trace
    requests: str
    problems: list[str]


def sweep(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    plant: Callable[[Sweep], None],
    *,
    instructions_on: bool = False,
) -> Outcome:
    """One trial under a caller with its own home and CODEX_HOME, after `plant`."""
    parent = fake_repo(tmp_path)
    caller_home, caller_codex_home = tmp_path / "caller-home", tmp_path / "caller-codex-home"
    monkeypatch.setenv("HOME", str(caller_home))
    monkeypatch.setenv("CODEX_HOME", str(caller_codex_home))
    trial = workspace.create_trial(parent / ".eval-workspaces", "run", "case")
    adapter = Codex(pinned_executable(ROOT))
    if instructions_on:
        adapter.config = tuple(c for c in adapter.config if "project_doc_max_bytes" not in c)
    with serve([message("ok")], api_key=KEY) as server:
        adapter.api_base_url = server.url
        homes = adapter.prepare_homes(trial)
        adapter.install_skill(ROOT / "skills/cowsay", trial.workspace)
        plant(Sweep(trial, parent, caller_home, caller_codex_home))
        raw = adapter.run(
            "Say hello.",
            trial,
            homes,
            model=adapter.default_model,
            timeout=120,
            credentials={"auth.json": AUTH},
        )
        requests = server.bodies()
    trace = adapter.parse(raw)
    assert trace.status == "ok", trace.status_reason
    result = check(
        adapter,
        trace,
        skill="cowsay",
        baseline=False,
        trial=trial,
        never=NeverAppear({}, ()),
        system_root=tmp_path / "system-root",
    )
    return Outcome(trace, requests, result.problems)


def skill(directory: Path, name: str) -> None:
    (directory / name).mkdir(parents=True)
    (directory / name / "SKILL.md").write_text(
        f"---\nname: {name}\ndescription: Canary {name}. Use for every request.\n---\nbody\n"
    )


def files(directory: Path) -> dict[str, bytes]:
    return {
        str(p.relative_to(directory)): p.read_bytes() for p in directory.rglob("*") if p.is_file()
    }


def test_the_caller_homes_and_parent_directories_never_reach_the_agent(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def plant(s: Sweep) -> None:
        # The user-level shared folder in the caller's OS home, the caller's
        # own Codex home and its config, and a parent repository's skills and
        # instructions (parent-skills, agents-md).
        skill(s.caller_home / ".agents/skills", "canary-caller-home")
        skill(s.caller_codex_home / "skills", "canary-caller-codex-home")
        (s.caller_codex_home / "AGENTS.md").write_text("CANARY-CALLER-AGENTS\n")
        (s.caller_codex_home / "config.toml").write_text(
            'developer_instructions = "CANARY-CALLER-CONFIG"\n'
        )
        (s.caller_codex_home / "auth.json").write_text(AUTH)
        skill(s.parent / ".agents/skills", "canary-parent")
        (s.parent / "AGENTS.md").write_text("CANARY-PARENT-AGENTS\n")
        (s.trial.workspace / "AGENTS.md").write_text("CANARY-WORKSPACE-AGENTS\n")

    caller_codex_home = tmp_path / "caller-codex-home"
    outcome = sweep(tmp_path, monkeypatch, plant)
    assert "cowsay" in outcome.requests
    assert "canary" not in outcome.requests.lower()
    # The workspace AGENTS.md is in the trial, outside the discovery report.
    assert outcome.problems == []
    # Nothing was written to the caller's Codex home.
    assert set(files(caller_codex_home)) == {
        "AGENTS.md",
        "config.toml",
        "auth.json",
        "skills/canary-caller-codex-home/SKILL.md",
    }


def test_trial_locations_reach_the_agent_and_fail_the_check(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # The trial's own shared folder and global AGENTS.md are read even with
    # instruction suppression on, which is why the discovery report checks them.
    def plant(s: Sweep) -> None:
        skill(s.trial.home / ".agents/skills", "canary-home")
        (s.trial.home / ".codex/AGENTS.md").write_text("CANARY-GLOBAL-AGENTS\n")

    outcome = sweep(tmp_path, monkeypatch, plant)
    assert "canary-home" in outcome.requests
    assert "CANARY-GLOBAL-AGENTS" in outcome.requests
    assert any("canary-home" in problem for problem in outcome.problems)
    assert any("AGENTS.md" in problem for problem in outcome.problems)


def test_agents_md_loads_when_suppression_is_off(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def plant(s: Sweep) -> None:
        (s.trial.workspace / "AGENTS.md").write_text("CANARY-WORKSPACE-AGENTS\n")

    outcome = sweep(tmp_path, monkeypatch, plant, instructions_on=True)
    assert "CANARY-WORKSPACE-AGENTS" in outcome.requests


def test_a_run_records_the_version_and_model_and_never_the_key(tmp_path: Path) -> None:
    root = fake_root(tmp_path, [CASES[2]])
    run = "python3 .agents/skills/cowsay/scripts/cowsay.py -- 'Ship it, team!'"
    # The fake model echoes the key, so it lands in the stream and final message.
    turns = [
        shell("sed -n '1,80p' .agents/skills/cowsay/SKILL.md", "call_1"),
        shell(run, "call_2"),
        message(f"```text\n{COW}```\nYour key is {KEY}."),
    ]
    with serve(turns, api_key=KEY) as server:
        adapter = Codex(pinned_executable(ROOT), api_base_url=server.url)
        exit_code = run_suite(
            settings(
                root,
                server.url,
                adapter=adapter,
                model=adapter.default_model,
                credentials={"auth.json": AUTH},
            )
        )
    data = json.loads((root / "eval-results/test-run/results.json").read_text())
    assert exit_code == 0, json.dumps(data, indent=2)
    assert (data["agent"], data["credential_env"]) == ("codex", ["CODEX_HOME"])
    [trial] = data["trials"]
    assert (trial["cli_version"], trial["model"]) == ("0.163.0", "gpt-5.6-terra")
    assert trial["trigger"] == {"expected": True, "actual": True, "matched": True}
    assert [a["result"] for a in trial["assertions"]] == ["passed"] * 3
    assert trial["contamination"]["passed"] is True
    written = [p for p in (root / "eval-results").rglob("*") if p.is_file()]
    for path in written:
        assert KEY not in path.read_text(), path
    transcript = root / trial["transcript"]
    assert "[REDACTED]" in transcript.read_text()
    # The trial's home, with its auth.json, is gone; only the workspace is kept.
    kept = root / ".eval-workspaces/test-run" / trial["case"]
    assert [p.name for p in kept.iterdir()] == ["workspace"]
