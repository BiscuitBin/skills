# 19: Merge risk: level, door and blast radius

**What to build:** every `change-viz` description carries a merge-risk call directly under the one-sentence why: a risk level, whether merging is a one-way or a two-way door, and the blast radius, followed by the reason for the level and how to walk the change back. A reader sees the critical call before any diagram.

Why: the maintainer wants "something like the 'merge danger' part" of mattpocock's `pr` skill, likes "the simple 'one-way' vs 'two-way' bit", and likes how similar systems "provide a simple clear 'risk score'".

**Blocked by:** 18 (Tracer: `change-viz` describes a branch).

Tickets 19 to 24 do not depend on each other, but each edits the same `SKILL.md`, `evals/change-viz/evals.json` and version. Land them one at a time, and rebase onto the last one before a live run.

**Status:** shipped in `0.2.0` (D9, 2026-11-17). Its boxes were not re-checked at the release, and the Claude Code and graded run ids are [ticket 30](30-maintainer-read-and-first-graded-benchmark.md)'s.

**Agent requirements:** Any implementing agent (Claude Code or Codex). The maintainer runs the live evals in their own terminal, with the token. Cross-model review is also required.

## Decisions already made

The maintainer chose this shape on 2026-11-10, from a preview. This is that preview, word for word:

```markdown
**Risk: 🟡 Medium** · **Door: two-way** · **Blast radius: eval harness**

- Why medium: changes the trial workspace that every eval run uses.
- Walk it back: revert the commit; no data or published state changes.
```

- **Levels:** three, written `🟢 Low`, `🟡 Medium` and `🔴 High`. A 1 to 5 score was offered and turned down.
- **Door:** `one-way` or `two-way`.
- **Blast radius:** a few words.
- **Two bullets:** `Why <level>:` with the level in lower case, then `Walk it back:`.
- **Position:** under the sentence in `## Why the change`, before `## Special things to note`.

The line has one fixed shape because the harness's outcome assertions are `output_contains` and `output_matches` only.

## What is known

As of 2026-11-10.

- mattpocock's `pr` skill (MIT) defines the terms: "You can walk back through two-way doors, but not one-way doors. A PR that is cheap to roll back is lower risk. Changes that involve destructive actions or hard-to-reverse decisions are one-way doors." Its blast radius is "the potential impact or scope of the changes", with the examples "layout shift, breakages for consumers, mobile responsiveness". Its template asks for a one-word blast radius; the maintainer chose a few words.
- That skill has no level. The rules for Low, Medium and High are new here.
- Text adapted from it needs the credit and notice ticket 18 set up.

A starting pattern for the line, to be made stricter in each eval case:

```text
\*\*Risk: (🟢 Low|🟡 Medium|🔴 High)\*\* · \*\*Door: (one-way|two-way)\*\* · \*\*Blast radius: [^*\n]+\*\*
```

**From ticket 18's second GREEN run (2026-11-12), inferred:** Codex's note called the new counting "more accurate" and never said which way the counts move for existing input, though `SKILL.md` asks for the direction. A risk line written that way would understate the blast radius for someone who relies on the old output.

**From ticket 18's real-branch read (2026-11-13), observed:** both agents described this repository's `change-viz` branch, and neither said that merging it publishes `change-viz` 0.1.0 to the marketplace and to `npx skills` while tickets 19 to 25 are open. Both had the new marketplace entry in view. The maintainer chose to settle it here, not in ticket 18's notes rule: what a merge publishes to people who install or deploy from the default branch is part of its blast radius. Write the rule so it holds for any project that ships from its default branch, and test it with a fixture of its own (ticket 18, **Real-branch read**).

## Acceptance criteria

