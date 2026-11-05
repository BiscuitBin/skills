# 10: Manual live-eval CI job

**What to build:** A maintainer can start live evals from GitHub Actions by hand, choosing the skills (named, or "changed since main") and the agents. The job runs them, builds the report, and uploads it as an artifact. When the needed secrets are missing it skips cleanly. It never runs automatically on PRs.

**Blocked by:** 04 (Installable via Claude marketplace and npx skills), 09 (Cross-agent benchmark report and history).

**Status:** done, except the two live demonstrations, which need the workflow on `main` (see Completion notes)

**Agent requirements:** Any implementing agent (Claude Code or Codex). The secret-present CI demonstration needs credentials for the selected agents and, when grading is enabled, the configured grader. If repository secrets cannot be configured, demonstrate the skip path and record the remaining demonstration for ticket 12 as allowed below. Cross-model review is also required.

## Acceptance criteria

- [x] A manually dispatched workflow has these inputs:
  - the skill selection (a name, or changed skills)
  - the agents (Claude Code or Codex, or both)
  - the trial count, with a low default
  - a baseline toggle
- [x] Inputs are validated: known skill names and agents, and a trial count within a documented maximum. They reach shell steps as data and are never pasted into commands.
- [x] The workflow has the minimum token permissions and keeps its secrets in a deployment environment.
- [x] It sets up the pinned toolchain the same way `just initialize` does, then runs the same `just eval` and `just eval-report` commands a developer runs locally.
- [x] Each selected agent whose secrets are missing is skipped with a clear notice in the job summary, not a failure. With no secrets at all, the job succeeds and does nothing.
- [x] The grader's credentials are checked the same way. If they are missing, evals still run with deterministic assertions only, and the job summary says grading was skipped.
- [x] It never triggers on pull requests or pushes, and never exposes secrets to fork code.
- [x] Secret values never appear in logs or artifacts.
  - The uploaded transcripts and results are checked for the configured secret values before upload.
  - Any setting that controls this is documented.
- [x] The report and raw results are uploaded as workflow artifacts. The job summary links them and shows the headline matrix.
- [x] "Changed skills" compares against the merge base with main.
  - A change to a skill or its eval cases selects that skill.
  - A change to shared eval code, adapters, the grader or the pinned agent versions selects every skill.
  - If nothing changed, nothing is selected, and the job says so.
  - This is unit-tested locally and in `just check`.
- [x] A how-to guide explains which secrets to configure, how to dispatch the job, and roughly what a run costs.
- [ ] Shown working twice: a dispatch with secrets present produces the artifact, and one without secrets skips cleanly. If repo secrets can't be configured from here, show the skip path, and record that the secret-present path still needs to be shown for ticket 12.

## Review checkpoints

Use the repo's cross-model adversarial review skill from ticket 01, or the protocol written out there:

- Pick the reviewer by the cross-model rule.
- A reviewer subagent saves its findings to the scratch folder.
- A separate triage subagent checks each finding against the code.
- Apply the valid fixes, rerun `just check`, and record every finding and how it was handled under **Completion notes**.

- **Implementation checkpoint:** before marking done, review the full diff against these acceptance criteria. Pay particular attention to secret exposure, fork and PR trigger paths, unpinned actions, and runaway cost.

## Completion notes

### What was built

- `.github/workflows/live-evals.yml`: `workflow_dispatch` only, with inputs `skills` (a name or `changed`), `agents` (`both|claude|codex`), `trials` (default 1, at most `MAX_TRIALS = 5`) and `baseline`. It runs with `permissions: {}` at the top and `contents: read` on the job, in the `live-evals` environment. Every action is pinned to a commit SHA, the checkout keeps no credential, and the setup is ci.yml's followed by `just initialize`. Inputs reach the shell only through `env`, and secrets are only in the env of the step that needs them. `tests/test_live_evals_workflow.py` checks all of this.
- `just eval --no-grader`: cases with expectations rest on their assertions. Graded and outcome rates are `null` (`no data` in the report), `n_grading_skipped` is counted, and `results.json` records `grading_skipped`.
- `src/skills_tooling/evals/dispatch.py`, behind `just eval-changed` and `just eval-ci plan|runs|scan`. This is a separate module entry point rather than new subcommands on `python -m skills_tooling.evals` (a change from the plan), so `eval-ci` cannot start a live run. It covers changed-skill selection against the merge base, input validation, the per-secret skip plan, finished-run listing, and the pre-upload secret and symlink scan (`SCANNED_ENV` plus the Codex login).
- `just eval-report --markdown` writes the headline matrix and regressions for the job summary.
- Docs: `docs/how-to/live-evals-in-ci.md` (secrets, environment protection, dispatch, cost), plus `docs/reference/evals.md`, `docs/reference/commands.md`, ADR 0004's link and the GLOSSARY entry **Changed skill**.
- `codex login --with-api-key`, run through `just run`, was verified locally. It writes `.tools/agent-homes/codex/auth.json`, and `~/.codex/auth.json`'s mtime was unchanged.

