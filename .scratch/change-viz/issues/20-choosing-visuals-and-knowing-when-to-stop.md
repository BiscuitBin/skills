# 20: Choosing visuals, and knowing when to stop

**What to build:** `change-viz` picks the smallest set of views that fits the change, and its length follows the size of the change. A one-line fix gets a short answer. A restructure gets a tree diff. A behaviour change gets a flow or a sequence. Nothing is drawn because a slot in a template was empty.

Why: the maintainer wants output that prioritises "high-impact prose and visuals so as to not confuse or overwhelm the consumer and to not distract from and hide critical pieces". The tracer (ticket 18) asks only for at least one fitting visual. This ticket gives the agent the reasons to choose well and to stop.

**Blocked by:** 18 (Tracer: `change-viz` describes a branch).

Tickets 19 to 24 do not depend on each other, but each edits the same `SKILL.md`, `evals/change-viz/evals.json` and version. Land them one at a time, and rebase onto the last one before a live run.

**Status:** ready-for-agent

**Agent requirements:** Any implementing agent (Claude Code or Codex). The maintainer runs the live evals in their own terminal, with the token. Cross-model review is also required.

## What is known

As of 2026-11-10.

- **The views**, from `show-me` and `visual-pr` (both MIT) and from the four pull requests the maintainer likes:

  | View | Shows |
  | --- | --- |
  | Mermaid flow, sequence or state | control flow, interaction between parts, or states and their transitions |
  | Diff sketch | what changed in a shape that already exists: a tree, a call tree, pseudocode |
  | File tree | where responsibilities live, or a broad restructure |
  | Call tree | runtime control flow |
  | Pseudocode | logic or an algorithm |
  | Outcome table | inputs against results, or claims against their sources |

- **Rules the sources give:** "Pick the smallest view that makes the key point clear." Use a diff "when the point is what changes and the surrounding shape already exists". Show the whole block "when most of it is new". "You may use one of these, you may use several, it is unlikely you will use all of them."
- **What the four pull requests used:** knarr#75 a diff, two Mermaid diagrams, two text sketches and a table. skills#1 three text sketches and three Mermaid diagrams. skills#4 two Mermaid diagrams, two text sketches and a table. rove#11 three Mermaid diagrams, tables, a diff and text sketches. They were written with session evidence, so their length is not a target.
- **Budget:** the grader reads at most 20 KB of the final message.
- **A pattern can cap length and forbid a construct.** `output_matches` is Python's `re.search`, so an anchored pattern with a bounded repeat limits the whole message, and a negative lookahead at the start rejects a message that holds a given fence. That is how this ticket's "does not" outcomes are checked.
- **From ticket 18's GREEN (2026-11-11):** `skills/change-viz/SKILL.md` says "Put every visual in a fenced block" and builds the outline from visuals "each in a fenced block", so a table cannot be a visual there. A ticket that adds an outcome or claim table edits both lines.
- **From ticket 18's Claude GREEN run (2026-11-12):** the skill arm put a pseudocode diff sketch with `+` marks in a `text` fence, though `references/views.md` gives a diff sketch the `diff` fence and the run read it, and its first two note bullets ran to about five sentences each, where ticket 18 sets no limit on a bullet's length. Its E3 fix (`253ee70`) has each lead-in open with what its visual draws, and rewrote the example's two lead-ins to match: any example lead-in this ticket adds or edits keeps that form.
- **From ticket 18's second GREEN run (2026-11-12):**
  - Both agents fenced the diff sketch as `diff`.
  - Codex put two sketches, tokenization and the CLI, under one lead-in in one `diff` fence.
  - Claude's second visual was a one-command `sh` usage block from the README: a sample of use, where `SKILL.md` prefers structure. Its lead-in says what the block draws but not what to notice.
  - Codex's second lead-in opens with its subject, "The CLI and tokenization changes: …", not with what it draws, and still passed E3. The lead-in rule rules out openers that narrate the commits, but not ones that name the subject.
  - Notes ran 4, 4 and 2 sentences on Claude, down from about five, and one each on Codex.
