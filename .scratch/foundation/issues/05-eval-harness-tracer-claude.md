# 05: Eval harness tracer bullet: cowsay on Claude Code

**What to build:** `just eval cowsay --agent claude` runs cowsay's eval cases against the pinned Claude Code, headless, and writes a results file. There are two kinds of case:

- **Trigger cases:** prompts where the skill should trigger and prompts where it should not.
- **Behaviour cases:** the agent ran the bundled script and showed the cow with the requested text.

Each run happens in a fresh, isolated workspace that only the skill under test can reach, and a contamination check proves that. The harness logic is unit-tested against recorded transcripts, so `just check` covers it without a live agent.

This ticket defines the case schema and the adapter interface that tickets 06, 07 and 08 build on. Agent facts and the contamination risk are in the research notes (`.scratch/foundation/research.md`).

**Blocked by:** 02 (Project-local toolchain and green `just check`), 03 (Cowsay skill passes a spec validator).

**Status:** ready-for-agent

**Agent requirements:** Any implementing agent (Claude Code, Codex or Pi). Authenticated access to the pinned Claude Code CLI is required to capture transcripts and pass the live eval. Codex and Pi live evals are deferred to tickets 06 and 07. Cross-model review is also required.

## Acceptance criteria

**Case schema:**

- [ ] The schema extends skill-creator's eval cases with a case kind (trigger or behaviour), an expected-trigger flag, and deterministic assertions such as output contains, output matches, script was run, and skill triggered.
- [ ] It includes an assertion that the final message contains the bundled script's exact output for a given input. The harness computes that output by running the script itself. At least one cowsay behaviour case uses it, and unit tests show it failing on altered whitespace, a missing line and wrong text.
- [ ] Input files for a case are either staged into the workspace (with a unit test) or explicitly rejected by the schema with a note that they are deferred. They are never silently ignored.
- [ ] It is documented in the reference docs, and `just check` validates every skill's eval case files against it, with no agent calls.
- [ ] Eval cases live outside the shipped skill's directory, so distribution (ticket 04) can never ship them.

**Adapter interface:**

- [ ] The interface is documented. An adapter does the following:
  - prepares an isolated agent home and an isolated user home
  - installs a skill into a workspace, or installs nothing for a baseline
  - runs a prompt headless with a pinned model
  - normalises the agent's event stream into a trace: skills triggered, commands run, final message, CLI version, model, and run status (exit status and whether the stream ended normally)
- [ ] The Claude Code adapter implements the interface and detects a trigger from the `Skill` tool call.

**Isolation:**

- [ ] Each run gets a fresh git repo as its workspace. The workspace sits inside the gitignored project area, is its own git root, and lives outside the shipped-skills and dev-skills trees.
- [ ] The workspace holds only the case's prompt fixtures and the installed skill. Expected outputs, rubrics and other cases stay outside it.
- [ ] Each run gets an isolated agent home *and* an isolated user home, so every user-level skill location in the research notes points at an empty, throwaway place. The run never reads skills or config from the user's real homes.
- [ ] The repo's own agent instructions and context files never load into an eval run.
- [ ] The docs state that the workspace limits discovery, not file access. An agent that browses parent directories can still read repo files, and this is recorded as a known limit.
- [ ] Credentials reach the isolated run without user skills or config coming with them.
  - They are limited to what the agent needs to authenticate.
  - They are never written into the workspace or results.
  - They are removed when the run ends, including on timeout or failure.
  - The chosen approach is documented per agent.
  - A test with a fake secret shows it does not appear in the results file or the transcript.
- [ ] Contamination check:
  - It proves that only the skill under test was visible, apart from skills built into the pinned agent. Those built-in skills form a recorded allowlist that is identical in the with-skill and baseline arms.
  - Where the agent reports its available skills, the check uses that report. Where it does not, the proof is the redirected homes plus the canary sweep below. The check fails closed only when a discovery location in the research notes can be neither redirected nor canaried.
  - It names what must never appear: the repo's dev skills (from ticket 01), other repo skills, the user's own Claude, Codex and Pi skills, and the repo's agent instructions.
  - It is shown to fail when a canary is planted, one at a time, in each discovery location the research notes list for the agent (user, shared, parent-directory and system locations). This includes a canary instruction in a parent directory's context file.

