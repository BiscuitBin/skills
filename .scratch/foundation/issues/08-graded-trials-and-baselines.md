# 08: Graded trials and baselines

**What to build:** An eval run can measure whether a skill actually helps:

- each case runs several times (trials)
- the same cases also run without the skill (a baseline)
- an LLM grader scores each run against rubric expectations
- a benchmark summarises trigger rate, pass rate, mean ± stddev and the delta against the baseline

Grading output follows skill-creator's shapes, described in the research notes (`.scratch/foundation/research.md`). This builds on the ticket 05 harness and works with every adapter that exists when it runs. Claude Code is the minimum.

**Blocked by:** 05 (Eval harness tracer bullet: cowsay on Claude Code).

**Status:** done

**Agent requirements:** Any implementing agent (Claude Code, Codex or Pi). Authenticated Claude Code access and access to the configured grader model are required for the live benchmark. The grader defaults to Opus 5.5 (`claude-opus-5-5`) but is configurable; this does not constrain the implementing agent. Cross-model review is also required.

## Acceptance criteria

**Trials and baselines:**

- [x] `just eval` accepts a trial count and a baseline switch. A dry-run mode prints the planned number of agent and grader calls before anything is spent.
- [x] A baseline run uses the same isolation as a with-skill run but installs no skill. The contamination check proves no skill was visible apart from the pinned agent's built-in skills, using the same recorded allowlist as the with-skill arm (ticket 05).

**Grader:**

- [x] Cases can carry rubric expectations alongside their deterministic assertions.
- [x] The grader writes one grading file per run, shaped like skill-creator's, with each expectation's text, verdict and evidence.
- [x] The grader model is configurable and defaults to Opus 5.5 (`claude-opus-5-5`). The model used is recorded with the results.
- [x] The grader judges rubric expectations from the run's final message and output files, with skill calls and skill paths removed, so it cannot tell which arm it is grading. Any expectation that needs the full transcript is marked unblinded in the results.
- [x] The grader treats graded material as data, not instructions.

**Benchmark:**

- [x] For each agent and case, the benchmark reports:
  - trigger accuracy: the share of trials whose trigger outcome matched the case's expectation
  - deterministic pass rate
  - graded pass rate
  - mean ± stddev across trials
  - the delta between with-skill and baseline, computed over outcome assertions and rubric expectations only. Skill-use assertions (skill triggered, script was run) are reported separately and shown as not applicable for the baseline.
- [x] It records the agent CLI versions, the run models, the grader model, the repo commit and whether the tree was dirty, and a content hash of the skill and of its eval cases and rubric.

**Tests and live run:**

- [x] The aggregation maths and the grader-output parsing are unit-tested against fixtures, including edge cases: one trial, all trials failing, a missing grading file, and a graded output that tells the grader to pass everything. That last one is either rejected by grader-output validation or marked failed. These tests run in `just check` without credentials.
- [x] A live run of cowsay on Claude Code (several trials, with baseline) produces a benchmark, summarised in the completion notes. If the outcome delta is not positive, say so and explain why. Do not change cases or rubrics just to get a positive delta.

## Review checkpoints

Use the repo's cross-model adversarial review skill from ticket 01, or the protocol written out there:

- Pick the reviewer by the cross-model rule.
- A reviewer subagent saves its findings to the scratch folder.
- A separate triage subagent checks each finding against the code.
- Apply the valid fixes, rerun `just check`, and record every finding and how it was handled under **Completion notes**.

- **Design checkpoint:** before building, write the proposed grading schema, rubric format, grader prompt and statistics (how small trial counts, flaky triggers and grader errors are treated), and get them reviewed. Can the grader be biased or gamed? Are the statistics honest at low trial counts?
- **Implementation checkpoint:** before marking done, review the full diff against these acceptance criteria.

## Completion notes

### Live run

The user ran `just eval cowsay --agent claude --trials 10 --baseline` in their own terminal, holding the token. The run was `20261031T183632Z-1aef`, from 18:36 to 18:49 UTC on 2026-10-31, and the overall result was `passed: true`.

**Provenance** (`benchmark.json`):

| Field | Value |
| --- | --- |
| Commit | 226d7b7 |
| Dirty | false |
| Agent CLI | Claude Code 2.1.309 |
| Run model | `claude-sonnet-5-5` |
| Grader | `claude-opus-5-5`, requested and reported, through CLI 2.1.309 |
| `skill_sha256` | `b505fdd6…` |
| `evals_sha256` | `50a3864a…` |
| `grader_prompt_sha256` | `85c2b2d6…` |

**Health:**

- There were 110 trials: 90 with the skill and 20 in the baseline.
- Every trial ended `ok`. None was contaminated and none had a secret found.
- The 40 gradings had no grader errors, no invalid replies, no rejections and no arm disclosures.
- The `order` field runs from 0 to 109 and alternates the arms each trial.
- The `_grader/` directories were removed after grading.
- A search for `sk-ant-` over `eval-results/<run>/` and `.eval-workspaces/<run>/`, binary files included, found nothing.
- The 7 trigger-only cases were skipped in the baseline, as designed. So the delta rests on the 2 behaviour cases.

