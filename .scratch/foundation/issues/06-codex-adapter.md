# 06: Codex adapter

**What to build:** `just eval cowsay --agent codex` runs the same cowsay eval cases against the pinned Codex, headless, through the adapter interface from ticket 05. They get the same isolation guarantees and the same results format. Codex has no documented trigger event, so a trigger means the agent read the skill's `SKILL.md`. Codex facts are in the research notes (`.scratch/foundation/research.md`).

**Blocked by:** 05 (Eval harness tracer bullet: cowsay on Claude Code).

**Status:** ready-for-agent

## Acceptance criteria

- [ ] The Codex adapter implements the ticket 05 interface without changing the case schema. If the interface has to change, the Claude Code adapter and its tests are updated in the same change.
- [ ] The run uses an isolated Codex home, ignores user config, and is ephemeral.
  - Credentials reach the isolated home without user skills or config coming with them.
  - The run never writes to the user's real Codex home.
- [ ] Trigger detection:
  - A command that reads the skill-under-test's `SKILL.md` counts as a trigger, but only if the read completed successfully. A failed read, or a command that merely mentions the path, does not count.
  - A run with no such read counts as not triggered, and a test asserts this.
  - A "failed to load skill" warning makes the run fail, not pass silently.
- [ ] One extra case uses Codex's explicit invocation (`$cowsay`) and asserts the skill triggered. First check, with a recorded transcript, how the pinned Codex loads an explicitly invoked skill. If that does not produce a read of the skill's `SKILL.md`, detect the explicit load another way and document how.
- [ ] The contamination check works for Codex. It is shown to fail on a deliberately contaminated run, with a canary in each discovery location the research notes list for Codex, including the user-level shared skills folder in the OS home.
- [ ] The results file records the Codex CLI version and the model.
- [ ] Recorded Codex transcripts drive unit tests of the parser and trigger detection. These tests run in `just check` without credentials.
- [ ] A live run of `just eval cowsay --agent codex` passes every case. The results are summarised in the completion notes. Any case that cannot pass on Codex for a documented reason is marked as an agent-specific expectation, not deleted.

## Review checkpoints

Use the repo's cross-model adversarial review skill from ticket 01, or the protocol written out there:

- Pick the reviewer by the cross-model rule.
- A reviewer subagent saves its findings to the scratch folder.
- A separate triage subagent checks each finding against the code.
- Apply the valid fixes, rerun `just check`, and record every finding and how it was handled under **Completion notes**.

- **Implementation checkpoint:** before marking done, review the full diff against these acceptance criteria. Pay particular attention to false-positive and false-negative trigger detection, and to isolation leaks.
