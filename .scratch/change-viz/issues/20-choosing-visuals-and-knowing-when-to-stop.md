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
- **From ticket 18's Claude GREEN run (2026-11-12):** the skill arm put a pseudocode diff sketch with `+` marks in a `text` fence, though `references/views.md` gives a diff sketch the `diff` fence and the run read it, and its first two note bullets ran to about five sentences each, where ticket 18 sets no limit on a bullet's length.

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
- [ ] Live evals are handed to the maintainer as absolute-path `just eval` commands. The agent reads `eval-results/` and never holds the token.
- [ ] Fixtures are a neutral project: no `skill` or `skills` wording anywhere in them, and none of Codex's sandbox-denial keywords (`operation not permitted`, `permission denied`, `read-only file system`, `seccomp`, `sandbox`, `landlock`, `failed to write file`) in output a failing command could print.
- [ ] Every "does not" outcome names how it is checked. A blinded expectation cannot be negative, so the check is an `output_matches` pattern, a transcript read by hand, or a limit stated in the completion notes.
- [ ] The skill explains why, not just what, and `SKILL.md` stays well under the validator's 500-line limit, with detail in `references/`.
- [ ] The skill's `plugin.json` version is higher than the one on `main` (ticket 18 keeps the scaffold's `0.1.0`), `just format` has run, the changes are committed, and then `just check` passes.

## Out of scope

Whether a diagram renders on GitHub (ticket 24), evidence tables and their labels (ticket 21), HTML or image output, and React component trees as their own view until a fixture needs one.

## Review checkpoints

Use the `cross-model-review` dev skill.

- **Design checkpoint:** before the live run, write the choosing rule, the length budgets, the three fixtures and their patterns, and get them reviewed. Does any pattern pass on a message that picked the wrong view? Does the length cap for the one-line fix still leave room for the three headings, and for ticket 19's risk line if it has landed?
- **Implementation checkpoint:** before marking done, review the full diff against these acceptance criteria. Pay particular attention to rules that read as "always include one of each", and to budgets the fixtures never test.
