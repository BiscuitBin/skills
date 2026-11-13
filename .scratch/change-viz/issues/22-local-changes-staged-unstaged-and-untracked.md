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
