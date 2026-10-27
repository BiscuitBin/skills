# 05: Eval harness tracer bullet: cowsay on Claude Code

**What to build:** `just eval cowsay --agent claude` runs cowsay's eval cases against the pinned Claude Code, headless, and writes a results file. There are two kinds of case:

- **Trigger cases:** prompts where the skill should trigger and prompts where it should not.
- **Behaviour cases:** the agent ran the bundled script and showed the cow with the requested text.

Each run happens in a fresh, isolated workspace that only the skill under test can reach, and a contamination check proves that. The harness logic is unit-tested against recorded transcripts, so `just check` covers it without a live agent.

This ticket defines the case schema and the adapter interface that tickets 06, 07 and 08 build on. Agent facts and the contamination risk are in the research notes (`.scratch/foundation/research.md`).

**Blocked by:** 02 (Project-local toolchain and green `just check`), 03 (Cowsay skill passes a spec validator).

**Status:** done

**Agent requirements:** Any implementing agent (Claude Code, Codex or Pi). Authenticated access to the pinned Claude Code CLI is required to capture transcripts and pass the live eval. Codex and Pi live evals are deferred to tickets 06 and 07. Cross-model review is also required.

## Acceptance criteria

**Case schema:**

- [x] The schema extends skill-creator's eval cases with a case kind (trigger or behaviour), an expected-trigger flag, and deterministic assertions such as output contains, output matches, script was run, and skill triggered.
- [x] It includes an assertion that the final message contains the bundled script's exact output for a given input. The harness computes that output by running the script itself. At least one cowsay behaviour case uses it, and unit tests show it failing on altered whitespace, a missing line and wrong text.
- [x] Input files for a case are either staged into the workspace (with a unit test) or explicitly rejected by the schema with a note that they are deferred. They are never silently ignored.
- [x] It is documented in the reference docs, and `just check` validates every skill's eval case files against it, with no agent calls.
- [x] Eval cases live outside the shipped skill's directory, so distribution (ticket 04) can never ship them.

**Adapter interface:**

- [x] The interface is documented. An adapter does the following:
  - prepares an isolated agent home and an isolated user home
  - installs a skill into a workspace, or installs nothing for a baseline
  - runs a prompt headless with a pinned model
  - normalises the agent's event stream into a trace: skills triggered, commands run, final message, CLI version, model, and run status (exit status and whether the stream ended normally)
- [x] The Claude Code adapter implements the interface and detects a trigger from the `Skill` tool call.

**Isolation:**

- [x] Each run gets a fresh git repo as its workspace. The workspace sits inside the gitignored project area, is its own git root, and lives outside the shipped-skills and dev-skills trees.
- [x] The workspace holds only the case's prompt fixtures and the installed skill. Expected outputs, rubrics and other cases stay outside it.
- [x] Each run gets an isolated agent home *and* an isolated user home, so every user-level skill location in the research notes points at an empty, throwaway place. The run never reads skills or config from the user's real homes.
- [x] The repo's own agent instructions and context files never load into an eval run.
- [x] The docs state that the workspace limits discovery, not file access. An agent that browses parent directories can still read repo files, and this is recorded as a known limit.
- [x] Credentials reach the isolated run without user skills or config coming with them.
  - They are limited to what the agent needs to authenticate.
  - They are never written into the workspace or results.
  - They are removed when the run ends, including on timeout or failure.
  - The chosen approach is documented per agent.
  - A test with a fake secret shows it does not appear in the results file or the transcript.
- [x] Contamination check:
  - It proves that only the skill under test was visible, apart from skills built into the pinned agent. Those built-in skills form a recorded allowlist that is identical in the with-skill and baseline arms.
  - Where the agent reports its available skills, the check uses that report. Where it does not, the proof is the redirected homes plus the canary sweep below. The check fails closed only when a discovery location in the research notes can be neither redirected nor canaried.
  - It names what must never appear: the repo's dev skills (from ticket 01), other repo skills, the user's own Claude, Codex and Pi skills, and the repo's agent instructions.
  - It is shown to fail when a canary is planted, one at a time, in each discovery location the research notes list for the agent (user, shared, parent-directory and system locations). This includes a canary instruction in a parent directory's context file.

**Results:**

- [x] Each run writes a results file recording:
  - the case
  - the agent and its CLI version
  - the model
  - start and finish times
  - the trigger outcome
  - each assertion's result
  - the path to the raw transcript
- [x] Each run records whether the agent finished normally, using the exit status and the stream's final event.
  - A run that errored, timed out or ended with a truncated stream is recorded as an infrastructure error. None of its assertions are scored, so a crash can never pass a should-not-trigger case.
  - Unit tests cover a failed authentication, a nonzero exit and a truncated stream.
