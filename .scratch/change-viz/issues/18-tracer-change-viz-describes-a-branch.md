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

Applied up to RED on branch `change-viz`, in commits `9b6e09e`, `34b0aad` and `9f10e71`, then the review fix `216a3c7`. Nothing is pushed, and no live eval has run.

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
- **Cases (`34b0aad`; E2 reworded at `216a3c7`).** `evals/change-viz/evals.json` has two cases on `wordstat-top`, both with the prompt "Describe what this branch changes.":
  - `behaviour-describe-branch`, marked `by_name: true`;
  - `no-trigger-unnamed-request`, an unmarked trigger case with `should_trigger: false`, which the baseline arm skips.
- **Assertions (frozen):**
  - `skill_triggered`.
  - `output_contains` `--top`, a guard against describing the wrong change.
  - P1: the three `##` headings in order, with no fence opening before `## Why the change`.
  - P2: between `## Special things to note` and `## Change outline`, only one to three bullets at column 0 (indented continuation lines and blank lines allowed) and an optional thematic break. `- None.` passes.
  - P3: a fenced block, backtick or tilde, opens and closes after `## Change outline`, with no `#` or `##` heading in between.
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
- **Patterns under Python `re`** (`ai_tmp/apply-18/patterns.py`): no difference from the PCRE2 results over the four liked pull requests and their copies, HumanLayer's template, `visual-pr`'s and `pr`'s `SKILL.md`, 13 synthetic messages and nine inline controls. A message with `\r\n` endings fails all three, as expected.
- **Fixture,** built with `fixture.build` and run with `python -B`: the facts listed under **Design as approved**, all as predicted. Tests: 2 OK at `main`, 4 after `folded`, 5 at the tip. `git status` is clean, both scripts are `100755`, `HEAD` is `refs/heads/add-top-words`, `git diff --stat main...HEAD` names three files, and `git show --stat HEAD` names only `README.md`. No `__pycache__/` was left.
- **Installer:** `skills add` of this checkout, for `claude-code` and for `codex`, printed `Found 2 skills`, `✓ change-viz (copied)` and `✓ cowsay (copied)`. Nothing was written to `~/.agents`.
- **Not run:** `just eval … --dry-run` and the live runs (the apply brief barred `just eval`), Ubuntu CI (nothing is pushed), and the marketplace install of `change-viz` (`claude plugin install change-viz@biscuitbin-skills`, `/change-viz:change-viz`), because the marketplace round trip installs cowsay only.

#### Implementer decisions (2026-11-11)

**Name.** `change-viz`, confirmed by the maintainer on 2026-11-10, before scaffolding, in the stage plan's "Decided with the maintainer". That plan is not in this repository, so the confirmation is recorded as the implementer's brief relayed it.

The implementer made the rest at apply time, on the design's open questions. The maintainer may override any of them at Hand-off 1.

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
| 1 | medium | E4 accepts a visual of wordstat's output without checking its values. A description showing `--top 3` as `the 6`, `river 3`, `mill 2` passes every pattern, and the blinded grader never sees the fixture. | valid (narrow, and already disclosed; low is closer) | Nothing frozen changes. The limit is stated here: each skill-arm message gets a hand read against the fixture facts under **Design as approved**, and a contradiction is recorded here as wrong about the fixture, whatever its grade. A values clause on E4 is open question 1, not recommended. |
| 2 | medium | E2's "counting a word once whatever its case or surrounding punctuation" can be read as counting repeats once, but the branch keeps every occurrence | valid (low is closer) | Fixed in `216a3c7`: E2 now reads "treating words that differ only in case or surrounding punctuation as the same word". It changes `evals_sha256`, before RED. The reviewer's "while retaining their occurrence counts" is not adopted: it adds a requirement a correct one-sentence why need not meet. E2's first-paragraph scope and its "or both" do not change. |
| 3 | medium | E1 and E2 read only the first paragraph, so further paragraphs under "Why the change" pass, against the ticket's one-sentence why | valid | The limit is stated here, with a hand read of each skill-arm message (the "does not" table under **Design as approved**). A fourth `output_matches`, P4, is open question 2, recommended. |

**The checkpoint's two questions.** Could the behaviour case pass on a description that is wrong about the fixture? In part, yes: E4 checks no values, and an extra false claim elsewhere can pass (finding 1), so the hand read covers it. Does any expectation need the grader to know which arm it is reading? No. Each is about text in the material, and E1 to E3 fail in the baseline because its message has no such headings.

No second round: the only frozen change rewords one clause of E2 and keeps its scope. The other two fixes are design text: a hand-read row and a list of facts. If the maintainer takes P4, it is a new frozen assertion and gets a focused review before RED.

#### Open questions for the maintainer

