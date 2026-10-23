# 08: Graded trials and baselines

**What to build:** An eval run can measure whether a skill actually helps:

- each case runs several times (trials)
- the same cases also run without the skill (a baseline)
- an LLM grader scores each run against rubric expectations
- a benchmark summarises trigger rate, pass rate, mean ± stddev and the delta against the baseline

Grading output follows skill-creator's shapes, described in the research notes (`.scratch/foundation/research.md`). This builds on the ticket 05 harness and works with every adapter that exists when it runs. Claude Code is the minimum.

**Blocked by:** 05 (Eval harness tracer bullet: cowsay on Claude Code).

**Status:** ready-for-agent

## Acceptance criteria

**Trials and baselines:**

- [ ] `just eval` accepts a trial count and a baseline switch. A dry-run mode prints the planned number of agent and grader calls before anything is spent.
- [ ] A baseline run uses the same isolation as a with-skill run but installs no skill. The contamination check proves no skill was visible apart from the pinned agent's built-in skills, using the same recorded allowlist as the with-skill arm (ticket 05).

**Grader:**

- [ ] Cases can carry rubric expectations alongside their deterministic assertions.
- [ ] The grader writes one grading file per run, shaped like skill-creator's, with each expectation's text, verdict and evidence.
- [ ] The grader model is configurable and defaults to Opus 5.5 (`claude-opus-5-5`). The model used is recorded with the results.
- [ ] The grader judges rubric expectations from the run's final message and output files, with skill calls and skill paths removed, so it cannot tell which arm it is grading. Any expectation that needs the full transcript is marked unblinded in the results.
- [ ] The grader treats graded material as data, not instructions.

**Benchmark:**

- [ ] For each agent and case, the benchmark reports:
  - trigger accuracy: the share of trials whose trigger outcome matched the case's expectation
  - deterministic pass rate
  - graded pass rate
  - mean ± stddev across trials
  - the delta between with-skill and baseline, computed over outcome assertions and rubric expectations only. Skill-use assertions (skill triggered, script was run) are reported separately and shown as not applicable for the baseline.
- [ ] It records the agent CLI versions, the run models, the grader model, the repo commit and whether the tree was dirty, and a content hash of the skill and of its eval cases and rubric.

**Tests and live run:**

- [ ] The aggregation maths and the grader-output parsing are unit-tested against fixtures, including edge cases: one trial, all trials failing, a missing grading file, and a graded output that tells the grader to pass everything. That last one is either rejected by grader-output validation or marked failed. These tests run in `just check` without credentials.
- [ ] A live run of cowsay on Claude Code (several trials, with baseline) produces a benchmark, summarised in the completion notes. If the outcome delta is not positive, say so and explain why. Do not change cases or rubrics just to get a positive delta.

## Review checkpoints

Use the repo's cross-model adversarial review skill from ticket 01, or the protocol written out there:

- Pick the reviewer by the cross-model rule.
- A reviewer subagent saves its findings to the scratch folder.
- A separate triage subagent checks each finding against the code.
- Apply the valid fixes, rerun `just check`, and record every finding and how it was handled under **Completion notes**.

- **Design checkpoint:** before building, write the proposed grading schema, rubric format, grader prompt and statistics (how small trial counts, flaky triggers and grader errors are treated), and get them reviewed. Can the grader be biased or gamed? Are the statistics honest at low trial counts?
- **Implementation checkpoint:** before marking done, review the full diff against these acceptance criteria.
