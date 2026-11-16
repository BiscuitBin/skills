# 27: `gh` without a login, on a Linux host

**What to build:** ticket 23's fallback cases, run where `gh` is present but not logged in. That is a dispatch of the `live-evals` workflow, whose `ubuntu-24.04` runner puts `/usr/bin/gh` on a trial's `PATH`. It shows whether the fallback cases pass there on both agents, and whether Codex can score them at all.

Why: a local run on macOS shows only the "no `gh`" half of the fallback, because Homebrew's `gh` is not on a trial's `PATH`. The "`gh` but no login" half needs a Linux host. The maintainer made it a follow-up, not a release blocker (D5, `ai_tmp/stage3/decisions.md`, **Stage 4 decisions (2026-11-16)**).

**Blocked by:** 23 (Pull requests as a source).

**Status:** needs-maintainer

**Agent requirements:** Any implementing agent (Claude Code or Codex). The maintainer adds `OPENAI_API_KEY` to the `live-evals` environment, dispatches the workflow, and approves the dispatch as the environment's required reviewer. The agent gives the exact dispatch command, then reads the uploaded results. Cross-model review is also required.

## What is known

As of 2026-11-16.

- **The fallback cases** run on `wordstat-top`, which has no remote:
  - `behaviour-describe-pr-4817`: "Describe pull request #4817."
  - `behaviour-describe-branch-pr`: "What does the open pull request for this branch change?"

  Each asserts by pattern that the answer names `gh` and offers the branch. In the transcript, A3 and B3 fail an agent that never tried `gh`, and A4 and B4 fail a cause the command list does not show (ticket 23, **Cases, fixtures and assertions**).
- **How `gh` fails in a trial, as built** (`docs/reference/evals.md`, **Isolation**, the GitHub paragraph):
  - On an Ubuntu runner, `/usr/bin/gh` is on the trial's `PATH`, and with no login it exits 4.
  - It stops before any network request, and prints none of Codex's denial keywords, so the trial stays `ok`.
- **T1 and T2 already check that on Ubuntu.** They run a scripted `gh pr view 4817` through the real pinned CLIs against fake model APIs (`tests/evals/test_codex_adapter.py`, `tests/evals/test_runner.py`). They never assert `gh`'s own wording. CI run 43966207277, whose `just check` holds T1 and T2, passed on `ubuntu-24.04` at `741510e`.
- **What only a live run adds: the real agent's own commands.**
  - The agent picks its own `gh` commands, and may try other ways to reach GitHub. T1's script does not.
  - Under Codex's sandbox, a command that exits nonzero and prints a denial keyword makes the trial an `infra_error` (ticket 23, **What is known**).
  - Ticket 23 inferred that the `workspace-write` sandbox probably blocks the network. That is a third way for a call to fail, and whether it prints a denial keyword is unknown. It decides whether Codex can score the case at all.
  - `gh`'s no-login exit comes before any network request, so the risk lies in a command that does reach for the network.
- **The dispatch** (`.github/workflows/live-evals.yml`, `docs/how-to/live-evals-in-ci.md`):
  - It is manual only: the Actions tab, or `gh workflow run live-evals.yml --ref <branch> -f skills=change-viz -f agents=both -f trials=<n> -f baseline=<true|false>`.
  - It runs in the `live-evals` environment, whose required reviewers approve each dispatch.
  - Its inputs are the skills, the agents, the trials and the baseline. It has no case filter, so a dispatch of `change-viz` runs all 21 cases on each agent.
  - Codex needs `OPENAI_API_KEY` in that environment. As of 2026-11-16 it holds only `CLAUDE_CODE_OAUTH_TOKEN` (`gh api --method GET …/environments/live-evals/secrets`).
  - No Codex dispatch has run yet, so a trial's auth from an API-key login is unverified (foundation ticket 10; `.scratch/foundation/follow-ups.md`).
  - `just eval change-viz --agent <agent> --dry-run` prints each run's spend cap.
  - The job uploads `eval-results/` as an artifact, kept 30 days. CI never records to `benchmarks/`.

## Acceptance criteria

- [ ] The maintainer approves the inputs and the cost first, from the `--dry-run` caps.
- [ ] `OPENAI_API_KEY` is in the `live-evals` environment, added by the maintainer.
- [ ] A dispatch of `change-viz` on both agents completes. Its workflow run id, the commit it ran, and its artifact are recorded here.
- [ ] Both fallback cases pass on each agent, or the notes name each assertion that failed and why.
- [ ] Each fallback trial's command list shows `gh` found and refused for want of a login, and its answer names that cause in one line (ticket 23, the "says which of the two it met" criterion).
- [ ] If a Codex trial is an `infra_error` because a failed call printed a denial keyword, the notes say so, with the run and the command that showed it, and say that Codex cannot score the case on Linux.
- [ ] Ticket 23's notes point here for the Linux result.

## Out of scope

Recording the dispatch as a benchmark iteration, hosts other than `ubuntu-24.04`, a `gh` login inside a trial, and the live pull request path (ticket 26).

## Review checkpoints

Use the `cross-model-review` dev skill.

- **Implementation checkpoint:** before marking done, review the recorded results against these acceptance criteria. Pay particular attention to a fallback that passes though the agent never tried `gh`, and to an `infra_error` read as a fault in the skill.
