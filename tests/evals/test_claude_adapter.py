"""Drive the pinned Claude Code CLI through the adapter against the fake API."""

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
