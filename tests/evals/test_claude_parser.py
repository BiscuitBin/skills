"""Parse recorded Claude Code stream-json transcripts into traces."""

import json
from collections.abc import Callable
from pathlib import Path
from typing import Any

from skills_tooling.evals.adapter import RawRun, Trace
from skills_tooling.evals.assertions import contains_lines, expected_script_output
from skills_tooling.evals.claude_code import BUILTIN_PLUGINS, BUILTIN_SKILLS, parse_stream

FIXTURES = Path(__file__).parents[1] / "fixtures/evals/claude"
SKILL_DIR = Path(__file__).parents[2] / "skills/cowsay"
Edit = Callable[[dict[str, Any]], dict[str, Any] | None]


def raw_run(transcript: Path, *, exit_code: int | None = 0, **overrides: object) -> RawRun:
    fields: dict[str, Any] = {
        "exit_code": exit_code,
        "timed_out": False,
        "transcript": transcript,
        "stderr": "",
        "debug_lines": (),
        "python_calls": (),
        "survivors": False,
        "elapsed": 1.0,
        **overrides,
    }
    return RawRun(**fields)


def parse(name: str, **overrides: object) -> Trace:
    return parse_stream(raw_run(FIXTURES / f"{name}.jsonl", **overrides))  # type: ignore[arg-type]


def edited(tmp_path: Path, name: str, edit: Edit) -> Path:
    """A copy of a fixture with each event passed through edit (None drops it)."""
    events = [json.loads(line) for line in (FIXTURES / f"{name}.jsonl").read_text().splitlines()]
    path = tmp_path / f"{name}.jsonl"
    kept = [e for e in map(edit, events) if e is not None]
    path.write_text("".join(json.dumps(e) + "\n" for e in kept))
    return path


def test_should_trigger_transcript_records_the_skill_call() -> None:
    trace = parse("fake-should-trigger")
    assert (trace.status, trace.stream_completed) == ("ok", True)
    assert trace.skills_triggered == ["cowsay"]
    assert trace.final_message == "Triggered."
    assert (trace.cli_version, trace.model) == ("2.1.309", "claude-sonnet-5-5")
    assert trace.visible_skills == BUILTIN_SKILLS["2.1.309"] | {"cowsay"}
    assert trace.visible_plugins == BUILTIN_PLUGINS["2.1.309"]


def test_should_not_trigger_transcript_has_no_trigger() -> None:
    trace = parse("fake-should-not-trigger")
    assert trace.status == "ok"
    assert (trace.skills_triggered, trace.skills_invoked, trace.commands) == ([], [], [])
    assert trace.final_message.startswith("Cows are ruminants")


def test_behaviour_transcript_records_the_command_and_its_output() -> None:
    trace = parse("fake-behaviour")
    [command] = trace.commands
    assert command.ok
    assert command.command.startswith("python3 .claude/skills/cowsay/scripts/cowsay.py")
    assert "< Ship it, team! >" in command.output


def test_a_plugin_prefixed_skill_name_counts_as_the_skill(tmp_path: Path) -> None:
    def prefix(event: dict[str, Any]) -> dict[str, Any]:
        for block in event.get("message", {}).get("content", []):
            if isinstance(block, dict) and block.get("name") == "Skill":
                block["input"]["skill"] = "cowsay:cowsay"
        return event

    trace = parse_stream(raw_run(edited(tmp_path, "fake-should-trigger", prefix)))
    assert trace.skills_triggered == ["cowsay"]


def test_a_failed_skill_call_is_invoked_but_not_triggered(tmp_path: Path) -> None:
    def fail(event: dict[str, Any]) -> dict[str, Any]:
        for block in event.get("message", {}).get("content", []):
            if isinstance(block, dict) and block.get("type") == "tool_result":
                block["is_error"] = True
        return event

    trace = parse_stream(raw_run(edited(tmp_path, "fake-should-trigger", fail)))
    assert (trace.skills_triggered, trace.skills_invoked) == ([], ["cowsay"])


def test_a_skill_call_without_a_result_is_not_a_trigger(tmp_path: Path) -> None:
    def drop_results(event: dict[str, Any]) -> dict[str, Any] | None:
        content = event.get("message", {}).get("content", [])
        if event.get("type") == "user" and any(
            isinstance(b, dict) and b.get("type") == "tool_result" for b in content
        ):
            return None
        return event

    trace = parse_stream(raw_run(edited(tmp_path, "fake-should-trigger", drop_results)))
    assert trace.skills_triggered == []


def test_commands_changed_events_are_collected(tmp_path: Path) -> None:
    def add(event: dict[str, Any]) -> dict[str, Any]:
        return event

    path = edited(tmp_path, "fake-should-not-trigger", add)
    lines = path.read_text().splitlines()
    commands = [{"name": "compact"}, {"name": "canary"}]
    changed = {"type": "system", "subtype": "commands_changed", "commands": commands}
    path.write_text("\n".join([lines[0], json.dumps(changed), *lines[1:]]) + "\n")
    trace = parse_stream(raw_run(path))
    assert trace.dynamic_commands == ["compact", "canary"]
    assert trace.initial_commands is not None
    assert {"compact", "cowsay"} <= trace.initial_commands
    assert "canary" not in trace.initial_commands


# Recorded from the live `just eval cowsay --agent claude` run (ticket 05),
# with paths replaced by placeholders and rate-limit details removed.


def test_live_should_trigger_transcript() -> None:
    trace = parse("live-should-trigger")
    assert (trace.status, trace.skills_triggered) == ("ok", ["cowsay"])
    assert (trace.cli_version, trace.model) == ("2.1.309", "claude-sonnet-5-5")
    assert trace.visible_skills == BUILTIN_SKILLS["2.1.309"] | {"cowsay"}
    assert trace.visible_plugins == BUILTIN_PLUGINS["2.1.309"]


def test_live_should_not_trigger_transcript() -> None:
    trace = parse("live-should-not-trigger")
    assert trace.status == "ok"
    assert (trace.skills_triggered, trace.skills_invoked, trace.commands) == ([], [], [])
    assert "cow" in trace.final_message.lower()


def test_live_behaviour_transcript_shows_the_scripts_exact_output() -> None:
    trace = parse("live-behaviour")
    assert (trace.status, trace.skills_triggered) == ("ok", ["cowsay"])
    [command] = trace.commands
    assert command.ok
    assert command.command.endswith(".claude/skills/cowsay/scripts/cowsay.py -- 'Ship it, team!'")
    cow = expected_script_output(SKILL_DIR, "scripts/cowsay.py", ("--", "Ship it, team!"))
    assert contains_lines(command.output, cow)
    assert contains_lines(trace.final_message, cow)
