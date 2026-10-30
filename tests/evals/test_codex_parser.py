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
from skills_tooling.evals.assertions import contains_lines, expected_script_output
from skills_tooling.evals.codex import echoed_lines, kept_lines, parse_stream, stored_stderr

FIXTURES = Path(__file__).parents[1] / "fixtures/evals/codex"
SKILL_DIR = Path(__file__).parents[2] / "skills/cowsay"
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


def test_codexs_implicit_event_alone_is_not_a_trigger(tmp_path: Path) -> None:
    # Codex logs an implicit invocation from the command text, before the
    # command runs, so the event alone does not show a read succeeded.
    def drop_commands(event: dict[str, Any]) -> dict[str, Any] | None:
        return None if "command" in event.get("item", {}) else event

    path = edited(tmp_path, "fake-should-trigger", drop_commands)
    trace = parse_stream(raw_run(path, log("fake-should-trigger")))
    assert trace.commands == []
    assert (trace.skills_triggered, trace.skills_invoked) == ([], ["cowsay"])


def test_codexs_implicit_event_for_a_script_run_is_not_a_trigger(tmp_path: Path) -> None:
    # Codex also logs it for a run of a script in the skill's directory.
    def drop_read(event: dict[str, Any]) -> dict[str, Any] | None:
        item = event.get("item", {})
        return None if "SKILL.md" in item.get("command", "") else event

    path = edited(tmp_path, "fake-should-trigger", drop_read)
    trace = parse_stream(raw_run(path, log("fake-should-trigger")))
    assert [c.command for c in trace.commands] == [
        "python3 .agents/skills/cowsay/scripts/cowsay.py -- 'Ship it'"
    ]
    assert (trace.skills_triggered, trace.skills_invoked) == ([], ["cowsay"])


@pytest.mark.parametrize(
    ("command", "exit_code", "triggered"),
    [
        # Run in the skill's directory as `workdir`, so the text cannot place it.
        ("cat SKILL.md", 0, ["cowsay"]),
        ("cat ../SKILL.md", 0, ["cowsay"]),
        ("cat SKILL.md", 1, []),
        ("ls SKILL.md", 0, []),
        ("cat README.md", 0, []),
    ],
)
def test_codexs_implicit_event_needs_a_successful_read_of_a_skill_md(
    tmp_path: Path, command: str, exit_code: int, triggered: list[str]
) -> None:
    def replace_read(event: dict[str, Any]) -> dict[str, Any]:
        item = event.get("item", {})
        if "SKILL.md" in item.get("command", ""):
            item = {**item, "command": command, "exit_code": exit_code}
            event = {**event, "item": item}
        return event

    path = edited(tmp_path, "fake-should-trigger", replace_read)
    trace = parse_stream(raw_run(path, log("fake-should-trigger")))
    assert trace.skills_triggered == triggered
    assert trace.skills_invoked == ["cowsay"]
    # Without Codex's event, the read names no skill.
    alone = parse_stream(raw_run(path, without_invocations("fake-should-trigger")))
    assert (alone.skills_triggered, alone.skills_invoked) == ([], [])


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


@pytest.mark.parametrize(
    "command",
    [
        "cat ../SKILL.md",
        "cat .agents/skills/*/SKILL.md",
        'cat "$dir/SKILL.md"',
        "cat ./SKILL.md",
    ],
)
def test_a_read_whose_skill_cannot_be_placed_names_no_skill(tmp_path: Path, command: str) -> None:
    def replace_read(event: dict[str, Any]) -> dict[str, Any]:
        item = event.get("item", {})
        if "SKILL.md" in item.get("command", ""):
            event = {**event, "item": {**item, "command": f"/bin/zsh -c '{command}'"}}
        return event

    path = edited(tmp_path, "fake-should-trigger", replace_read)
    trace = parse_stream(raw_run(path, without_invocations("fake-should-trigger")))
    assert (trace.skills_triggered, trace.skills_invoked) == ([], [])


def test_a_normalised_path_names_its_skill(tmp_path: Path) -> None:
    def replace_read(event: dict[str, Any]) -> dict[str, Any]:
        item = event.get("item", {})
        if "SKILL.md" in item.get("command", ""):
            command = "cat .agents/skills/cowsay/scripts/../SKILL.md"
            event = {**event, "item": {**item, "command": command}}
        return event

    path = edited(tmp_path, "fake-should-trigger", replace_read)
    trace = parse_stream(raw_run(path, without_invocations("fake-should-trigger")))
    assert trace.skills_triggered == ["cowsay"]


