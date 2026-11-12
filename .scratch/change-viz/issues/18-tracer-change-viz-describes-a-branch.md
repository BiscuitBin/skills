# 18: Tracer: `change-viz` describes a branch

**What to build:** a new shipped skill, `change-viz`. Invoked by name on a branch, it returns a short description of what the branch changes: one sentence of why, one to three notes, and a change outline with at least one fitting visual, each visual led in by one line. The description is the agent's final message, as GitHub-flavoured Markdown that renders in a pull request description or comment. No file is written unless the request asks for one.

Why: the maintainer describes a branch today by chaining two personal skills (`/show-me`, then `/visual-pr`). This skill does the describing in one step, and will later be the base of a skill that writes pull request descriptions. This ticket is the thin first slice through every layer: scaffold, by-name invocation, a fixture branch, eval cases on both agents, distribution. Tickets 19 to 24 each add one behaviour to it.

**Blocked by:** 16 (Eval cases can stage a git fixture), 17 (Eval cases can invoke a skill by name).

**Status:** ready-for-agent

**Agent requirements:** Any implementing agent (Claude Code or Codex). The maintainer runs the live evals in their own terminal, with the token, and reads the skill's output on one real branch before tickets 19 to 24 start. Cross-model review is also required.

## Decisions already made

The maintainer made these on 2026-11-10. Do not reopen them in this ticket.

- **Outline:** three headings, kept from `visual-pr`, in this order. Ticket 19 adds a risk line directly under the one-sentence why.

  ```markdown
  ## Why the change

  One sentence.

  ## Special things to note

  - 1 to 3 bullets.

  ## Change outline

  Short lead-in, then a visual. Repeat as needed.
  ```

- **Invocation:** by name only. `SKILL.md` sets `disable-model-invocation: true`, and `agents/openai.yaml` sets `policy.allow_implicit_invocation: false`.
- **Format:** Markdown for a GitHub pull request description or comment. Richer formats (HTML, artifacts) come later, perhaps as a separate skill.
- **Not this skill's job:** creating, editing or commenting on a pull request.

Two more were the planning agent's defaults. The maintainer approved the plan that stated them, but did not choose them from options:

- **Name:** `change-viz`, after the branch. It must not be `show-me` or `visual-pr`, which are the maintainer's personal skills and would collide in the contamination check. Confirm the name with the maintainer before scaffolding, because it is cheap to change only until then.
- **Where the output goes:** the description is the agent's final message, and no file is written unless the request asks for one.

The maintainer's words for the goal: "effective and clear communication through visualizations", "with just enough text to clear up any ambiguity", and output that does "not confuse or overwhelm the consumer" or "distract from and hide critical pieces".

## What is known

As of 2026-11-10.

- **Sources to adapt**, all MIT (the licence field of each repository, read through the GitHub API):
  - humanlayer/skills `show-me`: the catalogue of views (pseudocode, call tree, component tree, file tree, Mermaid, diff sketch, whole block) and "pick the smallest view that makes the key point clear".
  - humanlayer/skills `visual-pr`: the three headings, "exactly one sentence", "1-3 bullets", and a change outline that is a "structural view rather than prose or a file-by-file changelog".
  - mattpocock/skills `pr`: the merge danger section, used by ticket 19.
- **Not carried over:** `visual-pr` creates and edits the pull request and saves files under `.humanlayer/`. `show-me` can write an HTML file. Neither belongs here.
- **Credit form:** mattpocock's skill credits its source with a nested `metadata.credits` block. This repo's validator takes `metadata` as string to string, so that form fails.
- **Licence notices:** `.scratch/foundation/follow-ups.md` (D3) records that installed skills carry `license: MIT` but not the licence's copyright and permission notices. Adapted upstream text makes that gap matter here.
- **Stale prose:** `README.md` says the repo ships "currently just `cowsay`", and `docs/reference/distribution.md` says "currently `skills/cowsay/`" and quotes `Found 1 skill`.
- **Budget:** the grader reads at most 20 KB of the final message, which is also a sensible ceiling for a description.
- **Trial tools:** a trial has `git` and `python3` on its `PATH`, and Claude Code trials allow only the Skill, Read and Bash tools.
- **Four pull requests the maintainer likes**, written with the two personal skills: BiscuitBin/knarr#75, BiscuitBin/skills#1, BiscuitBin/skills#4 and BiscuitBin/rove#11. All are public. Read them for the level of detail and the mix of Mermaid, diff sketches, trees and tables. Ticket 25 compares against them; this ticket does not fit to them.

## Acceptance criteria

- [ ] The skill is scaffolded with `just new-skill change-viz`. No `TODO(new-skill)` is left, and `just validate-skills` reports no errors and no `[placeholder]` warning for it.
- [ ] It is by-name-only on both agents, with the two settings above. `agents/` holds only `openai.yaml`: a Markdown file there would become a Claude Code subagent (ADR 0010).
- [ ] Invoked by name on a fixture branch, it returns the three headings in order, with:
  - **Why the change:** one sentence.
  - **Special things to note:** one to three bullets, or `- None.`
  - **Change outline:** at least one visual that fits the change, each with a one-line lead-in. Not a file-by-file changelog.
- [ ] It describes the commits on the current branch since its base, and finds that base without assuming a remote exists. `GLOSSARY.md` gains **Change source**; a branch is the only one this ticket handles.
- [ ] The description is the final message. The skill writes no file unless the request asks for one, and changes nothing else in the repository it describes.
- [ ] Scratch output from developing the skill stays out of `skills/`. The validator treats every direct child of `skills/` as a skill and requires its `SKILL.md`, so a workspace folder beside the skill, which skill-creator makes by default, would be read as one. The repo's `just eval` runs take the place of skill-creator's own loop.
- [ ] Eval cases, on a fixture from ticket 16 and marked as invoked by name (ticket 17):
  - a behaviour case that asserts `skill_triggered`, the three headings in order, and a fenced visual, with `output_matches`
  - expectations for what a pattern cannot say, such as the why being one sentence and each visual having a lead-in
  - a plain request about the same branch with `should_trigger: false`, which shows the skill stays quiet
- [ ] The baseline arm fails the behaviour case on both agents. If it passes, the case changes until it measures a real gap (`CONTRIBUTING.md` §2).
- [ ] Credit and licence:
  - Text adapted from the three sources carries credit in a form the validator accepts.
  - Each upstream's MIT copyright and permission notice travels with the installed skill, since MIT requires it for substantial portions. The form is recorded here, and D3 in the follow-ups is updated to match.
- [ ] `README.md` and `docs/reference/distribution.md` no longer say cowsay is the only shipped skill, and the install round trips in `just check` pass with two.
- [ ] **Maintainer checkpoint:** the maintainer reads the skill's output on one real branch of their choosing, before tickets 19 to 24 start. Their feedback is recorded here and applied by changing what the skill explains, not by fitting that one branch.

### Every `change-viz` ticket

These repeat in tickets 18 to 24 so that each can be read alone.

- [ ] Eval cases are written and baselined before the skill text changes (RED, then GREEN), and each rubric is frozen before its live run (`CONTRIBUTING.md` §2 and §3). The baseline and skill-arm run ids on Claude Code and Codex are recorded here.
- [ ] Live evals are handed to the maintainer as absolute-path `just eval` commands. The agent reads `eval-results/` and never holds the token.
- [ ] Fixtures are a neutral project: no `skill` or `skills` wording anywhere in them, and none of Codex's sandbox-denial keywords (`operation not permitted`, `permission denied`, `read-only file system`, `seccomp`, `sandbox`, `landlock`, `failed to write file`) in output a failing command could print.
- [ ] Every "does not" outcome names how it is checked. A blinded expectation cannot be negative, so the check is an `output_matches` pattern, a transcript read by hand, or a limit stated in the completion notes.
- [ ] The skill explains why, not just what, and `SKILL.md` stays well under the validator's 500-line limit, with detail in `references/`.
- [ ] The skill's `plugin.json` version is higher than the one on `main` (ticket 18 keeps the scaffold's `0.1.0`), `just format` has run, the changes are committed, and then `just check` passes.

## Out of scope

Each of these is its own ticket: the risk line (19), rules for choosing among visuals and for length (20), evidence labels and running commands (21), uncommitted changes (22), pull requests (23), and GitHub rendering rules (24). A benchmark iteration is recorded in ticket 25.

## Review checkpoints

Use the `cross-model-review` dev skill.

- **Design checkpoint:** before the live run, get the eval cases, the frozen rubric and the credit form reviewed. Could the behaviour case pass on a description that is wrong about the fixture? Does any expectation need the grader to know which arm it is reading?
- **Implementation checkpoint:** before marking done, review the full diff against these acceptance criteria. Pay particular attention to instructions that only restate the template without saying why, to upstream text copied without its notice, and to anything in the skill that could write to the repository it describes.

## Completion notes

### Design checkpoint

Applied up to RED on branch `change-viz`, in commits `9b6e09e`, `34b0aad` and `9f10e71`, then the review fix `216a3c7`. P4 was added with the maintainer's decisions of 2026-11-11 (**Questions for the maintainer**), and narrowed with f3 under question 7, whose focused review found nothing (**P4 review**, round 2). The branch is on `origin/change-viz`, so CI runs on what is pushed. No live eval has run.

No acceptance box is ticked yet. The commits already meet the scaffold criterion, the by-name criterion and the prose criterion (with the round trips installing two skills), but each box waits for the implementation checkpoint. Everything else waits for RED, GREEN, the credit and glossary records, or the maintainer's read of a real branch.

#### What was built so far

- **Scaffold (`9b6e09e`).** `just new-skill change-viz`, with every `TODO(new-skill)` replaced.
  - `SKILL.md`: `name: change-viz`, `license: MIT`, `disable-model-invocation: true`, and a neutral 124-character RED description: "Describes what the current branch changes, as Markdown for a pull request. Runs only when invoked by name, never on its own." The body is `# Change Viz` and one stub line, "Describe what the current branch changes."
  - `agents/openai.yaml`, the only file in `agents/`: `display_name: 'Change Viz'`, a 43-character `short_description` ("Describe a branch as a short visual outline") and `policy.allow_implicit_invocation: false`.
  - `.claude-plugin/plugin.json` keeps version `0.1.0`. Its description, "Describe what a branch changes, as a short Markdown outline with visuals for a pull request. Invoked by name only.", was copied by `just format` into the `change-viz` entry of `.claude-plugin/marketplace.json`.
  - No `metadata.credits` and no `NOTICE.md` yet: they land with the first upstream text.
- **Fixture (`34b0aad`).** `evals/change-viz/fixtures/wordstat-top/`: a standard-library Python word-count CLI with four root files, `README.md`, `sample.txt`, `wordstat.py` and `test_wordstat.py`. Both scripts start with a shebang and are listed in `executable`, so they are `100755`. Five trees hold 19 files from 11 versions.
  - `main` has two commits: "Add the word count command" and "Print the number of distinct words".
  - Branch `add-top-words` has three: "Count words without case or surrounding punctuation", "Add --top to list the most common words" and "Document the --top option".
  - No `staged` and no `worktree`, so `git status` is clean. There is no remote and no `origin/main`, so the base is local `main`.
  - The branch changes `wordstat.py`, `test_wordstat.py` and `README.md`. The last commit alone shows only the README's `--top` text, so describing the new word handling needs commit 1 or the diff against `main`.
  - It is neutral: no skill wording and none of Codex's denial keywords, which `validate-evals` checks.
- **Cases (`34b0aad`; E2 reworded at `216a3c7`; P4 added on 2026-11-11 and narrowed with f3).** `evals/change-viz/evals.json` has two cases on `wordstat-top`, both with the prompt "Describe what this branch changes.":
  - `behaviour-describe-branch`, marked `by_name: true`;
  - `no-trigger-unnamed-request`, an unmarked trigger case with `should_trigger: false`, which the baseline arm skips.
- **Assertions (frozen):**
  - `skill_triggered`.
  - `output_contains` `--top`, a guard against describing the wrong change.
  - P1: the three `##` headings in order, with no fence opening before `## Why the change`.
  - P2: between `## Special things to note` and `## Change outline`, only one to three bullets at column 0 (indented continuation lines and blank lines allowed) and an optional thematic break. `- None.` passes.
  - P3: a fenced block, backtick or tilde, opens and closes after `## Change outline`, with no `#` or `##` heading in between.
  - P4: under `## Why the change`, one paragraph of non-blank lines, none starting with whitespace, `#` or `**Risk:`; then optionally a block starting `**Risk:` or one thematic break; then `## Special things to note`. The maintainer added it on 2026-11-11 (question 2) and narrowed it with f3 the same day (question 7).
- **Expectations (frozen).** E1 to E7 are graded blind. E8 is graded from the transcript.
  - E1: the first paragraph under 'Why the change' is a single sentence.
  - E2: that paragraph says what the branch makes possible: listing the most common words, treating words that differ only in case or surrounding punctuation as the same word, or both.
  - E3: under 'Change outline', every diagram or code block is directly preceded by its own one-line lead-in that says what it shows.
  - E4: at least one diagram or code block, anywhere in the description, shows the `--top` listing or the new case and punctuation handling as part of how wordstat works.
  - E5: the description says the branch adds `--top`, listing the most common words with how many times each occurs.
  - E6: the description says words are now lower-cased and stripped of surrounding punctuation before counting.
  - E7: the description warns that, because words are now lower-cased and stripped before counting, counts for existing input can be lower than before, such as the distinct count.
  - E8 (`needs_transcript`): a command compares the branch with local `main`, such as `git log main..HEAD`, `git diff main...HEAD` or `git merge-base HEAD main`.
- **Prose (`9f10e71`).** `README.md` and `docs/reference/distribution.md` no longer say cowsay is the only shipped skill, and give no count, so the next skill does not make them stale.
  - README: "The shipped skills are `cowsay` … and `change-viz` …", an `## Install` heading, a `claude plugin install change-viz@biscuitbin-skills` line, and invocation lines written with `<name>`.
  - Distribution reference: "one plugin per skill", the install check lists every shipped skill, and `Found <n> skills` replaces `Found 1 skill`.

#### Checks run

