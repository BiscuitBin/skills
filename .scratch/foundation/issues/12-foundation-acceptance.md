# 12: Foundation acceptance: fresh-clone walkthrough and full-repo review

**What to build:** Proof that the foundation works for someone who has only the docs. A fresh-context agent, starting from a fresh clone, follows only the README and the docs to:

- get a green `just check`
- run the cowsay eval on all three agents
- build the report
- install cowsay through each distribution channel

Then the whole repo gets a cross-model adversarial review. Valid findings are fixed, and anything left becomes a follow-up note, so the next round of skill specs starts from a known state.

**Blocked by:** 10 (Manual live-eval CI job), 11 (New-skill authoring workflow and docs).

**Status:** ready-for-agent

**Agent requirements:** Any implementing agent (Claude Code, Codex or Pi). A fresh-context subagent must perform the walkthrough with authenticated access to Claude Code, Codex and Pi, plus the configured grader when grading is enabled. Claude Code is also required for marketplace installation. The full-repo review and fix review require a reviewer from a different model family, plus separate reviewer and triage subagents.

## Acceptance criteria

**Walkthrough:**

- [ ] A fresh-context subagent, given only the repo URL or a fresh clone and the instruction to follow the docs, completes these steps:
  - `just initialize` and `just check`, both green
  - `just eval cowsay` on Claude Code, Codex and Pi, all passing
  - `just eval-report`
  - installing cowsay through the marketplace and through `npx skills` into a throwaway project
- [ ] Every point where the walkthrough agent got stuck, guessed, or had to read source code is fixed in the docs, and the walkthrough is repeated until it runs clean.
- [ ] The walkthrough leaves nothing outside the project directory and throwaway projects. Compare the user's agent homes before and after.

**Carried-over checks:**

- [ ] The ticket 01 dev skill is confirmed discoverable by Claude Code, Codex and Pi in this repo.
- [ ] Any gaps recorded by earlier tickets are closed or carried into the follow-up notes, for example the secret-present dispatch from ticket 10 or Pi discovery from ticket 01.

**Full-repo review:**

- [ ] A cross-model adversarial review covers the whole repo, not just a diff. It is checked against the foundation goals in the research notes and every earlier ticket's acceptance criteria.
- [ ] Every finding is triaged, valid fixes are applied, and `just check` is green afterwards.
- [ ] Residual gaps, deferred items and out-of-scope findings are written as follow-up notes in the foundation scratch folder. The deferred items are description-routing evals, description optimisation, a catalogue site, Codex and Pi package manifests, and a custom installer.
- [ ] Every ticket in the foundation set has its completion notes and a done status, except where a mandatory criterion is still unmet. Those criteria are listed by ticket in this ticket's completion notes as open, not as follow-ups, and the user confirms them before the foundation is called done.

## Review checkpoints

Use the repo's cross-model adversarial review skill from ticket 01:

- Pick the reviewer by the cross-model rule.
- A reviewer subagent saves its findings to the scratch folder.
- A separate triage subagent checks each finding against the code.
- Apply the valid fixes, rerun `just check`, and record every finding and how it was handled under **Completion notes**.

- **Full-repo checkpoint:** this ticket's main review, described above.
- **Implementation checkpoint:** after the fixes, run one re-review round over the fix diff.