- [ ] Every description has the risk line and its two bullets, in the shape and position above.
- [ ] The skill says what makes a door one-way, with the reasons: data loss, migrations, published formats, and effects outside the repository that a revert does not undo. It says why each matters, so an agent can judge a case the list does not name.
- [ ] The skill says how the level is chosen, including how the door and the blast radius bear on it. The rules come from the design checkpoint.
- [ ] For a one-way door, `Walk it back:` says plainly what cannot be walked back and what the nearest recovery is. It never implies a revert is enough.
- [ ] The blast radius names what is affected (who or what breaks if this is wrong), not which files changed.
- [ ] Eval cases:
  - a low-risk, two-way fixture, asserting `🟢 Low` and `two-way` in the line by pattern
  - a one-way fixture, such as a migration that drops data or a change to a published format, asserting `one-way` by pattern
  - both assert the line's position, between the why and `## Special things to note`
  - expectations for the substance, such as the reason naming the step that cannot be undone
- [ ] The completion notes say how much of the skill arm's gain is shape alone. A baseline agent will not print this exact line, so the pattern assertions show the shape, and the expectations show whether the call is right.

### Every `change-viz` ticket

These repeat in tickets 18 to 24 so that each can be read alone.

- [ ] Eval cases are written and baselined before the skill text changes (RED, then GREEN), and each rubric is frozen before its live run (`CONTRIBUTING.md` §2 and §3). The baseline and skill-arm run ids on Claude Code and Codex are recorded here.
  - Changed by D1 (2026-11-16): RED is folded into the final GREEN `--baseline` run, whose baseline arm shows the cases discriminate.
  - Changed by D9 (2026-11-17): `0.2.0` shipped before any Claude Code or graded run of this ticket's cases, so those run ids are [ticket 30](30-maintainer-read-and-first-graded-benchmark.md)'s. The Codex `--no-grader` run ids are under **Stage 4: skill text**.
- [ ] Live evals are handed to the maintainer as absolute-path `just eval` commands. The agent reads `eval-results/` and never holds the token.
  - Changed by D2 (2026-11-16): the agent may now run Codex live evals with `--no-grader` on the project's Codex login and read the outputs against the expectations itself; Claude Code runs and the graded final runs stay with the maintainer.
- [ ] Fixtures are a neutral project: no `skill` or `skills` wording anywhere in them, and none of Codex's sandbox-denial keywords (`operation not permitted`, `permission denied`, `read-only file system`, `seccomp`, `sandbox`, `landlock`, `failed to write file`) in output a failing command could print.
- [ ] Every "does not" outcome names how it is checked. A blinded expectation cannot be negative, so the check is an `output_matches` pattern, a transcript read by hand, or a limit stated in the completion notes.
- [ ] The skill explains why, not just what, and `SKILL.md` stays well under the validator's 500-line limit, with detail in `references/`.
- [ ] The skill's `plugin.json` version is higher than the one on `main` (ticket 18 keeps the scaffold's `0.1.0`), `just format` has run, the changes are committed, and then `just check` passes.
  - Changed by D4 (2026-11-16): the version is set once, to `0.2.0`, after tickets 19 to 24 have all landed, so this ticket's own commit leaves it unchanged.

## Out of scope

A numeric score, a risk section at the end of the description, and any gate that blocks a merge. The skill reports a call; it enforces nothing.

## Review checkpoints

Use the `cross-model-review` dev skill.

- **Design checkpoint:** before the live run, write the level rules, the one-way list with its reasons, the two fixtures and the frozen rubric, and get them reviewed. Can a one-way door ever be Low? Would two careful readers pick the same level for each fixture? Does the one-way fixture make its irreversible step findable in the diff without naming it in a comment?
- **Implementation checkpoint:** before marking done, review the full diff against these acceptance criteria. Pay particular attention to level rules an agent could satisfy by always answering Medium, and to a `Walk it back:` line that suggests a revert where data is already gone.

## Completion notes

### Stage 3: cases, fixtures and frozen rubric (2026-11-15)

Design: `ai_tmp/stage3/design-19.md`. Base: `change-viz` at `c3a1222`. RED measures that commit's skill text, `skill_sha256` `8b459f34…` (`ai_tmp/stage3/decisions.md`, **Pre-freeze checks**).