- `just check` passed at `9f10e71` (`ai_tmp/gate-18.log`) and again at `216a3c7` (`ai_tmp/gate-18b.log`), exit 0. pytest: 1202 passed, 4 skipped (two case-folding tests on macOS, two CI-only canaries). `validate-evals`: "2 eval suites valid." Claude Code 2.1.309, Codex 0.163.0. The install round trips installed two skills on every `skills` channel; the marketplace round trip still installs only cowsay.
- `just validate-skills`: 0 errors. The one warning is the expected `[extension-portability]` on `disable-model-invocation`. No `[placeholder]`.
- `just validate-distribution`: the pinned `claude plugin validate --strict` accepts `disable-model-invocation`. Its only remark is the `ICON_MISSING` warning that cowsay also gets.
- **P1 to P3 under Python `re`, before P4** (`ai_tmp/apply-18/patterns.py`): no difference from the PCRE2 results over the four liked pull requests and their copies, HumanLayer's template, `visual-pr`'s and `pr`'s `SKILL.md`, 13 synthetic messages and nine inline controls. A message with `\r\n` endings fails all three, as expected.
- **Fixture,** built with `fixture.build` and run with `python -B`: the facts listed under **Design as approved**, all as predicted. Tests: 2 OK at `main`, 4 after `folded`, 5 at the tip. `git status` is clean, both scripts are `100755`, `HEAD` is `refs/heads/add-top-words`, `git diff --stat main...HEAD` names three files, and `git show --stat HEAD` names only `README.md`. No `__pycache__/` was left.
- **Installer:** `skills add` of this checkout, for `claude-code` and for `codex`, printed `Found 2 skills`, `✓ change-viz (copied)` and `✓ cowsay (copied)`. Nothing was written to `~/.agents`.
- **After P4 (2026-11-11):**
  - `just format`, then `just validate-evals`: "2 eval suites valid."
  - `ai_tmp/apply-18/patterns.py` now runs all four patterns and asserts that P4 equals the block under question 2. It gives 0 differences on 30 inputs. Its unbolded `Risk: Low.` control now expects P4 to fail, and a copy with `**Risk: Low.**` passes all four.
  - `ai_tmp/apply-18/p4_probe.py` now also asserts that P4 equals the fourth `output_matches` in `evals.json`. It gives 0 differences on 31 inputs.
  - Some P4 expected values were read from the pattern by hand: HumanLayer's template, Matt Pocock's `SKILL.md` and the inline controls. `rg -U --pcre2` gave each of them.
  - `just check` passed at `227eb93`: 1202 passed, 4 skipped (two case-folding tests on macOS, two CI-only canaries).
- **After f3 (2026-11-11, question 7):**
  - `evals.json`'s P4 is the committed P4 with f3's one substitution from `ai_tmp/triage-pre-red.md`, and it equals f3's line in `ai_tmp/triage-pre-red/probe.out`.
  - `just format`, then `just validate-evals`: "2 eval suites valid." `evals_sha256` for `change-viz` is now `78828f74f0a72581d29d915ba3e3cfb1ccfcde1701c1622dc3d83d53ba5726d2`; it was `c49b1f3fc64d1fc057715cf37e06b300689e47d5e154e726262879df01b26fd6` at `227eb93`.
  - `ai_tmp/apply-18/patterns.py` asserts that P4 equals the block under question 2, which now shows the narrowed pattern. It gives 0 differences on 31 inputs. Its new row, a why section that is only a `**Risk:` line, passes P1 to P3 and fails P4.
  - `ai_tmp/apply-18/p4_probe.py` asserts that P4 is the triage's P4 with f3 applied, and equals the fourth `output_matches` in `evals.json`. It now also runs the 17 rows of the pre-RED triage's `probe.sh`, and runs every input through P4 before f3 as well. It gives 0 differences on 48 inputs, so Python `re` gives the PCRE2 f3 column on every row. f3 changes two results, both from pass to fail: a why section that is only a `**Risk:` line, and a `**Risk:` line before the sentence. Every other result is unchanged.
  - `ai_tmp/triage-pre-red/p4_timing.py` now reads P4 before f3 from `227eb93` and asserts that f3 is the committed P4 (output in `p4_timing-f3.out`). Before f3: 0.096 s, 0.867 s and 9.459 s at 12, 36 and 120 KB. After: 0.000 s, 0.001 s and 0.003 s.
  - `just check` passed at `3d3dc4b`: 1202 passed, 4 skipped (the same four).
- **Runner probe (2026-11-11, before RED):** the committed suite ran through `run_suite` with the pinned CLIs against the fake APIs (both agents, both arms, plus a Claude quiet-case trial that reads `SKILL.md`). Every plumbing check passed: Claude's trigger comes from the session record, Codex's prompt is `$change-viz:change-viz …` with an explicit event, the baseline and every grader request carry the bare request, the inventory and contamination pass in both arms, and the quiet case fails only on the confirmed read. `just eval change-viz --agent <claude|codex> --baseline --dry-run` needs no token and plans 3 trials per agent. Scripts in `ai_tmp/probe-red/`.
- **Not run:** the live runs, Ubuntu CI (`ci.yml` runs on pull requests and on pushes to `main` only, so the pushed branch started no run), and the marketplace install of `change-viz` (`claude plugin install change-viz@biscuitbin-skills`, `/change-viz:change-viz`), because the marketplace round trip installs cowsay only.

#### Implementer decisions (2026-11-11)

**Name.** `change-viz`, confirmed by the maintainer on 2026-11-10, before scaffolding, in the stage plan's "Decided with the maintainer". That plan is not in this repository, so the confirmation is recorded as the implementer's brief relayed it.

The implementer made the rest at apply time, on the design's open questions. On 2026-11-11 the maintainer kept the three departures among them: the neutral RED text, and the two notice timings under **Notices**. The answer named no override (question 6).

