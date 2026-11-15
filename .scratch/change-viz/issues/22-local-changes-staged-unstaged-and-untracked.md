# 22: Local changes: staged, unstaged and untracked

**What to build:** `change-viz` describes uncommitted work, alone or on top of a branch's commits, and opens with a scope line that says exactly what is covered. When there is nothing to describe, it says so in one line and invents nothing.

Why: the maintainer wants changes described whether they are "part of a Pull Request, a branch, or those staged/unstaged locally". The tracer (ticket 18) reads commits only. Once local edits can be in or out, a reader has to know which before they trust the description, so the scope comes first.

**Blocked by:** 18 (Tracer: `change-viz` describes a branch).

Tickets 19 to 24 do not depend on each other, but each edits the same `SKILL.md`, `evals/change-viz/evals.json` and version. Land them one at a time, and rebase onto the last one before a live run.

**Status:** ready-for-agent

**Agent requirements:** Any implementing agent (Claude Code or Codex). The maintainer runs the live evals in their own terminal, with the token. Cross-model review is also required.

## What is known

As of 2026-11-10.

- Ticket 16's fixtures can carry staged edits, unstaged edits and untracked files, each optional, and hide the installed skill from Git in both arms. So `git status` in a fixture trial lists only the fixture's own edits.
- The skill's outline, and the change source for a branch, come from ticket 18.
- Not decided by the maintainer: what the skill covers when the request names no change source, and the scope line's wording. Both are for this ticket's design checkpoint.
- `output_matches` is Python's `re.search`. An anchored pattern with a bounded repeat caps the whole message, and a negative lookahead at the start rejects a message that holds a given heading. That is how the empty case is checked.
- **From ticket 18's GREEN (2026-11-11):** `change-viz` already answers an empty branch in one line (`skills/change-viz/references/reading-the-branch.md`, "Nothing is ahead"), and notes uncommitted changes in one bullet. So the empty case's skill arm may pass at RED: record it as a guard from ticket 18.
- **From ticket 18 (2026-11-13):** with `--no-optional-locks` and `GIT_OPTIONAL_LOCKS=0`, `git diff` and `git diff HEAD` still rewrite a stat-dirty `.git/index` on Apple Git 2.50.1, where `status --porcelain`, `diff-files`, `diff-index HEAD` and `git -c diff.autoRefreshIndex=false diff` leave it alone. `skills/change-viz/SKILL.md:18` now tells agents to diff two commits only, so reading uncommitted changes needs one of the reads that leave it alone, and that line changes with it.
- **From ticket 18's Stage 2 /code-review (2026-11-14), carried here:**
  - Untracked litter such as `?? .DS_Store` triggers the uncommitted-changes note, which takes one of the three note slots (finding F8, `ai_tmp/stage2-code-review/triage-F8.md`). Decide whether the scope line takes that mention out of the notes, and how litter is told apart from a forgotten new file.
  - Working-tree reads run a configured clean filter on every changed file, and that filter is needed for a correct diff (F3).
  - `rg` over a dirty tree misses a committed line that a local edit removed. Reaching it needs `git grep -e <pattern> HEAD`, which is not on `SKILL.md:18`'s list. Once local work is in scope, context reads follow the declared scope (F5).

## Acceptance criteria

- [ ] The skill describes each of these when asked, and the request's own words pick among them:
  - staged edits only
  - all uncommitted work: staged, unstaged and untracked
  - a branch's commits together with the uncommitted work on top
- [ ] With no change source named, the skill covers what the design checkpoint settles, and the scope line makes that visible either way.
- [ ] The description opens with a scope line, before `## Why the change`, in one fixed form set at the design checkpoint. It names the base, the number of commits, and which of staged, unstaged and untracked are included.
- [ ] Anything left out is named in the scope line when it exists. A reader is never left to assume that unstaged edits were covered when they were not.
- [ ] Untracked files are covered as new files. A binary file, or one too large to read, is listed by name and size only, and the scope line or a note says so.
- [ ] An empty change source gets a one-line answer that says what was looked at and that nothing differs. No outline is written and no visual is drawn.
- [ ] The skill changes nothing: it does not stage, commit, stash, reset or check out. It reads with commands that leave the index and the working tree alone.
- [ ] Eval cases:
  - **Staged and unstaged together:** a fixture with both, where the two sets of edits differ in a way the description can show. A pattern asserts the scope line, and expectations say that an edit from each set is described.
  - **Staged only:** the same fixture, with a request for the staged edits. The scope line says the unstaged edits are left out.
  - **Empty:** a fixture with a clean tree and no commits ahead of its base. A pattern caps the message's length and rejects `## Change outline`.