**Results**, as means over 10 trials per arm:

| Case | Arm | Trigger | Skill use | Deterministic | Graded | Outcome |
| --- | --- | --- | --- | --- | --- | --- |
| behaviour-ship-it | skill | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 |
| behaviour-ship-it | baseline | n/a | n/a | 0.40 ± 0.21 | 1.00 ± 0.00 | 0.76 ± 0.08 |
| behaviour-wrapped-text | skill | 1.00 | 1.00 | 1.00 | 1.00 | 1.00 |
| behaviour-wrapped-text | baseline | n/a | n/a | 0.05 ± 0.16 | 0.50 ± 0.45 | 0.32 ± 0.30 |

- Trigger accuracy was 1.00 on all 9 cases (90 of 90), so no trigger was flaky.
- Pooled over both cases, the deltas (skill − baseline) are:
  - deterministic: +0.78
  - graded: +0.25
  - outcome: +0.46

**What the delta does and doesn't show.** The delta is positive, but it is smaller than the deterministic number suggests, and it depends on the case:

- **The deterministic delta partly measures use of the script, not quality.** `final_contains_script_output` requires the exact bytes that the skill's script produces. A baseline cow drawn by hand can look right and still fail it. That check failed in all 20 baseline trials. That accounts for most of the deterministic delta.
- **On `behaviour-ship-it`, the rubric doesn't discriminate.** The graded delta is 0.00. All 10 baseline trials found no `cowsay` binary, drew the cow by hand, and passed all three expectations. The benchmark flags all three expectations as non-discriminating. For a short single-line message, the skill adds nothing a grader can see.
- **On `behaviour-wrapped-text`, the skill helps.** The graded delta is +0.50. In 4 of 10 baseline trials (6, 7, 9 and 10), the agent stopped to ask whether to install `cowsay` and drew nothing, so those trials scored 0/3. Of the 6 baseline trials that drew a cow, 3 (trials 2, 3 and 8) failed at least one expectation. They either didn't wrap the bubble or split a word. The skill arm scored 3/3 in every trial.
- **The spreads are descriptive.** There is no significance test, and baseline variance on wrapped-text is high (± 0.45).
- **The rubric was frozen before the run and has not been changed since.** The non-discriminating `behaviour-ship-it` expectations are a finding for whoever next edits the cases, not something to fix here.
- **Blinding held, but only partly.** No grading disclosed the arm. However, several baseline grader notes say the agent "reported that cowsay was not installed". The outcome itself reveals the arm, which is the residual risk ADR 0012 records.

**Writes outside the project.** Two baseline trials of `behaviour-wrapped-text` installed the PyPI `cowsay` package into the host's `/tmp`:

- trial 1: `pip3 install --target /tmp/cowsay-pkg`
- trial 5: `python3 -m venv /tmp/cowvenv`

The Claude Code adapter runs with `--permission-mode dontAsk --allowedTools Skill Read Bash` (ticket 05), so its Bash can write anywhere the user can. `TMPDIR` points into the trial, but a literal `/tmp` path bypasses it. Trial 8 used `mktemp -d` and stayed inside the trial. Both directories are still on the host. No later trial in this run used them, but a later baseline trial could find them. This is recorded per AGENTS.md. Confining the adapter's Bash is a follow-up below. Before this run, nothing had triggered it: only the baseline arm, with no skill installed, goes looking for a tool to install.

### Toolchain

The host's just (1.59.0) and uv (0.13.6) were newer than the repo's pins, so the pins were bumped to match (227e35f): `pyproject.toml`, the `Justfile` version gate, the README table and CI.

### Cross-model review: design checkpoint

- **Implementer:** Claude Code running `claude-opus-5-5`
- **Reviewer:** Codex `gpt-6-astra` (fallback: no). The first run was rejected (exit 4) because Codex wrote its home setup files into the worktree on first start; the rerun was clean.
- **Reviewed:** `.scratch/foundation/design/08-grading.md` at 7572a1a
- **Findings:** `ai_tmp/review-20261030T234406Z-codex.md` · **Triage:** `ai_tmp/triage-20261030T2350Z-design.md`

| # | Severity | Finding | Verdict | Action |
| --- | --- | --- | --- | --- |
| 1 | high | The agent's prose can name the arm, but the expectation is still labelled blinded | valid (medium) | Fixed in 6a1d040: a deterministic disclosure check records `arm_disclosed` and its matches, counted per arm and noted on graded deltas; §7 and §8 reworded |
| 2 | high | A malformed grader reply is excluded, so material that breaks the reply removes its own trial | valid (medium) | Fixed in 6a1d040: `invalid_reply` counts as failed; only a call with no reply is a `grader_error` (ADR 0012) |
| 3 | medium | An empty or whitespace-only quote satisfies the quote rule | valid | Fixed in 6a1d040: the quote must be nonempty after whitespace normalisation |
| 4 | medium | Three different rules say which denominators a grader error drops | valid | Fixed in 6a1d040: one rule, graded and outcome rates only |
| 5 | medium | The skill arm always runs first, confounding arm with order | valid | Fixed in 6a1d040: the order alternates each trial, and each trial records `order` |