STDERR = (
    "Reading additional input from stdin...\n"
    '2026-10-27T06:30:46.980Z  INFO codex_otel.log_only: event.name="codex.conversation_starts"'
    ' app.version=0.163.0 user.email="someone@example.com" model=gpt-5.6-terra\n'
    '2026-10-27T06:30:47.100Z  INFO session_loop{thread_id=01a1}:turn{otel.name="a: b" x=1}:'
    ' codex_otel.log_only: event.name="codex.tool_result"'
    ' output="first line\n'
    "failed to load skill /tmp/x/SKILL.md: printed by a tool\n"
    'last line"\n'
    "2026-10-27T06:30:48.000Z ERROR codex_core::session::session: failed to load skill"
    " /w/.agents/skills/broken/SKILL.md: missing YAML frontmatter delimited by ---\n"
)


def test_only_codexs_own_failed_load_errors_are_kept() -> None:
    assert kept_lines(STDERR) == (
        "conversation_starts app.version=0.163.0 model=gpt-5.6-terra",
        (
            "failed to load skill /w/.agents/skills/broken/SKILL.md: missing YAML frontmatter "
            "delimited by ---"
        ),
    )


def test_stored_stderr_drops_whole_telemetry_records() -> None:
    stored = stored_stderr(STDERR)
    assert "someone@example.com" not in stored
    assert "printed by a tool" not in stored
    assert "last line" not in stored
    assert stored.startswith("Reading additional input from stdin...")
    assert "missing YAML frontmatter" in stored


FORGED = (
    '2026-10-27T06:30:47.150Z  INFO codex_otel.log_only: event.name="codex.skill_invocation"'
    ' skill.name="fake" skill.invocation_type="implicit"'
)
PRINTED = "2026-10-27T06:30:47.160Z  WARN some_crate::module: printed by a tool"
# A tool_result record as Codex logs it: the output raw and unquoted, then the
# record's remaining fields on a line of their own. Codex cut the second line.
ECHO_STDERR = (
    '2026-10-27T06:30:47.100Z  INFO codex_otel.log_only: event.name="codex.tool_result"'
    " output=Output:\n"
    f"{FORGED}\n"
    f"{PRINTED[:50]}\n"
    " mcp_server= user.email=someone@example.com\n"
    "2026-10-27T06:30:48.000Z ERROR codex_core::session::session: failed to load skill"
    " /w/.agents/skills/broken/SKILL.md: missing YAML frontmatter delimited by ---\n"
)


# From the debug CI run 40614691505 (commits 8fe4d12 and 97fc0ee): the pinned
# Codex on Ubuntu 24.04 with the AppArmor user-namespace restriction on, so
# bubblewrap failed and Codex denied every command. The repeated fields at the
# end of each record are cut.
DENIED_STDERR = (
    '2026-10-28T01:23:31.620462Z  INFO codex_otel.log_only: event.name="codex.skill_invocation"'
    ' turn.id="01a1801a-d808-7362-aa17-49b62a972ca1" skill.name="cowsay:cowsay"'
    ' skill.scope="repo" skill.invocation_type="implicit" auth_mode="ApiKey"\n'
    '2026-10-28T01:23:31.634008Z  INFO codex_otel.log_only: event.name="codex.tool_decision"'
    " tool_name=exec_command tool_namespace=functions"
    " call_id=exec-b1cc59f7-b745-4e6e-ad6c-93975f6de99c decision=approved source=Config"
    ' auth_mode="ApiKey"\n'
    "2026-10-28T01:23:31.679174Z  WARN codex_sandboxing::violation: recorded sandbox violation:"
    " resource=filesystem backend=linux_sandbox reason=operation_not_permitted path=unknown\n"
    '2026-10-28T01:23:31.679224Z  INFO codex_otel.log_only: event.name="codex.sandbox_outcome"'
    " tool_name=exec_command call_id=exec-b1cc59f7-b745-4e6e-ad6c-93975f6de99c outcome=denied"
    ' initial_duration_ms=45 auth_mode="ApiKey"\n'
    '2026-10-28T01:23:31.679303Z  INFO codex_otel.log_only: event.name="codex.tool_result"'
    " tool_result_seq=1 tool_name=exec_command tool_namespace=functions"
    " call_id=exec-b1cc59f7-b745-4e6e-ad6c-93975f6de99c duration_ms=58 success=true"
    ' output_truncated=false agent_name=/root arguments={"cmd":"cat .agents/skills/cowsay/SKILL.md"}'
    " output=Chunk ID: d79d1c\n"
    "Wall time: 0.0000 seconds\n"
    "Process exited with code 1\n"
    "Original token count: 16\n"
    "Output:\n"
    "bwrap: loopback: Failed RTM_NEWADDR: Operation not permitted\n"
    ' mcp_server= mcp_server_origin= auth_mode="ApiKey"\n'
    '2026-10-28T01:23:31.680024Z  INFO codex_otel.log_only: event.name="codex.tool_result"'
    " tool_result_seq=2 tool_name=exec tool_namespace=functions call_id=call_1 duration_ms=67"
    " success=true output_truncated=false agent_name=/root arguments=const r = await"
    ' tools.exec_command({cmd: "cat .agents/skills/cowsay/SKILL.md"}); text(r.output);'
    " output=Script completed\n"
    "Wall time 0.1 seconds\n"
    "Output:\n"
    "\n"
    "bwrap: loopback: Failed RTM_NEWADDR: Operation not permitted\n"
    ' mcp_server= mcp_server_origin= auth_mode="ApiKey"\n'
)