**Results:**

- [ ] Each run writes a results file recording:
  - the case
  - the agent and its CLI version
  - the model
  - start and finish times
  - the trigger outcome
  - each assertion's result
  - the path to the raw transcript
- [ ] Each run records whether the agent finished normally, using the exit status and the stream's final event.
  - A run that errored, timed out or ended with a truncated stream is recorded as an infrastructure error. None of its assertions are scored, so a crash can never pass a should-not-trigger case.
  - Unit tests cover a failed authentication, a nonzero exit and a truncated stream.
- [ ] The command exits nonzero when any case fails or any run hits an infrastructure error.
- [ ] Runs have a timeout and a configurable model, and the model is pinned by default.
- [ ] A case filter lets you run a single case.

**Tests and live run:**

- [ ] Recorded Claude Code transcripts drive unit tests of the parser, the trigger detection, the assertions and the contamination check. These tests run in `just check` and PR CI without credentials.
- [ ] Docs state that live evals need an authenticated agent and are never part of the PR gate.
- [ ] A live run of `just eval cowsay --agent claude` passes every case. The results file is attached to the completion notes, or summarised there.

## Review checkpoints

Use the repo's cross-model adversarial review skill from ticket 01, or the protocol written out there:

- Pick the reviewer by the cross-model rule.
- A reviewer subagent saves its findings to the scratch folder.
- A separate triage subagent checks each finding against the code.
- Apply the valid fixes, rerun `just check`, and record every finding and how it was handled under **Completion notes**.

- **Design checkpoint:** before building, write the proposed case schema, adapter interface, isolation approach and credential approach, and get them reviewed. Will Codex and Pi fit the adapter interface (see the research notes)? Can contamination slip through? Does credential handling leak user config or secrets into results?
- **Implementation checkpoint:** before marking done, review the full diff against these acceptance criteria.

## Completion notes

### Design checkpoint: cross-model review

- **Implementer:** Claude Code running Claude Opus 5.5 (`claude-opus-5-5`)
- **Reviewer:** Codex `gpt-6-astra` (fallback: no)
- **Reviewed:** design proposal `ai_tmp/design-05.md` at base `005bbfb`, before any harness code
- **Findings:** `ai_tmp/review-20261026T233337Z-codex.md` · **Triage:** `ai_tmp/triage-design-05.md` (fresh separate subagent)
- **Review runs:** the first four runs were rejected (exit 4) because Codex writes runtime state into its project-local home. None of the rejected output was triaged. The runner was fixed in three commits before the fifth run succeeded: `52a464e` ignores Codex's caches, logs, temporary files and state databases; `4b0ccc6` ignores its SQLite maintenance lock; `1b3734b` disables Codex plugins and apps for the read-only reviewer, because Codex updated a curated remote plugin mid-review. Codex config, auth, instructions, memories, plugins and skills stay monitored.

| # | Severity | Finding | Verdict | Action |
| --- | --- | --- | --- | --- |
| 1 | high | `script_ran` passes on a command that only names the script path | valid | Design §5: `script_ran` needs a python-interpreter command shape, a tool_result containing the harness-computed output, and an entry in the trial `python3` wrapper's exec log. Negative tests cover `printf`/`echo`/`cat`, comments, `false && … ; true` and quoted arguments. |
| 2 | high | Canary sweep cannot establish nested and managed discovery coverage | valid | Probed: nested `<ws>/sub/.claude/skills` is discovered mid-session after a `Read` in `sub/` (debug `Dynamically discovered`, `system/commands_changed`). The visible set now unions init skills, `commands_changed` and `Skill` calls; the workspace inventory is checked before each run; the nested canary is exercised mid-session. The managed location cannot be redirected, so it is `reported` on every trial and canaried by a CI-only sudo test (user's decision). The injectable system root is a checker unit test only. |
| 3 | medium | A normal exit can leave credential-bearing descendants alive | valid | The process group is killed and verified empty on every path, normal exit included, with a background-`sleep` test. Probed: the pinned CLI already strips `CLAUDE_CODE_OAUTH_TOKEN` from Bash children; `CLAUDE_CODE_SUBPROCESS_ENV_SCRUB=1` added as a second guard. A `setsid` escape is documented as a limit. |