#### Decisions that bind this ticket

From `ai_tmp/stage3/decisions.md`. Each matches the design's recommendation.

| Row | Decided |
| --- | --- |
| 2b | Only descriptions carry the risk line. Short answers that are not descriptions skip the scope line, the headings and the risk line; the scope line also goes on the "nothing to describe" line. |
| 3 | A runtime claim carries an inline bracket right after it: `(read from the code, not run)`, `` (observed: ran `cmd`) ``, `(observed: commit <sha>)` or `(observed: CI <check>)`. The commit label is used only when a message reports a run's result. |
| 4 | The level comes from two yes-or-no questions, then the table. One-way: a revert cannot undo what merging sets off. Reach: something that exists behaves differently as written. Two-way and no is Low; two-way and yes, or one-way and no, is Medium; one-way and yes is High. |

Decision 4 settles the design's questions 1 and 2 as (a), so merging that publishes a release is one-way and its receivers are the blast radius (fix 5). Decision 2b settles question 3. Under row 3, ticket 21's design keeps the label off the risk line (its requirement 4).

#### Cases, fixtures and assertions

Three by-name behaviour cases, appended after the tracer's two. All three prompt "Describe what this branch changes." The ids name the branch, not what is scored.

| Case | Fixture (files) | Assertions | Expectations |
| --- | --- | --- | --- |
| `behaviour-describe-add-weekdays` | `daygap-weekdays` (17): Low, two-way | `skill_triggered`; `output_contains` `--weekdays`; R1; R2 door `two-way`; R2 level Low | A1, A3, A4 |
| `behaviour-describe-retire-wishlist` | `readlog-drop-wishlist` (21): High, one-way | `skill_triggered`; `output_contains` `wishlist`; R1; R2 door `one-way`; R2 level High; R4 | B1 to B4 |
| `behaviour-describe-add-weekdays-2` | `daygap-release` (35): Medium, one-way, publishes 1.4.0 on merge | `skill_triggered`; `output_contains` `1.4.0`; R1; R2 door `one-way`; R2 level Medium | C1 to C5 |

- **R1** is the risk block's shape, position and uniqueness, the same in all three cases: the line under the why, its two plain-label bullets, at most eight words of blast radius that are not only file names, and no risk heading outside a code fence. **R2 door** and **R2 level** read the line's door and level and the first bullet's label. **R4** asks that the `Walk it back:` bullet name the `.bak` copy.
- All 12 expectations are blinded. A's and B's blast radii are hand-read only. C5 checks that C's names the release's receivers.
- The case file is `ai_tmp/stage3/f19/cases-19.json`, sha256 `dab25ce0a146e840…` after the design review. The fixtures come from `f19/make_fixtures.py`, 73 files.
- RED costs 6 agent trials and 6 grader calls per agent (`ai_tmp/stage3/review/final-check.md` §5).
- One repository change goes with the fixtures, test first: `renovate.json`'s `ignorePaths` gains `evals/*/fixtures/**` and re-lists the preset's eight entries (`tests/test_renovate.py`). It must land before any fixture (final-check §4 step 4).

#### RED predictions (unobserved)

From design §7. The current text says nothing about risk, door or blast radius.

- R1, R2 door, R2 level and R4 fail in every arm on both agents, because no answer has the line. So each case fails in the baseline, and none is guard-only.
- A3, A4, B3, B4 and C3 to C5 fail, because there is no block to read.
- The `output_contains` guards and B1 likely pass in both arms. A1, B2 and C2 can go either way.
- C1, that merging publishes 1.4.0, likely fails in both arms. Ticket 18's real-branch read missed the same thing on both agents.
- How the gain is split: shape is R1. The call is R2 door, R2 level and C5. Substance in both arms is A1, B1, B2, C1 and C2. Substance that needs the block is A3, A4, B3, B4, C3, C4 and R4.

