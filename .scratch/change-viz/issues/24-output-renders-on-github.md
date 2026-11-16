# 24: Output renders on GitHub

**What to build:** what `change-viz` writes renders correctly in a GitHub pull request description and in a comment. The skill bundles a reference of what GitHub renders and what it breaks, checked against GitHub itself, and the skill's recorded outputs are shown rendering in a real comment.

Why: the maintainer asked for "output that can display and render properly in a GitHub pull request description or comment". A Mermaid block that GitHub cannot parse shows an error where the diagram should be, and nothing in this repository checks rendering. A diagram that fails to render hides exactly the part the reader came for.

**Blocked by:** 18 (Tracer: `change-viz` describes a branch).

Tickets 19 to 24 do not depend on each other, but each edits the same `SKILL.md`, `evals/change-viz/evals.json` and version. Land them one at a time, and rebase onto the last one before a live run.

**Status:** ready-for-agent

**Agent requirements:** Any implementing agent (Claude Code or Codex). Posting to GitHub is outward-facing: the maintainer posts the rendering comment, or approves the exact text and place before the agent posts it. The maintainer also runs the live evals in their own terminal, with the token. Cross-model review is also required.

## What is known

As of 2026-11-10.

Read in the code and docs:

- No check in `just check` renders Markdown as GitHub does. markdownlint checks structure only.
- The risk line from ticket 19 uses the emoji 🟢, 🟡 and 🔴.
- `script_ran` recognises only `python`, `python3` or `python3.N` running a script inside the skill directory, and needs the call to exit 0. With no `args` it passes when the call's output is nonempty, which fits a script that reads a draft on stdin.
- `final_contains_script_output` reruns the shipped script outside the workspace with `/dev/null` as stdin, so it cannot check a script whose output depends on the draft.
- ADR 0006 chose cowsay because a bundled script gives the deterministic assertions something to check.
- A bundled script is linted by ruff, has a test file by cowsay's precedent, and makes the skill need Python 3, which `compatibility` would then say.

Recalled by the planning agent, not checked. Each line is **to verify** against GitHub or its docs before it goes into the reference:

- Mermaid node and edge labels that hold parentheses, brackets, quotes or other punctuation need quoting.
- `<br/>` breaks a line inside a Mermaid label.
- GitHub renders only the diagram types its own Mermaid version supports, and that version trails Mermaid's releases.
- A `|` inside a table cell needs escaping, even inside inline code, and a table cell cannot hold a fenced block.
- A fence nested inside another needs a longer outer fence.
- A `diff` fence colours a line only when `+` or `-` is its first character.
- A pull request description or comment is limited to 65,536 characters.
- Whether Mermaid renders inside a collapsed `<details>` block is not known.
- Whether any API or offline tool reports what a comment will render, Mermaid errors included, is not known. The planning agent's recollection is that Mermaid renders in the browser, so an API that returns HTML would not show a diagram error.

**From ticket 18's Claude GREEN run (2026-11-12):** the skill arm put a pseudocode diff sketch with `+` marks in a `text` fence, though `references/views.md` gives a diff sketch the `diff` fence; whether GitHub colours those marks only in a `diff` fence is on the "to verify" list above.

**From ticket 18's second GREEN run (2026-11-12):** Codex put parentheses inside quoted Mermaid labels, `B["words(): split, trim punctuation, lowercase"]` and `E["Counter.most_common(N)"]`, a live sample for the "to verify" line on quoting. Its `diff` fence holds a bare blank line. Both agents now fence diff sketches as `diff`.

## Acceptance criteria

- [ ] Every line of the "to verify" list above is checked against GitHub's documentation or a real render, and marked confirmed, corrected or dropped, with the source. The list in this ticket is updated to match.
  - Changed by D3 (2026-11-16): for a Mermaid line, a render by the official Mermaid CLI pinned at Mermaid 12.2.0 stands in for a GitHub render, and the GitHub render moves to [ticket 28](28-render-proof-in-a-github-post.md).
- [ ] The skill bundles a reference under `references/` holding only verified rules, each with the reason and a right and a wrong example. `SKILL.md` says when to read it.
- [ ] The rules cover what the skill actually emits: each Mermaid diagram type it uses, tables, `diff` and `text` fences, the risk line, and the length limit.
- [ ] The design checkpoint decides between rules only, and rules plus a small bundled checker: a standard-library Python script that reads a draft and reports the constructs known to break. If the checker is built:
  - It has tests that run in `just check`, and passes ruff.
  - It exits 0 on a clean draft, and its messages hold none of Codex's denial keywords.
  - The skill tells the agent to run it on its draft and fix what it reports before answering.
  - An eval case asserts `script_ran` for it.
  - `compatibility` says the skill needs Python 3.
