"""Parse recorded Claude Code stream-json transcripts into traces."""

import json
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest

from skills_tooling.evals.adapter import RawRun, Trace
from skills_tooling.evals.assertions import contains_lines, expected_script_output
from skills_tooling.evals.claude_code import (
    BUILTIN_PLUGINS,
    BUILTIN_SKILLS,
    EXPANSION,
    ClaudeCode,
    parse_stream,
    session_lines,
)

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


@pytest.mark.parametrize("separator", ["\u2028", "\u2029", "\x85"])
def test_unicode_line_separators_inside_a_string_do_not_split_an_event(
    tmp_path: Path, separator: str
) -> None:
    # JSON allows these unescaped inside strings, and the CLI writes them raw.
    def add_separator(event: dict[str, Any]) -> dict[str, Any]:
        for block in event.get("message", {}).get("content", []):
            if isinstance(block, dict) and block.get("type") == "text":
                block["text"] += f"{separator}moo"
        if event.get("type") == "result":
            event["result"] += f"{separator}moo"
        return event

    events = [json.loads(line) for line in (FIXTURES / "fake-should-trigger.jsonl").open()]
    path = tmp_path / "separators.jsonl"
    path.write_text(
        "".join(json.dumps(add_separator(e), ensure_ascii=False) + "\n" for e in events)
    )
    trace = parse_stream(raw_run(path))
    assert (trace.status, trace.stream_completed) == ("ok", True)
    assert trace.skills_triggered == ["cowsay"]
    assert trace.final_message.endswith(f"{separator}moo")


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


# Recorded for ticket 17 from the pinned CLI and the fake API, with session
# persistence on and a throwaway by-name-only skill, branch-brief. Each pairs
# the stream with the session file the CLI wrote, kept to its user and
# assistant records, so the tests drive the reduction as well as the parser.
BY_NAME = "branch-brief"
CLAUDE = ClaudeCode(Path(__file__).parents[2] / "node_modules/.bin/claude")


def session_id(name: str) -> str:
    init = json.loads((FIXTURES / f"{name}.jsonl").read_text().split("\n", 1)[0])
    return str(init["session_id"])


def by_name(name: str, *, session: str | None = None, **overrides: object) -> Trace:
    """A fixture parsed as the adapter parses a run, with a session file's kept lines."""
    lines = session_lines(FIXTURES / f"{session or name}.session.jsonl")
    transcript = FIXTURES / f"{name}.jsonl"
    return CLAUDE.parse(raw_run(transcript, session_lines=lines, **overrides))  # type: ignore[arg-type]


def test_a_by_name_invocation_triggers_through_the_session_record() -> None:
    # The stream shows no sign of the expansion; the session file does.
    assert session_lines(FIXTURES / "fake-by-name.session.jsonl") == (
        f"session {session_id('fake-by-name')}",
        f"skill_expanded <TRIAL>/workspace/.claude/skills/{BY_NAME}",
    )
    trace = by_name("fake-by-name")
    assert (trace.status, trace.status_reason) == ("ok", "")
    assert trace.skills_triggered == [BY_NAME]
    assert trace.skills_invoked == [BY_NAME]
    assert trace.commands == []
    assert trace.final_message == "BRIEFED"


@pytest.mark.parametrize(
    ("name", "invoked"),
    [
        # A plain request: the CLI does not list a by-name-only skill to the model.
        ("fake-by-name-quiet", []),
        # The model asks anyway, and the CLI refuses: invoked, not triggered.
        ("fake-by-name-refused", [BY_NAME]),
        # Bash prints the expansion's first line; it lands in a tool_result.
        ("fake-by-name-forged", []),
        # A baseline sent the prefix: no such command, so nothing expands.
        ("fake-by-name-baseline", []),
    ],
)
def test_a_session_with_no_expansion_records_no_by_name_trigger(
    name: str, invoked: list[str]
) -> None:
    assert session_lines(FIXTURES / f"{name}.session.jsonl") == (f"session {session_id(name)}",)
    trace = by_name(name)
    assert (trace.status, trace.status_reason) == ("ok", "")
    assert (trace.skills_triggered, trace.skills_invoked) == ([], invoked)


def test_a_forged_expansion_line_in_a_tool_result_is_not_a_trigger() -> None:
    trace = by_name("fake-by-name-forged")
    [command] = trace.commands
    assert command.ok
    assert command.output.startswith(
        f"Base directory for this skill: <TRIAL>/workspace/.claude/skills/{BY_NAME}"
    )
    assert trace.skills_triggered == []