#### Residual risk and what is carried

- **n = 1 per arm.** At GREEN a level is a judgement, so read why each miss happened before blaming the text.
- **Grader leniency.** A4's "because", C3's "both", and C5 passed on "daygap users". B4 does not ask for revert-then-restore. The hand read records every radius and walk-back verbatim (design §6, §13).
- **Open:** the triage's optional B5 for B's blast radius ("the saved wishes, or the people whose logs hold them") was not adopted. `decisions.md` does not settle it.
- **Lookups.** The door calls on B and C are close to lookups. No case tests a one-way kind the list leaves out, so a generalisation case is a follow-up (review row 11).
- **Encoding.** The emoji and `·` are the first non-ASCII the output assertions read. Under a non-UTF-8 locale, R1 and R2 would fail for a harness reason. Reading with `encoding="utf-8"` in `cases.py` and the transcript reads is a follow-up (design §8).
- **Running the fixture's code.** On Codex, `pip`, `python -m build` or a `git checkout` to demonstrate the loss can make a trial an `infra_error`. The batch's one-rerun rule applies.
- **The package name.** `daygap` was rechecked unclaimed on PyPI (404) on 2026-11-15 (`ai_tmp/stage3/build/recheck.md`). A later registration would contradict the fixture.
- **Owed before the freeze:**
  - the Renovate test and change;
  - the fixture copy, and `just format`, which re-wraps the three `fixture.json` files;
  - the first pinned 3.14.8 run of `f19/patterns.py` (final-check §4 step 5.4). The revised patterns ran under 3.9.6 only.
- **Before RED:** a clean tree with `git_dirty: false`, and ticket 21's `python_not_run` merged.
- **At Stage 4:** `ai_tmp/stage3/review/final/bans.batch.txt` (23 lines for this ticket) runs at every commit. The paraphrase read in design §9 item 10, with hand entry 19-7 `wish`, stays by hand.

#### Design review (Codex `gpt-6-astra`, 2026-11-15)

- **Reviewer:** Codex `gpt-6-astra`, through `review.py run --implementer claude-code`, with no fallback. One run, exit 0.
- **Reviewed:** `change-viz` at `c3a1222`: `ai_tmp/stage3/design-19.md`, `f19/cases-19.json` (sha256 `bd5522ef…`), `f19/patterns.py` and `f19/make_fixtures.py`. The brief is `ai_tmp/stage3/review/brief-19.md`, sent as `brief-19-run.md`, with eight questions.
- **Findings:** `ai_tmp/stage3/review/codex-19.md`, a copy of `ai_tmp/review-20261115T193633Z-codex.md`. **Triage:** `ai_tmp/stage3/review/triage-19.md`, 14 rows: 8 valid, 5 invalid, 1 out of scope.

Severity is Codex's, then the triage's. A dash means none was given.