- [x] The command exits nonzero when any case fails or any run hits an infrastructure error.
- [x] Runs have a timeout and a configurable model, and the model is pinned by default.
- [x] A case filter lets you run a single case.

**Tests and live run:**

- [x] Recorded Claude Code transcripts drive unit tests of the parser, the trigger detection, the assertions and the contamination check. These tests run in `just check` and PR CI without credentials.
- [x] Docs state that live evals need an authenticated agent and are never part of the PR gate.
- [x] A live run of `just eval cowsay --agent claude` passes every case. The results file is attached to the completion notes, or summarised there.

## Review checkpoints

Use the repo's cross-model adversarial review skill from ticket 01, or the protocol written out there:

- Pick the reviewer by the cross-model rule.
- A reviewer subagent saves its findings to the scratch folder.
- A separate triage subagent checks each finding against the code.
- Apply the valid fixes, rerun `just check`, and record every finding and how it was handled under **Completion notes**.

- **Design checkpoint:** before building, write the proposed case schema, adapter interface, isolation approach and credential approach, and get them reviewed. Will Codex and Pi fit the adapter interface (see the research notes)? Can contamination slip through? Does credential handling leak user config or secrets into results?
- **Implementation checkpoint:** before marking done, review the full diff against these acceptance criteria.

## Completion notes

### Implementation and verification

- **Command:** `just eval <skill> --agent claude [--case ID] [--model M] [--timeout S]` runs `python -m skills_tooling.evals run`. `just validate-evals` validates every `evals/*/evals.json` and is part of `just check`. Reference: `docs/reference/evals.md`. Explanation: `docs/explanation/eval-isolation.md`. Decision: ADR 0011.
- **Case schema:** `evals/cowsay/evals.json` sits outside `skills/cowsay/`, so distribution never ships it. It holds 3 should-trigger, 3 should-not-trigger and 2 behaviour cases. Unknown keys are rejected everywhere. A non-empty `files` is rejected with a "staging is deferred" message. `final_contains_script_output` runs the shipped script itself, isolated, and its unit tests fail on altered whitespace, a missing line, wrong text, a freehand cow, joined lines and a missing trailing blank line.
- **`script_ran`:** it needs a python command whose script argument is the script, a CLI-written tool result holding the script's output, and a log entry from the trial's `python3` wrapper for the installed copy. `printf`/`echo`/`cat` of the path, comments, `false && … ; true`, `sh -c` and `-c`/`-m` all fail it.
- **Adapter interface:** `adapter.py`, a `Protocol` with `reports_skills` and `discovery_report_problems`, so Codex and Pi can rest on the preflight and the sweep without changing the shared checker. Claude Code is implemented in `claude_code.py`, and its trigger comes from the `Skill` tool call.
- **Isolation:** each trial gets `.eval-workspaces/<run>/<case>/{workspace,home,tmp,bin}`. The child environment is built from scratch, so the Justfile's shared `CLAUDE_CONFIG_DIR` never reaches it (tested). Instruction files are switched off with `CLAUDE_CODE_DISABLE_CLAUDE_MDS=1`, and the preflight fails closed without it. The process group is killed and checked empty on every exit.
- **Canary sweep:** `tests/evals/test_contamination_canaries.py` runs the pinned CLI against `tests/evals/fake_anthropic.py` in `just check`, without credentials. It found three things:
  - with instruction loading on, the CLI reads `~/.claude/CLAUDE.md` as an ancestor's project instructions;
  - `cc-plugin-agents-md` loads `AGENTS.md` only when no `CLAUDE.md` is found up the tree;
  - nested `<subdir>/.claude/skills` is discovered mid-session.

  The managed-location canary is CI-only (Linux, `CI=true`, passwordless sudo), by the user's choice. **It has not run yet: it first runs in this branch's PR CI.**