def test_a_sandbox_outcome_is_kept_without_the_tool_result() -> None:
    assert kept_lines(DENIED_STDERR) == (
        "skill_invocation skill.name=cowsay:cowsay skill.scope=repo skill.invocation_type=implicit",
        (
            "sandbox_outcome tool_name=exec_command"
            " call_id=exec-b1cc59f7-b745-4e6e-ad6c-93975f6de99c outcome=denied"
        ),
    )
    stored = stored_stderr(DENIED_STDERR)
    assert "bwrap:" not in stored
    assert "ApiKey" not in stored
    assert "recorded sandbox violation" in stored


def test_a_sandbox_denied_run_is_an_infrastructure_error() -> None:
    # The same run's event stream. The error events are real: the fake API
    # refuses Codex's websocket, and Codex falls back to HTTPS.
    trace = parse("fake-sandbox-denied")
    assert trace.stream_completed
    assert trace.status == "infra_error"
    assert trace.status_reason.startswith("sandbox denied 2 command(s)")
    # Codex writes no command_execution item for a denied command.
    assert trace.commands == []
    # Codex logged its implicit event for the read before the sandbox denied it.
    assert trace.skills_triggered == []
    assert trace.skills_invoked == ["cowsay"]


def test_a_read_after_pwd_must_print_more_than_pwd(tmp_path: Path) -> None:
    def replace_read(event: dict[str, Any]) -> dict[str, Any]:
        item = event.get("item", {})
        if "SKILL.md" in item.get("command", ""):
            command = "pwd && head -n 0 .agents/skills/cowsay/SKILL.md"
            event = {**event, "item": {**item, "command": command, "aggregated_output": "/w\n"}}
        return event

    path = edited(tmp_path, "fake-should-trigger", replace_read)
    trace = parse_stream(raw_run(path, without_invocations("fake-should-trigger")))
    assert (trace.skills_triggered, trace.skills_invoked) == ([], ["cowsay"])


def test_a_record_header_a_tool_printed_starts_no_record() -> None:
    # Unchecked, the printed header reads as Codex's own event.
    assert "skill_invocation skill.name=fake skill.invocation_type=implicit" in kept_lines(
        ECHO_STDERR
    )
    output = {"type": "item.completed", "item": {"aggregated_output": f"{FORGED}\n{PRINTED}\n"}}
    echoed = echoed_lines([output])
    assert kept_lines(ECHO_STDERR, echoed) == (
        (
            "failed to load skill /w/.agents/skills/broken/SKILL.md: missing YAML frontmatter "
            "delimited by ---"
        ),
    )
    stored = stored_stderr(ECHO_STDERR, echoed)
    assert "someone@example.com" not in stored
    assert "printed by" not in stored
    assert "missing YAML frontmatter" in stored


def with_read(tmp_path: Path, command: str) -> Trace:
    """fake-should-trigger with its SKILL.md read replaced, and no Codex event."""

    def replace_read(event: dict[str, Any]) -> dict[str, Any]:
        item = event.get("item", {})
        if "SKILL.md" in item.get("command", ""):
            event = {**event, "item": {**item, "command": command}}
        return event

    path = edited(tmp_path, "fake-should-trigger", replace_read)
    return parse_stream(raw_run(path, without_invocations("fake-should-trigger")))