- **From ticket 18's real-branch read (2026-11-13), observed:** on this repository's `change-viz` branch, 82 commits and 122 files ahead of `origin/main`, a branch large enough that choosing views and knowing when to stop matter, Claude Code drew four visuals and Codex three. Codex's factual errors fell almost all in its outline: 8 of its 9 (8 of 33 outline claims), one in the first lead-in (`codex-final.md:13`), three in the trial flowchart (`codex-final.md:27`, `:28-31`, `:31`) and four in the last block and its lead-in (`codex-final.md:37`, `:41`, `:43`, `:44`). Claude Code's outline held 4 of its 8 (4 of 30 outline claims): `claude-final.md:17` in the first flowchart, `claude-final.md:40` in the skill's steps, and `claude-final.md:52` and `:55` in the last block. So half of each agent's outline errors sit in its last block or that block's lead-in, and both last blocks list the whole change. Claude Code's (`claude-final.md:48-56`) gives five paths and what each holds, which the rule check passed as a small file tree. Codex's (`codex-final.md:39-50`) is a `text` tree of features with no paths that paraphrases the code's names, against `views.md:10` and `:23` ("A sketch that tries to show everything shows nothing in particular"). Both last lead-ins fall short of `c85caaa`'s `SKILL.md:95`: Claude Code's "The files that hold the pieces." (`claude-final.md:48`) gives nothing to notice, and Codex's (`codex-final.md:37`) opens with what the change adds, not with what the block draws, and gives nothing to notice either. Codex's first lead-in (`codex-final.md:13`) only retells the diagram's nodes, and Claude Code's first visual draws the harness though its why leads with the skill (ticket 18, **Real-branch read, and the fixes from it**; `ai_tmp/real-read-check/hand-read.md`).

## Acceptance criteria

- [ ] The skill says which view fits which kind of change, and why, so an agent can choose for a change the list does not name. One example of each view lives in `references/`; `SKILL.md` holds the choosing rule.
- [ ] The skill says when to stop: what earns a second visual, and that a view repeating what another already shows is cut.
- [ ] The outline's three headings stay for every change. What shrinks for a small change is the change outline.
- [ ] Each shape has a length budget, set at the design checkpoint and stated in the skill, all inside the 20 KB ceiling.
- [ ] Eval fixtures, one per shape, each checking the choice and the length:
  - **A one-line fix:** a short answer. A pattern caps the message's length and rejects a Mermaid block.
  - **A restructure** (files moved or split, behaviour unchanged): a tree, shown as a diff. A pattern finds a `diff` or `text` fence holding tree lines.
  - **A behaviour change:** a Mermaid flow, sequence or state diagram. A pattern finds a `mermaid` fence opening with one of those diagram types.
- [ ] Expectations cover what a pattern cannot: the visual shows the change this fixture makes, and each visual has a one-line lead-in.
- [ ] The baseline arm fails each case on both agents, or the completion notes say which case it passed and what was done about it.

### Every `change-viz` ticket

These repeat in tickets 18 to 24 so that each can be read alone.

- [ ] Eval cases are written and baselined before the skill text changes (RED, then GREEN), and each rubric is frozen before its live run (`CONTRIBUTING.md` §2 and §3). The baseline and skill-arm run ids on Claude Code and Codex are recorded here.
  - Changed by D1 (2026-11-16): RED is folded into the final GREEN `--baseline` run, whose baseline arm shows the cases discriminate.
- [ ] Live evals are handed to the maintainer as absolute-path `just eval` commands. The agent reads `eval-results/` and never holds the token.
  - Changed by D2 (2026-11-16): the agent may now run Codex live evals with `--no-grader` on the project's Codex login and read the outputs against the expectations itself; Claude Code runs and the graded final runs stay with the maintainer.