- [ ] The completion notes record what the baseline arm did on the empty case. It may well pass, since an agent without the skill is likely to report no changes too. The case is then a guard against the skill inventing a description, not a measured gap, and the notes say so.
- [ ] "Changes nothing" is checked by hand: the commands in the recorded transcripts of the live runs are listed here, and none writes to the index, the working tree or a ref.

### Every `change-viz` ticket

These repeat in tickets 18 to 24 so that each can be read alone.

- [ ] Eval cases are written and baselined before the skill text changes (RED, then GREEN), and each rubric is frozen before its live run (`CONTRIBUTING.md` §2 and §3). The baseline and skill-arm run ids on Claude Code and Codex are recorded here.
- [ ] Live evals are handed to the maintainer as absolute-path `just eval` commands. The agent reads `eval-results/` and never holds the token.
- [ ] Fixtures are a neutral project: no `skill` or `skills` wording anywhere in them, and none of Codex's sandbox-denial keywords (`operation not permitted`, `permission denied`, `read-only file system`, `seccomp`, `sandbox`, `landlock`, `failed to write file`) in output a failing command could print.
- [ ] Every "does not" outcome names how it is checked. A blinded expectation cannot be negative, so the check is an `output_matches` pattern, a transcript read by hand, or a limit stated in the completion notes.
- [ ] The skill explains why, not just what, and `SKILL.md` stays well under the validator's 500-line limit, with detail in `references/`.
- [ ] The skill's `plugin.json` version is higher than the one on `main` (ticket 18 keeps the scaffold's `0.1.0`), `just format` has run, the changes are committed, and then `just check` passes.

## Out of scope

Pull requests (ticket 23), stashes, submodules, a comparison between two arbitrary commits, and files Git ignores.

## Review checkpoints

Use the `cross-model-review` dev skill.

- **Design checkpoint:** before the live run, write the scope line's form, the default change source, the fixtures and the frozen rubric, and get them reviewed. Can the scope line be right while the description covers something else? Does the staged-only fixture make a description that read the unstaged edits fail?
- **Implementation checkpoint:** before marking done, review the full diff against these acceptance criteria. Pay particular attention to commands that touch the index, to untracked files read without a size limit, and to an empty answer that still fills in the headings.

## Completion notes

### Stage 3: cases, fixtures and frozen rubric (2026-11-15)

Design: `ai_tmp/stage3/design-22.md`. Base: `change-viz` at `c3a1222`. RED measures that commit's skill text, `skill_sha256` `8b459f34…` (`ai_tmp/stage3/decisions.md`).

#### Decisions that bind this ticket

| Row | Decided |
| --- | --- |
| 2a | The scope line has fixed fields: `` **Scope:** `my-branch` against `main` · commits: 2 included · staged: left out · unstaged: left out · untracked: none ``. The "nothing to describe" answer is that line with every field `none`, as row 9 refines. |
| 2b | Only descriptions carry the risk line. Short answers that are not descriptions skip the scope line, the headings and the risk line, but the "nothing to describe" line carries the scope line. |
| 5 | When the request names no source, describe the commits since the base if there are any, otherwise all uncommitted work. The scope line names what was left out. |
| 9 | Rule 4's reading of 2a is confirmed. Each field keeps its meaning. A selected kind that is empty, and any kind that does not exist, read `none`. A kind that exists but was not selected reads `left out`. Every field reads `none` only when nothing exists. `behaviour-describe-staged-try-ideas` is added before the freeze: 19 new cases, and 38 agent trials per agent. |
| Assumed | An untracked text file over 256 KB is listed by name and size only, with a note. This is the standing default before Stage 4 (`questions.md`). |

#### Cases, fixtures and assertions

The fixtures are one hiking-log project:

- `hikelog-wip` (27 files): two commits ahead, a staged `--year`, unstaged `--miles` edits, and two untracked files, `summary.sh` and the 352-byte binary `tracks/ridge-loop.fit`;
- `hikelog-level` (9): branch level with `main`, and a clean tree;
- `hikelog-fresh` (13): branch level with `main`, and one unstaged edit.

Every case is by name and asserts `skill_triggered`.

| Case | Prompt | Fixture | Patterns; `output_contains` | Expectations |
| --- | --- | --- | --- | --- |
| A `behaviour-describe-uncommitted` | "Describe everything I haven't committed yet." | `hikelog-wip` | S-A, P1, SZ; `--year`, `--miles`, `summary.sh`, `ridge-loop.fit` | A1 to A4 |
| B `behaviour-describe-staged` | "Describe only what I have staged." | `hikelog-wip` | S-B, P1, N-B, U-N; `--year` | none |
| C `behaviour-describe-changes-plan-routes` | "Describe the changes." | `hikelog-level` | G-C, S-C, N-C | none |
| D `behaviour-describe-changes-longest-hike` | "Describe the changes." | `hikelog-wip` | S-D, P1, N-D, U-N; `--longest` | none |
| E `behaviour-branch-and-uncommitted` | "Describe this branch together with everything I haven't committed yet." | `hikelog-wip` | S-E, P1, SZ; `--longest`, `--year`, `--miles`, `summary.sh`, `ridge-loop.fit` | E1 to E5 |
| F `behaviour-describe-changes-try-ideas` | "Describe the changes." | `hikelog-fresh` | S-F, P1 | F1 |
| G `behaviour-describe-staged-try-ideas` | "Describe only what I have staged." | `hikelog-fresh` | G-C, S-G (`D2_FRESH`), N-C | none |

- **The patterns:**
  - S-A to S-G: the case's scope line.
  - P1: ticket 18's P1, verbatim.
  - G-C: the one-line answer, at most 400 characters, with no heading or fence.
  - N-C: no image and no risk label on that line.
  - N-B and N-D: no content from left-out work.
  - U-N: no untracked file name anywhere.
  - SZ: the binary's size, with a byte unit.
- **G** is decision 9's case, added before the freeze as triage-22 proposes it. It is not in the reviewed case file, and it adds no expectation and no grader call.
- **The case file** is `ai_tmp/stage3/work-22/cases-22.json`. It was `01a1d141e45d4eab…` after the design review, without G. With G, it read `26bc12b18d1d1ab3…` at 13:17 on 2026-11-15, and G's object matched triage-22's proposal. The apply was checked: 0 differences over 560 cells on the pinned 3.14.8 (`review/case7/patterns-3.14.out`). Codex's design review never saw G's final bytes, which come from its own triage (residual risk). Hand verdict H-C covers G as well as C.
- **Ten blinded expectations, in A, E and F.** RED costs 14 agent trials and 6 grader calls per agent.
- **The batch** becomes 19 cases, 38 agent trials and 36 grader calls per agent. The RED commands in final-check §5 carry `--case behaviour-describe-staged-try-ideas`, after `--case behaviour-describe-changes-try-ideas`.
- **No harness change.**

#### RED predictions (unobserved)

From design §7.

- **Every case fails** in both arms on both agents, on its scope pattern. The current text has no `**Scope:**` line.
- **The baseline also fails P1** on the description cases.
- **Substance gaps:**
  - SZ and the expanded `tracks/` directory, on A and E;
  - A4 and E5;
  - N-D and U-N in the baseline, on D;
  - P1 and F1 in the current-text arm, on F.
- **Format gains only, in at least one arm:** B, C and D in the skill arm, and B, C and F in the baseline. These notes name them as such.
- **Guards, likely in both arms:** G-C, N-C, E1, and the options' `output_contains`.
- **On B,** the current text may do worse than the baseline, because `SKILL.md:18` steers it away from `--cached`.
- **On G** (triage-22, inferred): both arms fail S-G, and G-C likely passes. That makes it a format gap, like C.

#### Residual risk and what is carried

