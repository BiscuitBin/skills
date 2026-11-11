"""Drive the pinned Claude Code CLI through the adapter against the fake API."""

import json
import shlex
import shutil
import subprocess
from pathlib import Path

from skills_tooling.evals import workspace
from skills_tooling.evals.claude_code import ClaudeCode
from tests.evals.fake_anthropic import serve, text, tool

ROOT = Path(__file__).parents[2]
CLAUDE = ROOT / "node_modules/.bin/claude"
TOKEN = "sk-ant-oat01-fake-adapter-test"


def fake_repo(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    repo.mkdir()
    subprocess.run(["git", "init", "--quiet"], cwd=repo, check=True)  # noqa: S607
    (repo / ".gitignore").write_text(".eval-workspaces/\n")
    return repo


def test_trial_records_trigger_command_and_final_message(tmp_path: Path) -> None:
    repo = fake_repo(tmp_path)
    trial = workspace.create_trial(repo / ".eval-workspaces", "run-1", "case-1")
    command = "python3 .claude/skills/cowsay/scripts/cowsay.py -- 'Ship it'"
    turns = [
        tool("Skill", {"skill": "cowsay"}, "toolu_1"),
        tool("Bash", {"command": command, "description": "Run cowsay"}, "toolu_2"),
        text("Here is your cow."),
    ]
    with serve(turns) as server:
        adapter = ClaudeCode(executable=CLAUDE, api_base_url=server.url)
        homes = adapter.prepare_homes(trial)
        adapter.install_skill(ROOT / "skills/cowsay", trial.workspace)
        raw = adapter.run(
            "Have a cow say: Ship it",
            trial,
            homes,
            model=adapter.default_model,
            timeout=90,
            credentials={"CLAUDE_CODE_OAUTH_TOKEN": TOKEN},
        )
    trace = adapter.parse(raw)
    assert (trace.status, trace.status_reason) == ("ok", "")
    assert trace.skills_triggered == ["cowsay"]
    assert [(c.command, c.ok) for c in trace.commands] == [(command, True)]
    assert "< Ship it >" in trace.commands[0].output
    assert trace.final_message == "Here is your cow."
    assert trace.cli_version == "2.1.309"
    assert trace.model == "claude-sonnet-5-5"
    assert server.requests[0].headers["Authorization"] == f"Bearer {TOKEN}"


def test_a_by_name_prompt_runs_the_skill_as_a_slash_command(tmp_path: Path) -> None:
    repo = fake_repo(tmp_path)
    trial = workspace.create_trial(repo / ".eval-workspaces", "run-1", "case-1")
    with serve([text("Here is your cow.")]) as server:
        adapter = ClaudeCode(executable=CLAUDE, api_base_url=server.url)
        homes = adapter.prepare_homes(trial)
        installed = adapter.install_skill(ROOT / "skills/cowsay", trial.workspace)
        assert installed is not None
        prompt = adapter.by_name_prompt(installed, "Have a cow say: Ship it")
        assert prompt == "/cowsay Have a cow say: Ship it"
        raw = adapter.run(
            prompt,
            trial,
            homes,
            model=adapter.default_model,
            timeout=90,
            credentials={"CLAUDE_CODE_OAUTH_TOKEN": TOKEN},
        )
    trace = adapter.parse(raw)
    assert (trace.status, trace.status_reason) == ("ok", "")
    # The CLI expanded the command: the skill's text is in the first request.
    first = server.requests[0].body
    assert "<command-name>/cowsay</command-name>" in first
    assert f"Base directory for this skill: {installed.resolve()}" in first
    assert "ARGUMENTS: Have a cow say: Ship it" in first
    # The stream shows none of it. The session file's record is the trigger.
    assert raw.session_lines[1:] == (f"skill_expanded {installed.resolve()}",)
    assert (trace.skills_triggered, trace.skills_invoked) == (["cowsay"], ["cowsay"])


def test_session_persistence_changes_no_request(tmp_path: Path) -> None:
    # The same by-name trial run twice in one directory: as the adapter runs
    # it, and through a wrapper that turns session persistence off.
    wrapper = tmp_path / "claude-without-sessions"
    wrapper.write_text(
        f'#!/bin/sh\nexec {shlex.quote(str(CLAUDE))} "$@" --no-session-persistence\n'
    )
    wrapper.chmod(0o755)
    repo = fake_repo(tmp_path)
    requests, traces = {}, {}
    for label, executable in (("off", wrapper), ("on", CLAUDE)):
        trial = workspace.create_trial(repo / ".eval-workspaces", "run-1", "case-1")
        skill_md = trial.workspace / ".claude/skills/cowsay/SKILL.md"
        turns = [tool("Read", {"file_path": str(skill_md)}, "toolu_1"), text("Here is your cow.")]
        with serve(turns) as server:
            adapter = ClaudeCode(executable=executable, api_base_url=server.url)
            homes = adapter.prepare_homes(trial)
            installed = adapter.install_skill(ROOT / "skills/cowsay", trial.workspace)
            assert installed is not None
            raw = adapter.run(
                adapter.by_name_prompt(installed, "Have a cow say: Ship it"),
                trial,
                homes,
                model=adapter.default_model,
                timeout=90,
                credentials={"CLAUDE_CODE_OAUTH_TOKEN": TOKEN},
            )
        traces[label] = adapter.parse(raw)
        requests[label] = [json.loads(request.body) for request in server.requests]
        shutil.rmtree(trial.root)
    # Off, the CLI writes no session file, so the trace fails closed.
    assert (traces["off"].status, traces["off"].status_reason) == (
        "infra_error",
        "no session record; failing closed",
    )
    assert (traces["on"].status, traces["on"].skills_triggered) == ("ok", ["cowsay"])
    # metadata.user_id holds the per-home device id and the session id.
    for bodies in requests.values():
        for body in bodies:
            assert set(body["metadata"]) == {"user_id"}
            del body["metadata"]
    assert len(requests["on"]) == 2
    assert requests["on"] == requests["off"]