def test_a_by_name_prompt_in_the_baseline_expands_nothing() -> None:
    trace = by_name("fake-by-name-baseline")
    assert trace.visible_skills is not None
    assert BY_NAME not in trace.visible_skills
    assert trace.skills_triggered == []


def session_records(name: str) -> list[dict[str, Any]]:
    text = (FIXTURES / f"{name}.session.jsonl").read_text()
    return [json.loads(line) for line in text.splitlines()]


def written(tmp_path: Path, records: list[dict[str, Any]]) -> Path:
    path = tmp_path / "session.jsonl"
    path.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in records))
    return path


def test_the_reduction_keeps_only_the_clis_expansion_before_the_first_reply(
    tmp_path: Path,
) -> None:
    command, expansion, reply = session_records("fake-by-name")
    after = written(tmp_path, [command, reply, expansion])
    assert session_lines(after) == (f"session {session_id('fake-by-name')}",)
    not_meta = written(tmp_path, [command, {**expansion, "isMeta": False}, reply])
    assert session_lines(not_meta) == (f"session {session_id('fake-by-name')}",)
    caveat = {**expansion, "message": {"role": "user", "content": "Caveat: the messages below"}}
    assert session_lines(written(tmp_path, [command, caveat, reply])) == (
        f"session {session_id('fake-by-name')}",
    )
    # The path is the rest of the text's first line, whatever the block holds.
    content = {"role": "user", "content": f"{EXPANSION}/w/.claude/skills/x\u2028y\n\nbody"}
    assert session_lines(written(tmp_path, [command, {**expansion, "message": content}])) == (
        f"session {session_id('fake-by-name')}",
        "skill_expanded /w/.claude/skills/x\u2028y",
    )


@pytest.mark.parametrize(
    "records",
    [
        # Two sessions' records: whose file it is cannot be told.
        lambda r: [r[0], {**r[1], "sessionId": "another"}, r[2]],
        lambda r: [{k: v for k, v in each.items() if k != "sessionId"} for each in r],
        lambda r: [{**each, "sessionId": 7} for each in r],
        lambda _: [],
    ],
)
def test_a_session_file_that_is_not_one_sessions_gives_nothing(
    tmp_path: Path, records: Callable[[list[dict[str, Any]]], list[dict[str, Any]]]
) -> None:
    path = written(tmp_path, records(session_records("fake-by-name")))
    assert session_lines(path) == ()


def test_a_session_file_that_is_missing_or_not_jsonl_gives_nothing(tmp_path: Path) -> None:
    assert session_lines(tmp_path / "missing.jsonl") == ()
    path = tmp_path / "cut.jsonl"
    path.write_text((FIXTURES / "fake-by-name.session.jsonl").read_text() + '{"type": "us\n')
    assert session_lines(path) == ()


@pytest.mark.parametrize(
    "path",
    [
        f"<TRIAL>/workspace/.claude/skills/{BY_NAME}/scripts",
        f"<TRIAL>/workspace/nested/.claude/skills/{BY_NAME}",
        f"<TRIAL>/home/.claude/skills/{BY_NAME}",
        f"/elsewhere<TRIAL>/workspace/.claude/skills/{BY_NAME}",
        "<TRIAL>/workspace/.claude/skills/",
        "<TRIAL>/workspace/.claude/skills/..",
    ],
)
def test_only_an_expansion_from_the_workspaces_skills_directory_is_a_trigger(
    path: str,
) -> None:
    lines = (f"session {session_id('fake-by-name')}", f"skill_expanded {path}")
    trace = CLAUDE.parse(raw_run(FIXTURES / "fake-by-name.jsonl", session_lines=lines))
    assert trace.status == "ok"
    assert (trace.skills_triggered, trace.skills_invoked) == ([], [])


NO_SESSION = ("infra_error", "no session record; failing closed")


def test_a_run_without_its_session_record_fails_closed() -> None:
    # No file found, or none read: nothing shows whether a skill expanded.
    trace = CLAUDE.parse(raw_run(FIXTURES / "fake-by-name.jsonl"))
    assert (trace.status, trace.status_reason) == NO_SESSION
    # Another session's file is not this run's record either.
    crossed = by_name("fake-by-name", session="fake-by-name-quiet")
    assert (crossed.status, crossed.status_reason) == NO_SESSION
    # The parser alone, which the grader calls, needs none.
    assert parse_stream(raw_run(FIXTURES / "fake-by-name.jsonl")).status == "ok"


def test_a_missing_session_record_does_not_hide_why_a_run_failed() -> None:
    trace = CLAUDE.parse(raw_run(FIXTURES / "fake-by-name.jsonl", exit_code=3))
    assert (trace.status, trace.status_reason) == ("infra_error", "nonzero exit 3")
