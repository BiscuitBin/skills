# 03: Cowsay skill passes a spec validator

**What to build:** The repo ships its first skill, `cowsay`. When a user asks an agent to have a cow say something, the agent runs the skill's bundled script and shows the ASCII cow with the text in a speech bubble, exactly as the script printed it.

The repo also gets its own skill validator. `just check` and CI run it over every skill in the repo, shipped skills and dev skills alike. Broken skills fail with clear, specific errors. Spec rules and agent-specific facts are in the research notes (`.scratch/foundation/research.md`).

**Blocked by:** 01 (Cross-model adversarial review as a repo dev skill), 02 (Project-local toolchain and green `just check`).

**Status:** done

**Agent requirements:** Any implementing agent (Claude Code, Codex or Pi). No live agent runs are required outside the cross-model review checkpoints below; the skill and validator are checked locally.

## Acceptance criteria

**Cowsay skill:**

- [x] The skill sits in the repo's shipped-skills area. An ADR records the layout chosen (flat or bucketed).
- [x] Its description makes it trigger on requests for a talking or ASCII cow, and not on unrelated requests that merely mention cows or ASCII art.
- [x] The bundled script has no third-party dependencies and runs unchanged on macOS and Linux. Its output depends only on its input.
- [x] The script handles a single word, long text (word-wrapped at a fixed width), multi-line input, empty input, and non-ASCII text. Unit tests cover each of these and run in `just check`.
- [x] The skill body tells the agent to run the script and show its output verbatim, not to draw the cow freehand.
- [x] The skill has Codex UI metadata (an `openai.yaml`) with a display name and a short description.

**Validator:**

- [x] It enforces the spec rules:
  - the name format and length
  - that the name matches its directory
  - description and compatibility lengths
  - that metadata is a map of strings to strings
  - the allowed top-level fields
- [x] Frontmatter fields outside the spec are accepted only if they are on a per-agent extension allowlist, for example Claude Code's documented extras. Anything else is an error. The allowlist records which agents accept each field. Shipped skills go to every agent, so a field that any target agent is known to reject is an error in a shipped skill.
- [x] It enforces size limits (body lines and an approximate token budget). An ADR or the validator's reference doc says which limits are errors and which are warnings.
- [x] Every relative reference in `SKILL.md` resolves to a file inside that skill. A missing file or a path that escapes the skill is an error. Referenced files that reference further files (a chain more than one level deep) are a warning. Directory depth is not limited.
- [x] It checks the `openai.yaml` shape when the file is present.
- [x] Each error names the file, the rule and a fix hint, and any error gives a nonzero exit.
  - A set of broken-skill fixtures covers every rule, one fixture per rule, each with a test asserting its specific error.
- [x] For the shared spec rules, a test compares the validator's verdicts with the `skills-ref` reference validator on the fixtures. Any intentional difference is documented.
- [x] `just check` runs the validator over every skill in the repo, including the dev skill from ticket 01, and it passes.

## Review checkpoints

Use the repo's cross-model adversarial review skill from ticket 01, or the protocol written out there:

- Pick the reviewer by the cross-model rule.
- A reviewer subagent saves its findings to the scratch folder.
- A separate triage subagent checks each finding against the code.
- Apply the valid fixes, rerun `just check`, and record every finding and how it was handled under **Completion notes**.

- **Design checkpoint:** before building the validator, write the proposed rule list (each rule with its severity and rationale) and the per-agent extension allowlist, and get them reviewed. Is anything too strict for real Claude Code, Codex or Pi skills? Too loose to catch real breakage? Wrong about the spec?
- **Implementation checkpoint:** before marking done, review the full diff against these acceptance criteria.

## Completion notes

### Design checkpoint

- **Implementer:** Codex (OpenAI family; runtime model ID not exposed).
- **Reviewer:** Claude Code `claude-opus-5-5` (fallback: no).
- **Reviewed:** working-tree design proposal and review-runner prerequisite patch against base `79145ca401463eb416d0f7a6b141516ad9d20ef7`.
- **Findings:** `ai_tmp/review-20261024T025901Z-claude.md` · **Triage:** `ai_tmp/triage-design.md`.

