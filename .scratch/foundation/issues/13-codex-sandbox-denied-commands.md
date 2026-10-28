# 13: Codex sandbox-denied commands

**What to build:** the Codex adapter reports a command its sandbox denied, and a trigger rests only on evidence that the skill was read. Ticket 06's first Linux CI run (actions run [40614691505](https://github.com/BiscuitBin/skills/actions/runs/40614691505), with the temporary debug prints of commit `8fe4d12`) showed two gaps. Ubuntu 24.04's AppArmor restriction made bubblewrap fail, so Codex denied every sandboxed command:

```text
INFO codex_otel.log_only: event.name="codex.sandbox_outcome" tool_name=exec_command call_id=exec-… outcome=denied initial_duration_ms=45 …
bwrap: loopback: Failed RTM_NEWADDR: Operation not permitted
WARN codex_sandboxing::violation: recorded sandbox violation: resource=filesystem backend=linux_sandbox reason=operation_not_permitted path=unknown
```

- The denied commands never reached the trace. `trace.commands` was empty, yet `trace.status` stayed `ok`, so the run looked like one where the agent ran nothing.
- `assert trace.skills_triggered == ["cowsay"]` passed in the trigger-command test even though no `SKILL.md` read ran. The next assertion, on `trace.commands[1]`, failed with `IndexError`.

CI now lifts the restriction (`sysctl -w kernel.apparmor_restrict_unprivileged_userns=0`), so these gaps no longer show there, but a user on a stock Ubuntu 23.10+ machine meets them.

**Blocked by:** 06 (Codex adapter).

**Status:** ready-for-agent

**Agent requirements:** Any implementing agent (Claude Code, Codex or Pi). Recording the transcript needs the pinned Codex on a Linux machine (or VM) with the AppArmor restriction on; the tests themselves must not. Cross-model review is also required.

## Acceptance criteria

- [ ] A command the sandbox denies (`codex.sandbox_outcome … outcome=denied`) shows up in the trace as a failed command, or marks the trial, rather than disappearing while the status stays `ok`. Record which, and why, in `docs/reference/evals.md`.
- [ ] Find out why `skills_triggered == ["cowsay"]` held on Linux when no `SKILL.md` read ran (a `codex.skill_invocation` event, a parser path, or something else), and record the answer here.
- [ ] A trigger requires a read that succeeded or Codex's own event for one. A denied read does not count, and a test asserts this.
- [ ] Regression tests drive the parser from a recorded denied-sandbox transcript in `tests/fixtures/evals/codex/`, with its stderr reduced to the kept lines. They run in `just check` on any OS.

## Review checkpoints

Use the repo's cross-model adversarial review skill from ticket 01, or the protocol written out there:

- Pick the reviewer by the cross-model rule.
- A reviewer subagent saves its findings to the scratch folder.
- A separate triage subagent checks each finding against the code.
- Apply the valid fixes, rerun `just check`, and record every finding and how it was handled under **Completion notes**.

- **Implementation checkpoint:** before marking done, review the full diff against these acceptance criteria. Pay particular attention to how a denied command is told apart from one that ran and failed, and to triggers that rest on stderr events alone.

## Completion notes