### Cross-model review: implementation checkpoint

- **Implementer:** Claude Code running `claude-opus-5-5`
- **Reviewer:** Codex `gpt-6-astra` (fallback: no). A first run was rejected (exit 4) because a pytest temp-dir cleanup left over from `just check` changed `.tools/tmp/` mid-review; its output (`ai_tmp/rejected-20261031T033311Z-codex.md`, the same claims as #1–#3) was not triaged. The rerun was clean.
- **Reviewed:** `3fbb4f1...cd08326`
- **Findings:** `ai_tmp/review-20261031T060650Z-codex.md` · **Triage:** `ai_tmp/triage-20261031T0610Z-impl.md`

| # | Severity | Finding | Verdict | Action |
| --- | --- | --- | --- | --- |
| 1 | high | A credential echoed in the trace reaches the grader unscrubbed (the sweep runs after teardown and never sees the transcript) | valid (medium) | Fixed in a044104: the trace is scrubbed before grading; end-to-end test with a token echoed in a command and the final message |
| 2 | medium | A lone surrogate in the grader's evidence or notes aborts the run when the grading is written | valid | Fixed in a044104: replaced with U+FFFD; a grading that cannot be written is a grader error and the run continues |
| 3 | medium | A grading without `grader.model` or `cli_version` crashes `aggregate()` | valid (low) | Fixed in a044104: `_well_formed` requires both |
| 4 | medium | With two grader calls, only the first call's model and CLI version are kept | invalid | No change: the design defines one scalar per grading, both calls use one pinned CLI and model, and drift between trials is recorded |

A re-review round on the fixes (`cd08326...df98abf`, findings `ai_tmp/review-20261031T064700Z-codex.md`, triage `ai_tmp/triage-20261031T0650Z-fixes.md`):

| # | Severity | Finding | Verdict | Action |
| --- | --- | --- | --- | --- |
| 1 | medium | An unexpected reply id is quoted raw in the validation reason, so a lone surrogate makes the grading unwritable and a counted invalid reply becomes an excluded grader error | valid | Fixed in 2976540: the grading's reason is passed through the same U+FFFD replacement |

### Code review (`/code-review high`)

Findings: `ai_tmp/code-review-08.md`. Each was checked by two independent verifiers, one trying to refute it.

| # | Finding | Verdict | Action |
| --- | --- | --- | --- |
| 1 | An empty reply, a timeout or the budget cap is a grader error, which the material might cause | partly valid | Fixed in df98abf: an empty reply is an `invalid_reply`. Timeouts and the budget cap stay grader errors by design; ADR 0012 now names this as a residual risk, counted per arm |
| 2 | With two calls, a grader error outranks a passed canary, so a caught injection is excluded | valid (low) | Fixed in df98abf: `invalid_reply` > `rejected` > `grader_error` > `ok` |
| 3 | A trial that fails only because of grading prints an empty reason | valid (low) | Fixed in df98abf: the reason names the grading status or the failed expectation count |
| 4 | The grader's working directory names the arm, and the pinned CLI sends it to the model despite `--system-prompt` | valid (high) | Fixed in df98abf: the grader directory has a random name; the pinned-CLI test asserts the request contains neither the trial key nor the case |
| 5 | The disclosure word matches "skilled", "skillet" | valid (low) | Fixed in df98abf: `skill` or `skills` as a word |
| 6 | `--timeout` does not reach the grader | design decision | No change: the grader has its own fixed 300 s timeout (design §4.1) |
| 7 | The grader-error and disclosure notes are missing without a baseline | design decision | No code change: those notes qualify a delta; the per-arm counts still show both. Docs wording clarified in df98abf |
| 8 | Output files are read and redacted in full before the 20 KB cut | low, efficiency | Follow-up |
| 9 | The skill-file walk is repeated per trial and duplicates `tree_sha256`'s filter | low, maintainability | Follow-up |
| 10 | `_scorable` repeats the benchmark's exclusion rule | valid (low) | Fixed in df98abf: the runner uses `benchmark.exclusion` |

**Follow-ups:**

- Read output files with a bounded prefix (code review #8), keeping the reported size and the cap-after-redaction rule.
- One helper for the skill's file list, shared by the disclosure check and `skill_sha256` (code review #9).
- `prompt_sha256` covers the prompt templates but not the expectation list format or the joins.
- The harness's own framing text in the material can be quoted to satisfy the quote rule.
- Some tests assert on `Verdict.claimed` or on CPython's JSON error text.
- `redact()` still handles the old keyed `_grader/<case>/<arm>-<n>` path shape, which no longer occurs.
- If two grader calls ever report different models, note both in `grader.notes` (implementation review #4, optional).
- Confine the Claude Code adapter's Bash to the trial, for example with Claude Code's sandbox settings. In the live run, two baseline trials wrote to the host's `/tmp` (see Live run).
- `behaviour-ship-it`'s three expectations didn't discriminate between the arms in the live run. A future case edit could add one that does, without tuning it to this run's delta.
