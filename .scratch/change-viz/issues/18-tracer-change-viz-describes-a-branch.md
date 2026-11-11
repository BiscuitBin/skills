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

#### Credit form (proposed; lands with the first upstream text)

At GREEN the frontmatter replaces the RED description with the full one and adds a string `metadata.credits`. The other fields stay as at RED:

```yaml
description: Describes what the current branch changes, as Markdown for a pull request description or comment, with one sentence on why, one to three notes and a change outline built from small visuals such as Mermaid diagrams, diff sketches and file trees. Runs only when invoked by name, never on its own. It reads the branch and writes no file unless asked.
metadata:
  credits: 'Adapted from show-me and visual-pr by HumanLayer (Copyright (c) 2026 HumanLayer), MIT. The full notice is in NOTICE.md.'
```

- **Why a string.** The validator requires `metadata` to map strings to strings, so mattpocock's nested `metadata.credits` fails. Codex 0.163.0's parser ignores unknown `metadata` fields (a source read of `codex-rs/skills/src/parser.rs`, not a run), and skills@1.7.4 reads `metadata` only for `internal`.
- **No "skill" wording.** Neither string uses the word or the slug `humanlayer/skills`, because Codex injects the frontmatter and the disclosure check would match. The URL is in `NOTICE.md`.
- **`skills/change-viz/NOTICE.md`,** beside `SKILL.md`: a `# Notices` heading, then "Parts of change-viz are adapted from an MIT-licensed project. Its copyright and permission notice follows, as its licence requires for copies and substantial portions." Then a `## HumanLayer` section:
  - source: [humanlayer/skills](https://github.com/humanlayer/skills) at commit `4d69d20f6e9b57b4fcf0d501ccfb1be961f0f329`, the `show-me` and `visual-pr` skills;
  - adapted: the three headings of the outline and their limits, the catalogue of views, and the rule to pick the smallest view that makes the point clear;
  - the upstream `LICENSE`, `Copyright (c) 2026 HumanLayer`, copied byte for byte into a `text` fence.
- **Ticket 19's entry.** Ticket 19 adds a `## Matt Pocock` section in the same shape: [mattpocock/skills](https://github.com/mattpocock/skills) at commit `4ae2317ddb22b046e26455e4f9c9b3aaaf62212d`, the `pr` skill; adapted, the merge-risk terms, one-way and two-way doors and blast radius; his `LICENSE`, `Copyright (c) 2026 Matt Pocock`. It changes the intro to "from two MIT-licensed projects. Their copyright and permission notices follow, as their licence requires", and extends the credit with "and the merge-risk terms from pr by Matt Pocock (Copyright (c) 2026 Matt Pocock)".
- **No link from the body,** and no licence line. Both installers copy the whole skill directory, and a body line would reach every Claude Code expansion. The `skills` round trips compare each installed copy with every file in `skills/<name>/`, so `NOTICE.md` travelling is tested there. For the marketplace it is reasoned, not tested.
- **Fallback.** If the pinned `claude plugin validate --strict` rejects `metadata` at GREEN, drop `metadata.credits`, keep `NOTICE.md`, and credit in one body line that links it.
- **Records at GREEN.** This ticket records the form, and D3's row in `.scratch/foundation/follow-ups.md` says `change-viz` carries its upstream notice. Both land with `NOTICE.md`.

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

The maintainer answered questions 1, 2, 3, 6 and 7 on 2026-11-11, as the briefs relay the answers. Questions 4 and 5 are still open.

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
4. **`__pycache__/` as a write.** **Open.** The design counts it, through the hand read, and reports it on its own line as "ran the fixture's code". If GREEN trials leave one, is that a ticket 18 failure, which needs a "read the branch, do not run its code" line in the skill now, or a limit recorded for ticket 21, which owns running code? No frozen text changes; settle before GREEN.
5. **ADR 0008.** **Open.** It says everything in the repository is under `LICENSE`. With an upstream notice beside a skill, does it need a sentence? The decision left this to the design review, which did not raise it. Not blocking; settle before `NOTICE.md` lands at GREEN.
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
| Writes no file | By hand, in each kept trial workspace: `git status --porcelain --untracked-files=all` is empty (the installed skill is excluded), and `find . -name __pycache__ -not -path './.git/*'` finds nothing. A `__pycache__/` is reported on its own line (open question 4). |
| Changes nothing else in the repository | By hand: `main`, `add-top-words` and the symbolic `HEAD` (`refs/heads/add-top-words`) match a baseline trial's. A `git checkout`, `switch`, `stash` or `worktree add` is an `infra_error` on Codex, whose sandbox denies writes to `.git/`, and any such trial is listed here under the Codex limits. On Claude Code it succeeds, and this check catches it. |

Fixture facts for the hand read. The first four were observed at apply time; the last is read from the trees.

- On `main`, `python3 wordstat.py sample.txt` prints `words: 23` and `distinct: 13`.
- On `add-top-words` it prints `words: 23` and `distinct: 10`, and `--top 3` adds `most common:` followed by `the 7`, `river 4` and `mill 3`.
- `one - two` is 3 words on `main` and 2 on the branch.
- The usage error now comes from argparse: `usage: wordstat.py FILE` becomes `usage: wordstat.py [-h] [--top N] file`.
- The README change documents `--top` only.

#### Residual risk

- **The trial path names the arm.** Each agent's working directory ends `<case>/skill-1/workspace` or `<case>/baseline-1/workspace` (`runner.py:96-98`), and the agent sees it: the fake-API runner probe (`ai_tmp/probe-red/`) found it in Claude Code's system prompt and in Codex's `<cwd>` context, in both arms. From a checkout whose path holds `skills/change-viz`, the baseline also sees the skill's name. The grader never sees the path. It affects every suite, cowsay included. The maintainer decided on 2026-11-11 that RED runs as is, and the fix is a harness follow-up: `.scratch/foundation/follow-ups.md`, **Ticket 18, the arm in the trial path**.
- **P4's stated limits** are under **Pattern limits**, and the hand read covers what they leave open.

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

The maintainer ran both commands under **Next** from `b28cd28`. That is later than `3d3dc4b`, and `evals/change-viz/` and `skills/change-viz/` are unchanged between the two. Each run got a reader and a skeptic: `ai_tmp/red/claude.md` with `claude-verify.md`, and `ai_tmp/red/codex.md` with `codex-verify.md`. Each final message is saved verbatim beside them as `ai_tmp/red/<agent>-<case>-<arm>.md`. Where a skeptic refuted its reader, this record follows the skeptic. No refutation changes a verdict. No acceptance box is ticked: each still waits for GREEN or for the implementation checkpoint.

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