| # | Severity | Finding | Verdict | Action |
| --- | --- | --- | --- | --- |
| 1 | high | Inline code examples misidentified as missing resources | valid | Defined concrete bundled path syntax; Markdown links remain strict. |
| 2 | high | Codex schema omitted supported fields | valid | Added products, command and callback port, enumerated interface keys and cited pinned source. |
| 3 | medium | Codex support unknown and rejection policy lacked evidence | valid (evidence gap) | Verified pinned parser ignores extensions; warnings describe missing semantics; rejection test uses explicitly synthetic evidence. |
| 4 | medium | Claude tool lists rejected and truncation unchecked | valid | Dev tool lists accepted; combined-description warning added. |
| 5 | medium | Entire agent-home exclusion hides persistent changes | valid | Narrowed to known Claude runtime paths; config and home symlink changes stay monitored, with regression tests. |
| 6 | low | Recursive discovery treats nested resources as skills | valid for nested resources | Flat direct-child discovery; missing entrypoints fail, nested templates stay resources; ADR 0009. |
| 7 | low | Chained-reference errors and text scope undefined | valid | UTF-8 text references checked recursively with cycles handled; missing/escaping descendants remain errors. |
| 8 | low | Line boundary and token heuristic undocumented | valid for boundary/documentation | Body errors at 500 lines; byte/4 heuristic documented as language dependent and warning only. Universal Unicode overcount claim unsupported. |
| 9 | low | Reference parser differences and pin unspecified | valid | Pinned skills-ref 0.1.1 and documented/tested YAML, scalar and naming differences. |

**Review setup:** Authentication required the isolated project-local Claude home. User explicitly authorized external review context. The first successful Claude invocation was rejected by the runner for its expected runtime writes; that output was not triaged. The prerequisite runner fix was then reviewed with the proposal and narrowed per finding 5. All CLI execution uses the project-pinned Python and agent CLIs.

**Follow-ups:** None from design triage.

### Implementation checkpoint

- **Implementer:** Codex (OpenAI family; runtime model ID not exposed).
- **Reviewer:** Claude Code `claude-opus-5-5` (fallback: no).
- **Reviewed:** full working-tree diff and untracked files against `79145ca401463eb416d0f7a6b141516ad9d20ef7`.
- **Findings:** `ai_tmp/review-20261024T030915Z-claude.md` · **Triage:** `ai_tmp/triage-implementation.md`.

| # | Severity | Finding | Verdict | Action |
| --- | --- | --- | --- | --- |
| 1 | high | Runtime exclusions hide Claude config and auto-memory | valid | Removed .claude.json and projects exclusions; added config/memory snapshot regression. |
| 2 | medium | Nested inline bundled paths use wrong base | valid, scoped | Retained parser provenance; inline bundle paths resolve from skill root, Markdown links from referrer. Added regression and docs. |
| 3 | medium | Trailing stdin newline adds row | invalid | Exact input preserves explicit trailing breaks in both transports; added equality regression. |
| 4 | medium | Case-insensitive host masks broken references | valid | Check exact path-component case, retaining symlink containment checks; added cross-platform regression. |
| 5 | low | Diagnostics omit invalid names/unknown keys | valid in part | Name errors identify value/constraint; schema errors identify key and section. Collecting every schema error per run is not required. |
| 6 | low | CLI dot path mismatches directory name | valid | Resolve input directory before name comparison; CLI regression. |
| 7 | low | Missing entrypoint gets YAML fix hint | valid in part | Specific missing-SKILL.md message and creation hint under stable frontmatter rule; docs and regression aligned. |
| 8 | low | No real allowlisted extension rejection | invalid | Conditional requirement uses actual pinned CLI loader evidence; packaging validators are different products. Synthetic rejection remains explicitly labeled. |
| 9 | low | Fixture overlap and positional selection | valid in part | Match directory to invalid uppercase name and select CLI fixture by ID. Existing exact-rule/severity assertion already prevents wrong-rule passes. |
| 10 | low | Unicode terminal-cell alignment | invalid under agreed scope | Deterministic Unicode code-point sizing was reviewed and disclosed; non-ASCII text is preserved. Full terminal-cell/grapheme sizing can be a future enhancement. |

**Validation before review:** just check passed: 141 tests, strict mypy, all lint/lockfile checks, both source skills with zero diagnostics, all three pinned CLI versions. The bundled external skill-creator quick_validate.py rejects the spec-valid compatibility field because its allowlist is stale; the repo validator and pinned skills-ref both support it.

