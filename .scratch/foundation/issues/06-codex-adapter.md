# 06: Codex adapter

**What to build:** `just eval cowsay --agent codex` runs the same cowsay eval cases against the pinned Codex, headless, through the adapter interface from ticket 05. They get the same isolation guarantees and the same results format. Codex has no documented trigger event, so a trigger means the agent read the skill's `SKILL.md`. Codex facts are in the research notes (`.scratch/foundation/research.md`).

**Blocked by:** 05 (Eval harness tracer bullet: cowsay on Claude Code).

**Status:** done

**Agent requirements:** Any implementing agent (Claude Code, Codex or Pi). Authenticated access to the pinned Codex CLI is required to capture transcripts and pass the live eval; the implementer need not be Codex. Cross-model review is also required.

## Acceptance criteria

- [x] The Codex adapter implements the ticket 05 interface without changing the case schema. If the interface has to change, the Claude Code adapter and its tests are updated in the same change.
- [x] The run uses an isolated Codex home, ignores user config, and is ephemeral.
  - Credentials reach the isolated home without user skills or config coming with them.
  - The run never writes to the user's real Codex home.
- [x] Trigger detection:
  - A command that reads the skill-under-test's `SKILL.md` counts as a trigger, but only if the read completed successfully. A failed read, or a command that merely mentions the path, does not count.
  - A run with no such read counts as not triggered, and a test asserts this.
  - A "failed to load skill" warning makes the run fail, not pass silently.
- [x] One extra case uses Codex's explicit invocation (`$cowsay`) and asserts the skill triggered. First check, with a recorded transcript, how the pinned Codex loads an explicitly invoked skill. If that does not produce a read of the skill's `SKILL.md`, detect the explicit load another way and document how.
- [x] The contamination check works for Codex. It is shown to fail on a deliberately contaminated run, with a canary in each discovery location the research notes list for Codex, including the user-level shared skills folder in the OS home.
- [x] The results file records the Codex CLI version and the model.
- [x] Recorded Codex transcripts drive unit tests of the parser and trigger detection. These tests run in `just check` without credentials.
- [x] A live run of `just eval cowsay --agent codex` passes every case. The results are summarised in the completion notes. Any case that cannot pass on Codex for a documented reason is marked as an agent-specific expectation, not deleted.

## Review checkpoints

Use the repo's cross-model adversarial review skill from ticket 01, or the protocol written out there:

- Pick the reviewer by the cross-model rule.
- A reviewer subagent saves its findings to the scratch folder.
- A separate triage subagent checks each finding against the code.
- Apply the valid fixes, rerun `just check`, and record every finding and how it was handled under **Completion notes**.

- **Implementation checkpoint:** before marking done, review the full diff against these acceptance criteria. Pay particular attention to false-positive and false-negative trigger detection, and to isolation leaks.

## Completion notes

### What was built

