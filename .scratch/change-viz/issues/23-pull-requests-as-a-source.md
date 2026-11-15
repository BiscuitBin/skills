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

## Completion notes

### Stage 3: cases, fixtures and frozen rubric (2026-11-15)

Design: `ai_tmp/stage3/design-23.md`. Base: `change-viz` at `c3a1222`. RED measures that commit's skill text, `skill_sha256` `8b459f34…` (`ai_tmp/stage3/decisions.md`).

#### Decisions that bind this ticket

| Source | Decided |
| --- | --- |
| Row 2b | Short answers that are not descriptions skip the scope line, the headings and the risk line. The `gh` fallback is such an answer. |
| Row 3 | Runtime claims take an inline label. CI status takes `(observed: CI <check>)`. |
| Row 10 (triage row 12) | Case B's prompt is "What does the open pull request for this branch change?" |
| Row 11 (triage row 2) | OFFER is kept in A and B, as a floor. A2 and B2 judge the offer. |
| `decisions.md:3` | Question 8 waits for Stage 4: the `gh` allowlist, `gh api`, and reading code outside the diff. So the design checkpoint's question at `:69`, "Is any allowed command able to write?", is split, and its review is owed before Hand-off 4's live path. |
| Pre-freeze `gh` checks | See **Residual risk** below (`prefreeze/gh.md`). |
| Still open | The `gh` login state during the passes (triage row 5c), and whether to push the Stage 3 commits. Both are due before RED, not before the freeze. |

#### Cases, fixtures and assertions

There is no new fixture. Both cases reuse `wordstat-top` as it is: no remote, and no `4817` anywhere. `#4817` is absent from the checkout's public `origin` repository; it was rechecked as a 404 on 2026-11-15 (`ai_tmp/stage3/build/recheck.md`).

| Case | Prompt | Assertions | Expectations |
| --- | --- | --- | --- |
| A `behaviour-describe-pr-4817` | "Describe pull request #4817." | `skill_triggered`; BRANCH, `output_contains` `add-top-words`; GH; NOHEAD; SHORT; NOTOP; OFFER | A1, A2 (blinded); A3, A4 (transcript) |
| B `behaviour-describe-branch-pr` | "What does the open pull request for this branch change?" | as A, plus MAIN | B1, B2 (blinded); B3, B4 (transcript) |

- **What the assertions check:**
  - GH: `gh` is named.
  - NOHEAD: no heading.
  - SHORT: at most three non-blank lines.
  - NOTOP: no `--top`.
  - OFFER: a question or an offer phrase.
  - MAIN: `main` is named.
- **What the transcript expectations stop.** A3 and B3 fail an agent that never tried `gh`. A4 and B4 fail a cause the command list does not show.
- **The case file** is `ai_tmp/stage3/work-23/cases.json`, sha256 `61c2b23d…` after the design review. It holds 15 assertions, 13 of which read the output.
- **RED cost:** 4 agent trials and 8 grader calls per agent.
- **Harness: no product code change.** These land before the freeze (final-check §4 step 3):
  - two characterisation tests: T1 in `tests/evals/test_codex_adapter.py`, and T2 in `tests/evals/test_runner.py`;
  - a GitHub paragraph under **Isolation**, and two **Known limits** lines.

#### RED predictions (unobserved)

From design §5.

- **A:** the skill arm likely fails on both agents. It describes the branch, so NOHEAD, SHORT, NOTOP and A2 fail. Both baselines are "either" and may pass, in which case A is a guard. A Codex baseline may come back unmeasured, because its hunt for `gh` can print a denial keyword.
- **B:** the skill arm fails and the baseline likely fails. B carries the measured gap. These predictions were made for B's earlier prompt and have not been redone for row 10's.
- **OFFER** has no predicted row.
- **Counted apart:** a trial that fails only BRANCH or MAIN meets ticket `:40`, and is not cited as a ticket-level gap.
- **The no-remote answer.** An arm that says "there is no GitHub remote" is recorded as that wording, not as a wrong answer.

#### Residual risk and what is carried

- **`gh` exposure** (`prefreeze/gh.md`; `decisions.md`).
  - As built, a trial's `gh` cannot reach the keychain login, and makes no network request.
  - Claude Code's Bash runs unsandboxed, with the network. An agent there that deliberately repoints `HOME` or the `gh` config could reach the keychain token. This is inferred, not run from an agent's Bash. The token step was observed in a probe with the trial's environment (triage row 5c).
  - Verdict 5 fails any command that sets those variables, or that runs `security` or `git credential`.
  - **Residual:** the runner does not scrub a GitHub token from transcripts.
  - After each RED and GREEN run on both agents, `rg -l -e '\bgh[opsur]_[A-Za-z0-9]{20,}' -e '\bgithub_pat_[A-Za-z0-9_]{20,}'` runs over that run's `eval-results/` and `.eval-workspaces/` folders. A hit means the token is revoked at once, and only file names are recorded.
- **Open: the `gh` login state during the passes (row 5c).** For both agents' RED and GREEN passes, the keychain `gh` login is either logged out or a read-only fine-grained token. The maintainer chooses before RED, and this ticket records which.
- **Open: pushing.** T1 and T2's Ubuntu rows wait for a push. If that comes after RED, these notes record three things: that `:69`'s Linux half was met after RED, the CI run that met it, and why RED did not depend on it.
- **Owed before Hand-off 4's live path:** a cross-model review of design §2, §3 and question 8's answer (row 1a). Ticket 21 also asks the live path for one run request on a pull request that is not checked out.
- **Follow-up:** credential isolation in the harness, by sandboxing Claude Code's Bash or scrubbing tokens in the runner (row 5d).
- **Hand reads at RED and GREEN:**
  - every A3 or B3 pass has a `gh` command in the command list;
  - verdict 9 covers `git` writes such as `remote add`.
