# 09: Cross-agent benchmark report and history

**What to build:** `just eval-report` turns recorded eval results into a static report a person can open offline. It shows:

- a matrix of agents (Claude Code, Codex, Pi) against cases
- each skill's delta against its baseline
- how results changed across iterations
- flags on regressions since the last recorded benchmark

This lets a skill author see at a glance whether a change helped, hurt, or broke one agent in particular.

**Blocked by:** 06 (Codex adapter), 07 (Pi adapter), 08 (Graded trials and baselines).

**Status:** ready-for-agent

## Acceptance criteria

- [ ] `just eval-report` builds a static report from stored results, with no network and no agent calls. It can be scoped to one skill.
- [ ] The report contains:
  - an agent × case matrix of trigger accuracy (the share of trials whose trigger outcome matched the case's expectation) and pass rate, with mean ± stddev where there were several trials
  - each agent's delta against the baseline
  - the agent CLI versions, the run models and the grader model behind every number
- [ ] Benchmarks can be recorded as named iterations. The report shows how each metric changed across iterations.
  - An ADR records where history is kept and whether it is committed.
- [ ] Regression flags mark any metric that fell beyond a configurable threshold since the last recorded benchmark for the same skill and agent. A run with a regression can be made to exit nonzero. When the cases, rubric, model or CLI version differ from the earlier benchmark, the report labels the comparison as such instead of presenting it as a like-for-like change.
- [ ] Missing data (an agent never run, a case added later) shows as missing, never as zero.
- [ ] Building the report from fixture results is tested in `just check`, including a fixture with a regression that gets flagged, and fixtures for a should-trigger case and a should-not-trigger case.
- [ ] A real report built from live cowsay runs on all three agents is produced and summarised in the completion notes.

## Review checkpoints

Use the repo's cross-model adversarial review skill from ticket 01, or the protocol written out there:

- Pick the reviewer by the cross-model rule.
- A reviewer subagent saves its findings to the scratch folder.
- A separate triage subagent checks each finding against the code.
- Apply the valid fixes, rerun `just check`, and record every finding and how it was handled under **Completion notes**.

- **Implementation checkpoint:** before marking done, review the full diff against these acceptance criteria. Pay particular attention to misleading numbers, regression false positives and false negatives, and comparisons across different models or CLI versions.
