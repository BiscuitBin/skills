# 23: Pull requests as a source

**What to build:** given a pull request number or URL, or asked about the current branch's pull request, `change-viz` reads the pull request with `gh`, describes its changes against the pull request's own base, and reports the status of its checks as evidence. It only reads: it never edits, comments on, merges or checks out the pull request. Without `gh`, or without a login, it says so and offers to describe the branch instead.

Why: a pull request is one of the three change sources the maintainer named, and the place this description will most often be read. Using the pull request's own base matters because a pull request stacked on another branch is not a diff against `main`.

**Blocked by:** 18 (Tracer: `change-viz` describes a branch).

Tickets 19 to 24 do not depend on each other, but each edits the same `SKILL.md`, `evals/change-viz/evals.json` and version. Land them one at a time, and rebase onto the last one before a live run.

**Status:** ready-for-agent

**Agent requirements:** Any implementing agent (Claude Code or Codex). The live path needs a `gh` login, which a trial never has: the agent runs it by hand in a session where the maintainer's `gh` works, or hands the maintainer absolute-path commands. The maintainer also runs the live evals in their own terminal, with the token, and dispatches the live-eval job if the fallback case needs a Linux host. Cross-model review is also required.

## What is known

As of 2026-11-10.

Read in the code and docs:

- A trial's `PATH` is `<trial>/bin:/usr/bin:/bin`. Its home is empty and its environment is built from scratch, so it holds no GitHub token.
- On the maintainer's Mac, `gh` is at `/opt/homebrew/bin/gh`. A local trial cannot find it.
- The live-eval job runs on `ubuntu-24.04`.
- A fixture from ticket 16 has no pull request and no GitHub remote.
- Codex makes a trial an `infra_error` when a sandboxed command exits nonzero and prints one of its denial keywords.
- The four pull requests the maintainer likes are public: BiscuitBin/knarr#75, BiscuitBin/skills#1, BiscuitBin/skills#4 and BiscuitBin/rove#11.

Inferred, not tried:

- On the `ubuntu-24.04` runner `gh` may sit in `/usr/bin`, where a trial would find it, present but not logged in.
- Codex's `workspace-write` sandbox probably blocks the network, so a `gh` call may fail there for a third reason. Whether that failure prints a denial keyword is unknown, and it decides whether the fallback case can be scored on Codex at all.

## Acceptance criteria

- [ ] The skill accepts a pull request number, a pull request URL, and a request about the current branch's pull request.
- [ ] It reads the pull request's title, base, head, changed files, diff and checks with `gh`, and describes the diff against the pull request's own base. The scope it reports names the pull request and that base.
- [ ] Check status appears as evidence, marked as observed in CI, with failing and pending checks named. If ticket 21 has landed, it uses that ticket's label.
- [ ] For a pull request that is not checked out, the skill says how much of the surrounding code it could read. How it reads that code without changing the working tree is settled at the design checkpoint.
- [ ] It never writes to GitHub or to the repository: no `gh pr edit`, `comment`, `review`, `merge`, `close` or `checkout`, and no `gh api` call with a writing method. The skill says why, so an agent does not reach for a write to "finish the job".
- [ ] Without `gh`, or with `gh` and no login, the skill says which of the two it met, in one line, and offers the current branch instead. It does not guess at the pull request's contents.
- [ ] The fallback is the eval case: a request naming a pull request, on a fixture branch. It asserts by pattern that the answer names `gh` and offers the branch.
  - It passes where `gh` is missing: a local run on macOS.
  - It passes where `gh` is present but not logged in: a run on a Linux host with `gh` in `/usr/bin`, which may mean a dispatch of the live-eval job.
  - If Codex cannot be scored on one of these because the failed `gh` call marks the trial an `infra_error`, the completion notes say so with the run that showed it.
- [ ] The completion notes record what the baseline arm did on the fallback case. It may well pass: an agent without the skill, given the same request, is likely to report that `gh` is unavailable and turn to the branch. The case is then a guard against the skill guessing at a pull request it could not read, not a measured gap, and the notes say so. This ticket's real evidence is the live path below.
- [ ] The live path is verified by hand on the four pull requests above and recorded here: the command, the agent, and where each output is saved under `ai_tmp/`.
- [ ] "Never writes" is checked by hand: every `gh` and `git` command in those four transcripts is listed here, and none writes. No eval assertion can show this, and the notes say so.
- [ ] The pull request's own base is shown working on a pull request whose base is not the default branch, if one of the four qualifies or another public one is at hand. Otherwise the notes say it was not shown.

### Every `change-viz` ticket

These repeat in tickets 18 to 24 so that each can be read alone.

- [ ] Eval cases are written and baselined before the skill text changes (RED, then GREEN), and each rubric is frozen before its live run (`CONTRIBUTING.md` §2 and §3). The baseline and skill-arm run ids on Claude Code and Codex are recorded here.
- [ ] Live evals are handed to the maintainer as absolute-path `just eval` commands. The agent reads `eval-results/` and never holds the token.
- [ ] Fixtures are a neutral project: no `skill` or `skills` wording anywhere in them, and none of Codex's sandbox-denial keywords (`operation not permitted`, `permission denied`, `read-only file system`, `seccomp`, `sandbox`, `landlock`, `failed to write file`) in output a failing command could print.
- [ ] Every "does not" outcome names how it is checked. A blinded expectation cannot be negative, so the check is an `output_matches` pattern, a transcript read by hand, or a limit stated in the completion notes.
- [ ] The skill explains why, not just what, and `SKILL.md` stays well under the validator's 500-line limit, with detail in `references/`.
- [ ] The skill's `plugin.json` version is higher than the one on `main` (ticket 18 keeps the scaffold's `0.1.0`), `just format` has run, the changes are committed, and then `just check` passes.

## Out of scope

Creating or updating a pull request or its description (a later skill built on this one), review comments and discussion threads, hosts other than GitHub, and a fake `gh` or a recorded GitHub API inside a trial.

## Review checkpoints

Use the `cross-model-review` dev skill.

- **Design checkpoint:** before the live run, find out what a failed `gh` call does in a trial on each agent and each host, then write the fallback's wording, the eval case, the frozen rubric and the list of `gh` commands the skill may use, and get them reviewed. Is any allowed command able to write? Can the fallback case pass when the agent never tried `gh`?
- **Implementation checkpoint:** before marking done, review the full diff against these acceptance criteria. Pay particular attention to any path that reaches a write to GitHub, to a base taken from the default branch instead of the pull request, and to check status reported from memory instead of from `gh`.