- [ ] If the checker is not built, an eval case uses a fixture that tempts a known break, such as function names with parentheses in a flow diagram, and a pattern rejects the broken form.
- [ ] Rendering is shown for real. Recorded outputs of the skill, at least one per diagram type it uses plus a table and the risk line if ticket 19 has landed, are posted in one GitHub comment or pull request description, and every block renders. The link, and a note of anything that failed and was fixed, are recorded here.
  - Changed by D5 (2026-11-16): the post moves to [ticket 28](28-render-proof-in-a-github-post.md), which does not block the release.
- [ ] The place and the exact text of that post are approved by the maintainer first, or the maintainer posts it.
  - Changed by D5 (2026-11-16): this moves with the post to [ticket 28](28-render-proof-in-a-github-post.md).

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

Rendering anywhere but GitHub pull request descriptions and comments, HTML and image output, a full Mermaid parser, and a rendering check in `just check` or CI.

- Changed by D3 (2026-11-16): the repository's Mermaid check, `just check-mermaid`, may run in `just check` and CI; it is a dev tool of this repository, not a checker bundled with the skill.

## Review checkpoints

Use the `cross-model-review` dev skill.

- **Design checkpoint:** before building, write the verified rule list with its sources and the choice on the checker, and get them reviewed. Is any rule still resting on recollection? If there is a checker, which rules can it check without parsing Mermaid, and can it flag a correct draft as broken?
- **Implementation checkpoint:** before marking done, review the full diff against these acceptance criteria. Pay particular attention to rules with no source, to a checker that passes a draft GitHub would break, and to the rendering proof covering fewer constructs than the skill emits.

## Completion notes

### Stage 3: cases, fixtures and frozen rubric (2026-11-15)

Design: `ai_tmp/stage3/design-24.md`. Base: `change-viz` at `c3a1222`. RED measures that commit's skill text, `skill_sha256` `8b459f34…` (`ai_tmp/stage3/decisions.md`).

#### Decisions that bind this ticket

| Source | Decided |
| --- | --- |
| Row 7 | Rules only, for now. A checker becomes a follow-up if a GREEN trial, or a ticket 25 real-branch run, shows a break the rules cover. |
| Row 3 | Runtime claims take an inline label. Ticket 21's requirement 4 keeps the labels out of Mermaid labels. |
| Assumed | Both diagram cases, flowchart and sequence (`questions.md`, **Recommendations assumed**; not overruled). |
| Figures | No recorded final has a broken Mermaid label by pattern: 35 of 35, plus `example.md`. Real GitHub rendering waits for the Preview probe. |
| Pending | The Mermaid Preview probe (design question 3): 13 blocks, of which the design review added block 13. It is with the maintainer, and no result is on file (`decisions.md:30`; `questions.md:240-243`). |

#### Cases, fixtures and assertions

The fixture is `pantry-comments` (13 files), a pantry list counter whose records are `name|count` lines. Its branch, `skip-comment-lines`, adds `read_records(lines)`, which skips blank lines and `#` comments. It also makes `parse_line`'s error name the line. So a faithful label meets parentheses, a pipe, a double-quoted literal and `#`.

| Case | Prompt | Assertions | Expectations |
| --- | --- | --- | --- |
| `behaviour-describe-with-flowchart` | "Describe what this branch changes, with a Mermaid flowchart of the path one line of the input now takes through the functions that handle it, and of what a malformed line now prints." | `skill_triggered`; PF1; PF2; PF3; PS2 | F-E1, F-E2 |
| `behaviour-describe-with-sequence` | "Describe what this branch changes, with a Mermaid sequence diagram of the calls one run of pantry.py now makes, from main down to parse_line." | `skill_triggered`; PS1; PF2; PF3; PS2 | S-E1, S-E2 |

- **PF1 and PS1** each ask for a top-level `mermaid` fence of their type that names a changed function.
- **The negatives:**
  - PF2: no flowchart label that breaks the parse, such as an unquoted bracket or `"`;
  - PF3: no `"` inside a quoted label;
  - PS2: no `#` or mid-line `;` that cuts a sequence message or block label.
