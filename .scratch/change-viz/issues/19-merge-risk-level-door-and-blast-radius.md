# 19: Merge risk: level, door and blast radius

**What to build:** every `change-viz` description carries a merge-risk call directly under the one-sentence why: a risk level, whether merging is a one-way or a two-way door, and the blast radius, followed by the reason for the level and how to walk the change back. A reader sees the critical call before any diagram.

Why: the maintainer wants "something like the 'merge danger' part" of mattpocock's `pr` skill, likes "the simple 'one-way' vs 'two-way' bit", and likes how similar systems "provide a simple clear 'risk score'".

**Blocked by:** 18 (Tracer: `change-viz` describes a branch).

Tickets 19 to 24 do not depend on each other, but each edits the same `SKILL.md`, `evals/change-viz/evals.json` and version. Land them one at a time, and rebase onto the last one before a live run.

**Status:** ready-for-agent

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
- [ ] Live evals are handed to the maintainer as absolute-path `just eval` commands. The agent reads `eval-results/` and never holds the token.
- [ ] Fixtures are a neutral project: no `skill` or `skills` wording anywhere in them, and none of Codex's sandbox-denial keywords (`operation not permitted`, `permission denied`, `read-only file system`, `seccomp`, `sandbox`, `landlock`, `failed to write file`) in output a failing command could print.
- [ ] Every "does not" outcome names how it is checked. A blinded expectation cannot be negative, so the check is an `output_matches` pattern, a transcript read by hand, or a limit stated in the completion notes.
- [ ] The skill explains why, not just what, and `SKILL.md` stays well under the validator's 500-line limit, with detail in `references/`.
- [ ] The skill's `plugin.json` version is higher than the one on `main` (ticket 18 keeps the scaffold's `0.1.0`), `just format` has run, the changes are committed, and then `just check` passes.

## Out of scope

A numeric score, a risk section at the end of the description, and any gate that blocks a merge. The skill reports a call; it enforces nothing.

## Review checkpoints

Use the `cross-model-review` dev skill.

- **Design checkpoint:** before the live run, write the level rules, the one-way list with its reasons, the two fixtures and the frozen rubric, and get them reviewed. Can a one-way door ever be Low? Would two careful readers pick the same level for each fixture? Does the one-way fixture make its irreversible step findable in the diff without naming it in a comment?
- **Implementation checkpoint:** before marking done, review the full diff against these acceptance criteria. Pay particular attention to level rules an agent could satisfy by always answering Medium, and to a `Walk it back:` line that suggests a revert where data is already gone.
