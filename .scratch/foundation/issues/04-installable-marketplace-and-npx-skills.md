# 04: Installable via Claude marketplace and npx skills

**What to build:** A user can install `cowsay` from this repo in two ways:

- as a Claude Code plugin from the repo's marketplace
- with `npx skills` for Claude Code, Codex or Pi

In both cases they get exactly the shipped skill and nothing internal to the repo. A round-trip test proves this. Distribution facts are in the research notes (`.scratch/foundation/research.md`).

**Blocked by:** 03 (Cowsay skill passes a spec validator).

**Status:** ready-for-agent

## Acceptance criteria

- [ ] The repo has a Claude Code marketplace and a plugin manifest. They list shipped skills only, which today means cowsay. Dev skills and eval material are excluded.
- [ ] The plugin version and the version recorded for the plugin in the marketplace stay in sync from a single source. The reference docs name the exact fields. `just check` fails when they drift. Show this with a deliberate drift, then revert.
- [ ] `just check` runs `claude plugin validate --strict`, using the pinned Claude Code, and it passes.
- [ ] A round-trip test installs into a throwaway project without needing the published GitHub repo.
  - The source is a clean copy of the committed tree, such as a local clone, added as a git source where the channel allows. The plugin is then installed as a cached copy, the way hosted users get it.
  - The installed skill must work with the development checkout out of reach.
  - It covers each of these:
    - the Claude Code marketplace and plugin
    - `npx skills` for claude-code
    - `npx skills` for codex
    - `npx skills` for pi
- [ ] For each install, the test asserts:
  - the cowsay skill landed where that agent discovers it
  - the bundled script is present and runs
  - no repo-internal files came along: no evals, no dev skills, no tests, no tooling config
- [ ] The round-trip test records whether `npx skills` copies or symlinks, and passes either way.
- [ ] Listing this repo's skills with the pinned `npx skills`, without naming a skill, shows only shipped skills. Installing all of them installs only shipped skills.
  - If the dev skill's placement from ticket 01 makes this fail, change the placement here, keep ticket 01's discovery working, and record why in an ADR.
  - Don't rely on the installer's internal-skill flag. It needs a non-string metadata value, which the validator rejects.
  - Codex and Pi find project skills only in the shared folder the installer also scans, so there may be no placement that satisfies both. The only candidate way out is linked skill folders that the installer turns out to skip (not yet tested), or any other placement that passes both the listing and the install assertions.
  - If no placement satisfies both ticket 01's discovery and the listing assertion, this criterion stays **open**. Stop and ask the user; do not weaken the assertion. The ADR records what was tried, and ticket 12 lists the criterion as open.
- [ ] Credentials:
  - If the round trip needs no agent credentials, it runs in `just check` and in PR CI.
  - If any part needs credentials, that part has its own recipe and the reason is documented.
- [ ] The install round trip leaves no files outside the project directory or the throwaway project. In particular, it never writes to the user's real agent homes.
- [ ] The README has install instructions for each channel and agent, matching what the round-trip test exercises.

## Review checkpoints

Use the repo's cross-model adversarial review skill from ticket 01, or the protocol written out there:

- Pick the reviewer by the cross-model rule.
- A reviewer subagent saves its findings to the scratch folder.
- A separate triage subagent checks each finding against the code.
- Apply the valid fixes, rerun `just check`, and record every finding and how it was handled under **Completion notes**.

- **Implementation checkpoint:** before marking done, review the full diff against these acceptance criteria. Pay particular attention to leaks of internal files, version drift paths, and writes outside the project.
