# 10: Manual live-eval CI job

**What to build:** A maintainer can start live evals from GitHub Actions by hand, choosing the skills (named, or "changed since main") and the agents. The job runs them, builds the report, and uploads it as an artifact. When the needed secrets are missing it skips cleanly. It never runs automatically on PRs.

**Blocked by:** 04 (Installable via Claude marketplace and npx skills), 09 (Cross-agent benchmark report and history).

**Status:** ready-for-agent

## Acceptance criteria

- [ ] A manually dispatched workflow has these inputs:
  - the skill selection (a name, or changed skills)
  - the agents (any of Claude Code, Codex, Pi)
  - the trial count, with a low default
  - a baseline toggle
- [ ] Inputs are validated: known skill names and agents, and a trial count within a documented maximum. They reach shell steps as data and are never pasted into commands.
- [ ] The workflow has the minimum token permissions and keeps its secrets in a deployment environment.
- [ ] It sets up the pinned toolchain the same way `just initialize` does, then runs the same `just eval` and `just eval-report` commands a developer runs locally.
- [ ] Each selected agent whose secrets are missing is skipped with a clear notice in the job summary, not a failure. With no secrets at all, the job succeeds and does nothing.
- [ ] The grader's credentials are checked the same way. If they are missing, evals still run with deterministic assertions only, and the job summary says grading was skipped.
- [ ] It never triggers on pull requests or pushes, and never exposes secrets to fork code.
- [ ] Secret values never appear in logs or artifacts.
  - The uploaded transcripts and results are checked for the configured secret values before upload.
  - Any setting that controls this is documented.
- [ ] The report and raw results are uploaded as workflow artifacts. The job summary links them and shows the headline matrix.
- [ ] "Changed skills" compares against the merge base with main.
  - A change to a skill or its eval cases selects that skill.
  - A change to shared eval code, adapters, the grader or the pinned agent versions selects every skill.
  - If nothing changed, nothing is selected, and the job says so.
  - This is unit-tested locally and in `just check`.
- [ ] A how-to guide explains which secrets to configure, how to dispatch the job, and roughly what a run costs.
- [ ] Shown working twice: a dispatch with secrets present produces the artifact, and one without secrets skips cleanly. If repo secrets can't be configured from here, show the skip path, and record that the secret-present path still needs to be shown for ticket 12.

## Review checkpoints

Use the repo's cross-model adversarial review skill from ticket 01, or the protocol written out there:

- Pick the reviewer by the cross-model rule.
- A reviewer subagent saves its findings to the scratch folder.
- A separate triage subagent checks each finding against the code.
- Apply the valid fixes, rerun `just check`, and record every finding and how it was handled under **Completion notes**.

- **Implementation checkpoint:** before marking done, review the full diff against these acceptance criteria. Pay particular attention to secret exposure, fork and PR trigger paths, unpinned actions, and runaway cost.