- [ ] Fixtures are a neutral project: no `skill` or `skills` wording anywhere in them, and none of Codex's sandbox-denial keywords (`operation not permitted`, `permission denied`, `read-only file system`, `seccomp`, `sandbox`, `landlock`, `failed to write file`) in output a failing command could print.
- [ ] Every "does not" outcome names how it is checked. A blinded expectation cannot be negative, so the check is an `output_matches` pattern, a transcript read by hand, or a limit stated in the completion notes.
- [ ] The skill explains why, not just what, and `SKILL.md` stays well under the validator's 500-line limit, with detail in `references/`.
- [ ] The skill's `plugin.json` version is higher than the one on `main` (ticket 18 keeps the scaffold's `0.1.0`), `just format` has run, the changes are committed, and then `just check` passes.
  - Changed by D4 (2026-11-16): the version is set once, to `0.2.0`, after tickets 19 to 24 have all landed, so this ticket's own commit leaves it unchanged.

## Out of scope

Whether a diagram renders on GitHub (ticket 24), evidence tables and their labels (ticket 21), HTML or image output, and React component trees as their own view until a fixture needs one.

## Review checkpoints

Use the `cross-model-review` dev skill.

- **Design checkpoint:** before the live run, write the choosing rule, the length budgets, the three fixtures and their patterns, and get them reviewed. Does any pattern pass on a message that picked the wrong view? Does the length cap for the one-line fix still leave room for the three headings, and for ticket 19's risk line if it has landed?
- **Implementation checkpoint:** before marking done, review the full diff against these acceptance criteria. Pay particular attention to rules that read as "always include one of each", and to budgets the fixtures never test.

## Completion notes

### Stage 3: cases, fixtures and frozen rubric (2026-11-15)

Design: `ai_tmp/stage3/design-20.md`, at revision 5. Base: `change-viz` at `c3a1222`. RED measures that commit's skill text, `skill_sha256` `8b459f34…` (`ai_tmp/stage3/decisions.md`).

#### Decisions that bind this ticket

| Source | Decided |
| --- | --- |
| Row 6 | Exact character ceilings: 1,500 for a small change, 2,500 for a restructure, 3,500 for a behaviour change, 5,000 for several changes at once, and 350 per note. They are limits, not targets, and the eval checks the stated number. |
| Row 12 | `MER_A` is not anchored. MER stays as designed: it does not require the Mermaid diagram to be the outline's first block. |
| Figures | The 350 cap stands, though it fails two of Claude Code's three recorded E7 passes (see below). |
| Assumed | Six stop-rule checks beyond the ticket's three are frozen. "Several changes at once" has no fixture, so its 5,000 ceiling is checked in ticket 25's real-branch reads (`questions.md`, **Recommendations assumed**; not overruled). |

#### Cases, fixtures and assertions

Three by-name behaviour cases, one per branch of a lending-desk CLI. All three prompt "Describe what this branch changes."

| Case | Fixture (files) | Assertions | Expectations |
| --- | --- | --- | --- |
| `behaviour-describe-fix-due-today` | `desk-due-today` (15): a one-line fix | `output_contains` `overdue`; H, P2, LEN1500, NOMER, DIFF, ONE, NOTE | F1 to F3 |
| `behaviour-describe-split-modules` | `desk-split` (26): a split into a `lending/` package | `output_contains` `events.py`; H, P2, LEN2500, TREE, LE2, NOTE | R1 to R3 |
| `behaviour-describe-add-holds` | `desk-holds` (25): a new `held` state | `output_contains` `held`; H, P2, LEN3500, MER, LE2, NOFL, NOTE | B1 to B3 |

- **Every case also asserts `skill_triggered`.** H and P2 are ticket 18's P1 and P2, verbatim.
- **The ticket's own patterns** are NOMER, TREE, MER and the length caps.
- **The additions** are P2, DIFF, ONE, LE2, NOFL and NOTE:
  - DIFF: the `>=` to `>` lines in a `diff` fence;
  - ONE: one fenced block;
  - LE2: one or two blocks;
  - NOFL: no file-list block;
  - NOTE: no note over 350 characters, counted as typed.
- **TREE** reads only the first block under the outline, which must name `lending`.
- **The expectations.** F2, R2 and B2 are ticket 18's E3, verbatim. All nine expectations are blinded.
- **Files.** The case file is `ai_tmp/stage3/work-20/cases-20.json`, sha256 `9b347e7f…5ba8` after the design review. The fixtures come from `work-20/fixtures/`. No harness change.
- **Cost of RED:** 6 agent trials and 6 grader calls per agent.

