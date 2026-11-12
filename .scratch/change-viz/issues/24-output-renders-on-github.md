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

## Acceptance criteria

- [ ] Every line of the "to verify" list above is checked against GitHub's documentation or a real render, and marked confirmed, corrected or dropped, with the source. The list in this ticket is updated to match.
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
- [ ] The place and the exact text of that post are approved by the maintainer first, or the maintainer posts it.

### Every `change-viz` ticket

These repeat in tickets 18 to 24 so that each can be read alone.

- [ ] Eval cases are written and baselined before the skill text changes (RED, then GREEN), and each rubric is frozen before its live run (`CONTRIBUTING.md` §2 and §3). The baseline and skill-arm run ids on Claude Code and Codex are recorded here.
- [ ] Live evals are handed to the maintainer as absolute-path `just eval` commands. The agent reads `eval-results/` and never holds the token.
- [ ] Fixtures are a neutral project: no `skill` or `skills` wording anywhere in them, and none of Codex's sandbox-denial keywords (`operation not permitted`, `permission denied`, `read-only file system`, `seccomp`, `sandbox`, `landlock`, `failed to write file`) in output a failing command could print.
- [ ] Every "does not" outcome names how it is checked. A blinded expectation cannot be negative, so the check is an `output_matches` pattern, a transcript read by hand, or a limit stated in the completion notes.
- [ ] The skill explains why, not just what, and `SKILL.md` stays well under the validator's 500-line limit, with detail in `references/`.
- [ ] The skill's `plugin.json` version is higher than the one on `main` (ticket 18 keeps the scaffold's `0.1.0`), `just format` has run, the changes are committed, and then `just check` passes.

## Out of scope

Rendering anywhere but GitHub pull request descriptions and comments, HTML and image output, a full Mermaid parser, and a rendering check in `just check` or CI.

## Review checkpoints

Use the `cross-model-review` dev skill.

- **Design checkpoint:** before building, write the verified rule list with its sources and the choice on the checker, and get them reviewed. Is any rule still resting on recollection? If there is a checker, which rules can it check without parsing Mermaid, and can it flag a correct draft as broken?
- **Implementation checkpoint:** before marking done, review the full diff against these acceptance criteria. Pay particular attention to rules with no source, to a checker that passes a draft GitHub would break, and to the rendering proof covering fewer constructs than the skill emits.
