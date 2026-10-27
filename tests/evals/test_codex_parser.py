"""Parse recorded `codex exec --json` transcripts and kept log lines into traces.

Each fixture pairs the JSONL stdout (<name>.jsonl) with the stderr lines the
adapter keeps (<name>.log). The fake-* fixtures are the real pinned CLI driven
by the fake Responses API; the live-* fixtures are from a live run.
"""

import json
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest

from skills_tooling.evals.adapter import RawRun, Trace
from skills_tooling.evals.codex import parse_stream

FIXTURES = Path(__file__).parents[1] / "fixtures/evals/codex"
Edit = Callable[[dict[str, Any]], dict[str, Any] | None]


def log(name: str) -> tuple[str, ...]:
    return tuple((FIXTURES / f"{name}.log").read_text().splitlines())


def raw_run(transcript: Path, lines: tuple[str, ...], **overrides: object) -> RawRun:
    fields: dict[str, Any] = {
        "exit_code": 0,
        "timed_out": False,
        "transcript": transcript,
        "stderr": "",
        "debug_lines": lines,
        "python_calls": (),
        "survivors": False,
        "elapsed": 1.0,
        **overrides,
    }
    return RawRun(**fields)


def parse(name: str, **overrides: object) -> Trace:
    lines = overrides.pop("debug_lines", log(name))
    return parse_stream(raw_run(FIXTURES / f"{name}.jsonl", lines, **overrides))  # type: ignore[arg-type]


def edited(tmp_path: Path, name: str, edit: Edit) -> Path:
    """A copy of a fixture with each event passed through edit (None drops it)."""
    events = [json.loads(line) for line in (FIXTURES / f"{name}.jsonl").read_text().splitlines()]
    path = tmp_path / f"{name}.jsonl"
    kept = [e for e in map(edit, events) if e is not None]
    path.write_text("".join(json.dumps(e) + "\n" for e in kept))
    return path


def without_invocations(name: str) -> tuple[str, ...]:
    return tuple(line for line in log(name) if not line.startswith("skill_invocation "))


def test_a_completed_read_of_skill_md_is_a_trigger() -> None:
    trace = parse("fake-should-trigger")
    assert (trace.status, trace.stream_completed) == ("ok", True)
    assert trace.skills_triggered == ["cowsay"]
    assert trace.final_message == "Here is your cow."
    assert (trace.cli_version, trace.model) == ("0.163.0", "gpt-5.6-terra")
    # Codex's `<shell> -c` wrapper is removed, so assertions see the agent's command.
    assert [c.command for c in trace.commands] == [
        "cat .agents/skills/cowsay/SKILL.md",
        "python3 .agents/skills/cowsay/scripts/cowsay.py -- 'Ship it'",
    ]
    assert all(c.ok for c in trace.commands)
    assert "< Ship it >" in trace.commands[1].output
    assert (trace.visible_skills, trace.visible_plugins) == (None, None)


def test_the_read_alone_triggers_without_codexs_own_event() -> None:
    trace = parse("fake-should-trigger", debug_lines=without_invocations("fake-should-trigger"))
    assert trace.skills_triggered == ["cowsay"]


def test_a_read_after_cd_names_the_skill_directory() -> None:
    trace = parse("fake-cd-read", debug_lines=without_invocations("fake-cd-read"))
    assert trace.commands[0].command == "cd .agents/skills/cowsay && sed -n '1,40p' SKILL.md"
    assert trace.skills_triggered == ["cowsay"]


def test_a_run_with_no_read_is_not_triggered() -> None:
    trace = parse("fake-should-not-trigger")
    assert trace.status == "ok"
    assert (trace.skills_triggered, trace.skills_invoked, trace.commands) == ([], [], [])
    assert trace.final_message == "Cows have four stomach compartments."


def test_a_failed_read_is_not_a_trigger() -> None:
    trace = parse("fake-failed-read")
    assert trace.status == "ok"
    assert [(c.command, c.ok) for c in trace.commands] == [
        ("cat .agents/skills/cowsay/SKILL.md /nonexistent", False)
    ]
    # The file's text is in the output, but the command failed.
    assert "name: cowsay" in trace.commands[0].output
    assert trace.skills_triggered == []
    assert trace.skills_invoked == ["cowsay"]