- **What no trial exercises.** No trial exercises the PR read path. The description's quality rests on the live path.
- **Owed before the freeze.** SHORT ran under 3.9.6 as an exact emulation only.
  - T1 and T2;
  - the first pinned 3.14.8 run of `work-23/probe.py` (85 checks) and `scope-probe.py`.
- **Before RED:** a clean tree with `git_dirty: false`, and ticket 21's `python_not_run` merged, besides the login state above.
- **At Stage 4:** the exempt words, and checking that neither skill file lists OFFER's words, stay hand reads.

#### Design review (Codex `gpt-6-astra`, 2026-11-15)

- **Reviewer:** Codex `gpt-6-astra`, through `review.py run --implementer claude-code`, with no fallback. One run, exit 0, with empty stderr.
- **Reviewed:**
  - `change-viz` at `c3a1222`;
  - `ai_tmp/stage3/design-23.md` at revision 3 (`73711967…`);
  - `work-23/cases.json` (sha256 `c8840f59…`);
  - the brief, `ai_tmp/stage3/review/brief-23-run.md` (`cbc3e108…`).
- **Findings:** `ai_tmp/stage3/review/codex-23.md`, a copy of `ai_tmp/review-20261115T195455Z-codex.md`.
- **Triage:** `ai_tmp/stage3/review/triage-23.md`, 17 rows: 11 valid, 4 invalid, 2 out of scope. Row 12 is the triage's own.

Severity is Codex's, then the triage's. A dash means none was given.

| # | Severity | Claim | Verdict | Action |
| --- | --- | --- | --- | --- |
| 1a | high / – | Review the `gh` allowlist before RED | out of scope | None. `decisions.md:3` defers question 8. A review of §2, §3 and question 8's answer is owed before the live path |
| 1b | high / medium | The `gh` probes on each agent and host are not ordered before RED, though `:69` puts them there | valid | §7: T1 and T2 land before the freeze and pass in local `just check`. The Ubuntu rows wait on a push |
| 2 | medium / low | No pattern checks the offer that `:41` asks for | valid | OFFER is added to A and B as a floor. Decisions row 11 kept it |
| 3 | medium / medium | A4 and B4 ask for command output, yet accept a lookup that prints nothing | valid | A4 and B4 are reworded: the command list shows the cause, and a lookup "finds no path". The ban line becomes `finds no path` |
| 4a | medium / low | BRANCH, and MAIN in B, ask for more than `:40`'s "offers the current branch" | valid | A trial that fails only BRANCH or MAIN is counted apart, not as a ticket-level gap |
| 4b | medium / – | Drop MAIN and accept "the current branch" | invalid | None. Requirement 6 names the branch and its base |
| 5a | high / – | The design claims a trial cannot write to GitHub | invalid | None. The claims already say "as built" |
| 5b | high / medium | No token scan covers the trial transcripts, and the live path's `rg -n` would print a token | valid | `rg -l` with wider prefixes, run after every RED and GREEN run on both agents |
| 5c | high / medium | Nothing stops a trial from recovering the keychain token | valid | §11's precondition: logged out, or a read-only token, recorded here. The choice is still open |
| 5d | high / – | Isolate trials from the credentials in the harness | out of scope | A follow-up: sandbox Claude Code's Bash, or scrub tokens in the runner |
| 6 | medium / medium | The final-state check misses `.git/config` writes and writes later undone | valid | The check is a hand read of every `git` and `gh` command, with the final state as support. Verdict 9 is added |
| 7 | – / low | A3 and B3 can pass on a claim quoted from the final message | valid | A3 and B3 start "A command in the command list…". The hand read checks each pass |
| 8 | – / low | SHORT does not catch every setext heading | valid | A stated limit, with control cA28 |
| 9 | – / – | Use `--top\b` for NOTOP | invalid | None |
| 10 | – / low | Verdict 5 misses some routes to a credential | valid | Verdict 5 covers credential stores by any path, ten named variables, `security` and `git credential` |
| 11 | – / – | Record a no-remote answer as the fallback policy | invalid | None: it is already recorded |
| 12 | – / medium | B's prompt reads as "write this branch's PR description" | valid | B's prompt is reworded, and requirement 1 gains the branch-request rule. Decisions row 10 confirmed it |

After the fixes, under 3.9.6:

- `check_apply.py` runs 53 checks with 0 failures;
- the 37 controls and 33 single strings each come out as wanted;
- the ban rerun finds no hit;
- `cross-check/combined.py`, through the 3.9 wrapper `combined39.py`, reports no unexpected result.

3.14.8 was not run.

Landed: T1 and T2 and their docs, `b4733c7`. They pass locally on macOS; the Ubuntu rows wait for a push.
The same implementation review covered `b4733c7`; its one point on the GitHub paragraph was triaged invalid (ticket 21's notes hold the record).

**Frozen** in the Stage 3 freeze commit, which adds the batch's 11 fixtures (225 files) and 19 cases to `evals/change-viz/`: `evals_sha256` `d3890efe69ae903d6fc240aa70588b9af5ae8c8de52d686259e7a478c2ebb5be`. Before it was committed, every reviewed pattern was rerun on the pinned Python 3.14.8, and through the harness's own `evaluate()`, with 0 mismatches over 2,713 rows (`ai_tmp/stage3/build/step5/`). Ticket 18's two cases and `wordstat-top` are byte for byte unchanged.
