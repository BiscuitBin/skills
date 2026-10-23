# 11: New-skill authoring workflow and docs

**What to build:** A contributor can start a new skill with `just new-skill <name>` and follow written guidance to take it from scaffold to validated, evaluated, reviewed and installable. The guidance covers eval-driven RED/GREEN development, the cross-model review protocol, and how versions and releases work.

**Blocked by:** 04 (Installable via Claude marketplace and npx skills), 09 (Cross-agent benchmark report and history).

**Status:** ready-for-agent

## Acceptance criteria

- [ ] `just new-skill <name>` creates a skill with spec-valid frontmatter, a stub body, Codex UI metadata and an eval directory with starter trigger and behaviour cases.
  - The result passes the validator straight away.
  - The command rejects invalid names and names that already exist, with a clear message.
- [ ] A new skill is either added to the distribution manifests automatically, or `just check` fails with a message that says exactly what to add.
- [ ] Starter eval cases are marked as placeholders, so `just eval` reports them as unwritten rather than passing. `just check` warns, naming the skill, when a skill in the distribution manifests still has only placeholder cases.
- [ ] Scaffolding is tested in `just check`: a valid name, an invalid name, a duplicate name, and cleanup.
- [ ] A contributing guide covers:
  - RED/GREEN skill development: write the eval cases and run a baseline first, then write the skill, then close the gaps the evals find.
  - When and how to run the cross-model review (pointing to the ticket 01 skill).
  - How versions are bumped and kept in sync.
  - How a release is cut, matching an actual `just` recipe or stating plainly that it is a manual version bump and merge.
- [ ] A tutorial takes a scratch skill from scaffold to validated, evaluated on at least one agent, and installed into a throwaway project. Every command in it is copy-pasteable.
- [ ] The tutorial is shown working: a fresh-context subagent follows it exactly in a scratch clone and succeeds. Every place it got stuck is fixed in the docs, and the scratch skill is not committed.
- [ ] The docs index and README link to the guide and the tutorial.

## Review checkpoints

Use the repo's cross-model adversarial review skill from ticket 01, or the protocol written out there:

- Pick the reviewer by the cross-model rule.
- A reviewer subagent saves its findings to the scratch folder.
- A separate triage subagent checks each finding against the code.
- Apply the valid fixes, rerun `just check`, and record every finding and how it was handled under **Completion notes**.

- **Implementation checkpoint:** before marking done, review the full diff against these acceptance criteria. Pay particular attention to docs that disagree with the actual commands, and to scaffolds that pass checks while being useless.