| # | Severity | Claim | Verdict | Action |
| --- | --- | --- | --- | --- |
| 1a | medium / medium | Canonical B's walk-back copies the `.bak` back while the branch stays merged, so the next run drops the wishes again | valid | Canonical B's walk-back now says to revert, then copy the `.bak` back. §0's byte range becomes 245 to 314 |
| 1b | medium / medium | Nothing scores or hand-reads a walk-back that offers the `.bak` without a revert | valid | §6's hand read fails acceptance on a `.bak`-only walk-back. §9 item 6 gains the general sentence. B4 stays, with its leniency stated in §13 |
| 1c | medium / – | B4 should require the overwrite caveat and the later-entries caveat | invalid | None to B4. Both facts are recorded, not failed, in §6's hand read |
| 2 | medium / medium | A wrong blast radius passes A and B | valid | §6 hand-reads A's and B's radii verbatim, and fails acceptance on one the change does not reach. No new expectation |
| 3 | medium / low | R1 reads text inside code fences as headings | valid | R1's heading check steps over closed fences. Six new controls and two stated limits |
| 4 | low / low | R1 accepts nested bullets, though §0 says exactly two | valid | A continuation line may not start a list item. Three new controls |
| 5a | medium / low | The reach rule does not settle new help or usage text | valid | §1.1 and §9 item 3: a new option shown in help or usage text is new input, not a change to what exists |
| 5b | medium / – | Narrow A1, A3, C2 and C3 to date-counting runs | invalid | None |
| 6 | – / medium | The design's canonical B likely fails B3 | valid | Canonical B's Why bullet ends "no revert brings it back". B3 is unchanged |
| 7 | – / – | Tighten C5 so that "daygap users" fails | invalid | None. The leniency is recorded, and the radii are kept verbatim |
| 8 | – / low | The GREEN text never states R1's eight-word cap or its no-emphasis rule | valid | §9 item 4: at most eight words, as plain text with no emphasis inside the bold field |
| 9 | – / – | R4 needs the literal `.bak` | invalid | None: it is already a stated limit |
| 10 | – / – | Report exclusions by case and arm, and record a conditional publish claim on its own | invalid | None: §7, §11 and §13 cover both |
| 11 | – / – | The door calls on B and C reduce to lookups, and no case tests a one-way kind the list leaves out | out of scope | A §13 limit. A generalisation case is a follow-up |

After the fixes, under 3.9.6:

- `f19/patterns.py` runs 84 controls with 0 failures, and the frozen P1 to P4 pass 7 of 7.
- `cross-check/combined.py` reports no unexpected result. It ran through the 3.9 wrapper `review/apply-19-work/combined39.py`, which skips the four patterns 3.9 cannot compile.
- The fixture rebuild is byte-equal.
- 3.14.8 was not run.

The brief's R1 copy is left as reviewed.