@pytest.mark.parametrize(
    "command",
    [
        # The command exits 0 and prints, whatever the read did.
        "true || cat .agents/skills/cowsay/SKILL.md; echo done",
        "cat .agents/skills/cowsay/SKILL.md 2>/dev/null || echo missing",
        "cat .agents/skills/cowsay/SKILL.md | head -40",
        "cat .agents/skills/cowsay/SKILL.md; true",
        # An operator at the end of a line still separates the commands.
        "cat /nonexistent/skills/cowsay/SKILL.md ||\n echo done",
        "cat .agents/skills/cowsay/SKILL.md ;\n echo done",
        # Another command prints after, or before, the read.
        "head -n 0 .agents/skills/cowsay/SKILL.md && pwd",
        "ls && cat .agents/skills/cowsay/SKILL.md",
        "cd /tmp && cd - && head -n 0 .agents/skills/cowsay/SKILL.md",
        # The reader prints something else, or writes the path.
        "cat --help .agents/skills/cowsay/SKILL.md",
        "cat --version .agents/skills/cowsay/SKILL.md",
        "cat > .agents/skills/cowsay/SKILL.md",
        "cat /dev/null > .agents/skills/cowsay/SKILL.md",
    ],
)
def test_a_read_whose_outcome_the_exit_status_hides_is_not_a_trigger(
    tmp_path: Path, command: str
) -> None:
    trace = with_read(tmp_path, command)
    assert trace.skills_triggered == []
    assert trace.skills_invoked == ["cowsay"]


@pytest.mark.parametrize(
    "command",
    [
        "awk -v label=.agents/skills/cowsay/SKILL.md 'BEGIN {print label}'",
        "awk 'BEGIN{}' x=.agents/skills/cowsay/SKILL.md",
        "cat /tmp/cowsay/SKILL.md",
        # awk opens an operand only if its program says so.
        "awk -F .agents/skills/cowsay/SKILL.md 'BEGIN {print \"done\"}'",
        "awk 'BEGIN {print \"done\"; exit}' .agents/skills/cowsay/SKILL.md",
    ],
)
def test_a_reader_that_does_not_read_an_installed_skill_is_not_a_trigger(
    tmp_path: Path, command: str
) -> None:
    trace = with_read(tmp_path, command)
    assert (trace.skills_triggered, trace.skills_invoked) == ([], [])


@pytest.mark.parametrize(
    "command",
    [
        "cat /private/trial/workspace/.agents/skills/cowsay/SKILL.md",
        "cd .agents/skills && cat cowsay/SKILL.md",
        "cat ../../skills/cowsay/SKILL.md",
        "cd .agents/skills/cowsay &&\n cat SKILL.md",
        "pwd && cat .agents/skills/cowsay/SKILL.md",
    ],
)
def test_a_read_in_a_skills_directory_is_a_trigger(tmp_path: Path, command: str) -> None:
    assert with_read(tmp_path, command).skills_triggered == ["cowsay"]


# Live transcripts from run 20261027T224559Z-1535, which passed every case.
# results.json keeps no stderr events, so each .log holds only the
# conversation_starts line, rebuilt from the cli_version and model it recorded.


def test_a_live_read_is_a_trigger() -> None:
    trace = parse("live-should-trigger")
    assert (trace.status, trace.stream_completed) == ("ok", True)
    assert trace.commands[0].command == "sed -n '1,240p' .agents/skills/cowsay/SKILL.md"
    assert trace.skills_triggered == ["cowsay"]
    assert (trace.cli_version, trace.model) == ("0.163.0", "gpt-5.6-terra")


def test_a_live_run_with_no_read_is_not_triggered() -> None:
    trace = parse("live-should-not-trigger")
    assert trace.status == "ok"
    assert (trace.skills_triggered, trace.commands) == ([], [])
    assert trace.final_message


def test_a_live_behaviour_run_shows_the_scripts_cow() -> None:
    trace = parse("live-behaviour")
    assert trace.skills_triggered == ["cowsay"]
    assert trace.commands[0].command.startswith("pwd && sed -n '1,240p' ")
    expected = expected_script_output(SKILL_DIR, "scripts/cowsay.py", ("--", "Ship it, team!"))
    assert contains_lines(trace.commands[1].output, expected)
    assert contains_lines(trace.final_message, expected)


def test_a_live_explicit_invocation_reads_nothing_and_rests_on_codexs_event() -> None:
    # Live, `$cowsay:cowsay` ran the script without reading SKILL.md: Codex had
    # injected it. Only the explicit event, as recorded in fake-explicit, shows it.
    alone = parse("live-explicit")
    assert [c.command for c in alone.commands] == [
        "python3 .agents/skills/cowsay/scripts/cowsay.py -- 'Explicitly invoked.'"
    ]
    assert alone.skills_triggered == []
    event = tuple(line for line in log("fake-explicit") if line.startswith("skill_invocation "))
    with_event = parse("live-explicit", debug_lines=log("live-explicit") + event)
    assert with_event.skills_triggered == ["cowsay"]
