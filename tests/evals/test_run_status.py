"""Run status: what makes a trial an infrastructure error rather than a result."""

from typing import TYPE_CHECKING

from skills_tooling.evals.claude_code import parse_stream
from tests.evals.test_claude_parser import FIXTURES, parse, raw_run

if TYPE_CHECKING:
    from pathlib import Path


def test_failed_authentication_is_an_infrastructure_error() -> None:
    # Recorded with no credentials: the result says "success" but is_error is true.
    trace = parse("auth-failure", exit_code=1)
    assert trace.status == "infra_error"
    assert "Not logged in" in trace.status_reason
    assert trace.skills_triggered == []


def test_auth_failure_is_an_error_even_with_exit_zero() -> None:
    trace = parse("auth-failure", exit_code=0)
    assert (trace.status, trace.stream_completed) == ("infra_error", True)


def test_nonzero_exit_is_an_infrastructure_error() -> None:
    trace = parse("fake-should-trigger", exit_code=2)
    assert (trace.status, trace.status_reason) == ("infra_error", "nonzero exit 2")


def test_truncated_stream_is_an_infrastructure_error(tmp_path: Path) -> None:
    lines = (FIXTURES / "fake-should-not-trigger.jsonl").read_text().splitlines()
    truncated = tmp_path / "truncated.jsonl"
    truncated.write_text("\n".join(lines[:-1]) + "\n")
    trace = parse_stream(raw_run(truncated))
    assert (trace.status, trace.stream_completed) == ("infra_error", False)
    assert "stream truncated" in trace.status_reason
    cut = tmp_path / "cut.jsonl"
    cut.write_text("\n".join(lines) + '\n{"type": "assist')
    assert parse_stream(raw_run(cut)).status == "infra_error"


def test_missing_or_empty_transcript_is_an_infrastructure_error(tmp_path: Path) -> None:
    assert parse_stream(raw_run(tmp_path / "missing.jsonl")).status == "infra_error"
    (tmp_path / "empty.jsonl").write_text("")
    assert parse_stream(raw_run(tmp_path / "empty.jsonl")).status == "infra_error"


def test_timeout_and_surviving_processes_are_infrastructure_errors() -> None:
    timed_out = parse("fake-should-trigger", exit_code=None, timed_out=True, elapsed=300.0)
    assert (timed_out.status, timed_out.status_reason) == ("infra_error", "timed out after 300s")
    survived = parse("fake-should-trigger", survivors=True)
    assert survived.status_reason == "trial processes survived teardown"
