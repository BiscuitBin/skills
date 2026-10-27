"""A fake secret reaches the agent, and never the results, transcripts or workspace."""

from typing import TYPE_CHECKING

import pytest

from skills_tooling.evals.results import SecretLeakError, scrub, verify_clean
from skills_tooling.evals.runner import run_suite
from tests.evals.fake_anthropic import serve, text, tool
from tests.evals.test_runner import CASES, TRIGGER, fake_root, settings

if TYPE_CHECKING:
    from pathlib import Path

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
    assert {p.name for p in written} == {"results.json", "trigger-moo.jsonl"}
    for path in written:
        assert SECRET not in path.read_text(), path
    assert (
        "[REDACTED]" in (root / "eval-results/test-run/transcripts/trigger-moo.jsonl").read_text()
    )
    trial = root / ".eval-workspaces/test-run/trigger-moo"
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