- **Neutral RED text, a departure from the plan.** The plan said to set the description at scaffold and keep the scaffold's stub. RED instead ships the neutral description and the one-line stub above, and the full description lands at GREEN. Two reasons:
  - Codex injects the whole `SKILL.md`, frontmatter included (ticket 17's spike), so a full description would show Codex's RED skill arm the outline the case tests.
  - The scaffold's stub reaches the skill-arm agent and names "skill" and "baseline".

  The `plugin.json` and picker descriptions mention visuals. Neither is known to reach the agent (the spike shows Codex injecting only `SKILL.md`; whether Codex shows either string is unobserved). If one does, both move to neutral wording.
- **Quiet prompt:** the quiet case reuses the behaviour prompt word for word, so the invocation is the only difference.
- **E7's strictness: kept.** The warning must say counts can be lower; "can change" fails.
- **A wrapped description fails.** P1 fails a description fenced or wrapped whole for copying. A `markdown` fence inside the outline still passes.
- **E2 and E4 scope: as drafted.** E4 is heading-free, so it measures the visual in both arms. E2 reads the first paragraph under 'Why the change', because a heading-free E2 would restate E5 and E6.
- **Notices: the form now, the files later.** `NOTICE.md` and `metadata.credits` land in the commit that first ships upstream text: HumanLayer's at GREEN, Matt Pocock's with ticket 19, which adapts his text. This repository's own notice is not added to `NOTICE.md`, so D3 stays open for it.
- **Trials:** `just eval`'s default, one trial per case per arm.

#### Credit form (applied at GREEN)

At GREEN the frontmatter replaces the RED description with the full one and adds a string `metadata.credits`. The other fields stay as at RED:

```yaml
description: Describes what the current branch changes, as Markdown for a pull request description or comment, with one sentence on why, one to three notes and a change outline built from small visuals such as Mermaid diagrams, diff sketches and file trees. Runs only when invoked by name, never on its own. It reads the branch and writes no file unless asked.
metadata:
  credits: 'Adapted from MIT-licensed work by HumanLayer (Copyright (c) 2026 HumanLayer). The full notice is in NOTICE.md.'
```

- **The credit string departs from design §5** (D2 under **GREEN**). The design's string was 'Adapted from show-me and visual-pr by HumanLayer (Copyright (c) 2026 HumanLayer), MIT. The full notice is in NOTICE.md.'. Codex injects the frontmatter, and it named two upstream skills that can be installed on a user's machine under the same names, one of which commits, pushes and edits pull requests. The string applied keeps the copyright holder and leaves the names to `NOTICE.md`, which is not injected.
- **Why a string.** The validator requires `metadata` to map strings to strings, so mattpocock's nested `metadata.credits` fails. Codex 0.163.0's parser ignores unknown `metadata` fields (a source read of `codex-rs/skills/src/parser.rs`, not a run), and skills@1.7.4 reads `metadata` only for `internal`.
- **No "skill" wording.** Neither string uses the word or the slug `humanlayer/skills`, because Codex injects the frontmatter and the disclosure check would match. Since D2, neither names an upstream skill either. The URL is in `NOTICE.md`.
- **`skills/change-viz/NOTICE.md`,** beside `SKILL.md`: a `# Notices` heading, then "Parts of change-viz are adapted from an MIT-licensed project. Its copyright and permission notice follows, as its licence requires for copies and substantial portions." Then a `## HumanLayer` section:
  - source: [humanlayer/skills](https://github.com/humanlayer/skills) at commit `4d69d20f6e9b57b4fcf0d501ccfb1be961f0f329`, the `show-me` and `visual-pr` skills;
  - adapted: the three headings of the outline and their limits, the kinds of note, the catalogue of views and the rules for choosing and trimming them, the lead-in above each visual, and the plain-language style (D3 under **GREEN**; design §5 named only the headings, the catalogue and the smallest-view rule);
  - the upstream `LICENSE`, `Copyright (c) 2026 HumanLayer`, copied byte for byte into a `text` fence.
- **Ticket 19's entry.** Ticket 19 adds a `## Matt Pocock` section in the same shape: [mattpocock/skills](https://github.com/mattpocock/skills) at commit `4ae2317ddb22b046e26455e4f9c9b3aaaf62212d`, the `pr` skill; adapted, the merge-risk terms, one-way and two-way doors and blast radius; his `LICENSE`, `Copyright (c) 2026 Matt Pocock`. It changes the intro to "from two MIT-licensed projects. Their copyright and permission notices follow, as their licence requires", and extends the credit with "and from Matt Pocock (Copyright (c) 2026 Matt Pocock)". Design §5 had "and the merge-risk terms from pr by Matt Pocock (Copyright (c) 2026 Matt Pocock)"; this follows D2 in leaving upstream skill names to `NOTICE.md`.
- **No link from the body,** and no licence line: applied as written. Both installers copy the whole skill directory, and a body line would reach every Claude Code expansion. The `skills` round trips compare each installed copy with every file in `skills/<name>/`, so `NOTICE.md` travelling is tested there. For the marketplace it is reasoned, not tested. The GREEN draft ended with a `## Credits` line that linked `NOTICE.md`; it came from an error in the brief, not a decision, and was removed at apply (D1 under **GREEN**).
- **Fallback.** If the pinned `claude plugin validate --strict` rejects `metadata` at GREEN, drop `metadata.credits`, keep `NOTICE.md`, and credit in one body line that links it. Not taken: it passed, though it turned out not to read the frontmatter (**GREEN**, **Checks run before the commit**).
- **Records at GREEN.** This ticket records the form, and D3's row in `.scratch/foundation/follow-ups.md` says `change-viz` carries its upstream notice. Both landed with `NOTICE.md`.

#### Cross-model review

- **Implementer:** Claude Code running Claude Opus 5.5 (`claude-opus-5-5`), per the commits' trailers. The review script recorded no implementer model.
- **Reviewer:** Codex `gpt-6-astra` (fallback: no)
- **Reviewed:** `5b618de...9f10e71`, with the design proposal `ai_tmp/design-18.md`, before any live run
- **Findings:** `ai_tmp/review-20261111T121803Z-codex.md` · **Triage:** `ai_tmp/triage-design-18.md`
- **Fix commit:** `216a3c7`. The other fixes are to the design text.

| # | Severity | Finding | Verdict | Action |
| --- | --- | --- | --- | --- |
| 1 | medium | E4 accepts a visual of wordstat's output without checking its values. A description showing `--top 3` as `the 6`, `river 3`, `mill 2` passes every pattern, and the blinded grader never sees the fixture. | valid (narrow, and already disclosed; low is closer) | Nothing frozen changes. The limit is stated here: each skill-arm message gets a hand read against the fixture facts under **Design as approved**, and a contradiction is recorded here as wrong about the fixture, whatever its grade. A values clause on E4 was question 1, not recommended, and the maintainer declined it on 2026-11-11. |
| 2 | medium | E2's "counting a word once whatever its case or surrounding punctuation" can be read as counting repeats once, but the branch keeps every occurrence | valid (low is closer) | Fixed in `216a3c7`: E2 now reads "treating words that differ only in case or surrounding punctuation as the same word". It changes `evals_sha256`, before RED. The reviewer's "while retaining their occurrence counts" is not adopted: it adds a requirement a correct one-sentence why need not meet. E2's first-paragraph scope and its "or both" do not change. |
| 3 | medium | E1 and E2 read only the first paragraph, so further paragraphs under "Why the change" pass, against the ticket's one-sentence why | valid | The limit is stated here, with a hand read of each skill-arm message (the "does not" table under **Design as approved**). A fourth `output_matches`, P4, was question 2, recommended. The maintainer took it on 2026-11-11, and it is in `evals.json` after P3. The hand read stays for what P4 leaves open. |

**The checkpoint's two questions.** Could the behaviour case pass on a description that is wrong about the fixture? In part, yes: E4 checks no values, and an extra false claim elsewhere can pass (finding 1), so the hand read covers it. Does any expectation need the grader to know which arm it is reading? No. Each is about text in the material, and E1 to E3 fail in the baseline because its message has no such headings.

No second round: the only frozen change rewords one clause of E2 and keeps its scope. The other two fixes are design text: a hand-read row and a list of facts. The maintainer took P4, a new frozen assertion, so it gets a focused review before RED.

#### P4 review

A focused cross-model round on P4 before RED, shared with ticket 16's /code-review fixes, which drew no finding.

- **Implementer:** Claude Code running Claude Opus 5.5 (`claude-opus-5-5`), per the commits' trailers. The review script recorded no implementer model.
- **Reviewer:** Codex `gpt-6-astra` (fallback: no)
- **Reviewed:** P4 as added in `227eb93` (`evals/change-viz/evals.json:29`), against **Decisions already made** and the acceptance criteria. The brief asked whether P4 passes every correct description, including ticket 19's risk line, whether it fails extra prose under the why, and whether it is safe under Python `re` as the harness applies it.
- **Findings:** `ai_tmp/review-20261111T185340Z-codex.md` · **Triage:** `ai_tmp/triage-pre-red.md`, whose candidates f1, f2, f3 and f23 are substitutions into P4, probed under PCRE2 (`ai_tmp/triage-pre-red/probe.sh` and `probe.out`)
- **Timing:** `ai_tmp/triage-pre-red/p4_timing.py`, run under Python 3.14.8 `re` after the review, output in `p4_timing.out`; rerun after f3, output in `p4_timing-f3.out`

| # | Severity | Finding | Verdict | Action |
| --- | --- | --- | --- | --- |
| 1 | medium (triage: low) | After a `**Risk:` line, P4 lets anything through up to the next level-two heading, so an extra paragraph after the risk line passes | valid, already disclosed under question 2's costs and **Pattern limits**. The reviewer's premise, that the decided risk content is a single line, is wrong: ticket 19's block is a line, a blank line and two bullets, so a one-line limit would fail a correct ticket 19 description | Not taken (question 7). The limit stays under **Pattern limits**: ticket 18's runs carry no risk line, and the hand read covers what follows one. f1 is passed to ticket 19's design checkpoint (**Room for tickets 19 to 24**): once its block is frozen, narrow P4's risk branch with f1 (the `**Risk:` line, at most two column-0 bullets with indented continuations, then an optional thematic break) |
| 2 | medium (triage: low) | P4 fails a why indented one to three spaces, or wrapped with an indented continuation line, though GitHub renders both as one paragraph. `\r\n` endings fail too | valid, already disclosed under question 2's costs and **Pattern limits**. The `\r\n` part changes no result: P1 to P3 already fail `\r\n` endings, and no recorded agent message uses them | Not taken (question 7); a stated limit under **Pattern limits**. The GREEN text writes the why sentence at column 0, as the decided outline does, and the hand read notes an indented one. f2 (up to three spaces before the first line, any indent after) would trade this false fail for a false pass: an indented bullet or fence directly under the sentence. `\r\n` handling would be a harness change for every suite, out of scope |
| 3 | medium (triage: low) | P4 backtracks quadratically when many `**Risk:` lines sit in the why paragraph and the match fails, and scoring has no regex timeout or size cap | valid. Timed on the reviewer's input: 0.093 s at 12 KB, 0.843 s at 36 KB and 9.370 s at 120 KB. A slow score, not a wrong verdict, on a shape no description the skill asks for has | Fixed with f3 (question 7), in the commit that records this: no column-0 `**Risk:` line inside the why paragraph, so the match is linear. At 120 KB, f3 took 0.003 s where P4 before f3 took 9.459 s, in the same run. f3 also fails a why section that opens with `**Risk:` before any sentence, which breaks the decided order |

The maintainer took f3 under question 7, a frozen change, so f3 got its own focused review before RED.

**Round 2 (f3):**

- **Implementer:** as in round 1.
- **Reviewer:** Codex `gpt-6-astra` (fallback: no), on the first attempt, with no rejected run
- **Reviewed:** `7816385` (base `1e0826d`), the f3 change to P4 (`git diff 1e0826d...HEAD -- evals`), from the brief `ai_tmp/brief-p4-f3.md`. The brief asked whether f3 is linear on every input, whether it still passes every correct description the decided outline allows, ticket 19's risk block included, whether it still fails a second paragraph under the why, and whether anything else about P4 is now wrong.
- **Findings:** `ai_tmp/review-20261111T204553Z-codex.md` · **Triage:** `ai_tmp/triage-p4-f3.md`
- **Probes,** rerun by the triage at `7816385` with no review running: `p4_probe.py` gave 0 differences on 48 inputs, and `patterns.py` 0 differences. `p4_timing.py` gave f3 0.000 s, 0.001 s and 0.003 s at 12, 36 and 120 KB, against 0.096 s, 0.855 s and 9.570 s for P4 before f3 in the same run. That shows linear growth on finding 3's input, not on every input. `git status` stayed clean.

| # | Severity | Finding | Verdict | Action |
| --- | --- | --- | --- | --- |
| – | – | No numbered finding. The review's whole text is "No new findings in f3; the previously accepted f1 and f2 limitations remain." | The remark is true, and out of scope: the maintainer decided f1 and f2 under question 7. The probe still passes both rows with an extra paragraph after a `**Risk:` line (f1's limit), and still fails the indented-why and `\r\n` rows (f2's limit) | None. No frozen change and no further review round. RED runs from the current head of `change-viz` (**Next**) |

#### Questions for the maintainer

The maintainer answered questions 1, 2, 3, 4, 6 and 7 on 2026-11-11, as the briefs relay the answers. Question 5 has the implementer's default, applied at GREEN, which the maintainer confirms at Hand-off 2.

1. **A values clause on E4** (finding 1). **Decided: no clause.** The hand read against the fixture facts covers the gap (the "does not" table under **Design as approved**), and E4's text does not change. The clause would have appended "If it shows wordstat's output for sample.txt, that output is …". The recommendation was no, for these reasons:
   - A pass needs a verbatim quote, and the burden of proof is on passing, so a correct visual made only of a diagram risks failing it.
   - The negative form ("shows no wrong counts") is barred for a blinded expectation.
   - Requiring the numbers would push the agent to run the fixture's code, which ticket 21 owns.
   - It would still miss wrong output for a made-up example text, and the hand read covers the gap.
2. **P4, one paragraph under 'Why the change'** (finding 3). **Decided: added**, after P3. The recommendation was yes: the decided outline and the criteria say "One sentence", and ticket 19's `**Risk: …**` line is a shape the maintainer decided on 2026-11-10.

   The block below is P4 as frozen: the pattern added in `227eb93`, narrowed with f3 under question 7. f3 adds only the lookahead `(?!\*\*Risk:)` at the start of each paragraph line, so no line of the paragraph starts `**Risk:`.

   ```json
   {
     "type": "output_matches",
     "pattern": "(?ms)^##[ \\t]+Why the change[ \\t]*\\n(?:[ \\t]*\\n)*(?:(?!\\*\\*Risk:)[^\\s#][^\\n]*\\n)+(?:[ \\t]*\\n)*(?:\\*\\*Risk:(?:(?!^##[ \\t]).)*?|(?:[-*_][ \\t]*){3,}\\n(?:[ \\t]*\\n)*)?^##[ \\t]+Special things to note[ \\t]*$"
   }
   ```

   - **What it requires:** under `## Why the change`, one paragraph of non-blank lines, none starting with whitespace, `#` or `**Risk:`; then optionally a block starting `**Risk:` or one thematic break; then `## Special things to note`.
   - **Probed:** Python `re` gives the triage's PCRE2 results on 31 inputs (`ai_tmp/apply-18/p4_probe.py`). It matches the four liked pull requests, ticket 19's shape, and a label inline on the sentence or on the next line. It fails the reviewer's probe, a fence or bullet after a blank line, and a label as its own paragraph.
   - **Costs:** it is lenient when a bullet or fence sits directly under the sentence, and after `**Risk:`. A one-space indent fails, and so do `\r\n` endings. Ticket 21's label would fail if set as its own paragraph. Since f3 (question 7), a why section that starts with `**Risk:` fails too.
   - **RED:** no expected effect (unobserved): neither arm writes the heading, so P4 fails in both, as P1 does.
   - **Done:**
     - P4 is in `evals.json`.
     - `ai_tmp/apply-18/patterns.py` has its count assert, its expected columns, and a bolded `**Risk:` copy of its unbolded `Risk: Low.` control, which P4 rejects.
     - `just format` and `just validate-evals` ran, and the change is committed (**Checks run**).
   - **Reviewed:** the focused review found three limits, two already disclosed above and one under **Pattern limits** (**P4 review**). Question 7 took f3 for the third, and the block above includes it. Round 2, on f3, found nothing.
3. **"One-line lead-in" in E3.** **Decided: one physical line of one to three sentences**, as the four liked pull requests write their lead-ins, not one sentence. E3's text does not change.
4. **`__pycache__/` as a write.** **Decided by the maintainer on 2026-11-11: ignored.** Writes under `__pycache__/` (`*.pyc` files) are ignored in the writes hand check (the "does not" table under **Design as approved**). So the skill gets no "read the branch, do not run its code" line: its text neither forbids nor invites running code, and ticket 21 owns running code. The hand read still lists each command that runs the fixture's code, as a record for ticket 21. The question was: the design counts it, through the hand read, and reports it on its own line as "ran the fixture's code". If GREEN trials leave one, is that a ticket 18 failure, which needs that line in the skill now, or a limit recorded for ticket 21? No frozen text changes.
5. **ADR 0008.** **Answered with the implementer's default, which the maintainer confirms at Hand-off 2.** ADR 0008 gains a second sentence, which landed with `NOTICE.md` at GREEN: "Text adapted from another MIT-licensed project keeps that project's copyright and permission notice, in a `NOTICE.md` beside the skill that carries it." The question was: it says everything in the repository is under `LICENSE`. With an upstream notice beside a skill, does it need a sentence? The decision left this to the design review, which did not raise it.
6. **Overrides.** **Decided: the maintainer kept all three implementer departures:**
   - the neutral RED description and stub body;
   - `NOTICE.md` and `metadata.credits` landing with the first upstream text, with no `SKILL.md` link before then;
   - Matt Pocock's notice shipping with ticket 19, though "each upstream's" notice can be read as all three at 18.

   The answer did not address the other implementer decisions, so they stand as the implementer made them. Among them, this repository's own notice stays out of `NOTICE.md`, so D3 stays open for it.
7. **P4 after its focused review** (**P4 review**). **Decided: f3, before RED, with a focused review round.** The recommendation had been no change.
   - **f3 (finding 3): taken.** It keeps column-0 `**Risk:` lines out of the paragraph group, so the risk branch starts once, at the first `**Risk:` line after the paragraph, and the match is linear. A bounded scoring time is worth having before the rubric freezes, and the cost is small: f3 newly fails only a why section that starts with `**Risk:`, which breaks the decided order (the sentence first, the risk line under it; ticket 19). Timing on finding 3's input under Python 3.14 `re` (`p4_timing-f3.out`): before f3, 0.096 s, 0.867 s and 9.459 s at 12, 36 and 120 KB; after, 0.000 s, 0.001 s and 0.003 s. Python `re` gives the PCRE2 results on all 48 of `p4_probe.py`'s inputs, and f3 changes only the two risk-first rows (**Checks run**, after f3). It is in `evals.json` and in the block under question 2.
   - **f1 (finding 1): not taken.** It would freeze ticket 19's block before that ticket's design checkpoint, and changes nothing ticket 18's runs measure. It goes to ticket 19's design checkpoint as a note (**Room for tickets 19 to 24**), and the leniency after `**Risk:` stays a stated limit (**Pattern limits**). Ticket 19 has no section for notes from earlier tickets, so the note is kept here.
   - **f2 (finding 2): not taken.** It trades a rare false fail for a rare false pass. Indented why lines failing stays a stated limit (**Pattern limits**), and the GREEN text writes the why sentence at column 0.

#### Design as approved

**Design as approved:** `ai_tmp/design-18.md` (gitignored), as reviewed at this checkpoint, with the fixes above and the maintainer's decisions of 2026-11-11 (its **Maintainer decisions (2026-11-11)** section). These bullets carry what exists only in that file:

- **Freeze.** `evals_sha256` covers `evals.json` and the fixture directory. The rubric does not change from the RED run to GREEN. Of the three possible changes before RED, the maintainer took only P4, which landed after `just format` and `just validate-evals`. E4 and E3 keep their text. P4's focused review is done (**P4 review**), and question 7 narrowed P4 with f3, which also landed after `just format` and `just validate-evals`. f3's own focused review (**P4 review**, round 2) found nothing, so the rubric is as at `7816385`, and RED runs from the current head of `change-viz` (**Next**).
- **Grader material.** The blinded call sees the bare prompt, never the invocation, the final message up to 20 KB, and any file the agent created or changed. Fixture files left as built are not sent, so each expectation carries its own facts. E8 is judged in a second call from the commands and their output. No expectation refers to another, so the canary's random place changes nothing.
- **Pattern limits.** P2 reads bullet markers at column 0 only: an indented marker, or an unindented wrapped line, fails on purpose, since allowing one would let four bullets pass as one. So the GREEN text writes note bullets at column 0 with indented continuations. P2 also reads an indented `- b` after `- a` as a continuation, though GitHub renders two bullets, and passes nested bullets. P4 is lenient when a bullet or fence sits directly under the sentence with no blank line. It is lenient after a `**Risk:` line too: anything up to the next level-two heading passes, so an extra paragraph after the risk line passes (finding 1). f1 would bound that branch to ticket 19's block, and is passed to ticket 19 (**Room for tickets 19 to 24**). A why line indented one to three spaces, or a wrapped why whose continuation line is indented, fails P4, though GitHub renders either as a paragraph (finding 2; f2 not taken). So the GREEN text writes the why sentence at column 0. Since f3, a why section that starts with `**Risk:`, before any sentence, fails P4; the decided order puts the sentence first. f3 made P4 linear: 0.003 s on a 120 KB message of `**Risk:` lines, where P4 before f3 took 9.459 s (**P4 review**, finding 3). P1 and P3 are still polynomial on their own pathological inputs (inferred, not timed), and scoring has no regex timeout. `\r\n` endings fail all four patterns.
- **Room for tickets 19 to 24.** P1 allows prose before the first heading (ticket 22's scope line) but no fence, and anything between the headings. P4 narrows the room under the why: one paragraph, then only a block starting `**Risk:` (ticket 19's line) or one thematic break. Since f3, the risk line must come after the sentence, not before it. For ticket 19's design checkpoint: once its block is frozen, narrow P4's risk branch with f1 from `ai_tmp/triage-pre-red.md` (the `**Risk:` line, at most two column-0 bullets with indented continuations, then an optional thematic break), which closes finding 1's leniency. Ticket 21's label passes inline on the sentence or on the next line, and fails as its own paragraph. E1 and E2 read only the first paragraph. P3 needs a fence under the outline, so a table-only outline (ticket 20) fails this case; a table can sit beside a fence. Ticket 19 asserts only its line's shape on this case and brings its own fixtures. Ticket 22 needs its own fixture, or a copy of these trees with `staged` and `worktree`. Ticket 23 can reuse this one (no remote). Ticket 24 can reuse it for Mermaid labels with parentheses.
- **GREEN gain,** recorded three ways: shape (P1 to P4, E1, E3); substance measured in both arms (E4 to E7); and E2, substance that passes only once the heading exists. E5, E8, and maybe E4 and E6, will show as non-discriminating. They stay as guards that make a wrong description fail. E6 may pass at RED on Claude Code if its startup context lists the commit subjects; the RED transcripts confirm it.
- **Disclosure reads.** In the skill arm the CLI's own text says "skill", so an echo marks the trial `arm_disclosed`, and it is still graded. E8's transcript material widens the check: on Codex at GREEN, a `cat` of the skill's files likely sets the flag. So read `disclosure_matches` in each grading file and look for each match in the final message; only those reached the blinded call. A bare `change-viz` or `Change Viz` is not flagged, so run `rg -i 'change[- ]?viz'` over each skill-arm final message and report hits beside `arm_disclosed`.
- **Records.** `GLOSSARY.md` gains **Change source** at GREEN: a branch is the only one this ticket handles. The run ids of RED and GREEN, both arms, both agents, go here; the RED ids also go to ticket 17, which closes its live-trial criterion.
- **Codex and `metadata.credits`.** To see a load failure before the GREEN live run, load the GREEN `SKILL.md` in the pinned Codex against the fake API, as `tests/evals/test_codex_adapter.py` does, and look for `failed to load skill`.

"Does not" outcomes and their checks. A blinded expectation cannot be negative, so each is a pattern, a hand read, or a limit stated here.

| Outcome | Check |
| --- | --- |
| No more than three notes | P2 |
| No prose under 'Why the change' beyond its one sentence | P4: one paragraph, then only a `**Risk:` block or one thematic break. Plus a hand read of each skill-arm message for what P4 leaves open: a bullet or fence directly under the sentence with no blank line, and anything after a `**Risk:` line. E1 and E2 read only the first paragraph. |
| Loads only when named | The quiet case, a lower bound (it sees only a confirmed load), plus a hand read of its transcripts |
| Not a file-by-file changelog | E4's positive form, plus a hand read of the skill-arm messages |
| Not wrong about the fixture | `--top`, E2 and E5 to E7 carry the facts. Limit: E4 checks no values (the maintainer declined a values clause, question 1), and an extra false claim can pass. So each skill-arm message gets a hand read against the facts below, and a contradiction is recorded here whatever its grade. |
| Writes no file | By hand, in each kept trial workspace: `git status --porcelain --untracked-files=all` lists nothing but files under `__pycache__/` (the installed skill is excluded). Files under `__pycache__/` (`*.pyc`) are ignored, by question 4's answer; `find . -name __pycache__ -not -path './.git/*'` lists them, and they are reported on their own line as a record that the trial ran the fixture's code. |
| Changes nothing else in the repository | By hand: `main`, `add-top-words` and the symbolic `HEAD` (`refs/heads/add-top-words`) match a baseline trial's. A `git checkout`, `switch`, `stash` or `worktree add` is an `infra_error` on Codex, whose sandbox denies writes to `.git/`, and any such trial is listed here under the Codex limits. On Claude Code it succeeds, and this check catches it. |
| Creates, edits or comments on no pull request, and pushes nothing (added at GREEN) | A stated limit: a trial has no `gh` on its `PATH` and the fixture has no remote, so no eval can show it. Checked by hand in the maintainer's real-branch read, which disables `push` and `gh` and lists every `gh` and `push` command in both transcripts; there should be none. Ticket 23 brings a case with `gh`. |
| Does not refer to itself as a skill (added at GREEN) | `disclosure_matches` read against each final message, plus `rg -i 'change[- ]?viz'` over each skill-arm final message (**Disclosure reads**), plus a look for a credit line or the names "HumanLayer", "show-me" and "visual-pr" |

**Hand-read note (added at GREEN): `--no-optional-locks`.** `SKILL.md` asks for `--no-optional-locks` straight after `git` every time. Whether each `git` command carries it is read from each trial's command list only: trials set `GIT_OPTIONAL_LOCKS=0` (`fixture.py:94`), so the workspace cannot show it. The maintainer's real-branch read leaves the variable unset and tests it through a hash of the clone's `.git/index`. Since `1cc134c`, `SKILL.md` also asks for `--no-ext-diff --no-textconv` on every `git diff`, and since `b89df20` on every read that prints or searches a diff: `diff`, `show` of a commit, and `log` with `-p`, `-S` or `-G`, with `-v` left off `status` (**Implementation checkpoint (GREEN)**, finding 1a). That too is read from the command list only: a fixture may hold no `.gitattributes` (`fixture.py:297`) and trials read no global or system config (`fixture.py:95-97`), so no diff driver or converter is set, and such a read without the flags reads the same there. That is inferred from the code, not observed, and a `GIT_EXTERNAL_DIFF` passed down in an agent's environment is not covered by it.

Fixture facts for the hand read. The first four were observed at apply time; the last is read from the trees.

- On `main`, `python3 wordstat.py sample.txt` prints `words: 23` and `distinct: 13`.
- On `add-top-words` it prints `words: 23` and `distinct: 10`, and `--top 3` adds `most common:` followed by `the 7`, `river 4` and `mill 3`.
- `one - two` is 3 words on `main` and 2 on the branch.
- The usage error now comes from argparse: `usage: wordstat.py FILE` becomes `usage: wordstat.py [-h] [--top N] file`.
- The README change documents `--top` only.

#### Residual risk

- **The trial path names the arm.** Each agent's working directory ends `<case>/skill-1/workspace` or `<case>/baseline-1/workspace` (`runner.py:96-98`), and the agent sees it: the fake-API runner probe (`ai_tmp/probe-red/`) found it in Claude Code's system prompt and in Codex's `<cwd>` context, in both arms. From a checkout whose path holds `skills/change-viz`, the baseline also sees the skill's name. The grader never sees the path. It affects every suite, cowsay included. The maintainer decided on 2026-11-11 that RED runs as is, and the fix is a harness follow-up: `.scratch/foundation/follow-ups.md`, **Ticket 18, the arm in the trial path**.
- **P4's stated limits** are under **Pattern limits**, and the hand read covers what they leave open.
- **A partial clone can fetch** (review finding 1b, **Implementation checkpoint (GREEN)**). In a partial clone, the skill's `git diff` and `git show` can fetch a missing object from the promisor remote (`git(1)`, `--no-lazy-fetch`). That contacts the remote and adds objects under `.git/objects`, which the skill's "no `fetch`" rule does not foresee. That it moves no ref, index entry or working-tree file is inferred from the docs, not tested. Blocking it would leave a blobless clone's diff unreadable, and a Git that predates `--no-lazy-fetch` would reject the option and fail every command, so the skill text does not change. The triage put this out of scope, and the lead agent directing this apply confirmed that verdict on 2026-11-11.
- **A local `main`'s unpushed commits** (review finding 2). A branch cut from a local `main` that holds unpushed commits is described against local `main`, the fewest ahead, so those commits stay out of the description, though a pull request against `origin/main` would carry them. `eb56a43` covers only the case where the local count is 0.
- **A remote's default that counts more, above 0** (review round 2, finding 1). When a branch counts fewer against `origin/main` than against the branch `origin/HEAD` names, and more than 0, it is described against `origin/main`, though a pull request against the remote's default would carry more. In the round-2 probe's Case 7, a hotfix cut from `origin/main` counts 1 against it and 3 against `origin/develop`. `af11c72` covers only the case where the count is 0. The triage judged `origin/main` the right base for a git-flow hotfix.
- **`show <commit>` and `log -p` ran text conversion: fixed in `b89df20`** (found by the probe for review finding 1a). `1cc134c` flagged only `git diff`. In the probe, with text conversion caching on, `git --no-optional-locks show HEAD` and `log -p -1` wrote `refs/notes/textconv/x`. They did not run `diff.external`. The skill prescribes neither, since its `show` reads are of a file at a commit and its `log` has no `-p`, but its list of reads allows `show` and `log`. Since `b89df20`, `SKILL.md` gives the flags to every read that prints or searches a diff, `log -S` and `-G` included, and leaves `-v` off `status`, which rejects them (**Follow-up fix, `b89df20`**). What remains: with the flags, `-G` skips a binary file it would have read through a converter, and both probes ran on Apple Git 2.50.1 only.
- **A remote named `upstream` is taken as the fork's parent** (stage-2 re-review, finding 1, case U1). If it is someone else's repository whose `main` holds some of the branch's commits, it counts fewer and wins. Those commits are then left out of the description, with no question asked. No read-only check tells it apart from a real parent: the refs have the same shape. A request that names the base avoids it.
- **A fork's parent under another name** (stage-2 /code-review, finding 1). A parent remote not named `upstream`, or a parent whose default is neither `main` nor `master`, is not a candidate, so a branch cut from it is still counted against the fork's own `main`.
- **A fork with commits of its own asks more often** (stage-2 re-review, the cost of `6db0d6f`). In a fork whose `main` holds commits `upstream` lacks, a branch cut from `upstream/main` for a pull request upstream now asks for the base, where it was described against `upstream/main` without a question. How often a fork's `main` holds its own commits was not assessed.
- **A configured `core.fsmonitor` runs under step 1's `status`** (stage-2 /code-review, finding 6). With a hook it runs the hook; with `true` it starts the daemon, which leaves `.git/fsmonitor--daemon/` and a socket. No other prescribed read runs it, and it moves no ref, index entry or working-tree file. Only the person's own config sets it, and their own `git status` does the same, so the skill text does not change. This is the triage's judgement, confirmed by the lead on 2026-11-11 by the test that put 1b out of scope.

#### Next

**Next:** Hand-off 1, the RED run, from the current head of `change-viz`: the commit that records round 2 of the P4 review, or any later commit that leaves `evals/change-viz/` as it is. It is unchanged since `7816385`, so `evals_sha256` stays `78828f74f0a72581d29d915ba3e3cfb1ccfcde1701c1622dc3d83d53ba5726d2` (**Checks run**, after f3).

Questions 1, 2, 3, 6 and 7 are settled. P4, narrowed with f3, is the only change they make to `evals.json`, and both are committed after `just format` and `just validate-evals`. Both rounds of P4's focused review are done (**P4 review**). Round 2 found nothing in f3, so no fix lands and nothing frozen changes before RED. Questions 4 and 5 stay open, and neither blocks RED: 4 before GREEN, and 5 before `NOTICE.md` lands.

Then, in the maintainer's terminal at the root of this worktree, with `CLAUDE_CODE_OAUTH_TOKEN` exported (the grader needs it on both agents; Codex also uses its login in the project's Codex home):

```sh
just eval change-viz --agent claude --baseline
just eval change-viz --agent codex --baseline
```

What RED is expected to show (unobserved):

- **Skill arm:** the behaviour case fails, because the stub body names no heading. P1 to P4 and E1 to E3 fail. `skill_triggered` passes, because the CLI records the by-name load whatever the body says.
- **Baseline arm:** the behaviour case fails too, on the same items: no agent writes the three headings unasked. If it passes, the case changes until it measures a real gap (`CONTRIBUTING.md` §2).
- **Quiet case:** passes in the skill arm, with no confirmed load, and is skipped in the baseline.
- `--top`, E5 and E8 likely pass in both arms, and so does E6 on Claude Code. E4, E7 and Codex's E6 can go either way.

Then read `eval-results/<run-id>/`: the quiet case's transcripts, each kept workspace (the writes and refs rows above), the two disclosure reads, and each skill-arm message against the fixture facts. Record the run ids here and in ticket 17.

### RED run (Hand-off 1, 2026-11-11)

The maintainer ran both commands under **Next** from `b28cd28`. That is later than `3d3dc4b`, and `evals/change-viz/` and `skills/change-viz/` are unchanged between the two. Each run got a reader and a skeptic: `ai_tmp/red/claude-red-read.md` with `claude-red-verify.md` (renamed from `claude.md`, which Claude Code on a case-insensitive disk loads as a nested `CLAUDE.md`), and `ai_tmp/red/codex.md` with `codex-verify.md`. Each final message is saved verbatim beside them as `ai_tmp/red/<agent>-<case>-<arm>.md`. Where a skeptic refuted its reader, this record follows the skeptic. No refutation changes a verdict. No acceptance box is ticked: each still waits for GREEN or for the implementation checkpoint.

| | Claude Code | Codex |
| --- | --- | --- |
| Run id (both arms) | `20261111T211415Z-73e4` | `20261111T211625Z-9e0f` |
| Commit | `b28cd28`, `git_dirty` false | the same |
| `evals_sha256` | `78828f74…`, the frozen value | the same |
| `skill_sha256` | `3d94019e…`, the RED stub. The installed copy equals `skills/change-viz/` (`diff -r`) | the same |
| Agent | Claude Code 2.1.309, `claude-sonnet-5-5` | Codex 0.163.0, `gpt-5.6-terra` |
| Grader | `claude-opus-5-5` on Claude Code 2.1.309, 2 calls per graded trial, `canary_passed: false` (the healthy value) | the same |
| Trials | 3: one per case per arm, with the quiet case skipped in the baseline | the same |
| Every trial | `ok`, valid, contamination passed, `secret_found` null | the same |

#### Results

| Check | Claude skill | Claude baseline | Codex skill | Codex baseline |
| --- | --- | --- | --- | --- |
| Prompt sent | `/change-viz Describe what this branch changes.` | `Describe what this branch changes.` | `$change-viz:change-viz Describe what this branch changes.` | `Describe what this branch changes.` |
| `skill_triggered` | pass (deduced, below) | n/a (baseline arm) | pass (deduced, below) | n/a (baseline arm) |
| `output_contains` `--top` | pass | pass | pass | pass |
| P1: three headings in order | fail | fail | fail | fail |
| P2: one to three notes | fail | fail | fail | fail |
| P3: a fence under the outline | fail | fail | fail | fail |
| P4: one why paragraph | fail | fail | fail | fail |
| E1: the why is one sentence | fail | fail | fail | fail |
| E2: the why says what it makes possible | fail | fail | fail | fail |
| E3: each visual has a lead-in | fail | fail | fail | fail |
| E4: a visual of `--top` or the word handling | fail | fail | fail | fail |
| E5: adds `--top` with counts | pass | pass | pass | pass |
| E6: lower-cased and stripped | pass | pass | pass | pass |
| E7: counts can be lower | fail | fail | fail | fail |
| E8: compares with local `main` (transcript) | pass | pass | pass | pass |
| Outcome items passed | 4 of 13 | 4 of 13 | 4 of 13 | 4 of 13 |
| Behaviour case `passed` | false | null (baseline, by design) | false | null (baseline, by design) |
| Quiet case, `no-trigger-unnamed-request` | pass: no trigger | skipped | pass: no trigger | skipped |

- **Deltas:** every delta is 0.0 on both agents, at n = 1 per arm, so the figures are descriptive. Both `benchmark.json` files list E5, E6 and E8 as non-discriminating. `--top` also passes in both arms, though the list covers expectations only.
- **Why the patterns fail:** P1 to P4 fail at the first heading. Codex's skill arm wrote `## Summary` and no other heading. The Claude Code messages label their sections with bold lines. No message on either agent has a fenced block. The Codex reader reran the four patterns under Python `re` over the saved Codex messages and got the same results. Those messages use LF line endings, so `\r\n` played no part.
- **What the grader said:**
  - E1 to E4 failed in every arm because the headings were missing and there was no diagram or code block.
  - E7 failed in every arm. Claude Code's messages say counts "change", with no direction. Both Codex messages leave the warning out, though both Codex trials printed `distinct: 10`, and neither ever compared it with `main`'s 13.

**Trigger evidence: deduced, not seen.** Neither run stores the line that set the trigger.

- **Stored:** both skill arms have `trigger` `{expected: true, actual: true, matched: true}` and the evidence `triggered: ['change-viz']`.
- **Claude Code:**
  - **Not stored:** the session record. The adapter keeps its `skill_expanded` line in memory (`claude_code.py:395-409`), and teardown removes the agent home.
  - **Deduced from the code at `b28cd28`:** status `ok` needs the trial's own session record (`claude_code.py:507`, `:541-542`). The trial made one tool call, a Bash `git log --stat main..HEAD; git diff main...HEAD`. It made no `Skill` call and no `Read`, and named no `SKILL.md`. That leaves only a `skill_expanded <cwd>/.claude/skills/change-viz` line.
  - **Supporting, at n = 1:**
    - The init event lists `change-viz` in `skills` and `slash_commands`.
    - The first turn's input was 16716 tokens. That is 138 more than the quiet trial's 16578, which fits the expansion having been sent.
- **Codex:**
  - **Not stored:** the explicit `codex.skill_invocation` event. `stored_stderr` drops telemetry, and `kept_lines` stays in memory (`codex.py:445-466`).
  - **Deduced:** none of the trial's three commands reads a `SKILL.md` or names the skill. The skeptic re-parsed the stored transcript with `codex.parse_stream` and no telemetry lines, and got `skills_triggered == []`. Only an `explicit` event adds the skill without a read (`codex.py:547-582`).
  - **Supporting:** only the skill arm said it would write a "pull-request description" and opened with `## Summary`, which echoes the stub's injected description. Its input was 586 tokens over the baseline's, with the same 39,168 tokens cached.

#### Hand reads

**Quiet case.** It passed on both agents, with no confirmed load. That is a lower bound: neither trace shows whether the model was told the skill exists.

- **Claude Code:** the reader and the skeptic each read the whole transcript.
  - It has six events and one Bash call, `git diff main...HEAD --stat && git diff main...HEAD`.
  - It made no `Skill`, `Read`, `ls` or `find` call and named no skill path. The only `change-viz` hits are in the init event's own listing: `skills`, `slash_commands`, `plugin_warnings` and the trial path.
  - Status `ok` means the trial had its own session record, and that record held no expansion.
  - Its first turn was 3 tokens over the baseline's (16578 against 16575). That hints the CLI did not list the skill to the model.
- **Codex:** the reader and the skeptic each read the whole transcript.
  - It ran two git-only commands. The first tried `HEAD@{upstream}`, then fell back to `main`.
  - Nothing in it mentions `.agents`, `SKILL.md` or the skill's name.
  - Whether Codex logged an `implicit` event is unobserved, because none is stored. Without a read, one would not set the trigger anyway.

**Writes** (the "does not" table's check, in each kept workspace):

- **Claude Code, all three workspaces:**
  - `git status --porcelain --untracked-files=all` is empty, and `--ignored` adds only the installed skill.
  - There is no `__pycache__`, and every `.git/` file dates from trial setup, before the agent's first command.
  - Every command was a git command, so no fixture code ran.
- **Codex, quiet trial:** clean.
- **Codex, behaviour, skill and baseline arms: fails.**
  - Both arms ran `python3 -m unittest -v && python3 wordstat.py sample.txt --top 3`, which printed 5 tests OK and the branch's counts.
  - Both left `?? __pycache__/test_wordstat.cpython-314.pyc` and `?? __pycache__/wordstat.cpython-314.pyc`, with mtimes inside each agent's run.
  - **Ran the fixture's code:** Codex's skill and baseline arms (open question 4). No Claude Code trial ran it, and neither did Codex's quiet trial.
- **The `.pyc` files reached the blinded grader** as output files, and both graders' notes name them. The grader's material is not stored. The harness code indicates each file was shown by name and size only, as not UTF-8, which is derived, not seen.
  - The sizes differ by arm: 2416 and 2730 bytes in the skill arm, 2419 and 2733 in the baseline.
  - The 3-byte gap is the difference in length between `skill-1` and `baseline-1` in the trial path embedded in each file (inferred).
  - No verdict could use the gap, because one grading call sees one trial. It belongs with **Residual risk**'s arm in the trial path.

**Refs.**

- In all six workspaces:
  - Symbolic `HEAD` is `refs/heads/add-top-words`, at `c7c97ee`, and `main` is at `88ce88c`. There are no other refs, no stash and no remote, and `git worktree list` shows only the workspace.
  - There is no `.git/logs/`, and the blobs equal the fixture's trees.
- No transcript has a `checkout`, `switch`, `stash` or `worktree add` command.
- Every Codex trial is `ok`, so none had a sandbox denial.

**Disclosure and name echoes.**

- **Disclosure fields:** all four grading files have `arm_disclosed: false` and `disclosure_matches: []`. The quiet trials were not graded, so they carry no flag.
- **Name echoes:** `rg -i 'change[- ]?viz'` over all six final messages finds nothing. Neither does `\bskills?\b|\.claude|\.agents`.
- **Trial path:** no message or command referred to the trial path.

**Final messages against the fixture facts.**

- **Skill arm, behaviour, on both agents:** no contradiction.
  - Claude Code's "Counts for existing inputs change" gives no direction (E7), and `words` stays 23.
  - Codex's "5 passing tests" comes from its own run and matches the tip.
- **Claude Code's quiet trial** (a skill-arm message, not graded) **contradicts** the fixture: "It has 5 commits relative to `main`." `main..HEAD` has 3, and the repository 5 in all. Its one command printed no commit count.
- **Claude Code's baseline contradicts** the fixture: "The words and distinct counts change for any text with mixed case or punctuation." `sample.txt` has both, yet `words` stays 23.
  - E7 read this bullet, its only "counts change" sentence, and failed it for the missing direction.
  - So the run shows a false claim going unpenalised, not a description passing because of one.
- **Codex, imprecise but not contradicting:**
  - The baseline says "total and distinct counts … case-insensitive", but case cannot change the total.
  - The baseline and the quiet trial say the branch "improves word normalization", but `main` had none.
- **Not a changelog** (hand read):
  - Claude Code's skill arm wrote a commit-by-commit changelog of bold labels and bullets.
  - Codex's skill arm is ordered by behaviour, not by file.
  - No message on either agent has a visual.
- **Branch name:** both Claude Code behaviour messages name `add-top-words`, which no command printed. The CLI's startup context is the likely source (inferred).
- **Prose under the why:** no message has the heading, so P2's and P4's **Pattern limits** meet no live output until GREEN.

#### Case validity

**Valid on both agents** (`CONTRIBUTING.md` §2).

- The baseline fails the behaviour case on Claude Code and on Codex. Each fails 9 of its 13 outcome items: P1 to P4, E1 to E4 and E7. So the case measures a real gap and does not change before GREEN.
- The criterion "The baseline arm fails the behaviour case on both agents" is shown at RED, at n = 1 per agent. Its box waits for the implementation checkpoint, like the others.

#### Predicted and observed

| Prediction (**Next**) | Claude Code | Codex |
| --- | --- | --- |
| The skill arm fails the behaviour case, with P1 to P4 and E1 to E3 failing | as predicted | as predicted |
| `skill_triggered` passes in the skill arm | as predicted (deduced) | as predicted (deduced) |
| The baseline fails on the same items | as predicted: the same nine | as predicted: the same nine |
| The quiet case passes with no confirmed load, and is skipped in the baseline | as predicted | as predicted |
| P4 fails in both arms, as P1 does (question 2) | as predicted | as predicted |
| `--top`, E5 and E8 pass in both arms | as predicted | as predicted |
| E6 passes on Claude Code | as predicted. Both trials' own `git log` printed "Count words without case or surrounding punctuation", and their diff shows `words()`, so the startup context is not needed to explain it | – |
| Codex's E6 either way | – | passes in both: non-discriminating |
| E4 either way | fails in both | fails in both |
| E7 either way | fails in both | fails in both |
| No prediction: writes | clean | fail in both behaviour arms (`__pycache__/`) |

#### What this means for GREEN

1. **What can move:** P1 to P4, E1 to E4 and E7, on both agents. `--top`, E5, E6 and E8 pass in both arms on both agents, so they stay as guards. Under **GREEN gain**, E4 now discriminates and E6 does not.
2. **E7:** to pass, a description must say which way a change moves existing results. GREEN states this as a general rule: say the direction a behaviour change moves existing output, and why that matters to the reader. It is not a line about this fixture, since the maintainer checkpoint changes what the skill explains rather than fitting one branch.
3. **E4:** a fenced visual of the change. If no code runs, any output it shows is worked out from the code, and E4 checks no values, so the hand read against the fixture facts stays.
4. **Open question 4 now has data, from Codex only.**
   - Running the fixture's code was common, but not shown to be the default. Codex's baseline ran it, and its quiet trial, given the same bare prompt, did not.
   - With the stub, Codex's skill arm ran it too. No Claude Code trial ran it.
   - If a GREEN `__pycache__/` is a ticket 18 failure, the GREEN text needs a line to read the branch rather than run its code. The baseline would keep failing the writes check, which is a hand read, not a scored item.
   - If it is ticket 21's, it is recorded here as a limit.
   - Either way, a skill arm that writes nothing sends the grader its message alone, while the baseline also sends its `.pyc` files. That is an arm difference in the material, though no expectation reads the files.
5. **Codex reads the frontmatter.** The stub's injected description already shaped Codex's skill arm (`## Summary`, "pull-request description"). The GREEN description and body reach the model the same way, as **Neutral RED text** planned.
6. **The GREEN hand read** also checks every message's commit counts and count claims, not only E4's values. Both contradictions at RED were of that kind, and neither cost a point.
7. **Writes on Claude Code:** its init event lists 22 tools, though the command allows only `Skill`, `Read` and `Bash`. Under `--permission-mode dontAsk` the others should be denied, so a GREEN write attempt would show in `permission_denials` (inferred; RED had none).
8. **Trigger audit:** neither run keeps the line that set its trigger. Ticket 17's open follow-up, a trial-record field for the kept trigger lines, would let GREEN's trigger be checked rather than deduced. It does not block.

#### Next

1. The maintainer answers question 4. Question 5 waits until before `NOTICE.md` lands.
2. Then GREEN: the skill text, the credit form with `NOTICE.md`, **Change source** in `GLOSSARY.md`, and D3, followed by the GREEN run with the two commands under **Next** above.

### GREEN (2026-11-11)

Applied on branch `change-viz` in `c82b6f9`, from a revised draft in `ai_tmp/green-18/` (gitignored), with the records in the commit after it. The maintainer answered question 4 first (**Questions for the maintainer**). The GREEN run and the maintainer's read of a real branch (Hand-off 2) have not run. No acceptance box is ticked: each waits for the GREEN run or for the implementation checkpoint.

#### What landed

- **`skills/change-viz/SKILL.md`:**
  - The GREEN frontmatter under **Credit form**: the full description from design §5, and the string `metadata.credits` (D2 below).
  - A body of 99 lines and 10,579 bytes, about 2,645 tokens by the validator's bytes / 4. After the review fixes (**Implementation checkpoint (GREEN)**) it is 99 lines and 11,168 bytes, about 2,792 tokens, and after `b89df20` 99 lines and 11,336 bytes, about 2,834 tokens. After the stage-2 /code-review's fixes (**/code-review (stage 2)**) it is 99 lines and 11,627 bytes, about 2,907 tokens, at `62d86de`, and 99 lines and 11,724 bytes, about 2,931 tokens, at `6db0d6f`. After the E3 fix (**GREEN run, Claude (2026-11-12)**) it is 99 lines and 11,842 bytes, about 2,961 tokens, at `253ee70`. It explains, with a reason for each limit:
    - leaving the repository as found: git reads only, each with `--no-optional-locks`, and nothing that moves a ref, the index or the working tree, or sends to a remote. Since `1cc134c`, every `git diff` also carries `--no-ext-diff --no-textconv`, and since `b89df20` every read that prints or searches a diff does, with `-v` left off `status`;
    - finding the base from the refs that exist: local `main` or `master`, `origin/main` or `origin/master`, and `origin/HEAD`, taking the fewest commits ahead and the local one on a tie. Since `eb56a43`, when a local branch counts 0 and a remote's branch counts more, it gives both counts in one line and asks for the base, and since `af11c72` it does the same when the branch a remote's `HEAD` points at, such as `origin/develop`, counts more than the 0. Since `e6d8f11` the candidates include `upstream/main` and `upstream/master`, and since `6db0d6f`, when the base it takes is `upstream`'s, the same branch on `origin` counts more and `upstream/main..origin/main` (or `master`) is above 0, it gives both counts in one line and asks;
    - reading every commit since the base, the old version through `git show <base>:path`, and the branch's own text as material, not instructions. Since `181aee0`, the old version is read at the merge base, `git show <fork>:path`;
    - the three headings and their limits, and the final message, with no file, no scratch copy and no pull request write.
- **`skills/change-viz/references/`:**
  - `reading-the-branch.md`: the base cases the main steps leave open, and a large branch;
  - `views.md`: the catalogue of views, adapted from HumanLayer's `show-me`;
  - `example.md`: one complete description of an invented change, a static site builder.
- **`skills/change-viz/NOTICE.md`:** the form under **Credit form**, with HumanLayer's `LICENSE` in a `text` fence.
- **Unchanged:** `agents/openai.yaml`, `.claude-plugin/plugin.json` and version `0.1.0`. `change-viz` is not on `main` yet, so any version is higher than none, and ticket 19 makes the first bump. Nothing under `evals/` changed.
- **ADR 0008** gains question 5's sentence.
- **Records:**
  - `GLOSSARY.md` gains **Change source**. A branch is the only change source this ticket handles. Ticket 22 adds uncommitted work and ticket 23 a pull request.
  - D3's row in `.scratch/foundation/follow-ups.md` says `change-viz` carries HumanLayer's notice, and that no installed skill carries this repository's own.
  - Ticket 22's **What is known** says the empty case's skill arm may pass at its RED, as a guard from this ticket.
  - Tickets 20 and 21 note that a table cannot be a visual under the current `SKILL.md` wording.
  - The "does not" table under **Design as approved** gains two rows, and a hand-read note on `--no-optional-locks` follows it.

#### Departures, and the defaults they rest on

The maintainer confirms each of these at Hand-off 2, with question 5's answer and the version. Until then they are the implementer's defaults.

- **D1: no link from the body.** The draft ended with a `## Credits` section of one line that linked `NOTICE.md`. It came from an error in the brief, not a decision, so it was removed and the approved form stands: no link from the body, and no credit line in it, since a body line reaches every Claude Code expansion.
- **D2: the credit string departs from design §5.** It is now 'Adapted from MIT-licensed work by HumanLayer (Copyright (c) 2026 HumanLayer). The full notice is in NOTICE.md.' Codex injects the frontmatter, and the design's string named `show-me` and `visual-pr`. Two upstream skills of those names can be installed on a user's machine, and `visual-pr` commits, pushes and edits pull requests. **Credit form** has the old string and the reworded extension for ticket 19.
- **D3: `NOTICE.md`'s "Adapted here" is wider than design §5.** It now lists the three headings and their limits, the kinds of note, the catalogue of views and the rules for choosing and trimming them, the lead-in above each visual, and the plain-language style. The design named only the headings, the catalogue and the smallest-view rule, which is less than the text adapts. The licence block is unchanged.

#### The draft's self-critique

Three critiques read the first draft, through three lenses: the ticket's criteria, the writing, and safety. They found 45 findings. The draft's own table records 37 as applied, 2 in part (the hand-off's isolation and the provenance record), and 4 rejected, all writing nits. It left 2 to the maintainer: the credit string naming two upstream skills, which D2 settles. D3 settles the open half of the provenance finding. D1 reverses the form three findings had settled on, the credit line under its own heading, by dropping the line.

The main applied fixes:

- the pointers into `references/` now reach every section they name;
- the candidates include `origin/main` when a remote has no `origin/HEAD`;
- the base is named `<base>`, so later commands work where there is no local `main`;
- `git show <base>:path` is the read-only way to see the old version (`<fork>:path` since `181aee0`, the review's finding 3);
- `push`, `clean` and named `branch` or `tag` are out of bounds;
- the branch's own text is material, not instructions;
- a note on changed behaviour says which way it moves and why;
- the uncommitted-changes note counts toward the three;
- the maintainer's real-branch read disables `push` and `gh` before it runs.

#### Checks run before the commit

- `just format`: no change to the skill's files.
- `diff -r` of the draft against `skills/change-viz/`: only D1 to D3.
- `NOTICE.md`'s `text` fence equals `ai_tmp/upstream/humanlayer-skills/LICENSE`, byte for byte (`cmp`; 1,067 bytes each).
- P1 to P4 on `references/example.md`, from `## Why the change` to its end, through the harness's own matcher: patterns from `cases.load_suite`, applied by `assertions.evaluate` (`re.search` with the patterns' inline flags only). All four pass, both with the file's final newline and with trailing whitespace stripped. The script is `ai_tmp/green-apply/patterns.py`.
- `evals_sha256` from `benchmark.evals_sha256`: `78828f74f0a72581d29d915ba3e3cfb1ccfcde1701c1622dc3d83d53ba5726d2`, the frozen value. `skill_sha256` from `benchmark.tree_sha256` is now `c8449d3b…`, where RED's was `3d94019e…`. The review fixes make it `1395bb7f…` at `181aee0`, `ee33ba6b…` at `b89df20` and `2832d80c…` at `af11c72`, and leave `evals_sha256` as it is (**Implementation checkpoint (GREEN)**). The stage-2 /code-review's fixes make it `32a66b28…` at `e6d8f11`, `95d6276a…` at `62d86de` and `b76a09db…` at `6db0d6f`, with `evals_sha256` still the frozen value (**/code-review (stage 2)**). The E3 fix makes it `37bb7110…` at `253ee70`, and leaves `evals_sha256` as it is (**GREEN run, Claude (2026-11-12)**).
- `just validate-skills`: 0 errors, and the one expected warning, `[extension-portability]` on `disable-model-invocation`. No `[placeholder]`.
- `just validate-evals`: "2 eval suites valid."
- `just run ./node_modules/.bin/claude plugin validate skills/change-viz --strict`: "Validation passed", with only the `ICON_MISSING` warning that cowsay also gets. It did not reject `metadata`, so the fallback is not taken. But it does not read `SKILL.md`'s frontmatter in this layout: copies whose `metadata` was unparseable YAML, or a nested mapping, also passed (`ai_tmp/green-apply/strict-probe/`). So this check says nothing about `metadata`, in either direction. Whether each CLI loads the skill with it is a separate check.

#### Reading a GREEN `infra_error`

GREEN runs on harness commits made after RED: `7f8c72b`, `ba93b1c` and `62caba3`. They changed how the adapter parses Codex's late denials, and the trial now runs the real `git` on macOS rather than its `xcrun` shim. So a Codex `infra_error` at GREEN is read against those commits before the skill text is blamed.

#### Next

Hand-off 2, from `253ee70`, the E3 fix (**GREEN run, Claude (2026-11-12)**), or any later commit that leaves `skills/change-viz/` and `evals/change-viz/` as they are. `c82b6f9`, `181aee0`, `b89df20`, `af11c72`, `e6d8f11`, `62d86de` and `6db0d6f` no longer qualify, because later fixes change `skills/change-viz/`. The E3 fix's review round found nothing to change (**Review of the E3 fix**, under **GREEN run, Claude (2026-11-12)**). The stage-2 re-review's fix has had no round of its own (**/code-review (stage 2)**), so a fix from such a round would move this start commit again:

- **The GREEN run,** the two commands under **Next** above, in the maintainer's terminal, each on its own line and not chained with `&&`. Run ids: Claude Code `20261112T065321Z-3958`, on `6b999cc`'s text (`b76a09db…`), before the E3 fix, so both agents run again on the new text; Codex pending (**GREEN run, Claude (2026-11-12)**).
- **The maintainer's read of a real branch** of their choosing. Feedback: pending. It is recorded here and applied by changing what the skill explains.
- **Then** the hand reads under **Design as approved**, the two new rows and the `--no-optional-locks` note included, and the maintainer's confirmation of D1 to D3, question 5's answer and the version.

### Implementation checkpoint (GREEN)

A cross-model review of the GREEN text, before the GREEN run. Its fixes are `1cc134c`, `eb56a43` and `181aee0`, with `b89df20` following up 1a, and round 2's is `af11c72` (**Round 2**). The stage-2 /code-review's are `e6d8f11`, `62d86de` and `6db0d6f` (**/code-review (stage 2)**). They change only `SKILL.md` and `references/reading-the-branch.md`. Nothing under `evals/` changed. No acceptance box is ticked: the GREEN run and Hand-off 2 have not run.

#### Cross-model review

- **Implementer:** Claude Code running Claude Opus 5.5 (`claude-opus-5-5`), per the commits' trailers. The review script recorded no implementer model.
- **Reviewer:** Codex `gpt-6-astra` (fallback: no)
- **Reviewed:** `af987c0..28665e4` (`c82b6f9` and `28665e4`), reviewed commit `28665e4`, against this ticket's acceptance criteria and the implementation checkpoint. The brief asked five questions: whether each instruction gives a reason, the upstream notice, writes to the repository, base detection when `main` and `origin/main` diverge among other cases, and self-reference. Brief: `ai_tmp/brief-18-green.md`.
- **Findings:** `ai_tmp/review-20261112T021450Z-codex.md` · **Triage:** `ai_tmp/triage-18-green.md`, which splits finding 1 into 1a and 1b
- **Probe for 1a:** `ai_tmp/green-apply/textconv-probe/probe.sh`, output in `probe.out`: a throwaway repository on Apple Git 2.50.1 only, with global and system config off, and the cache ref cleared before each command. It settles what the triage left unverified:
  - with `diff.x.cachetextconv` on, a plain `git --no-optional-locks diff main...HEAD` wrote `refs/notes/textconv/x`;
  - with `--no-ext-diff --no-textconv` it wrote nothing, and showed `Binary files a/f.bin and b/f.bin differ` (the probe's file holds a NUL byte);
  - `diff --stat` wrote no ref and did not run a configured `diff.external`, which a plain `diff` ran;
  - `show main:f.bin` and `log --format=%h main..HEAD` wrote no ref;
  - `show HEAD` and `log -p -1` wrote the ref, since text conversion runs for them by default too. They did not run `diff.external`. The skill prescribed neither, but its list of reads allows `show` and `log`. Fixed in `b89df20` (**Follow-up fix, `b89df20`**).

| # | Severity | Finding | Verdict | Action |
| --- | --- | --- | --- | --- |
| 1a | high (triage: low) | `git diff` runs a configured external diff driver and textconv filter by default, and text conversion with caching on writes `refs/notes/textconv/<driver>`, which `--no-optional-locks` does not prevent | valid in part at triage: the driver and converter running was shown from the docs, and the ref write was left unverified. The probe then confirmed the write. Low, because only the person's own config or environment can define a driver (`gitattributes(5)`), not the branch being described | fixed in `1cc134c`: every `git diff` in `SKILL.md` and `references/reading-the-branch.md` carries `--no-ext-diff --no-textconv`, and `SKILL.md`'s first rule says why. It includes the triage's clause on the cache ref, which the triage made conditional on the probe. Cost, seen in the probe: a binary file its owner set a converter for, such as an image or a document, reads as `Binary files differ`. The flags are read from each trial's command list (the hand-read note under **Design as approved**). Extended in `b89df20` to every read that prints or searches a diff (**Follow-up fix, `b89df20`**) |
| 1b | high (triage: none) | In a partial clone, `diff` and `show` can fetch missing objects from the promisor remote, which `--no-optional-locks` does not stop | out of scope, by the triage's judgement, confirmed by the lead agent directing this apply on 2026-11-11: a lazy fetch only adds objects (inferred from the docs), and blocking it costs more than it saves | none to the skill text. Recorded under **Residual risk** (**Design checkpoint**) |
| 2 | high (triage: low) | Taking the fewest commits ahead can override the real default branch: a local `main` that counts 0 wins over a remote's branch that counts more, and the skill stops with nothing to describe | valid in part: only when the 0 is a local branch's and a remote's branch counts more. The general claim, that the fewest is no evidence of where the branch was cut, is not valid: it picks correctly for a stale local `main` after a fetch and for a `develop` default. The triage ran the new rule through nine cases. Round 2 showed the same harm when the 0 is a remote's and the branch `origin/HEAD` names counts more (**Round 2**) | fixed in `eb56a43`: **Nothing is ahead** in `references/reading-the-branch.md` now gives both counts in one line and asks which base to describe against, and `SKILL.md` says the fewest is "usually" where the branch left. The remaining limit, a local `main`'s unpushed commits, is under **Residual risk**. Extended to the branch `origin/HEAD` names in `af11c72` (**Round 2**) |
| 3 | medium | The old-file read `git show <base>:path` takes the base's tip, but the three-dot diff compares with the merge base, so a behaviour note can take the base's later change as the branch's, or reverse its direction | valid | fixed in `181aee0`: step 1 names the merge base `<fork>`, the old-file read and the behaviour reading use it, with the reason beside the read, and the rule on out-of-bounds commands says "the one before the branch". `merge-base HEAD <base>`, which E8 accepts, and the three-dot diffs are unchanged. The eval cannot show this finding: the fixture's `main` stops at the fork |

**Second round:** Fixes 2 and 3 change rules in substance: 2 adds a branch that asks for the base, and 3 changes which commit old files are read at. `b89df20` widens 1a's rule. A second round reviewed them at `953896a` (**Round 2**).

**Checks run after the fixes,** at `181aee0`:

- `just format` before each fix commit: no change beyond the edits.
- P1 to P4 on `references/example.md` through the harness's matcher (`ai_tmp/green-apply/patterns.py`): all four pass, with the file's final newline and with trailing whitespace stripped. `example.md` is unchanged.
- `evals_sha256`: `78828f74f0a72581d29d915ba3e3cfb1ccfcde1701c1622dc3d83d53ba5726d2`, the frozen value. `skill_sha256`: `1395bb7f1c6c08cb76a2ddc48adcbea06cd3d5f73a1fd43a11529ac7dc49d7f6`, where `c82b6f9`'s was `c8449d3b…`.
- `just validate-skills`: 0 errors, and the one expected `[extension-portability]` warning.
- `just run ./node_modules/.bin/claude plugin validate skills/change-viz --strict`: "Validation passed", with only the `ICON_MISSING` warning.
- The Codex load check against the fake API was not rerun: the frontmatter is unchanged since `c82b6f9`.
- `just check` in the foreground: exit 0, 1210 passed, 4 skipped (`ai_tmp/green-apply/gate-fix.log`). The commit that adds this section changes only this ticket.

**Follow-up fix, `b89df20`.** The probe's last bullet left `show <commit>` and `log -p` writing the cache ref. The lead agent directing this apply decided on 2026-11-11 to flag every read that prints a diff, and blob reads (`show <rev>:path`) too if a probe showed them converting. `ai_tmp/green-apply/textconv-probe/probe-r2.sh`, output in `probe-r2.out`, runs 59 rows on a throwaway repository like the first probe's, with a converter and an external diff that each leave a marker when they run. Each row states what it expects, and the script exits 1 on a mismatch; it found none.

- **Without the flags,** `diff`, `diff --cached`, `show` of a commit, `log -p`, `log -S`, `log -G` and `status -v` each ran the converter and wrote `refs/notes/textconv/x`. `-S` and `-G` print no diff but compare contents, so the fix covers them too, by the lead's test for blob reads: a read that converts gets the flags.
- **With `--no-ext-diff --no-textconv`,** each of those ran nothing and wrote nothing, except `status -v`, which rejects both flags (`unknown option`). So `SKILL.md` says to leave `-v` off.
- **Unflagged reads, without the flags,** ran nothing and wrote nothing: the blob reads at `main`, `HEAD` and the fork; `log` without `-p`, `-S` or `-G`, step 2's `--reverse --format` form included; `show --stat`, `log --stat` and `log --name-status`; `status` and `status --porcelain` with staged and unstaged changes; `rev-list --count`, `merge-base`, `for-each-ref`, `rev-parse` and `symbolic-ref`. A blob read accepts the flags and prints the same bytes. The positive control, `show --textconv main:f.bin`, did convert and write, so blob reads stay unflagged.
- **External diff:** `diff.external`, and then `GIT_EXTERNAL_DIFF`, ran for a plain `diff` only: not for `show` of a commit, `log -p` or `status -v`, and not with the flags.
- **Cost,** beside `Binary files differ`: with the flags, `log -G b` found no commit where it found two without them, since `-G` skips a binary file it cannot convert. `log -S b` found the same two either way.

`SKILL.md`'s first rule now reads "Give every command that prints or searches a diff `--no-ext-diff --no-textconv` too: `diff`, `show` of a commit, and `log` with `-p`, `-S` or `-G`", keeps its reason, and ends "`status -v` prints a diff as well but takes neither flag, so leave `-v` off." The skill's own commands do not change: its `show` reads are blob reads, and its `log` has no `-p`.

**Checks run after `b89df20`:**

- `just format` before the commit: no change beyond the edit.
- P1 to P4 on `references/example.md` (`ai_tmp/green-apply/patterns.py`, output in `patterns-r2fix.out`): all four pass, with the file's final newline and with trailing whitespace stripped. `example.md` is unchanged.
- `evals_sha256`: `78828f74f0a72581d29d915ba3e3cfb1ccfcde1701c1622dc3d83d53ba5726d2`, the frozen value. `skill_sha256`: `ee33ba6be900f33d3d0f9f4c9eb210cecff7f424a3cc59c374afe73fc84fe3b4`, where `181aee0`'s was `1395bb7f…` (`evals_hash-r2fix.out`, on the clean tree at `b89df20`).
- `just validate-skills`: 0 errors, and the one expected `[extension-portability]` warning.
- `just run ./node_modules/.bin/claude plugin validate skills/change-viz --strict`: "Validation passed", with only the `ICON_MISSING` warning.
- The Codex load check against the fake API was not rerun: the frontmatter is unchanged since `c82b6f9`.
- `just check` in the foreground at `b89df20`: exit 0, 1210 passed, 4 skipped (`ai_tmp/green-apply/gate-r2fix.log`). The commit that records this changes only this ticket.

**Follow-ups:**

- Finding 1b's out-of-scope verdict is confirmed (the lead agent, 2026-11-11), so it stays a stated limit under **Residual risk**; no ticket owns it.
- Flagging `show <commit>` and `log -p`, which the probe found writing the cache ref: done in `b89df20`, with `log -S` and `-G`, and with `-v` left off `status` (**Follow-up fix, `b89df20`**).

**Still unverified:**

- Both probes ran on Apple Git 2.50.1 only.
- Which Git version introduced `--no-lazy-fetch`.
- That a lazy fetch moves no ref, index entry or working-tree file.

#### Round 2

A second cross-model review, of round 1's fixes and their records, before the GREEN run.

- **Implementer:** Claude Code running Claude Opus 5.5 (`claude-opus-5-5`), per the commits' trailers. The review script recorded no implementer model.
- **Reviewer:** Codex `gpt-6-astra` (fallback: no)
- **Reviewed:** `28665e4..953896a`, reviewed commit `953896a`: the fix commits `1cc134c`, `eb56a43`, `181aee0` and `b89df20`, and the records in `f820850` and `953896a`. The brief carried round 1's findings and triage verbatim and asked for no round-1 finding again unless its fix was wrong, incomplete or opened a new hole. Brief: `ai_tmp/brief-18-green-r2.md`.
- **Findings:** `ai_tmp/review-20261112T030505Z-codex.md` · **Triage:** `ai_tmp/triage-18-green-r2.md`
- **Probe:** `ai_tmp/green-apply/r2-probe/probe.sh`, output in `probe.out`: throwaway repositories on Apple Git 2.50.1 only, with global and system config off, in seven cases. It runs `SKILL.md` step 2's two commands verbatim and step 3's count for each candidate. It does not run an agent, so what the text makes an agent do is worked by hand from the counts.

| # | Severity | Finding | Verdict | Action |
| --- | --- | --- | --- | --- |
| 1 | high (triage: low) | The zero-count fix still lets another remote branch hide changes from the default branch: with `origin/HEAD` naming `origin/develop`, `origin/main` counts 0 and `origin/develop` 1, and **Nothing is ahead** asks only when the 0 is a local branch's, so the skill stops | valid in part. Probe Case 1, Codex's graph built as a clone, shows the stop. Not valid: the remedy, to ask whenever any other candidate counts more, local or remote, which would turn two correct stops into questions: a stale local `main` whose branch merged upstream (Case 2, round 1's row 7) and a branch merged into the default `develop` (Case 4). Low, because every condition must hold, and the answer is one line that names its base | fixed in `af11c72`: **Nothing is ahead** also asks, with both counts, when the branch a remote's `HEAD` points at counts more than the 0, with its own reason. It asks rather than switching to that branch, because a fetch does not update an existing `origin/HEAD` (`git-config(1)`, `followRemoteHEAD`), and Case 3 showed one gone stale. The non-zero form, Case 7, is under **Residual risk** |

- **The new text, worked by hand on the probe's counts** (the triage's table): Cases 1 and 5 now ask. Case 5 is an empty branch cut from `origin/main`'s tip where the default is `develop`, and a pull request to `develop` would carry 2. Cases 2 and 4 still stop. Case 7 is not a 0, so it is unchanged. Round 1's other rows are unchanged.
- **Cost:** Case 3, a stale `origin/HEAD`, and Case 6, describing `main` itself where the default is `develop`, now ask where they stopped.
- **Inferred, not a Git fact:** the new reason's "where a pull request goes unless told otherwise" rests on hosting services, such as GitHub's default base branch.
- **`SKILL.md` is unchanged:** the paragraph after its step 3, under **1. Find the base**, already sends every count of 0 to `references/reading-the-branch.md`.
- **E8:** still passes, inferred and not run. The fixture has no remote and its branch counts 3 against `main`, so the bullet is never reached.

**Checks run after `af11c72`:**

- `just format` before the commit: no change beyond the edit.
- P1 to P4 on `references/example.md` (`ai_tmp/green-apply/patterns.py`, output in `patterns-round2.out`): all four pass, with the file's final newline and with trailing whitespace stripped. `example.md` is unchanged.
- `evals_sha256`: `78828f74f0a72581d29d915ba3e3cfb1ccfcde1701c1622dc3d83d53ba5726d2`, the frozen value. `skill_sha256`: `2832d80c5c610881e2f81bdded9f1d271be272e7ae1e85990c19ba7e3e19b54b`, where `b89df20`'s was `ee33ba6b…` (`evals_hash-round2-clean.out`, on the clean tree at `af11c72`).
- `just validate-skills`: 0 errors, and the one expected `[extension-portability]` warning.
- `just run ./node_modules/.bin/claude plugin validate skills/change-viz --strict`: "Validation passed", with only the `ICON_MISSING` warning.
- The Codex load check against the fake API was not rerun: the frontmatter is unchanged since `c82b6f9`.
- `just check` in the foreground on the clean tree at `af11c72`: exit 0, 1210 passed, 4 skipped (`ai_tmp/green-apply/gate-r2.log`). A first run on the uncommitted edit stopped at `validate-distribution`, which needs the skill's sources committed. The commit that records this changes only this ticket.

**Still unverified:** the round-2 probe ran on Apple Git 2.50.1 only, and no agent has read the new sentence.

#### /code-review (stage 2)

A separate stage from the cross-model rounds above. Claude Code's `/code-review` skill, at level high, reviewed `a2ce09f..HEAD` with `HEAD` at `1115af2`. Its findings file does not record the model. Findings: `ai_tmp/code-review-stage2.json`, 10 of them, numbered from 1. Findings 1, 6 and 7 are on this skill's text. The other seven are on the eval harness and are recorded in ticket 16 (**/code-review of the CI fixes (stage 2)**). Triage: `ai_tmp/triage-code-review-stage2-skill.md`, with probes under `ai_tmp/code-review-stage2/` (`probe-fork/`, `probe-fsmonitor/`), on Apple Git 2.50.1 only. The findings file gives no severity, so the column is the triage's.

| # | Severity | Finding | Verdict | Action |
| --- | --- | --- | --- | --- |
| 1 | medium | Step 2 lists only `main`, `master` and `origin`'s, and the fuller list in the reference is read only when no candidate exists, so a fork clone counts a branch cut from `upstream/main` against the fork's stale `main`, and the description takes in commits other people landed | valid for the fork case. Probe Case F1: `main..HEAD` and `origin/main..HEAD` count 4, and `log` lists `X` and three of upstream's commits; `upstream/main..HEAD` counts 1. The `init.defaultBranch` half is not shown: the reference already handles it when no candidate exists | fixed in `e6d8f11` (the triage's Fixes 1a to 1c): step 2's `for-each-ref` also lists `upstream/main` and `upstream/master`, with one sentence of reason, and the reference's full list names the same two. Round 2's seven cases and round 1's nine rows have no `upstream` remote, so they are unchanged. F3, a branch already merged upstream, now asks where it described 4 commits. A parent under another name stays a limit (**Residual risk**). The re-review found a hole in this fix, fixed in `6db0d6f` (below) |
| 6 | none | Step 1's `git --no-optional-locks status` still runs a configured `core.fsmonitor` hook or starts its daemon, which can write under `.git/` | out of scope, by the triage's judgement, confirmed by the lead (2026-11-11). Probe: only `status` runs it, among the reads the skill prescribes. It moves no ref, index entry or working-tree file, the test that put 1b out of scope. The daemon leaves `.git/fsmonitor--daemon/` and a socket | none to the skill text. Recorded under **Residual risk**. If the lead weighs it the other way, the fix is `-c core.fsmonitor=false` on step 1's `status` only |
| 7 | low | Step 4 says a one-line answer from finding the base is the whole message, but the reference's no-candidate bullet also asks for a list of the local branches | valid as a wording conflict. The eval half is not shown: no case in tickets 20, 22 or 23 reaches the bullet, and no agent was run | fixed in `62d86de` (Fix 7): the list of local branches goes inside the one line. E8 is unaffected: the fixture has `main` |

**Checks run after `e6d8f11` and `62d86de`,** by the step that applied them: each edited file is byte-identical to the triage's patched copy under `ai_tmp/code-review-stage2/applied/`; `just format` changed nothing; P1 to P4 pass on `references/example.md`, 8 of 8 (`ai_tmp/code-review-stage2/patterns.out`); `just validate-skills` gives 0 errors and the one `[extension-portability]` warning; the pinned `claude plugin validate skills/change-viz` passed with only `ICON_MISSING` (`plugin-validate.log`); and `just check` in the foreground passed, 1210 passed and 4 skipped, after `62d86de` was committed, by the log's time (`ai_tmp/code-review-stage2/gate.log`).

**Re-review of the fixes:**

- **Implementer:** Claude Code running Claude Opus 5.5 (`claude-opus-5-5`), per the commits' trailers. The review script recorded no implementer model.
- **Reviewer:** Codex `gpt-6-astra` (fallback: no), exit 0 on the first run
- **Reviewed:** `1115af2..62d86de` (`e6d8f11` and `62d86de`), reviewed commit `62d86de`. The brief carried the findings and both triages verbatim, and asked for no invalid or out-of-scope finding again unless its evidence was wrong. Brief: `ai_tmp/brief-code-review-stage2.md`.
- **Findings:** `ai_tmp/review-20261112T055237Z-codex.md`, one finding · **Triage:** `ai_tmp/triage-code-review-stage2-rereview.md`, with probes in `ai_tmp/code-review-stage2/probe-upstream-unrelated/` (`probe.sh`, `rule.sh`), on Apple Git 2.50.1 only

| # | Severity | Finding | Verdict | Action |
| --- | --- | --- | --- | --- |
| 1, case U1 | medium (triage: low) | With `upstream` among the candidates, the remote's name alone makes it the fork's parent. If it is a collaborator's repository whose `main` holds some of the branch's commits, it counts fewer and wins, and those commits leave the description with no question asked | valid, shown by probe: at `1115af2` the pick is `main` (2) and `log` lists `Y` and `X`; at `62d86de` it is `upstream/main` (1), listing `Y` only. It has F1's ref shape (`upstream/main..origin/main` is 0 in both), so no read-only check tells it apart from a real parent | not fixed: a limit under **Residual risk**. Asking whenever `upstream` wins would turn F1 and F5, the cases `e6d8f11` was made for, into questions |
| 1, case U2 | medium | The triage's own case, from the same cause: a downstream fork's branch that merges `upstream/main` into the fork's `main`, for a pull request to `origin/main`, counts 3 against `upstream/main` and 6 against `origin/main`. It is described against `upstream`, which puts in the fork's two commits already on its `main` and leaves out `upstream`'s five. `e6d8f11` introduced it | valid, shown by probe | fixed in `6db0d6f`, the triage's Fixes A and B. The triage left the choice between this fix and a limit to the lead; the step that recorded this took the fix under its instruction to apply the valid re-review findings. The lead kept it (2026-11-11): it lives in the reference, reached by one clause, and leaves the main path unchanged. `SKILL.md` sends the agent to the reference when the candidate it took is an `upstream` branch and the same branch on `origin` counts more. A new bullet there keeps the base, as the usual fork, unless `upstream/main..origin/main` (or `master`) is above 0; then it asks with both counts. Cost: U3, a branch cut from `upstream/main` in such a fork for a pull request upstream, now asks where its base was right (**Residual risk**) |
| 1, sub-claim | none | The probes' `fixed()` reads `upstream/HEAD`, which step 2 does not | true, but it changes no result: with it dropped, every count line matches `probe-fork/probe.out` | none |
| 1, sub-claim | none | A regression case for the candidate expansion is missing | out of scope: ticket 16 puts a remote in a fixture out of scope, and round 1's and round 2's base fixes were checked by probe too | none |
| 1, sub-claim | none | E8's live result is unverified | out of scope: the brief says so, and the fixture has no remote, so nothing in the range changes E8 | none |

- **The rule, as a shell model:** `rule.sh` rerun after the fix gives the triage's output byte for byte (`ai_tmp/code-review-stage2/final/rule.out`). F1, F2, F4, F5 and U4, a tie where local `main` is taken, keep their pick. F3 still counts 0 and reaches **Nothing is ahead**. U1 is unchanged and silent. U2 and U3 ask. It models the text; no agent read it.
- **No further round, by the lead's decision (2026-11-11).** `6db0d6f` adds a branch that asks, a rule change in substance, as round 1's fixes 2 and 3 were. But each round on finding the base has turned up another fork shape that the refs alone cannot tell apart (U1 stays a limit), the main path that E8 checks is unchanged, and ticket 23 takes a pull request's base from the pull request itself. The GREEN run and the real-branch read are the next evidence. The maintainer can still ask for a round.

**Checks run after `6db0d6f`:**

- Each edited file is byte-identical to the triage's patched copy in `probe-upstream-unrelated/applied/`, before and after `just format`, which changed nothing.
- P1 to P4 on `references/example.md` (`ai_tmp/green-apply/patterns.py`, output in `ai_tmp/code-review-stage2/final/patterns.out`): all four pass, with the file's final newline and with trailing whitespace stripped. `example.md` is unchanged.
- `evals_sha256`: `78828f74f0a72581d29d915ba3e3cfb1ccfcde1701c1622dc3d83d53ba5726d2`, the frozen value. `skill_sha256`: `b76a09db4440fe14abf00b8971fdf82d96071df94e7ef1d6f428f90781797200`, on the clean tree at `6db0d6f` (`final/evals_hash.out`). From each commit's archive (`final/hash_at.out`), `e6d8f11` gives `32a66b28…` and `62d86de` `95d6276a…`, and `af11c72` gives `2832d80c…`, as recorded above.
- Body: 99 lines and 11,724 bytes, about 2,931 tokens, where `62d86de`'s was 11,627 bytes (`final/body_at.out`; the same method gives `b89df20`'s 11,336).
- `just validate-skills`: 0 errors, and the one expected `[extension-portability]` warning.
- `just run ./node_modules/.bin/claude plugin validate skills/change-viz --strict`: "Validation passed", with only the `ICON_MISSING` warning.
- The Codex load check against the fake API was not rerun: the frontmatter is unchanged since `c82b6f9`.
- `just check` in the foreground on the clean tree at `6db0d6f`: exit 0, 1210 passed, 4 skipped (`ai_tmp/code-review-stage2/gate-final.log`). The commit that records this changes only tickets 16 and 18.

**Still unverified:** every probe in this stage ran on Apple Git 2.50.1 only. No agent has read the new bullet. How often a fork's `main` holds commits its parent lacks, which is how often U3's question comes up, was not assessed.

### GREEN run, Claude (2026-11-12)

The maintainer ran the Claude Code half of Hand-off 2's GREEN run from `6b999cc`. The hand checks are in `ai_tmp/green-read/claude-green-hand-checks.md`, the E3 diagnosis in `e3-diagnosis.md` and the chosen fix in `e3-recommendation.md`, all in that folder. The run's one failed expectation, E3, led to the fix `253ee70`, so this run is the record for `6b999cc`'s text only. The Codex half did not run (below). No acceptance box is ticked.

| | Claude Code |
| --- | --- |
| Run id (both arms) | `20261112T065321Z-3958` |
| Commit | `6b999cc`, `git_dirty` false |
| `evals_sha256` | `78828f74…`, the frozen value |
| `skill_sha256` | `b76a09db…`, the text of `6db0d6f`. The installed copy equals `skills/change-viz/` (`diff -r`) |
| Agent | Claude Code 2.1.309, `claude-sonnet-5-5` |
| Grader | `claude-opus-5-5` on Claude Code 2.1.309, 2 calls per graded trial, `canary_passed: false` (the healthy value) |
| Every trial | `ok`, valid, contamination passed, `secret_found` null, `permission_denials: []` |

#### Results

| Check | Skill arm | Baseline |
| --- | --- | --- |
| `skill_triggered` | pass (deduced, below) | n/a (baseline arm) |
| `--top` and P1 to P4: deterministic | 1.00: all pass | 0.20: only `--top` passes |
| E1 to E8: graded | 0.88: 7 of 8, only E3 fails | 0.50: E5 to E8 pass |
| Behaviour case `passed` | false, on E3 alone | null (baseline, by design) |
| Quiet case, `no-trigger-unnamed-request` | pass: not triggered | skipped |

- **Non-discriminating:** `benchmark.json` lists E5 to E8, each passed in both arms.
- **E7 passed in the baseline this time,** where it failed at RED. With no skill text in that arm, this is variance at n = 1.

#### Hand reads

Observed in the transcripts and the kept workspaces, unless marked.

- **Flags:** all 7 of the skill arm's git calls carried `--no-optional-locks`, and its `diff` carried `--no-ext-diff --no-textconv`. Its `log` had no `-p`, `-S` or `-G`. The baseline and quiet trials, which had no skill text, ran a flagless `git diff --stat` and `git diff`: recorded, not a failure.
- **Writes and refs:** no write in any of the three workspaces: `status --porcelain --untracked-files=all` is empty, there is no `__pycache__/`, and every mtime falls inside setup. No ref moved: `main`, `add-top-words` and the symbolic `HEAD` match RED's. No command was `gh` or `push`.
- **Disclosure:** no final message names `change-viz` or a skill, or carries a credit line or an upstream name. Both grading files have `arm_disclosed: false` and `disclosure_matches: []`.
- **Reads:** the skill arm read `references/views.md`, as `SKILL.md:93` asks, but not `references/example.md`, though `SKILL.md:71` says to read it before writing. It had no need of `reading-the-branch.md`: `main` was the only candidate, 3 ahead.
- **Against the fixture facts:**
  - The baseline's "It has four commits on top of `main`" is wrong: the branch has 3. No expectation reads a commit count, so it was not scored.
  - The skill arm's "The `words` and `distinct` numbers change for existing input" is overgeneral, since `words` stays 23 on `sample.txt`, but not a contradiction by RED's bar.
- **Trigger:** deduced, as at RED. `results.json` has `triggered: ['change-viz']`, and the transcript stores no expansion. Supporting (inferred): the first turn's input was 3,806 tokens over the baseline's.
- **Quiet case:** one Bash call and no `Skill` or `Read`. Its first turn's input was 16,575 tokens against the baseline's 16,572: a lower bound, as at RED.

#### E3

- **The grader's evidence, verbatim:** "Each block's lead-in is two sentences describing the commit, not a single line saying what the block shows. The second lead-in ('The second commit adds the `--top` option. `main` now reads its arguments...') does not say that the block is an outline of main's steps. Because of this ambiguity the expectation is not clearly met."
- **Diagnosis:** the outline was told commit by commit, each block one commit, with lead-ins that open "The first commit …" and "The second commit …", against `SKILL.md:91`. Nothing in `SKILL.md:95` asked a lead-in to name what its visual draws, so "what they are looking at" could be read as the commit, and the second sentence narrated the change. `references/example.md:18` and `:28` modelled the same narrating lead-ins, though this run did not read them.
- **The fix, `253ee70`** (`e3-recommendation.md` §1):
  - `SKILL.md:95`: a lead-in "opens with what the visual draws and then says what to notice", with a whole-line instance, "What `fetch()` calls when a retry times out: every retry now shares one deadline". Its reason now reads "before knowing what it draws and why it is there". "One line, of one to three sentences" stays, as question 3 decided.
  - `references/example.md:18` and `:28` open by naming their view: "The path each page now takes through a build: …" and "The build loop, old and new: …".
  - Nothing else in the skill changed, and the frontmatter is untouched.
- **Held back,** each until its trigger, so a rerun stays attributable to one change (`e3-recommendation.md` §5 has the exact text):
  - the `:71` pointer, which puts "Read" first: if a run skips `example.md` again and its lead-ins differ from what the example models;
  - the `:99` done line, which adds "which opens with what the visual draws": if, under the new rule, a lead-in again opens on a commit or a change rather than on what its visual draws.
- **Not yet shown:** no agent has read the new text. The review round the recommendation left to the lead (§7) found nothing (**Review of the E3 fix**, below), which does not show that the fix works. At n = 1 a rerun can pass or fail E3 on either text by variance.

**Checks run on `253ee70`:**

- Before the edit, each old string occurred once in the tracked files (`git grep -c -F`). Both edited files equal the recommendation's patched copies in `ai_tmp/green-read/e3-rec/core/` byte for byte (`cmp`), before and after `just format`, which changed nothing.
- P1 to P4 on `references/example.md` (`ai_tmp/green-apply/patterns.py`, output in `ai_tmp/e3-fix/patterns.out`): all four pass, with the file's final newline and with trailing whitespace stripped, 8 of 8.
- `just validate-skills`: 0 errors, and the one expected `[extension-portability]` warning.
- `just run ./node_modules/.bin/claude plugin validate skills/change-viz --strict`: "Validation passed", with only the `ICON_MISSING` warning.
- `evals_sha256`: `78828f74f0a72581d29d915ba3e3cfb1ccfcde1701c1622dc3d83d53ba5726d2`, the frozen value. `skill_sha256`: `37bb71109d0f8e4e9a0677aaf7104d3fc51726763fcf67c081baac23ea17f501`, on the clean tree at `253ee70`, where `6db0d6f`'s was `b76a09db…` (`ai_tmp/e3-fix/evals_hash-after.out`).
- Body: 99 lines and 11,842 bytes, about 2,961 tokens (`ai_tmp/e3-fix/body_size.out`), where `6db0d6f`'s was 11,724 bytes.
- The Codex load check against the fake API was not rerun: the frontmatter is unchanged since `c82b6f9`.
- `just check` runs on the commit that adds this section, so its result is not recorded here.

#### Review of the E3 fix

A cross-model round on `253ee70` and its records, before the GREEN run again.

- **Implementer:** Claude Code running Claude Opus 5.5 (`claude-opus-5-5`), per the commits' trailers. The review script recorded no implementer model.
- **Reviewer:** Codex `gpt-6-astra` (fallback: no), exit 0 on the first run, with no rejected run
- **Reviewed:** `6b999cc..78d2a21` (`253ee70` and `78d2a21`), reviewed commit `78d2a21`. The brief carried `SKILL.md:51-99`, `references/example.md` and the whole diff, each equal to `78d2a21` byte for byte by the triage's comparison. It asked four questions: whether the change addresses the cause, lead-ins that narrate the commits, for branches in general and not only for the fixture or the rubric's wording; whether the new instance or the example's lead-ins invite a pattern that fails E1, E2 or E4, or crowds tickets 20 to 24; whether the rule's reason is given, short, in one home and consistent with "one line, of one to three sentences"; and whether these records are accurate. Brief: `ai_tmp/brief-e3-fix.md`.
- **Findings:** `ai_tmp/review-20261112T081504Z-codex.md` · **Triage:** `ai_tmp/triage-e3-fix.md`

| # | Severity | Finding | Verdict | Action |
| --- | --- | --- | --- | --- |
| – | – | No numbered finding. The review's whole text is "No actionable findings in `6b999cc..78d2a21`; the fix’s effectiveness remains unverified pending both agents’ reruns, as the records explicitly acknowledge." | The remark is true, and already recorded: **E3**'s "Not yet shown" and **Next** say both agents run again on the new text | None. No skill or eval file changed, so Hand-off 2 still starts from `253ee70`, and `skill_sha256` stays `37bb7110…` |

- **How much it shows:** the review took about 83 seconds, by its run files' times, on a brief of 88,118 bytes, and answered none of the four questions. The brief allows a one-line "nothing found". The triage found no Codex session transcript under `.tools/agent-homes/codex/`, so what the reviewer read is not recorded.
- **Checks,** read by the triage and not rerun, since nothing changed: P1 to P4 pass 8 of 8 (`ai_tmp/e3-fix/patterns.out`), and the body size and both hashes are as recorded above. `just check` after `78d2a21` was committed, by the log's time: 1210 passed, 4 skipped (`ai_tmp/e3-fix/gate.log`).

#### The Codex GREEN run did not run

- **Relayed by the lead, not observed:** the two commands were chained with `&&`.
- **Observed:** `just eval` exits 1 unless every skill-arm trial passes and every baseline trial is valid (`runner.py:578`, `:642`). Run `3958`'s behaviour case failed on E3, so the Codex command never started, and `eval-results/` holds no Codex GREEN run.
- The next hand-off gives each command its own line, so one agent's failure cannot skip the other.

#### Carried over

- **`+` marks inside a `text` fence:** block 2 was a pseudocode diff sketch fenced `text`, though `views.md:12` gives a diff sketch, pseudocode included, the `diff` fence, and the run read `views.md`. The rule exists and was read, so this ticket changes nothing. It is handed to ticket 20 (view choice) and ticket 24 (fences on GitHub), in each one's **What is known**.
- **Long notes:** the skill arm's first two note bullets each run to about five sentences. This ticket sets no limit on a bullet's length. Handed to ticket 20 (length), in its **What is known**.

#### Next

- The GREEN run again, on both agents, from `253ee70` or a later commit that leaves `skills/change-viz/` and `evals/change-viz/` as they are, with each command on its own line (**GREEN**, **Next**).
- The maintainer's read of a real branch: still pending.