- `src/skills_tooling/evals/codex.py`, the Codex adapter. `just eval cowsay --agent codex` runs the shared cases against the pinned `codex-cli 0.163.0` native binary, with `gpt-5.6-terra` as the default model (the user asked for "terra"; it is the only terra in the CLI's bundled catalog).
- **Interface change:** `Adapter` gained `executable`, `read_credentials`, `secrets` and `trial_secrets` (none for Claude Code). The Claude Code adapter implements them with unchanged behaviour, and its tests pass unchanged. The case schema is unchanged.
- **Credential:** only `auth.json` from the project's `CODEX_HOME` (`.tools/agent-homes/codex`) is copied, mode 0600, into each trial's `CODEX_HOME`. Its long string values are scrubbed and swept, and so is a login Codex refreshes mid-trial, which the runner reads back after the run and again before teardown, on every path. The user's `~/.codex` is never read or written. `tests/evals/test_codex_adapter.py` shows that the caller's `CODEX_HOME` is never written, and that the caller's skills, `AGENTS.md` and `config.toml` never reach the model.
- **Isolation flags:**
  - `--ephemeral --ignore-user-config --ignore-rules --sandbox workspace-write`
  - `allow_login_shell=false`: a login shell's `path_helper` hid the trial's `python3` wrapper.
  - `project_doc_max_bytes=0`
  - `--disable plugins remote_plugin apps`: Codex syncs the account's remote plugins otherwise.
- **Trigger detection:**
  - A completed `command_execution` counts when it reads `<skills dir>/<skill>/SKILL.md` with a reader program (not `awk`), joined only by `&&`, exits 0 and prints. Reads in other shapes (`||`, `;`, pipes, `2>&1`, awk) rest on Codex's own event.
  - So does Codex's own `codex.skill_invocation` telemetry event (`implicit` for a read, `explicit` for a `$skill` mention).
  - `failed to load skill` makes the run an `infra_error`.
  - Fixtures cover each case: a should-trigger read, a `cd` read, no read, a failed read, a mention-only command, a read that never completed, masked reads, a broken skill, a failed login and a truncated stream.
- **Explicit invocation:**
  - Checked with the real CLI against a fake API. `$name` makes Codex inject `SKILL.md` into the request as a `<skill>` message; no command reads it, and the JSONL shows nothing. It is detected by the `invocation_type="explicit"` event that `RUST_LOG=warn,codex_otel.log_only=info` puts on stderr (`fake-explicit` fixture). Documented in `docs/reference/evals.md`.
  - Codex names the shipped skill `cowsay:cowsay`, because it reads `skills/cowsay/.claude-plugin/plugin.json` (which `npx skills` also installs for Codex). A bare `$cowsay` loads nothing explicitly, so the new case `trigger-explicit-invocation` uses `$cowsay:cowsay`, as the user chose. It runs on Claude Code too.
- **Contamination:**
  - Codex does not report its skills (`reports_skills = False`), so the adapter reads every location after the run: `<workspace>/.agents/skills`, `<home>/.agents/skills`, `$CODEX_HOME/skills` and `.system`, plugin directories, `$CODEX_HOME/AGENTS.md` and `AGENTS.override.md`, and `/etc/codex`.
  - `tests/evals/test_codex_contamination.py` plants a canary in each and shows the check fails.
  - Finding: `project_doc_max_bytes=0` does not suppress the global `$CODEX_HOME/AGENTS.md`, which the check therefore requires to be absent.
- **Results:** `cli_version` and `model` come from Codex's `codex.conversation_starts` event, and `credential_env` is `["CODEX_HOME"]`.
- **Tests without credentials:** the real pinned Codex runs against a fake Responses API (`tests/evals/fake_openai.py`), and the parser tests use the recorded fixtures in `tests/fixtures/evals/codex/`. All run in `just check`.

### Code review (`/code-review`, Claude)

| # | Finding | Verdict | Action |
| --- | --- | --- | --- |
| 1 | `..`, globs and variables before `SKILL.md` were recorded as skill names | valid | fixed in d4dff54: normalised paths, unplaceable names skipped |
| 2 | Refreshed ChatGPT tokens are not scrubbed | valid | documented, then fixed in 4d4c816 (cross-model finding 4) |
| 3 | Short `auth.json` strings would become scrub needles | valid | fixed in d4dff54: 20-character minimum |
| 4 | `failed to load skill` matched inside telemetry (tool output) | valid | fixed in d4dff54: only Codex's own log lines count |
| 5 | Multi-line telemetry continuation lines reached the stored stderr | valid | fixed in d4dff54: whole telemetry records dropped, log target parsed past span prefixes |
| 6 | The Codex-only `$cowsay:cowsay` prompt sits in the shared suite | out of scope | the user's choice; it runs on Claude Code as an ordinary prompt |
| 7 | The repo-skills check counts entries but does not name them | low, not fixed | the preflight checks the name before the run |
| 8 | `auth.json` was briefly world-readable | valid | fixed in d4dff54: created 0600 |
| 9 | Helpers duplicated from `claude_code.py` | low, not fixed | kept local, to leave the Claude adapter untouched |
| 10 | `RunSettings.secrets` re-parses `auth.json` on each access | low, not fixed | negligible cost |

### Cross-model review

- **Implementer:** Claude Code running Claude Opus 5.5 (`claude-opus-5-5`)
- **Reviewer:** codex `gpt-6-astra` (fallback: no). The first attempt was rejected (exit 4): Codex initialised its own home under `.tools/agent-homes/codex/` on its first run in this worktree, which the reviewer's snapshot counts as a change. The rerun was clean.
- **Reviewed:** `03dadcf...d4dff54`
- **Findings:** `ai_tmp/review-20261027T221335Z-codex.md` · **Triage:** `ai_tmp/triage-20261027-06.md`

| # | Severity | Finding | Verdict | Action |
| --- | --- | --- | --- | --- |
| 1 | high | Reads masked by `\|\|`, `;` or a pipe count as triggers | valid | fixed in 4d4c816: only `&&` may join a counted read |
| 2 | high (triage: low) | `awk -v x=…/SKILL.md` counts as a read | valid | fixed in 4d4c816: `name=value` words skipped |
| 3 | medium | Any `<name>/SKILL.md`, such as `/tmp/cowsay/SKILL.md`, counts | valid | narrowed in 4d4c816: must sit in a skills directory. A same-named skill in another skills directory still counts (round two, finding 3) |
| 4 | high (triage: medium) | Refreshed tokens escape the scrub and the sweep | valid | fixed in 4d4c816: read back before teardown, added to the trial's secrets |
| 5 | high | The live run has not happened | out of scope | pending; see below |

#### Round two

- **Reviewer:** codex `gpt-6-astra` (fallback: no)
- **Reviewed:** `d4dff54...42d1a65`, the round-one fixes
- **Findings:** `ai_tmp/review-20261027T225854Z-codex.md` · **Triage:** `ai_tmp/triage-20261027-06-round2.md`

| # | Severity | Finding | Verdict | Action |
| --- | --- | --- | --- | --- |
| 1 | high (triage: medium) | `\|\|` or `;` at the end of a line was not split, so a masked read still counted | valid | fixed: the shared lexer reads an operator run such as `\|\|\n` as its operator. `script_ran` gains the same split |
| 2 | high (triage: low) | `awk -F <path>` and `awk 'BEGIN{exit}' <path>` counted as reads | valid | fixed: `awk` is no longer a reader; awk reads rest on Codex's event |
| 3 | medium (triage: low) | A same-named skill in any `*skills` directory counts as the skill under test | valid | accepted and documented: the location checks rule out a second copy, and narrowing the rule would mean counting failed Skill calls in the contamination check, which changes Claude Code's semantics |
| 4 | medium (triage: low) | A refreshed token was missed when reading the run's evidence raised | valid | fixed: `Adapter.trial_secrets`, which the runner reads after the run and in `finally` before teardown. It replaces `RawRun.secrets` |

**Follow-ups:**

- `review.py` treats a reviewer's first-run initialisation of its own home as a worktree change. Excluding `.tools/agent-homes/<reviewer>/` startup files would avoid the false rejection.
- With the stricter trigger rule, a masked read of a canary skill is seen only through Codex's own event. The location check still catches the canary itself.
- The end-to-end tests use Codex's `workspace-write` sandbox. Their first Linux CI run, on `ubuntu-24.04`, failed the trigger-command and version/key tests in `test_codex_adapter.py`. A debug run ([40614691505](https://github.com/BiscuitBin/skills/actions/runs/40614691505), prints added in `8fe4d12` and removed by `143d61f`) showed the cause: the runner sets `kernel.apparmor_restrict_unprivileged_userns=1`, so bubblewrap fails with `loopback: Failed RTM_NEWADDR: Operation not permitted` and Codex denies every sandboxed command. Naming the trial's `TMPDIR` as a Codex writable root (`313e2f7`) had no effect and was reverted (`ac1b808`). CI now lifts the restriction with `sysctl` before the gate, and the gate also runs on `macos-15`, where the sandbox is Seatbelt. Run [40777692982](https://github.com/BiscuitBin/skills/actions/runs/40777692982) at `882b2f2` passed both jobs, with `test_codex_adapter.py` 7/7 on each and no `bwrap: loopback` or `sandbox violation` line in either log: [`ubuntu-24.04`](https://github.com/BiscuitBin/skills/actions/runs/40777692982/job/123131124189) 411 passed, 1 skipped; [`macos-15`](https://github.com/BiscuitBin/skills/actions/runs/40777692982/job/123131123735) 410 passed, 2 skipped. The skips are platform-bound: the case-insensitive filesystem test on Linux, the two Linux-only managed-skill canaries on macOS. The two parser gaps the run exposed, a denied command missing from the trace and a trigger recorded with no read, are ticket 13.
- A read with `2>&1` is not counted by the text rule, because the lexer sees an `&`; it rests on Codex's implicit event.
- The shared suite's `trigger-explicit-invocation` (`$cowsay:cowsay`) has not been run on Claude Code yet.

### Live run

The user ran `just eval cowsay --agent codex` at 4d4c816 (run `20261027T224559Z-1535`, 2026-10-27 22:45:59 to 22:46:58 UTC). It passed all 9 cases, on `codex-cli 0.163.0` with `gpt-5.6-terra`. `credential_env` was `["CODEX_HOME"]`, every trial's contamination check passed, and no secret was found. No case needed an agent-specific expectation.

| Case | Trigger (expected → actual) | Evidence |
| --- | --- | --- |
| trigger-talking-cow, trigger-cowsay-output, trigger-cow-speech-bubble | true → true | `sed -n '1,240p' .agents/skills/cowsay/SKILL.md`, then the script |
| trigger-explicit-invocation | true → true | no `SKILL.md` read: Codex injected it, and the script ran directly. The trigger rests on the `explicit` event |
| no-trigger-cow-facts, no-trigger-ascii-cat, no-trigger-cow-haiku | false → false | no commands |
| behaviour-ship-it, behaviour-wrapped-text | true → true | all 4 assertions passed in each, including `script_ran` and `final_contains_script_output` |

Four live transcripts are fixtures in `tests/fixtures/evals/codex/live-*.jsonl`, driving tests in `tests/evals/test_codex_parser.py`. `results.json` keeps no stderr events, so each `.log` holds only the `conversation_starts` line, rebuilt from the `cli_version` and `model` the run recorded. The explicit-case test pairs the live transcript with the event line recorded in `fake-explicit.log`.
