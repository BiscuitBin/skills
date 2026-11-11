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