**Follow-ups:** Optional terminal-cell-aware Unicode rendering; not needed for this ticket. Revised implementation re-review completed below.

### Implementation re-review

- **Reviewer:** Claude Code `claude-opus-5-5` (fallback: no).
- **Reviewed:** revised working-tree diff and untracked files against `79145ca401463eb416d0f7a6b141516ad9d20ef7`, with prior triage decisions supplied.
- **Findings:** `ai_tmp/review-20261024T031643Z-claude.md` · **Triage:** `ai_tmp/triage-rereview.md` (fresh separate subagent).

| # | Severity | Finding | Verdict | Action |
| --- | --- | --- | --- | --- |
| 1 | medium | Linked programming source parsed as Markdown | valid | Recurse into documentation formats (.md, .markdown, .txt, extensionless), check other resources without interpreting code. Python and shell regression tests added. |
| 2 | medium | Subagent brief omits pinned CLI PATH | valid | Put project node_modules/.bin PATH explicitly in both concrete runner commands. Completed reviews already used it. |
| 3 | low | Case checks enumerate ancestors outside skill | valid | Start case checks at skill root for literal and resolved paths; regression forbids ancestor enumeration. |
| 4 | low | Synthetic fixture excuses undocumented mismatch | valid in part | Give the fixture its actual extension-policy difference and require explicit differences. Overall verdict comparison remains appropriate; independent tests assert our rule and severity. |
| 5 | low | Raw HTML resource links skipped | valid | Parse HTML href/src attributes with stdlib HTMLParser; valid, missing, escaping and fenced-example coverage. |
| 6 | low | Missing discovery roots raise traceback | valid | Actionable discovery diagnostic names root and supplies invocation hint; CLI regression covers both absent roots. |
| 7 | low | Exact stdin transfer unclear and documented -- untested | valid in part | Explain printf transfer and intentional newlines; all argument tests now use --, including empty text and a new leading-hyphen regression. |

**Final validation:** `just check` passed: 156 tests, strict mypy, all lint and lockfile checks, two source skills with zero errors and warnings, and all three pinned CLI version checks. `just format` applied repository formatting. No external tools wrote outside the project.

**Result:** Shipped cowsay skill, dependency-free deterministic script, Codex UI metadata, flat-layout ADR 0009, validator CLI/API and reference documentation, per-rule fixtures and skills-ref differential tests, wired into the full local and CI gate. All acceptance criteria are checked above.

### PR #4 feedback and CI repair

- **Implementer:** Codex (OpenAI family; runtime model ID not exposed).
- **Reviewer:** Claude Code `claude-opus-5-5` (fallback: no).
- **Reviewed:** PR diff against origin/main at HEAD `126ae29a52560fb0ae2a74fe490364d3f828108b`.
- **Findings:** `ai_tmp/review-20261024T040411Z-claude.md` · **Triage:** `ai_tmp/triage-pr4-feedback.md` (fresh separate subagent).

| # | Severity | Finding | Verdict | Action |
| --- | --- | --- | --- | --- |
| 1 | medium | Extensionless source parsed as Markdown | valid | Recurse only into .md/.markdown/.txt documentation; extensionless Python, shell, bin and dotfile regressions retain resource existence checks. |
| 2 | low | Parent paths still enumerate ancestors | valid | Enumerate only directories inside the root; resolve each component to retain symlink/parent semantics. Added exit-and-return paths and symlink-parent regression. |
| 3 | low | Inline literal # and % treated as URL syntax | valid | Separate literal filesystem paths from Markdown/HTML URL destinations. Test correct resources and decoded/truncated decoys. |
| 4 | low | Back/self links incorrectly warn about deeper chains | valid | Exclude resolved self and SKILL.md links from chain depth, while retaining all resource checks, cycle detection and real descendant warnings. |
| 5 | low | Codex icon resources not checked | out of scope | Ticket requires metadata shape and SKILL.md references. Documented shape-only icon boundary; resource validation is a follow-up. |
| 6 | low | Reference documentation misstates behavior | valid in part | Correct rule ownership and discovery fixture coverage; replace proposal instructions with implemented behavior and link ADR 0009. Existing discovery CLI test already covers this rule. |
| 7 | low | User backticks close outer display fence | invalid | Rendered bubble prefixes every text line; CommonMark reproductions retain stdout exactly inside one fence. |
| 8 | low | No live triggering evidence | invalid as ticket gap | Static description satisfies this ticket; live agent evals are explicitly deferred. No empirical trigger-quality claim is made. |