### Demonstrations: not yet shown

`gh workflow run live-evals.yml --ref ticket/10-manual-live-eval-ci-job` returned `HTTP 404: workflow live-evals.yml not found on the default branch`, because GitHub dispatches only workflows that are on `main`. Both demonstrations therefore wait for the merge:

1. The skip path: dispatch with no secrets in `live-evals`. The job should succeed with a skip notice per agent.
2. The secret-present path: add `CLAUDE_CODE_OAUTH_TOKEN` and `OPENAI_API_KEY` to the environment, then dispatch cowsay on both agents at 1 trial. The run should produce the artifact.

If either cannot be shown before ticket 12, ticket 12 carries it (its gaps criterion names this one). The local skip path was shown: `just eval-ci plan … --has-claude false --has-openai false` printed both skip notices and wrote an empty `runs.txt`.

### Code review (`/code-review high`)

| # | Finding | Verdict | Action |
| --- | --- | --- | --- |
| 1 | The job timeout cancels the job, so Report, Scan and Upload are skipped and paid-for results are lost | valid | Fixed in d1e545b: a 90-minute step timeout on Run evals, inside the job's 120 |
| 2 | Rename detection hides a file moved out of a skill | valid | Fixed in d1e545b: `--no-renames`; test added |
| 3 | The docs' branch restriction to `main` leaves `changed` nothing to select | valid | Docs fixed in d1e545b |
| 4 | With `--no-grader` a trial passes without its expectations | invalid (by design) | The criterion asks for deterministic-only runs with a summary notice |
| 5 | A failed Codex login skips the Claude runs | valid | Fixed in d1e545b: Run evals runs under `!cancelled()` |
| 6 | The scan never reads symlinks, which the upload follows | valid | Fixed in d1e545b: any symlink fails the scan; test added |
| 7 | Every-suite triggers miss the Python toolchain and the Justfile | valid | Fixed in d1e545b: `pyproject.toml`, `uv.lock`, `.python-version`, `Justfile` added; tests added |
| 8 | A third dispatch replaces a pending second one | valid | Documented in the workflow and the how-to (GitHub behaviour) |
| 9 | `finished_runs` duplicates the report's finished-run check | valid | Fixed in d1e545b: it reuses `history.assemble` |
| 10 | `Plan.skills` is dead | valid | Removed in d1e545b. `grading_skipped` stays explicit, because `grader is None` also means a suite with no expectations |

### Cross-model review

- **Implementer:** Claude Code running `claude-opus-5-5`
- **Reviewer:** Codex `gpt-6-astra` (fallback: no). The first run exited 4 on Codex's own home setup files under `.tools/agent-homes/codex/` and was rerun once. Its output (`ai_tmp/rejected-20261105T045510Z-codex.md`) was not triaged.
- **Reviewed:** 1e136bf...d1e545b
- **Findings:** `ai_tmp/review-20261105T045603Z-codex.md` · **Triage:** `ai_tmp/triage-20261105T045629Z.md`

| # | Severity | Finding | Verdict | Action |
| --- | --- | --- | --- | --- |
| 1 | medium | A failed `just eval-report` left the job green, with no report or matrix | valid | Fixed: Report sets a `failed` output (also when a skill has no finished run), and the last step fails the job on it after the upload; workflow test and how-to updated |

**Follow-ups:**

- Show both dispatches once the workflow is on `main`, and record the run URLs here or in ticket 12.