def test_a_command_that_only_names_the_path_is_not_a_trigger() -> None:
    trace = parse("fake-mention-only")
    assert trace.commands[0].ok
    assert ".agents/skills/cowsay/SKILL.md" in trace.commands[0].output
    assert (trace.skills_triggered, trace.skills_invoked) == ([], [])


def test_a_read_that_never_completed_is_not_a_trigger(tmp_path: Path) -> None:
    def drop_completed_read(event: dict[str, Any]) -> dict[str, Any] | None:
        item = event.get("item", {})
        if event["type"] == "item.completed" and "SKILL.md" in item.get("command", ""):
            return None
        return event

    path = edited(tmp_path, "fake-should-trigger", drop_completed_read)
    lines = without_invocations("fake-should-trigger")
    trace = parse_stream(raw_run(path, lines))
    assert trace.skills_triggered == []


def test_codexs_implicit_event_alone_is_a_trigger(tmp_path: Path) -> None:
    # Codex logs an implicit invocation when it sees a read of SKILL.md, which
    # also covers a read the command text cannot place, such as one in `workdir`.
    def drop_read(event: dict[str, Any]) -> dict[str, Any] | None:
        item = event.get("item", {})
        return None if "SKILL.md" in item.get("command", "") else event

    path = edited(tmp_path, "fake-should-trigger", drop_read)
    trace = parse_stream(raw_run(path, log("fake-should-trigger")))
    assert trace.skills_triggered == ["cowsay"]


def test_an_explicit_invocation_is_a_trigger_without_a_read() -> None:
    # `$cowsay:cowsay` injects SKILL.md into the request; no command reads it.
    trace = parse("fake-explicit")
    assert trace.status == "ok"
    assert trace.commands == []
    assert trace.skills_triggered == ["cowsay"]
    assert trace.skills_invoked == ["cowsay"]


def test_a_skill_that_failed_to_load_fails_the_run() -> None:
    trace = parse("fake-broken-skill")
    assert trace.stream_completed
    assert trace.status == "infra_error"
    assert trace.status_reason.startswith("failed to load skill ")
    assert "broken/SKILL.md" in trace.status_reason


def test_failed_authentication_is_an_infrastructure_error() -> None:
    trace = parse("fake-auth-failure", exit_code=1)
    assert trace.status == "infra_error"
    assert trace.status_reason.startswith("agent reported an error: ")
    assert "401 Unauthorized" in trace.status_reason


def test_a_truncated_stream_is_an_infrastructure_error(tmp_path: Path) -> None:
    path = edited(
        tmp_path, "fake-should-trigger", lambda e: None if e["type"] == "turn.completed" else e
    )
    trace = parse_stream(raw_run(path, log("fake-should-trigger")))
    assert (trace.stream_completed, trace.status) == (False, "infra_error")
    assert trace.status_reason.startswith("stream truncated")


def test_an_unparsable_line_is_a_truncated_stream(tmp_path: Path) -> None:
    path = tmp_path / "broken.jsonl"
    path.write_text((FIXTURES / "fake-should-trigger.jsonl").read_text() + '{"type": "tur\n')
    trace = parse_stream(raw_run(path, log("fake-should-trigger")))
    assert trace.status == "infra_error"


@pytest.mark.parametrize(
    ("overrides", "reason"),
    [
        ({"exit_code": 3}, "nonzero exit 3"),
        ({"exit_code": None, "timed_out": True, "elapsed": 300.0}, "timed out after 300s"),
        ({"survivors": True}, "trial processes survived teardown"),
    ],
)
def test_a_complete_stream_still_fails_on_the_process_outcome(
    overrides: dict[str, object], reason: str
) -> None:
    trace = parse("fake-should-trigger", **overrides)
    assert (trace.status, trace.status_reason) == ("infra_error", reason)
