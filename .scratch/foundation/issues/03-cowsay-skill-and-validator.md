# 03: Cowsay skill passes a spec validator

**What to build:** The repo ships its first skill, `cowsay`. When a user asks an agent to have a cow say something, the agent runs the skill's bundled script and shows the ASCII cow with the text in a speech bubble, exactly as the script printed it.

The repo also gets its own skill validator. `just check` and CI run it over every skill in the repo, shipped skills and dev skills alike. Broken skills fail with clear, specific errors. Spec rules and agent-specific facts are in the research notes (`.scratch/foundation/research.md`).

**Blocked by:** 01 (Cross-model adversarial review as a repo dev skill), 02 (Project-local toolchain and green `just check`).

**Status:** ready-for-agent

## Acceptance criteria

**Cowsay skill:**

- [ ] The skill sits in the repo's shipped-skills area. An ADR records the layout chosen (flat or bucketed).
- [ ] Its description makes it trigger on requests for a talking or ASCII cow, and not on unrelated requests that merely mention cows or ASCII art.
- [ ] The bundled script has no third-party dependencies and runs unchanged on macOS and Linux. Its output depends only on its input.
- [ ] The script handles a single word, long text (word-wrapped at a fixed width), multi-line input, empty input, and non-ASCII text. Unit tests cover each of these and run in `just check`.
- [ ] The skill body tells the agent to run the script and show its output verbatim, not to draw the cow freehand.
- [ ] The skill has Codex UI metadata (an `openai.yaml`) with a display name and a short description.

**Validator:**

- [ ] It enforces the spec rules:
  - the name format and length
  - that the name matches its directory
  - description and compatibility lengths
  - that metadata is a map of strings to strings
  - the allowed top-level fields
- [ ] Frontmatter fields outside the spec are accepted only if they are on a per-agent extension allowlist, for example Claude Code's documented extras. Anything else is an error. The allowlist records which agents accept each field. Shipped skills go to every agent, so a field that any target agent is known to reject is an error in a shipped skill.
- [ ] It enforces size limits (body lines and an approximate token budget). An ADR or the validator's reference doc says which limits are errors and which are warnings.
- [ ] Every relative reference in `SKILL.md` resolves to a file inside that skill. A missing file or a path that escapes the skill is an error. Referenced files that reference further files (a chain more than one level deep) are a warning. Directory depth is not limited.
- [ ] It checks the `openai.yaml` shape when the file is present.
- [ ] Each error names the file, the rule and a fix hint, and any error gives a nonzero exit.
  - A set of broken-skill fixtures covers every rule, one fixture per rule, each with a test asserting its specific error.
- [ ] For the shared spec rules, a test compares the validator's verdicts with the `skills-ref` reference validator on the fixtures. Any intentional difference is documented.
- [ ] `just check` runs the validator over every skill in the repo, including the dev skill from ticket 01, and it passes.

## Review checkpoints

Use the repo's cross-model adversarial review skill from ticket 01, or the protocol written out there:

- Pick the reviewer by the cross-model rule.
- A reviewer subagent saves its findings to the scratch folder.
- A separate triage subagent checks each finding against the code.
- Apply the valid fixes, rerun `just check`, and record every finding and how it was handled under **Completion notes**.

- **Design checkpoint:** before building the validator, write the proposed rule list (each rule with its severity and rationale) and the per-agent extension allowlist, and get them reviewed. Is anything too strict for real Claude Code, Codex or Pi skills? Too loose to catch real breakage? Wrong about the spec?
- **Implementation checkpoint:** before marking done, review the full diff against these acceptance criteria.