Landed: the Renovate change and its test, `ae6fc72`.
The same implementation review covered `ae6fc72`; it raised no finding against it (ticket 21's notes hold the record).

**Frozen** in the Stage 3 freeze commit, which adds the batch's 11 fixtures (225 files) and 19 cases to `evals/change-viz/`: `evals_sha256` `d3890efe69ae903d6fc240aa70588b9af5ae8c8de52d686259e7a478c2ebb5be`. Before it was committed, every reviewed pattern was rerun on the pinned Python 3.14.8, and through the harness's own `evaluate()`, with 0 mismatches over 2,713 rows (`ai_tmp/stage3/build/step5/`). Ticket 18's two cases and `wordstat-top` are byte for byte unchanged.

### Stage 4 decisions (2026-11-16)

From `ai_tmp/stage3/decisions.md`, **Stage 4 decisions (2026-11-16)**.

- **D1:** there is no separate RED run. The baseline-arm predictions under **RED predictions** are read against the final GREEN `--baseline` run's baseline arm. `c3a1222`'s skill text is never run, so the predictions for its skill arm stay unmeasured.
- **D2:** the agent iterates on this ticket's cases with Codex `--no-grader` runs, and reads each expectation by hand. Claude Code runs and the graded final runs stay with the maintainer.
- **D4:** the version is set once, to `0.2.0`, for the whole pull request.

### Stage 4: skill text (2026-11-17)

Written third, on ticket 20's `562c630`. The running log is `ai_tmp/stage4/progress.md`.

- **What the text now teaches** (design §0 and §9):
  - `SKILL.md`: the template carries the risk line, with placeholders naming every level and both doors so it leans towards none, and its two bullets. "Writing the why" puts the risk call under the sentence. A new **Writing the risk call** section says why the call comes first in one fixed shape, that it rates only the change being described (§9 item 13, stated generally until ticket 22's scope line), the two questions and the level table in a sentence (decision 4), and an always-read pointer to the reference, since what merging sets off often sits outside the diff. An answer that is not a description carries no call (decision 2b). `ls-tree` joins the read-only git list. The `description` names the call (§9 item 12). "Risk call" means the risk line and its two bullets.
  - `references/merge-risk.md` (new): the shape rules (at most eight plain words of radius, nothing after the closing `**`, no sub-list, once, descriptions only); what the call rates; the door, with the three kinds and why a revert does not undo each, and that a checkout is not an install; how to find what merging sets off: list the project's files from git, hidden paths included, read every file that defines what runs when the base changes, trace a changed version number, and claim nothing ships only after a search that could have found it; the blast radius; the reach; the level table with a reason per cell; the two bullets: `Why <level>:` names the part of the change that decides the level, and anything outside the diff it rests on with the file that defines it, and `Walk it back:` separates what the branch adds from what was already on the base; a worked example and two invented calls (Low two-way, High one-way).
  - `references/example.md` gains a Medium two-way call. `NOTICE.md` names two projects and gains Matt Pocock's section, its licence block byte-equal to upstream. `metadata.credits` names him, without the word "skill" (§9 item 9).
  - `references/rendering-on-github.md`'s risk-line example already matched §0.
- **Checks:** ban scan 0 hard hits ("leaves the choice", 23-8, hit while drafting and was reworded); `hand` hits in their allowed senses (the licence's "copy", 20-12; "blank line" as layout, 21-x); the §9 item 10 paraphrase read by hand (one clause that restated C5 was cut). `just validate-skills` 0 errors. `SKILL.md` 137 lines, body 18,543 bytes (about 4,636 tokens). `ai_tmp/stage4/w19/check_risk.py` runs R1 and R2 through the harness's `evaluate()` on the example and the reference's two calls: all pass, and the wrong door and levels fail.
- **Live runs (D2),** Codex, skill arm, no grader, one trial per case, tree dirty, each read by a fresh reader who did not read the skill text:

  | Round | Run | add-weekdays | retire-wishlist | add-weekdays-2 | What changed after it |
  | --- | --- | --- | --- | --- | --- |
  | 1 | `20261116T235241Z-91a3` | pass | strict fail, B3 | fail: Low, two-way, no `1.4.0`; C1, C3 to C5 | The agent searched the CI directory with a tool that skips hidden directories, saw nothing, and wrote that nothing runs on merge. Fix: list files from git, claim absence only after a search that could find it, trace a changed version; the `Why` bullet names the part of the change behind the level. |
  | 2 | `20261117T000551Z-ce25` | pass | pass | strict fail, C1: the publish is stated, but not what publishes | Fix: the `Why` bullet names what the call rests on outside the diff, with its file; the walk-back separates what the branch adds from what the base already had (round 2 said "a revert stops future releases"). |
  | 3 | `20261117T001750Z-7a52` | pass | pass | pass | None. |

  Reads: `ai_tmp/stage4/t19/r<n>/read.md`. Round 3, verbatim radii: "users of the new `--weekdays` flag", B's in the read, "people installing daygap 1.4.0". C1 names the mechanism ("the release workflow publishes it to PyPI on every push to `main`"). C4 is the closest call: its walk-back says the published 1.4.0 cannot be removed, without naming the index.
  - **False or loose claims recorded** (none fails an item): B's flowchart draws the backup and the drop on every run, after the migrations, where the code copies the log first and only when it exists; B's note says the drop happens "only when" an existing log is opened; C's walk-back credits `skip-existing` with preventing a republish; A's diff sketch shows an invented `main(start, end, --weekdays)` on a context line (rounds 2 and 3).
- **D1:** the predictions under **RED predictions** for the baseline arm are read against the final `--baseline` run.

### Stage 4 implementation review (2026-11-17)

Recorded in full in [ticket 25](25-review-with-the-maintainer-then-ship.md), **Stage 4 implementation review, for tickets 19 to 24**: Codex `gpt-6-astra` over `741510e..01b3817`, triaged separately. The rows that touch this ticket: 3 (no rule that a visual agrees with the code; this ticket's reads recorded an invented signature) and 4 (unlabelled runtime claims in `merge-risk.md`'s two calls and `example.md`'s risk call): both fixed.
