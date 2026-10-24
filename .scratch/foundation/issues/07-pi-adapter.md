# 07: Pi adapter

**What to build:** `just eval cowsay --agent pi` runs the same cowsay eval cases against the project-pinned Pi, headless, through the adapter interface from ticket 05. They get the same isolation guarantees and the same results format. Pi facts are in the research notes (`.scratch/foundation/research.md`). In particular, project skills load in JSON mode only when the run is explicitly approved, and a trigger shows up as a read of the skill's `SKILL.md`.

**Blocked by:** 05 (Eval harness tracer bullet: cowsay on Claude Code).

**Status:** ready-for-agent

**Agent requirements:** Any implementing agent (Claude Code, Codex or Pi). Access to the pinned Pi CLI with authenticated access to its selected provider and model is required to capture transcripts, verify dev skill discovery and pass the live eval; the implementer need not be Pi. Cross-model review is also required.

## Acceptance criteria

- [ ] The Pi adapter implements the ticket 05 interface without changing the case schema. If the interface has to change, every existing adapter and its tests are updated in the same change.
- [ ] Pi runs in JSON mode with its agent directory pointed at an isolated location.
  - Project skills are approved for the run.
  - Credentials and the provider/model choice reach the isolated run without user skills or config coming with them.
  - The run never writes to the user's real Pi agent directory.
- [ ] The Pi provider and model are set explicitly. Both are recorded in the results file along with the Pi CLI version.
- [ ] Trigger detection:
  - A read-tool call on the skill-under-test's `SKILL.md` counts as a trigger, but only if the read completed successfully. A failed read, or a command that merely mentions the path, does not count.
  - A run with no such read counts as not triggered, and a test asserts this.
  - Explicit invocation is detected separately. Pi expands the skill command itself and puts the skill body into the user message, so no read-tool call happens. The adapter recognises that expansion in the event stream, and a recorded transcript of an explicit invocation tests it. Check this against the pinned Pi.
- [ ] One extra case uses Pi's explicit skill invocation and asserts the skill triggered.
- [ ] The contamination check works for Pi. It is shown to fail on a deliberately contaminated run, with a canary in each discovery location the research notes list for Pi, including the user-level shared skills folder in the OS home and a parent directory's shared skills folder.
- [ ] Recorded Pi transcripts drive unit tests of the parser and trigger detection. These tests run in `just check` without credentials.
- [ ] A live run of `just eval cowsay --agent pi` passes every case. The results are summarised in the completion notes. Any case that cannot pass on Pi for a documented reason is marked as an agent-specific expectation, not deleted.
- [ ] The ticket 01 dev skill's discovery under Pi is verified now that Pi is runnable, or the reason it can't be is recorded.

## Review checkpoints

Use the repo's cross-model adversarial review skill from ticket 01, or the protocol written out there:

- Pick the reviewer by the cross-model rule.
- A reviewer subagent saves its findings to the scratch folder.
- A separate triage subagent checks each finding against the code.
- Apply the valid fixes, rerun `just check`, and record every finding and how it was handled under **Completion notes**.

- **Implementation checkpoint:** before marking done, review the full diff against these acceptance criteria. Pay particular attention to the project-trust approval scope, trigger detection accuracy, and isolation leaks.