#### RED predictions (unobserved)

From design §6. The base rates come from 2 Claude Code and 4 Codex messages on `wordstat-top`.

- **The baseline** fails every case on both agents, on H, P2 and a fence check (DIFF, TREE, MER or LE2). That is ticket 18's gap, not this ticket's.
- **The current-text skill arm** is mostly "either" at one trial. One item per case and agent is expected to discriminate:

  | Case | Claude Code | Codex |
  | --- | --- | --- |
  | fix | ONE | NOMER |
  | split | NOTE | TREE: Codex led with Mermaid 3 of 4 times |
  | holds | MER | B1 |

- **Guards.** The split may pass on Claude Code, and the holds may pass on Codex. A case that passes at RED is recorded as a guard for that agent, and no case changes after RED.
- **GREEN.** This design asks Hand-off 4 for `--trials 3` at GREEN.
  - Changed by the approved plan (Phase 4 step 5, 2026-11-16): the final runs use `--baseline --trials 1`, so n = 1 per case and arm is recorded as a limit, and three-trial reruns are left to a follow-up.

#### Residual risk and what is carried

- **The 350-character note cap against E7.**
  - Claude Code has four notes over 350 characters on record: 357, 412, 421 and 423. The cap fails all four.
  - Of Claude Code's three recorded E7 passes, the cap fails two: 357 (`11b6`) and 412 (`3958`, on the first GREEN text `b76a09db…`). It passes the third, 329 (`33d0`).
  - The maintainer kept the cap (`decisions.md`, row 6 and **Figures**). At GREEN, ticket 18's frozen case reruns as the regression guard. A Claude Code E7 fail whose note was cut under the cap is counted against the cap, never a reason to edit E7. `3958`'s message also fails NOTE in all three cases here.
- **LEN1500** is the likeliest GREEN fail on Claude Code, because agents count characters poorly. Three notes of about 300 characters, plus the risk block, overrun 1,500.
- **The sibling tickets.** One freeze covers six tickets. A larger line from 19, 21 or 22 can fail LEN1500 at GREEN for a reason outside this ticket.
- **E3 is lenient**, so "what to notice" in a lead-in is a hand read.
- **The quote rule.** F1, R1 and B1 need a verbatim quote, and F1 needs the `def is_overdue` context line.
- **DIFF and NOFL** are specific to these fixtures, and their limits are stated (design §3.6).
- **Codex.** A test run or a baseline's `git checkout` can make a Codex trial an `infra_error`. The batch's one-rerun rule applies. After the batch, list the system temp directory for leftovers moved out of a workspace.
- **To ticket 25:** the 5,000 ceiling and the several-changes rule, in the real-branch and four-PR reads.
- **Owed before the freeze:**
  - the first pinned 3.14.8 run of `work-20/patterns.py`, `check2.py` and `check3.py`, and `make_cases.py`'s `load_suite`. The revision 5 patterns ran under 3.9.6 only;
  - carrying revisions 4 and 5 into `work-20/design-20.template.md` before any `render.py` run.
- **Before RED:** a clean tree with `git_dirty: false`, and ticket 21's `python_not_run` merged. The notes record each run's `git_commit`, `skill_sha256` and `evals_sha256`.
- **Stale text.** `design-20.md:1461` still calls ticket 21's hand-read variant a fallback. Decision 1 and triage-21 C4 replaced it: stop and ask (final-check §6.5).
- **At Stage 4:** design §8 item 8's structure read, and ban hand entries 20-9 to 20-15 and 20-20, stay by hand at each commit.

#### Design review (Codex `gpt-6-astra`, 2026-11-15)

- **Reviewer:** Codex `gpt-6-astra`, through `review.py run --implementer claude-code`, with no fallback. One run, exit 0, with empty stderr.
- **Reviewed:**
  - `change-viz` at `c3a1222`;
  - `ai_tmp/stage3/design-20.md` at revision 4, kept in `work-20/pre-design-review/`;
  - `work-20/cases-20.json`, sha256 `8fa50b33…6f8a`;
  - the brief, `ai_tmp/stage3/review/brief-20-run.md` (`01d5ac91…18db`).