- **Both cases carry all three negatives,** so a break in any diagram fails the case. Since the design review, the negatives read only top-level fences.
- **No headings are asserted.**
- **The four expectations** are blinded.
- **The case file** is `ai_tmp/stage3/work-24/cases-24.json`, sha256 `85431827abe8218b…` after the design review.
- **RED cost:** 4 agent trials and 4 grader calls per agent. No harness change.

#### RED predictions (unobserved)

From design §6.

- **The flowchart case:**
  - Claude Code's skill arm is likelier to fail PF2. Its one recorded flowchart left every label unquoted, and this fixture's labels hold parentheses and the error's `"`.
  - Codex quoted every node label in 5 of 5 flowcharts, so its likelier break is PF3.
  - The baselines are "either".
- **The sequence case:** PS2 is unknown in every arm. No agent has drawn a sequence diagram on record.
- **If RED passes the flowchart case in all four trials,** it stays as the regression guard ticket `:55` requires. It is recorded as "no gap seen in one draw", never as "no gap".
- **If the sequence case passes too,** this ticket's eval shows no measured gap at RED, and its evidence is the render proof (`:56`).
- **Two rules to name** (review answer 6): `CONTRIBUTING.md:47` asks for a failing baseline, while ticket `:55` requires the flowchart case whatever RED shows. These notes name both.
- **The gain** is PF2, PF3 and PS2. PF1, PS1 and the expectations are guards.

#### Residual risk and what is carried

- **The probe is pending** (final-check §6.1 item 1). Until it is reported, these rest on Mermaid's grammar at v10.0.0 and develop, not on GitHub:
  - PF2's `"` hit;
  - PF3;
  - PS2's `#`, `;` and keyword heads.

  The options:

  - (a) run the probe, which is recommended;
  - (b) freeze on the grammar, the default if the probe is skipped;
  - (c) the reworded probe-free form, which gives up PF3, Codex's likeliest gap.
- **If a frozen PF2, PF3 or PS2 rule is corrected after RED** (C4):
  - RED for both cases is rerun on both agents and both arms, under the corrected `evals.json`.
  - The maintainer chooses the whole batch or `--case`.
  - Rescoring the saved finals is a cross-check only, never the RED result.
- **Never probed, so grammar only:** PS2's `rect` and `par_over` heads, and `#` in an `opt` label. GitHub does not publish its Mermaid version.
- **False fails and misses.**
  - PF1 or PS1 can fail for reasons other than rendering: a tilde fence, `Mermaid` capitalised, or a fence indented inside a list item.
  - An unclosed `mermaid` fence followed by prose passes every pattern, so it is a hand read.
  - Each false fail is checked by hand before it is recorded as a render break.
- **Running the project.** The flowchart prompt asks what a malformed line prints. A run nobody asked for is recorded by ticket 21's rule. It fails no case here.
- **At Stage 4:**
  - A.2a, B.2a and the A.2 and B.2 corrections go into `github-rules-24.md` and the bundled reference (final-check §4);
  - the render proof needs a state diagram that no case produces;
  - the "invent every example" read and hand entries H1 to H4 stay by hand at each commit.
- **Owed before the freeze:** the first pinned 3.14.8 run of `work-24/patterns_24.py`, `make_cases.py`, `doc_check.py` and `suite_probe.py`. Every pattern result in the review came from a user-local CPython 3.14.8, not the pinned build. System 3.9.6 cannot compile these patterns.
- **Before RED:** a clean tree with `git_dirty: false`, and ticket 21's `python_not_run` merged.
- **Not re-rendered:** the `brief-24.md` sites. They are the record of what Codex reviewed, and design-24's **Not done** gives their replacement text.

#### Design review (Codex `gpt-6-astra`, 2026-11-15)

- **Reviewer:** Codex `gpt-6-astra`, through `review.py run --implementer claude-code`, with no fallback. One run, exit 0.
- **Reviewed:**
  - `change-viz` at `c3a1222`;
  - `ai_tmp/stage3/design-24.md` at revision 4;
  - `work-24/cases-24.json`, sha256 `c678c4fa…`;
  - the fixture;
  - the brief, `ai_tmp/stage3/review/brief-24.md`, sent as `brief-24-run.md`, with eight questions.

  The sources as reviewed are kept in `work-24/pre-design-review/`.
- **Findings:** `ai_tmp/stage3/review/codex-24.md`, a copy of `ai_tmp/review-20261115T200051Z-codex.md`.
- **Triage:** `ai_tmp/stage3/review/triage-24.md`, 7 rows: 6 valid, 0 invalid, 1 out of scope. A1 and A2 are the triage's own. It downgrades every reviewer severity, because none of the forms appears in 55 recorded sources.

