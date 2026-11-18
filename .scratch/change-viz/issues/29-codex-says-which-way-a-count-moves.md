# 29: Codex says which way a changed count moves

**What to build:** find the general reason Codex's descriptions leave out which way a changed count moves, change what the skill explains, and show ticket 18's E7 passing on Codex.

Why: a reader who relies on the old output needs to know whether the numbers they get go up or down. On Codex, the skill names the new rule and leaves that to the reader. The maintainer made it a follow-up, not a release blocker (D5, `ai_tmp/stage3/decisions.md`, **Stage 4 decisions (2026-11-16)**). `0.2.0` shipped with E7 as it is, and with no benchmark (D9); ticket 30's graded runs record it as it is.

**Blocked by:** 25 (Review with the maintainer, then ship).

**Status:** needs-maintainer

**Agent requirements:** Any implementing agent (Claude Code or Codex). Under D2 the agent may iterate with Codex `--no-grader` runs and read E7 by hand. The maintainer runs Claude Code and the graded runs, in their own terminal, with the token. Cross-model review is also required.

## What is known

As of 2026-11-16. From ticket 18: **E7 (Codex)**, **Codex trials, and the E7 fix**, **GREEN rerun on `c397d04`** and **The maintainer's decisions (2026-11-14)**. `SKILL.md` line cites are to `c397d04`'s text.

- **What E7 asks** (`evals/change-viz/evals.json`, `behaviour-describe-branch`, expectation 6): "The description warns that, because words are now lower-cased and stripped of punctuation before counting, the counts printed for existing input can be lower than before, for example the number of distinct words." It is frozen.
- **Codex's record:**
  - On `253ee70`'s text: 1 of 4 graded (`06b1`, then run `20261113T005315Z-c5be`).
  - On `c397d04`'s text, run `20261114T205926Z-d9c9`: 1 of 3 graded, and 0 of 3 by hand. The hand count asks whether a note says a printed count goes down, or gives its old and new values.
  - A two-sided Fisher exact test on 1 of 4 against 1 of 3 gives p = 1: no sign of improvement between the two texts. Three commits separate them, and no run isolates one.
  - The baseline fails E7 in 3 of 3.
- **What is missing.** Each failing note names the rule and its cause, and makes the word and distinct totals its subject. But it states the change as a token merge, "`The` and `the,` count as the same word", not as a count that goes down. That shape predates `:83`, and appears in Codex's baselines too.
- **Where it is lost, unranked:**
  - `SKILL.md:83`: Codex has the totals in view, but writes their change as a token merge.
  - `SKILL.md:49`: whether Codex worked out at all that `distinct` falls.
  - The transcripts keep no reasoning text, so the two cannot be told apart. Codex read `wordstat.py` at `<fork>` in 7 of 7 trials, and no trial ran the old code.
- **Claude Code** passed E7 at `3958`, `11b6` and `33d0`. Its notes compare old and new values with no read at `<fork>` and no run; ticket 18 infers it worked them out from the diff. On this repository's own branch it missed the direction once, with the rule in context (ticket 18, **Real-branch read, and the fixes from it**).
- **Declined on 2026-11-14:** the lead's recommended change, to work out from the code what a small input printed at `<fork>` and prints now for each change to existing behaviour, then run three Codex trials. The maintainer chose to carry the gap instead.
- **Still held:** a clause for a change framed as a gain ("even when the new behaviour is the better one"). No `c5be` note framed the change that way.
- **When E7 counts as closed on Codex** (ticket 18): on three Codex trials, 3 of 3 closes it, 2 of 3 is improved but not closed, and one or none means the fix failed.
- **Ticket 20's 350-character note cap** fails two of Claude Code's three recorded E7 passes, 357 characters at `11b6` and 412 at `3958` (ticket 20, **Residual risk**).
- **Stage 4 rewrites `SKILL.md`,** so the cited lines move.
- **On the released `0.2.0` text:** the strict hand read failed E7 in both draws, `f47c` ("can report different word and distinct counts") and `7a96` ("can change"), with no grader (ticket 25, **Outputs before the maintainer's session**). Ticket 30's graded runs give the first graded result.

## Acceptance criteria

- [ ] The general reason is found from the transcripts and recorded here, with its evidence: which locus, or another, and why it holds beyond this fixture.
- [ ] The fix changes what the skill explains and holds for any change to existing output. It adds no word from the eval fixtures, and no rule that makes sense only for `wordstat-top`.
- [ ] E7 is unchanged, and passes on Codex in 3 of 3 trials, graded and by hand.
- [ ] The full suite passes on Claude Code and Codex with `--baseline`, Claude Code's E7 included, and the two runs are recorded as a benchmark iteration with `just eval-record`.
- [ ] The version is bumped by semver (`CONTRIBUTING.md:89-95`), `just format` has run, the changes are committed, and then `just check` passes.

## Out of scope

Changing E7, the rubric or the grader, and any other expectation's gap.

## Review checkpoints

Use the `cross-model-review` dev skill.

- **Implementation checkpoint:** before marking done, review the text change against these acceptance criteria. Pay particular attention to teaching to the test: a rule that fits only a counting change, or wording taken from E7.