- **Findings:** `ai_tmp/stage3/review/codex-20.md`, a copy of `ai_tmp/review-20261115T194152Z-codex.md`.
- **Triage:** `ai_tmp/stage3/review/triage-20.md`, 11 rows: 5 valid, 6 invalid, 0 out of scope. Fixes C1 to C5 tighten patterns, which is within the designer's remit.

Severity is Codex's, then the triage's. A dash means none was given.

| # | Severity | Claim | Verdict | Action |
| --- | --- | --- | --- | --- |
| 1a | high / low | TREE passes a flat `+events.py`, `+rules.py`, `+report.py` list | valid (pattern half) | C1: TREE's block must name `lending`. Two new controls |
| 1b | high / – | Require parent-child structure in TREE, and a file tree in R1 | invalid | None. A `+lending/events.py` path list is a tree by design |
| 2a | medium / low | NOTE stops counting at a blank line inside a note | valid | C2: NOTE counts across blank lines, in all three cases |
| 2b | medium / – | A 40-space wrap of 170 + 170 characters counts as 381 | invalid under C2's rule | Rule stated: a line break and its indent count as one, so that note is 341 and passes. Stage 4's text states the rule |
| 3a | medium / medium | TREE can match a later block, so a Mermaid-led split passes | valid | C3: only the first block under the outline counts. A `python` block before the tree now fails |
| 3b | medium / – | On the holds, a diff first and then a state diagram passes MER and B1 | invalid, as designed | None. `MER_A` was left to the maintainer, and decisions row 12 kept MER unanchored |
| 4a | medium / low | DIFF fails `+    return today > due  # was >=` | valid | C4: the `+` line is read up to its first `#` |
| 4b | medium / – | Allow a context line between the `-` and `+` lines | invalid | None. The unbounded form is quadratic, and the limit stays |
| 5a | medium / low | NOFL rejects correct views | valid, in part | C5: NOFL skips a run that starts at a `mermaid` opener, and needs two different file names. Two new stated limits |
| 5b | medium / – | Move catalogue detection to the hand read; NOFL accepts closing catalogues | invalid | None |
| 5c | medium / – | ONE and LE2 permit a redundant Markdown table | invalid | None. On the fix it is a hand read; on the holds, NOFL rejects it |

**Also applied, from the triage's answer to Q3:** §11's quote-rule risk now names F1.

**After the fixes, under 3.9.6:**

- 77 controls, 0 mismatches;
- the §3.5 matrix is unchanged;
- `cross-check/combined.py`, through the 3.9 wrapper `combined39.py`, reports no unexpected result;
- the fixture rebuild is byte-equal.

3.14.8 was not run.

**Frozen** in the Stage 3 freeze commit, which adds the batch's 11 fixtures (225 files) and 19 cases to `evals/change-viz/`: `evals_sha256` `d3890efe69ae903d6fc240aa70588b9af5ae8c8de52d686259e7a478c2ebb5be`. Before it was committed, every reviewed pattern was rerun on the pinned Python 3.14.8, and through the harness's own `evaluate()`, with 0 mismatches over 2,713 rows (`ai_tmp/stage3/build/step5/`). Ticket 18's two cases and `wordstat-top` are byte for byte unchanged.

### Stage 4 decisions (2026-11-16)

From `ai_tmp/stage3/decisions.md`, **Stage 4 decisions (2026-11-16)**.

- **D1:** there is no separate RED run. The baseline-arm predictions under **RED predictions** are read against the final GREEN `--baseline` run's baseline arm. `c3a1222`'s skill text is never run, so the predictions for its skill arm, the table included, stay unmeasured.
- **D2:** the agent iterates on this ticket's cases with Codex `--no-grader` runs, and reads each expectation by hand. Claude Code runs and the graded final runs stay with the maintainer.
- **D4:** the version is set once, to `0.2.0`, for the whole pull request.
- **Trials (plan Phase 4 step 5, approved by the maintainer on 2026-11-16):** the final runs use `--baseline --trials 1`, not the `--trials 3` that **RED predictions** asks for at GREEN. So n = 1 per case and arm is recorded as a limit, and three-trial reruns are left to a follow-up.