Severity is Codex's, then the triage's. A dash means none was given.

| # | Severity | Claim | Verdict | Action |
| --- | --- | --- | --- | --- |
| 1 | high / low | An odd `"` in a valid own-line `%%` comment blinds PF2 and PF3 | valid | C1: an own-line `%%` comment, not a `%%{` directive, is one unit in PF2's and PF3's scan |
| 2 | medium / low | PS2 fails a valid indented `%%` comment | valid | C2: the comment test comes before the indent is consumed |
| 3 | medium / low | PF2, PF3 and PS2 read a literal `mermaid` example inside another fence | valid | C3: the negatives read only top-level fences, as PF1 and PS1 do. The change in meaning is stated |
| 4a | high / medium | Three gaps: no remedy if a frozen rule is wrong after RED, option (c) mislabelled, and PS2's keyword heads never probed | valid | C4: the rerun remedy; (c) reworded as probe-free, with its cost; probe block 13 added |
| 4b | high / – | Wait for the probe, since freezing on the grammar fails the criterion | out of scope | None. Question 3 is the maintainer's, and the design recommends the probe first |
| A1 | – / low | An unclosed `mermaid` fence followed by prose passes every pattern | valid | A hand-read row in §5, and a stated limit |
| A2 | – / low | Four limits are missing from §3 | valid | Added to §3's limits and its false-fail table, each with a `LIMITS` row |

After the fixes:

- **Under the user-local 3.14.8,** `patterns_24.py` gives 101 rows and 166 checks with 0 mismatches, and 20 limit rows. `cross-check/combined.py` reports no unexpected result.
- **Under 3.9.6,** the fixture rebuild is byte-equal, and `doc_check.py` gives 0 mismatches.

**Frozen** in the Stage 3 freeze commit, which adds the batch's 11 fixtures (225 files) and 19 cases to `evals/change-viz/`: `evals_sha256` `d3890efe69ae903d6fc240aa70588b9af5ae8c8de52d686259e7a478c2ebb5be`. Before it was committed, every reviewed pattern was rerun on the pinned Python 3.14.8, and through the harness's own `evaluate()`, with 0 mismatches over 2,713 rows (`ai_tmp/stage3/build/step5/`). Ticket 18's two cases and `wordstat-top` are byte for byte unchanged.

### Stage 4 decisions (2026-11-16)

From `ai_tmp/stage3/decisions.md`, **Stage 4 decisions (2026-11-16)**. The bare `:N` cites in these notes, this section's included, are to this file at `741510e`; the sub-bullets added for these decisions have moved the lines since.

- **D1:** there is no separate RED run. The baseline-arm predictions under **RED predictions** are read against the final GREEN `--baseline` run's baseline arm. `c3a1222`'s skill text is never run, so the predictions for its skill arm stay unmeasured.
- **D2:** the agent iterates on this ticket's cases with Codex `--no-grader` runs, and reads each expectation by hand. Claude Code runs and the graded final runs stay with the maintainer.
- **D3:** there is no GitHub Preview. Mermaid validity is checked offline with the official Mermaid CLI, `@mermaid-js/mermaid-cli`, pinned at Mermaid 12.2.0. That is the version GitHub's viewer bundle hard-codes, in one snapshot taken on 2026-11-10. The check is a repository dev tool, `scripts/check-mermaid.mjs`, behind `just check-mermaid` (plan Phase 1).
  - It is a repository check, not a checker bundled with the skill, so row 7 ("rules only") still holds for the skill.
  - The 13-block probe the Preview step was for (the **Pending** row above; `decisions.md`, **Ticket 24, question 3**) now runs through that tool (plan Phase 1, use 1). If a block contradicts a frozen PF2, PF3 or PS2 pattern, the pattern is fixed and re-frozen before any Codex iteration, with a new `evals_sha256`. C4's remedy (**Residual risk**) assumed a RED run, which D1 removes.
  - Its limit: GitHub does not publish its Mermaid version, so the check is against the pinned one.
- **D4:** the version is set once, to `0.2.0`, for the whole pull request.
- **D5:** the render proof (`:56`) and its approval (`:57`) move to [ticket 28](28-render-proof-in-a-github-post.md), which does not block the release. The state diagram the proof needs (**Residual risk**, **At Stage 4**) goes with it.