- **Credentials:** `CLAUDE_CODE_OAUTH_TOKEN` (`claude setup-token`) reaches only the child's environment. The fake-secret end-to-end test proves it reaches the API (the `Authorization` header) but appears in no results file, transcript or workspace file. Results are scrubbed and reread, and a leaking file is deleted and fails the run.
- **Live run:** `just eval cowsay --agent claude`, run `20261027T021602Z-b0ec`, passed all 8 trials. CLI 2.1.309, model `claude-sonnet-5-5`, contamination passed on every trial. Every should-trigger case triggered and no should-not-trigger case did, and both behaviour cases passed every assertion. `--case no-trigger-cow-facts` (run `20261027T021721Z-35ec`) ran exactly one trial and passed. No token-shaped string (`sk-ant-…`) appears under `eval-results/` or `.eval-workspaces/`. The implementer could not grep for the token's value itself, because it never entered the session. Every trial directory kept only `workspace/`.
- **Fixtures:** three live transcripts (`tests/fixtures/evals/claude/live-*.jsonl`) drive the parser, trigger, assertion and contamination tests. Their paths are placeholders and their rate-limit details are removed. The recorded no-credential auth failure and fake-API transcripts cover run status. Truncated-stream and nonzero-exit cases are derived from them.
- **Writes outside the project:** Claude Code creates its messaging socket at `/tmp/cc-socks/<pid>.sock` and ignores `TMPDIR`. It removes the socket on exit. Recorded per AGENTS.md; nothing else wrote outside the project.
- **Review tooling:** Codex could not review from the project-local home at first. The runner was fixed in `52a464e`, `4b0ccc6` and `1b3734b` (see the design checkpoint).
- **Validation:** `just check` passes with 317 tests, 2 skipped (the CI-only managed canary), strict mypy, lint, lock checks, distribution validation, both skills, the eval suite and the pinned CLI versions. `git status` is clean afterwards.

### Local code review (`code-review` skill, high)

| # | Finding | Verdict | Action |
| --- | --- | --- | --- |
| 1 | One trial's exception lost the whole run | valid | Recorded as that trial's infra error; a missing pinned CLI is a usage error (`97cee59`) |
| 2 | `--model` alias failed every trial | valid | The results record the reported model; the exact-match check was removed |
| 3 | A non-string assertion `type` crashed validation | valid | Reported as a schema problem |
| 4 | Never-appear names matched the trial's own paths | valid | Matched against reported skills only; paths are checked by location |
| 5 | A failed call to a missing skill counted as contamination | valid | Only successful `Skill` calls count |
| 6 | `project=[]` resolved to the repo root | valid | Empty entries ignored |
| 7 | `-X utf8`/`-W` and `env -i` hid the script | valid | Options with values and env options handled |
| 8 | Secret scan read each file once per secret | valid | Read once |
| 9 | The not-scored record was built twice | valid | One `_not_scored` builder |
| 10 | Expected output computed twice per case | valid | Cached |

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

### Implementation checkpoint: cross-model review

- **Implementer:** Claude Code running Claude Opus 5.5 (`claude-opus-5-5`)
- **Reviewer:** Codex `gpt-6-astra` (fallback: no)
- **Reviewed:** `main...03c216e`, against these acceptance criteria
- **Findings:** `ai_tmp/review-20261027T022445Z-codex.md` · **Triage:** `ai_tmp/triage-impl-05.md` (fresh separate subagent)

| # | Severity | Finding | Verdict | Action |
| --- | --- | --- | --- | --- |
| 1 | high | The managed-canary cleanup ran `rm -rf /etc/claude-code` | valid | Skips if `/etc/claude-code` exists; removes only what it created (`09620a7`) |
| 2 | medium | Expected-output computation could hang outside the trial timeout | valid | stdin closed, 30-second timeout |
| 3 | medium | Contamination passed with missing built-ins and no plugin report | valid in part | A reporting agent's missing plugin report fails closed. Missing built-ins: invalid, because the allowlist is one recorded constant per version and `schedule` is listed only under OAuth |
| 4 | medium | The exact-output assertion accepted a missing trailing blank line | valid | `removesuffix` |
| 5 | medium | The shared checker rejected the documented non-reporting adapter path | valid | `reports_skills` and `discovery_report_problems` on the adapter; the Claude debug-log check moved into `claude_code.py` |

### Fixes re-review

- **Reviewer:** Codex `gpt-6-astra` (fallback: no)
- **Reviewed:** `03c216e..09620a7`, with the findings and triage above as context
- **Findings:** `ai_tmp/review-20261027T023309Z-codex.md` · **Triage:** `ai_tmp/triage-impl-05-fixes.md` (fresh separate subagent)

| # | Severity | Finding | Verdict | Action |
| --- | --- | --- | --- | --- |
| 1 | medium (triaged low) | The script timeout left the script's descendants running | valid | Runs through `run_isolated` in its own process group, with a regression test (`55f370a`) |
| 2 | low | A scoring failure dropped the trial's metadata and contamination result | valid | Scoring is guarded; the evidence is kept and the assertions are left unscored, with a regression test |

**Follow-ups:**

- Ticket 06/07: Codex and Pi set `reports_skills = False` (or report), supply `discovery_locations` and `context_isolation`, and keep file credentials in the per-trial agent home.
- Ticket 08: baselines (`install_skill(None, …)` and `check(baseline=True)` exist and are unit-tested) and rubric `expectations`.
- Input-file staging stays deferred; the schema rejects it.
- Check the managed-canary result in this branch's PR CI.