**CI finding:** The committed completion notes had an extra blank line (MD012); removed it. The notes were edited after the previous local gate, so that earlier pass did not cover final committed contents. A generated local-only PR description also needed a file-local MD041 directive for the visual-pr template's opening links; fixed without disabling repository lint rules or staging the artifact.

**Validation after fixes:** `just check` passed locally with 166 tests, strict mypy, lint/lock checks, two skills with zero diagnostics and all pinned CLI version checks. Focused validator tests cover the repaired cases. A focused re-review and final post-notes gate precede publication; GitHub CI on the pushed commit is the completion gate.

**Follow-ups:** Optional Codex icon resource validation and the previously recorded terminal-cell-aware Unicode rendering. Live trigger evals remain in later foundation tickets.

### PR #4 focused fixes re-review

- **Reviewer:** Claude Code `claude-opus-5-5` (fallback: no).
- **Reviewed:** complete working-tree fixes against HEAD `126ae29a52560fb0ae2a74fe490364d3f828108b`, with prior triage supplied.
- **Findings:** `ai_tmp/review-20261024T040916Z-claude.md` · **Triage:** `ai_tmp/triage-pr4-fixes.md` (fresh separate subagent).

| # | Severity | Finding | Verdict | Action |
| --- | --- | --- | --- | --- |
| 1 | low | Direct sibling links still produce chain warning | invalid as behavior; valid hint clarity | A two-hop resource traversal remains a chain even with another direct entrypoint link. Kept warning, clarified unnecessary-cross-link hint and reference wording, added regression. |
| 2 | low | Case alias of root reported as escaping | valid diagnostic defect | Recognize alternate root spelling by filesystem identity without listing ancestors; retain rejection with reference-missing and exact-case hint. Added case-insensitive-filesystem regression (skips on case-sensitive hosts). |
| 3 | low | Reference doc retains proposal instructions | valid editorial remainder | Rewrote remaining behavior descriptions, preserving validation policy. |

**Final local verification:** `just check` passes with 168 tests on macOS, strict mypy, all lint and lock checks, both source skills with zero diagnostics and all three pinned CLI version checks. The full gate is rerun after these completion-note edits before commit; final GitHub CI status is reported on PR #4 after pushing. Linux may skip the single filesystem-specific case-alias regression; all portable path regressions run there.

### PR #4 entrypoint-case feedback

- **Implementer:** Codex (OpenAI family; runtime model ID not exposed).
- **Reviewed commit:** `7377aab64f11ee80690e32993930b6cde0ec6dc9`.
- **PR finding:** Copilot [review comment 4366078270](https://github.com/BiscuitBin/skills/pull/4#discussion_r4366078270) · **Triage:** `ai_tmp/triage-pr4-entrypoint.md` (separate subagent).

| # | Severity | Finding | Verdict | Action |
| --- | --- | --- | --- | --- |
| 1 | medium | Case-insensitive filesystems accept skill.md or Skill.md as the entrypoint | valid | Check actual entrypoint spelling with the existing exact-case helper before reading; document the requirement. API and default-discovery CLI regressions cover both variants. |

**Focused cross-model review:** Claude Code `claude-opus-5-5` (fallback: no) reviewed the working-tree fix against the commit above. Findings: `ai_tmp/review-20261024T052026Z-claude.md`; fresh separate triage: `ai_tmp/triage-pr4-entrypoint-fix.md`.

| # | Severity | Finding | Verdict | Action |
| --- | --- | --- | --- | --- |
| 1 | low | Directory-listing permission failures receive an unrelated YAML hint | valid | Handle OSError separately with an actionable read/search-permissions hint. Portable regression simulates an unreadable directory while its entrypoint remains readable. |

**Validation:** Both incorrect-case regressions failed before the fix and pass after it. The final `just check` gate, run after these notes, passes locally with 171 tests, strict mypy, lint and lock checks, two source skills with zero diagnostics and all three pinned CLI version checks. Case-insensitive-filesystem-only coverage skips on Linux; portable casing and permission regressions run there. Latest pushed-commit CI and review-thread status are checked on PR #4 before reporting completion.
