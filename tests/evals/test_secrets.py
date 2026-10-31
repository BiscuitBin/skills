"""A fake secret reaches the agent, and never the results, transcripts or workspace."""

import json
from dataclasses import replace
from pathlib import Path
from typing import TYPE_CHECKING

import pytest

from skills_tooling.evals import workspace
from skills_tooling.evals.claude_code import ClaudeCode
from skills_tooling.evals.results import SecretLeakError, scrub, verify_clean
from skills_tooling.evals.runner import run_suite
from tests.evals.fake_anthropic import serve, text, tool
from tests.evals.test_runner import CASES, GOOD, TRIGGER, fake_root, settings

if TYPE_CHECKING:
    from collections.abc import Mapping

    from skills_tooling.evals.adapter import Homes, RawRun, Trace, TrialPaths

ROOT = Path(__file__).parents[2]
SECRET = "sk-ant-oat01-FAKE-0123456789abcdef-secret"


def test_a_fake_token_reaches_the_api_but_not_the_results(tmp_path: Path) -> None:
    root = fake_root(tmp_path, [CASES[0]])
    # The fake API echoes the token back, so it lands in the agent's stream and
    # final message: the run must scrub it everywhere it writes.
    script = {
        TRIGGER: [
            tool("Skill", {"skill": "cowsay"}, "toolu_1"),
            text(f"Your token is {SECRET}."),
        ]
    }
    with serve(script) as server:
        exit_code = run_suite(
            settings(root, server.url, credentials={"CLAUDE_CODE_OAUTH_TOKEN": SECRET})
        )
    assert exit_code == 0
    assert server.requests[0].headers["Authorization"] == f"Bearer {SECRET}"
    written = [p for p in (root / "eval-results").rglob("*") if p.is_file()]
    assert {p.relative_to(root / "eval-results/test-run").as_posix() for p in written} == {
        "benchmark.json",
        "results.json",
        "transcripts/trigger-moo/skill-1.jsonl",
    }
    for path in written:
        assert SECRET not in path.read_text(), path
    assert (
        "[REDACTED]"
        in (root / "eval-results/test-run/transcripts/trigger-moo/skill-1.jsonl").read_text()
    )
    trial = root / ".eval-workspaces/test-run/trigger-moo/skill-1"
    assert [p.name for p in trial.iterdir()] == ["workspace"]
    for path in trial.rglob("*"):
        if path.is_file():
            assert SECRET.encode() not in path.read_bytes(), path


def test_scrub_replaces_every_secret() -> None:
    assert scrub(f"a {SECRET} b {SECRET}", [SECRET, ""]) == "a [REDACTED] b [REDACTED]"


def test_a_file_that_still_holds_a_secret_is_deleted_and_rejected(tmp_path: Path) -> None:
    clean, leaked = tmp_path / "clean.json", tmp_path / "leaked.json"
    clean.write_text("{}")
    leaked.write_text(f'{{"token": "{SECRET}"}}')
    with pytest.raises(SecretLeakError, match=r"leaked\.json"):
        verify_clean(tmp_path, [SECRET])
    assert clean.exists()
    assert not leaked.exists()


def test_the_agents_bash_commands_never_see_the_token(tmp_path: Path) -> None:
    # The harness hands the token only to the CLI; the CLI must not pass it on
    # to the processes its Bash tool starts. Checked on the unscrubbed trace.
    trial = workspace.create_trial(tmp_path, "run", "case")
    env_dump = tool("Bash", {"command": "env", "description": "Show env"}, "toolu_1")
    with serve([env_dump, text("done")]) as server:
        adapter = ClaudeCode(ROOT / "node_modules/.bin/claude", api_base_url=server.url)
        homes = adapter.prepare_homes(trial)
        raw = adapter.run(
            "Show the environment.",
            trial,
            homes,
            model=adapter.default_model,
            timeout=90,
            credentials={"CLAUDE_CODE_OAUTH_TOKEN": SECRET},
        )
    [command] = adapter.parse(raw).commands
    assert command.ok
    assert f"HOME={trial.home}" in command.output
    assert SECRET not in command.output
    assert "CLAUDE_CODE_OAUTH_TOKEN" not in command.output


def test_a_secret_left_outside_the_workspace_deletes_the_trial_and_fails_it(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    class Spills(ClaudeCode):
        def run(  # noqa: PLR0913 -- the Adapter signature
            self,
            prompt: str,
            trial: TrialPaths,
            homes: Homes,
            *,
            model: str,
            timeout: float,
            credentials: Mapping[str, str],
        ) -> RawRun:
            # Beside the workspace, where removing only the workspace would miss it.
            (trial.root / "token.txt").write_text(credentials["CLAUDE_CODE_OAUTH_TOKEN"])
            return super().run(
                prompt, trial, homes, model=model, timeout=timeout, credentials=credentials
            )

    root = fake_root(tmp_path, [CASES[0]])
    with serve(GOOD) as server:
        adapter = Spills(ROOT / "node_modules/.bin/claude", api_base_url=server.url)
        exit_code = run_suite(
            settings(
                root, server.url, adapter=adapter, credentials={"CLAUDE_CODE_OAUTH_TOKEN": SECRET}
            )
        )
    assert exit_code == 1
    [trial] = json.loads((root / "eval-results/test-run/results.json").read_text())["trials"]
    assert trial["passed"] is False
    assert trial["secret_found"] == {"files": ["token.txt"], "deleted": True}
    assert not (root / ".eval-workspaces/test-run/trigger-moo/skill-1").exists()
    assert "secret found in the trial directory" in capsys.readouterr().out


def test_failure_diagnostics_on_stdout_are_scrubbed(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    class EchoesTheToken(ClaudeCode):
        def parse(self, raw: RawRun) -> Trace:
            trace = super().parse(raw)
            return replace(
                trace, status="infra_error", status_reason=f"agent reported an error: {SECRET}"
            )

    root = fake_root(tmp_path, [CASES[0]])
    with serve(GOOD) as server:
        adapter = EchoesTheToken(ROOT / "node_modules/.bin/claude", api_base_url=server.url)
        exit_code = run_suite(
            settings(
                root, server.url, adapter=adapter, credentials={"CLAUDE_CODE_OAUTH_TOKEN": SECRET}
            )
        )
    assert exit_code == 1
    out = capsys.readouterr().out
    assert SECRET not in out
    assert "agent reported an error: [REDACTED]" in out
