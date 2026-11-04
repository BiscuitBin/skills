# 09: Cross-agent benchmark report and history

**What to build:** `just eval-report` turns recorded eval results into a static report a person can open offline. It shows:

- a matrix of agents (Claude Code, Codex) against cases
- each skill's delta against its baseline
- how results changed across iterations
- flags on regressions since the last recorded benchmark

This lets a skill author see at a glance whether a change helped, hurt, or broke one agent in particular.

**Blocked by:** 06 (Codex adapter), 08 (Graded trials and baselines). Pi is deferred ([ADR 0013](../../../docs/adr/0013-pi-deferred-past-mvp.md)); future ticket 07 adds its column.

**Status:** done

**Agent requirements:** Any implementing agent (Claude Code or Codex). Report generation itself requires no agent calls. Completion requires results from live cowsay runs on Claude Code and Codex; authenticated access to both agents and the configured grader is needed if those results must be generated. Cross-model review is also required.

## Acceptance criteria

- [x] `just eval-report` builds a static report from stored results, with no network and no agent calls. It can be scoped to one skill.
- [x] The report contains:
  - an agent × case matrix of trigger accuracy (the share of trials whose trigger outcome matched the case's expectation) and pass rate, with mean ± stddev where there were several trials
  - each agent's delta against the baseline
  - the agent CLI versions, the run models and the grader model behind every number
- [x] Benchmarks can be recorded as named iterations. The report shows how each metric changed across iterations.
  - An ADR records where history is kept and whether it is committed.
- [x] Regression flags mark any metric that fell beyond a configurable threshold since the last recorded benchmark for the same skill and agent. A run with a regression can be made to exit nonzero. When the cases, rubric, model or CLI version differ from the earlier benchmark, the report labels the comparison as such instead of presenting it as a like-for-like change.
- [x] Missing data (an agent never run, a case added later) shows as missing, never as zero.
- [x] Building the report from fixture results is tested in `just check`, including a fixture with a regression that gets flagged, and fixtures for a should-trigger case and a should-not-trigger case.
- [x] A real report built from live cowsay runs on both agents is produced and summarised in the completion notes.

## Review checkpoints

Use the repo's cross-model adversarial review skill from ticket 01, or the protocol written out there:

- Pick the reviewer by the cross-model rule.
- A reviewer subagent saves its findings to the scratch folder.
- A separate triage subagent checks each finding against the code.
- Apply the valid fixes, rerun `just check`, and record every finding and how it was handled under **Completion notes**.

- **Implementation checkpoint:** before marking done, review the full diff against these acceptance criteria. Pay particular attention to misleading numbers, regression false positives and false negatives, and comparisons across different models or CLI versions.

## Completion notes

- **Commands:** `just eval-record <name> <run-id>...` records finished runs, one per agent, as `benchmarks/<skill>/<name>.json`. `just eval-report [skill]` writes `eval-results/report.html`, takes `--threshold`, `--fail-on-regression` (exit 1), `--out` and `--run <run-id>` (an unrecorded run as a last iteration), and calls no agent and no network. Code: `src/skills_tooling/evals/{history,report}.py`; docs: `docs/reference/evals.md` ("History and report"); decision: [ADR 0014](../../../docs/adr/0014-benchmark-history.md) (history committed under `benchmarks/`, one file per iteration, aggregates only).
- **Decisions to revisit:** a fall labelled not like-for-like still fails `--fail-on-regression`; grader labels apply only to graded and outcome metrics and their deltas; the matrix's pass rate is `outcome_pass_rate`, so excluded trials are never counted as 0.
- **Fixture tests in `just check`:** `tests/evals/test_history.py`, `tests/evals/test_report.py`, `tests/evals/test_report_command.py`, on `tests/fixtures/evals/report/` (v1 Claude Code and Codex, v2 Claude Code only, with its should-trigger ship-it case falling to 1/3: flagged, and `--fail-on-regression` exits 1). Each carries a should-trigger and a should-not-trigger case.

### Live report

Built with `just eval-report cowsay` from `benchmarks/cowsay/ticket-08.json` (the ticket 08 Claude Code run, 10 trials) and `benchmarks/cowsay/ticket-09.json` (runs `20261104T063552Z-19c7`, Codex, and `20261104T064435Z-d208`, Claude Code; 3 trials per case and arm, with baseline, at c1e6190, clean tree). Both runs share `skill_sha256` b505fdd6… and `evals_sha256` 50a3864a…. All 66 trials of each run were `ok`; no token-shaped string in `eval-results/` or `benchmarks/`.

| ticket-09 | Claude Code | Codex |
| --- | --- | --- |
| Trigger accuracy, each of the 9 cases (3 should-not-trigger) | 1.00 ± 0.00 (n=3) | 1.00 ± 0.00 (n=3) |
| Pass rate, ship-it / wrapped-text | 1.00 / 1.00 (n=3) | 1.00 / 1.00 (n=3) |
| Outcome Δ vs baseline, ship-it / wrapped-text | +0.27 / +1.00 | +1.00 / +0.60 |
| Agent Δ: deterministic / graded / outcome (cases=2) | +0.83 / +0.50 / +0.63 | +1.00 / +0.67 / +0.80 |
| Agent CLI, model | 2.1.309, `claude-sonnet-5-5` | 0.163.0, `gpt-5.6-terra` |
| Grader | `claude-opus-5-5` on 2.1.309 | `claude-opus-5-5` on 2.1.309 |

No regression beyond 0.10. Claude Code's ticket-08 → ticket-09 comparison is labelled `grader prompt changed`, correctly: 883a9fb changed the grader's framing after the ticket 08 run. Codex has one benchmark, so nothing to compare. Trigger cases have no pass rate and show `n/a`, not 0.

### Code review (`/code-review`)

| # | Finding | Verdict | Action |
| --- | --- | --- | --- |
| 1 | "no data" over all cases when every trial was excluded | valid | Fixed in c1e6190: `no scored trials` |
| 2 | "no data" for a case delta when an arm had no scored trials | valid | Fixed in c1e6190 |
| 3 | Docs said `eval-record` refuses different cases; it refuses different case files | valid | Docs corrected in c1e6190 |
| 4 | A damaged iteration file raised a KeyError traceback | valid | Fixed in c1e6190: refused with a message |
| 5 | Iterations were ordered by `recorded_at`, so a backfilled run sorted last | valid | Fixed in c1e6190: ordered by the runs' `started_at` |
| 6 | The CSS muted plain data cells | valid | Fixed in c1e6190 |
| 7 | Provenance printed a literal `None` | valid | Fixed in c1e6190: `default` or `no grader` |
| 8 | "snapshot" is a glossary avoid-term | valid | Renamed to `assemble` in c1e6190 |
| 9 | `load` globbed the directory twice | valid | Fixed in c1e6190 |
| 10 | Pooled values recomputed; formatting duplicated | out of scope | Follow-up |

### Cross-model review

- **Implementer:** Claude Code running `claude-opus-5-5`
- **Reviewer:** Codex `gpt-6-astra` (fallback: no). The first run exited 4 on Codex's own home setup files (`.tools/agent-homes/codex/skills/.system/`) and was rerun once; its output (`ai_tmp/rejected-20261104T233842Z-codex.md`) was not triaged.
- **Reviewed:** 186035b...334159c
- **Findings:** `ai_tmp/review-20261104T233945Z-codex.md` · **Triage:** `ai_tmp/triage-20261104-benchmark-report.md`

| # | Severity | Finding | Verdict | Action |
| --- | --- | --- | --- | --- |
| 1 | high | The last two benchmarks were picked by iteration order, which an iteration of runs started days apart can reverse, hiding a fall | valid | Fixed in 9c5fab3: each agent's runs are ordered by their own `started_at`; test added |
| 2 | medium | A comparison over a different case selection of one case file read `like-for-like` | valid | Fixed in 9c5fab3: the comparison line carries `case set changed`, and `case changed` when a shared case was redefined; tests added |
| 3 | medium | An agent never run had no column instead of showing as missing | valid | Fixed in 9c5fab3: every agent the harness runs (`adapter.AGENTS`, also `--agent`'s choices) gets a column, `not run`, and its history says so; test updated |
| 4 | medium | The live-report summary was absent from the completion notes | out of scope | A step pending at review time; done above |

**Follow-ups:**

- Compute each run's pooled values once, and share the matrix and history cell formatting (code review #10).