1. **A values clause on E4** (finding 1). Changes frozen text, so settle before RED. The clause would append "If it shows wordstat's output for sample.txt, that output is …". **Recommendation: no.**
   - A pass needs a verbatim quote, and the burden of proof is on passing, so a correct visual made only of a diagram risks failing it.
   - The negative form ("shows no wrong counts") is barred for a blinded expectation.
   - Requiring the numbers would push the agent to run the fixture's code, which ticket 21 owns.
   - It would still miss wrong output for a made-up example text, and the hand read covers the gap.
2. **P4, one paragraph under 'Why the change'** (finding 3). A new frozen assertion, so settle before RED. **Recommendation: yes.** The decided outline and the criteria say "One sentence", and ticket 19's `**Risk: …**` line is a shape the maintainer decided on 2026-11-10. It would go after P3:

   ```json
   {
     "type": "output_matches",
     "pattern": "(?ms)^##[ \\t]+Why the change[ \\t]*\\n(?:[ \\t]*\\n)*(?:[^\\s#][^\\n]*\\n)+(?:[ \\t]*\\n)*(?:\\*\\*Risk:(?:(?!^##[ \\t]).)*?|(?:[-*_][ \\t]*){3,}\\n(?:[ \\t]*\\n)*)?^##[ \\t]+Special things to note[ \\t]*$"
   }
   ```

   - **What it requires:** under `## Why the change`, one paragraph of non-blank lines, none starting with whitespace or `#`; then optionally a block starting `**Risk:` or one thematic break; then `## Special things to note`.
   - **Probed:** Python `re` gives the triage's PCRE2 results on 31 inputs (`ai_tmp/apply-18/p4_probe.py`). It matches the four liked pull requests, ticket 19's shape, and a label inline on the sentence or on the next line. It fails the reviewer's probe, a fence or bullet after a blank line, and a label as its own paragraph.
   - **Costs:** it is lenient when a bullet or fence sits directly under the sentence, and after `**Risk:`. A one-space indent fails, and so do `\r\n` endings. Ticket 21's label would fail if set as its own paragraph.
   - **RED:** no expected effect (unobserved): neither arm writes the heading, so P4 fails in both, as P1 does.
   - **If adopted:** add it to `evals.json`; update `ai_tmp/apply-18/patterns.py` (its `assert len(patterns) == 3`, its expected columns, and its unbolded `Risk: Low.` control, which P4 rejects); run `just format` and `just validate-evals`; commit; then a focused review of P4.
3. **"One-line lead-in" in E3.** E3 reads "one line of prose" as one physical line of one to three sentences, as the four liked pull requests write their lead-ins, not as one sentence. Confirm. If the answer is "one sentence", E3's text changes, so settle before RED.
4. **`__pycache__/` as a write.** The design counts it, through the hand read, and reports it on its own line as "ran the fixture's code". If GREEN trials leave one, is that a ticket 18 failure, which needs a "read the branch, do not run its code" line in the skill now, or a limit recorded for ticket 21, which owns running code? No frozen text changes; settle before GREEN.
5. **ADR 0008.** It says everything in the repository is under `LICENSE`. With an upstream notice beside a skill, does it need a sentence? The decision left this to the design review, which did not raise it. Not blocking; settle before `NOTICE.md` lands at GREEN.
6. **Overrides.** Any implementer decision above. Two rest on a reading of this ticket: Matt Pocock's notice ships with ticket 19, though "each upstream's" notice can be read as all three at 18; and this repository's own notice stays out of `NOTICE.md`.

#### Design as approved

**Design as approved:** `ai_tmp/design-18.md` (gitignored), as reviewed at this checkpoint, with the fixes above. The implementer decisions in it still await the maintainer at Hand-off 1. These bullets carry what exists only in that file:

- **Freeze.** `evals_sha256` covers `evals.json` and the fixture directory. The rubric does not change from the RED run to GREEN, so any change (P4, an E4 clause, E3's wording) lands before RED, after `just format` and `just validate-evals`. RED runs from `216a3c7` or later.
- **Grader material.** The blinded call sees the bare prompt, never the invocation, the final message up to 20 KB, and any file the agent created or changed. Fixture files left as built are not sent, so each expectation carries its own facts. E8 is judged in a second call from the commands and their output. No expectation refers to another, so the canary's random place changes nothing.
- **Pattern limits.** P2 reads bullet markers at column 0 only: an indented marker, or an unindented wrapped line, fails on purpose, since allowing one would let four bullets pass as one. So the GREEN text writes note bullets at column 0 with indented continuations. P2 also reads an indented `- b` after `- a` as a continuation, though GitHub renders two bullets, and passes nested bullets. `\r\n` endings fail all three patterns.
- **Room for tickets 19 to 24.** P1 allows prose before the first heading (ticket 22's scope line) but no fence, and anything between the headings (ticket 19's risk line). E1 and E2 read only the first paragraph. P3 needs a fence under the outline, so a table-only outline (ticket 20) fails this case; a table can sit beside a fence. Ticket 19 asserts only its line's shape on this case and brings its own fixtures. Ticket 22 needs its own fixture, or a copy of these trees with `staged` and `worktree`. Ticket 23 can reuse this one (no remote). Ticket 24 can reuse it for Mermaid labels with parentheses.
- **GREEN gain,** recorded three ways: shape (P1 to P3, E1, E3); substance measured in both arms (E4 to E7); and E2, substance that passes only once the heading exists. E5, E8, and maybe E4 and E6, will show as non-discriminating. They stay as guards that make a wrong description fail. E6 may pass at RED on Claude Code if its startup context lists the commit subjects; the RED transcripts confirm it.
- **Disclosure reads.** In the skill arm the CLI's own text says "skill", so an echo marks the trial `arm_disclosed`, and it is still graded. E8's transcript material widens the check: on Codex at GREEN, a `cat` of the skill's files likely sets the flag. So read `disclosure_matches` in each grading file and look for each match in the final message; only those reached the blinded call. A bare `change-viz` or `Change Viz` is not flagged, so run `rg -i 'change[- ]?viz'` over each skill-arm final message and report hits beside `arm_disclosed`.
- **Records.** `GLOSSARY.md` gains **Change source** at GREEN: a branch is the only one this ticket handles. The run ids of RED and GREEN, both arms, both agents, go here; the RED ids also go to ticket 17, which closes its live-trial criterion.
- **Codex and `metadata.credits`.** To see a load failure before the GREEN live run, load the GREEN `SKILL.md` in the pinned Codex against the fake API, as `tests/evals/test_codex_adapter.py` does, and look for `failed to load skill`.

"Does not" outcomes and their checks. A blinded expectation cannot be negative, so each is a pattern, a hand read, or a limit stated here.

| Outcome | Check |
| --- | --- |
| No more than three notes | P2 |
| No prose under 'Why the change' beyond its one sentence | A hand read of each skill-arm message. Limit: E1 and E2 read only the first paragraph, to leave room for ticket 19's risk line, and nothing else checks further paragraphs unless P4 is adopted. |
| Loads only when named | The quiet case, a lower bound (it sees only a confirmed load), plus a hand read of its transcripts |
| Not a file-by-file changelog | E4's positive form, plus a hand read of the skill-arm messages |
| Not wrong about the fixture | `--top`, E2 and E5 to E7 carry the facts. Limit: E4 checks no values, and an extra false claim can pass. So each skill-arm message gets a hand read against the facts below, and a contradiction is recorded here whatever its grade. |
| Writes no file | By hand, in each kept trial workspace: `git status --porcelain --untracked-files=all` is empty (the installed skill is excluded), and `find . -name __pycache__ -not -path './.git/*'` finds nothing. A `__pycache__/` is reported on its own line (open question 4). |
| Changes nothing else in the repository | By hand: `main`, `add-top-words` and the symbolic `HEAD` (`refs/heads/add-top-words`) match a baseline trial's. A `git checkout`, `switch`, `stash` or `worktree add` is an `infra_error` on Codex, whose sandbox denies writes to `.git/`, and any such trial is listed here under the Codex limits. On Claude Code it succeeds, and this check catches it. |

Fixture facts for the hand read. The first four were observed at apply time; the last is read from the trees.

- On `main`, `python3 wordstat.py sample.txt` prints `words: 23` and `distinct: 13`.
- On `add-top-words` it prints `words: 23` and `distinct: 10`, and `--top 3` adds `most common:` followed by `the 7`, `river 4` and `mill 3`.
- `one - two` is 3 words on `main` and 2 on the branch.
- The usage error now comes from argparse: `usage: wordstat.py FILE` becomes `usage: wordstat.py [-h] [--top N] file`.
- The README change documents `--top` only.

#### Next

**Next:** Hand-off 1, the RED run.

Settle open questions 1 to 3 first. If any of them changes `evals.json`, commit that change after `just format` and `just validate-evals`, and review it (P4 needs a focused review) before the run.

Then, in the maintainer's terminal with `CLAUDE_CODE_OAUTH_TOKEN` exported (the grader needs it on both agents; Codex also uses its login in the project's Codex home):

```sh
cd /Users/scutting/.supacode/repos/skills/change-viz
just eval change-viz --agent claude --baseline
just eval change-viz --agent codex --baseline
```

What RED is expected to show (unobserved):

- **Skill arm:** the behaviour case fails, because the stub body names no heading. P1 to P3 and E1 to E3 fail. `skill_triggered` passes, because the CLI records the by-name load whatever the body says.
- **Baseline arm:** the behaviour case fails too, on the same items: no agent writes the three headings unasked. If it passes, the case changes until it measures a real gap (`CONTRIBUTING.md` §2).
- **Quiet case:** passes in the skill arm, with no confirmed load, and is skipped in the baseline.
- `--top`, E5 and E8 likely pass in both arms, and so does E6 on Claude Code. E4, E7 and Codex's E6 can go either way.

Then read `eval-results/<run-id>/`: the quiet case's transcripts, each kept workspace (the writes and refs rows above), the two disclosure reads, and each skill-arm message against the fixture facts. Record the run ids here and in ticket 17.