### Stage 4: skill text (2026-11-16)

Written second, on ticket 24's `deb129f` (plan Phase 2; the order put 24 first so its no-hard-wrap rule landed before 21). The running log is `ai_tmp/stage4/progress.md`.

- **What the text now teaches** (design §1 and §8):
  - `SKILL.md`: the smallest set of views, each chosen by the kind of structure the change alters, with four shapes and the reason for each (a small change: a diff sketch of the lines in their function; a restructure: a file tree as a diff; a behaviour change: the Mermaid diagram built for it, plus the diff behind it when needed; several changes: a view per change, at most four). A view the request names is drawn first, and nothing the request asks for is cut (ticket 24's clause is folded in). The stop rule: stop once each change the why or a note rests on is drawn, cut repeats, never end on a catalogue, one sketch per block. The ceilings (decision 6) as limits, not targets, with the reason and what to drop at a ceiling. Each note is at most 350 characters. An answer that is not a description has no headings and no ceiling (decision 2b). An outcome table sits beside a fenced view, never in its place. A lead-in names what the whole visual draws.
  - `references/views.md`: a view table and nine invented examples (a webhook-sending service), one per view, with sections on what earns a second view and what to cut.
  - `references/example.md`: one sentence ties its flowchart and diff to the behaviour-change shape.
  - **Departures from §8:** the component tree is not its own view (**Out of scope**); the ceiling says "every line counted" rather than naming the risk and scope lines, which tickets 19 and 22 add; a small change's `- None.` is not restated.
- **Checks:** ban scan 0 hard hits, every `hand` hit in old text and its allowed sense (20-11 "hold" as a verb, 20-12 "copy", 21-x "blank line" in layout); a hand read found no fixture structure in the examples; `just validate-skills` 0 errors; `just check-mermaid` 16 blocks, 0 failed. `SKILL.md` is 128 lines, about 4,385 tokens: it leaves little room under the 5,000-token aim for tickets 19, 21, 22 and 23.
- **Live run (D2):** run `20261116T232220Z-609b`, Codex, skill arm, no grader, one trial per case, tree dirty. All three cases pass every pattern assertion and, read by hand by a fresh reader who did not read the skill text, every expectation (`ai_tmp/stage4/t20/r1/read.md`). One round.

  | Case | Shape | Length / ceiling | Notes (characters) | Views |
  | --- | --- | --- | --- | --- |
  | `behaviour-describe-fix-due-today` | small change | 787 / 1,500 | 157 | one `diff` sketch |
  | `behaviour-describe-split-modules` | restructure | 1,065 / 2,500 | 207 | one `diff` file tree |
  | `behaviour-describe-add-holds` | behaviour change | 861 / 3,500 | 125, 97 | one `stateDiagram-v2` (renders on the pinned Mermaid) |

  - **Close calls, passed and recorded:** B3: the note says "only the member named on the hold may lend it", with the verb backwards, while the diagram's edge `Held --> OnLoan: lend to held member` gives the right direction. R1: the file tree marks the unchanged `main()` as added. F1: one `diff` fence also holds the new test's hunk, from a second file. A strict grader could fail B3.
  - **Unscored:** the holds lead-in claims reporting the diagram does not draw; three `--> [*]` edges match nothing in the code, and `return` out of `Held` is missing; the first note of the fix and of the holds restates the why rather than warning. No trial ran an interpreter or wrote anything.

### Stage 4 implementation review (2026-11-17)

Recorded in full in [ticket 25](25-review-with-the-maintainer-then-ship.md), **Stage 4 implementation review, for tickets 19 to 24**: Codex `gpt-6-astra` over `741510e..01b3817`, triaged separately. The rows that touch this ticket: 3 (no rule that a visual agrees with the code; this ticket's reads recorded unchanged lines marked `+`), fixed in `views.md`, and 4 (unlabelled runtime claims in `views.md`'s examples), fixed.