- **The no-refresh read prefix.** No pinned agent has run `-c diff.autoRefreshIndex=false`. Probe it through both CLIs before the GREEN text names it; the fallback is plumbing (I2). The index hazard itself cannot show in a trial.
- **Strict patterns.** The scope patterns fail a GREEN answer on trivia, so the text has to give the exact form. N-D still fails "…including the year", a stated limit. SZ needs the byte unit beside 352, on the name's line.
- **Untested:** B's account of `--year` (finding 4); the too-large branch; the no-base and detached-`HEAD` forms, which are a hand check on a real repository at ticket 25.
- **Other tickets' text:**
  - The risk-call rule (design §9 item 12) must reach ticket 19's GREEN text. Otherwise a ticket 19 fault fails frozen ticket 22 patterns, and these notes say so.
  - Decision 2b's exemption must reach the GREEN text for 19 to 24.
- **Carried from ticket 18's Stage 2 review into the GREEN text:**
  - F8, untracked litter: the rule must fit the frozen grammar;
  - F3, clean filters;
  - F5, context reads, such as `git grep … HEAD`.
- **Shared fixture.** Four cases share `hikelog-wip`.
- **Owed before the freeze.** The revised patterns ran under 3.9.6 only.
  - G's bytes;
  - the first pinned 3.14.8 run of `work-22/patterns.py` and `matrix_any_python.py`;
  - `format_check.py`, `cases.load_suite` and the build smoke.
- **Before RED:** a clean tree with `git_dirty: false`, and ticket 21's `python_not_run` merged. For the GREEN text, not the freeze: `probe_reads.sh` and the `-c` probe.
- **Not made:** the optional `summary.sh` line in A's model message (finding 5).

#### Design review (Codex `gpt-6-astra`, 2026-11-15)

- **Reviewer:** Codex `gpt-6-astra`, through `review.py run --implementer claude-code`, with no fallback. One run, exit 0, with empty stderr.
- **Reviewed:**
  - `change-viz` at `c3a1222`;
  - `ai_tmp/stage3/design-22.md`;
  - `work-22/cases-22.block.json` and `cases-22.json`;
  - `patterns.py`, `build.py` and `fixtures/`.
- **The reviewed sha.** The triage records no sha. Design-22's review section gives `cases-22.json` as `621342e3…` before the review, and `cases-22.block.json` as `7ac1aafb…`.
- **The brief:** `ai_tmp/stage3/review/brief-22.md`, sent as `brief-22-run.md`, with eight questions.
- **Findings:** `ai_tmp/stage3/review/codex-22.md`, a copy of `ai_tmp/review-20261115T195030Z-codex.md`.
- **Triage:** `ai_tmp/stage3/review/triage-22.md`, 7 findings: 6 valid, 1 invalid, 0 out of scope.

Severity is Codex's, then the triage's. A dash means none was given.

| # | Severity | Claim | Verdict | Action |
| --- | --- | --- | --- | --- |
| 1 | high / medium | Rule 4's "every field `none`" misreports existing work as absent when a named source is empty | valid (fix split) | Rule 4 and §9 item 6 take the triage's text. The seventh case waited on the maintainer. Decisions row 9 confirmed the reading and adds the case before the freeze |
| 2 | medium / low | Case C passes invented content, an inline visual or a risk label on its one line | valid | N-C is appended to C, and hand verdict H-C covers the free clause. Three matrix messages |
| 3 | medium / medium | SZ checks for the number 352, not a size in bytes | valid | SZ needs a byte unit beside 352, in A and E. Four matrix messages and three limits |
| 4 | medium / – | Case B passes a wrong account of `--year` | invalid | No rubric change: B1 was dropped on critique S4. §12 records it |
| 5 | medium / low | Case E passes with its untracked files only named | valid | E gains E4 (`summary.sh`) and E5 (the binary, contents not shown). Ten expectations; grader calls unchanged |
| 6 | medium / low | U-N skips line 1, so a scope line that names excluded files passes | valid | U-N covers the whole message. One `EXPECT` flip |
| 7 | medium / low | N-D's year token fails correct commits-only sentences | valid (narrower fix) | The token is narrowed, so hyphenated compounds pass. "…including the year" stays a stated limit |

After the fixes, under 3.9.6:

- the matrix is 78 messages by 6 cases, 468 cells, with 0 differences;
- `check_cases.py` gives 0 problems;
- the fixture rebuild is byte-equal;
- `cross-check/combined.py`, through the 3.9 wrapper `combined39.py`, reports no unexpected result.

3.14.8 was not run. G has no matrix run in this record.

Freeze commit: TBD; evals_sha256: TBD.
