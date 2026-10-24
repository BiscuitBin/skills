# 04: Installable via Claude marketplace and npx skills

**What to build:** A user can install `cowsay` from this repo in two ways:

- as a Claude Code plugin from the repo's marketplace
- with `npx skills` for Claude Code, Codex or Pi

In both cases they get exactly the shipped skill and nothing internal to the repo. A round-trip test proves this. Distribution facts are in the research notes (`.scratch/foundation/research.md`).

**Blocked by:** 03 (Cowsay skill passes a spec validator).

**Status:** in-progress (implementation and checks complete; fixes re-review pending)

**Agent requirements:** Any implementing agent (Claude Code, Codex or Pi). The pinned Claude Code CLI is required for plugin validation and marketplace installation. The `npx skills` round trip targets Claude Code, Codex and Pi; this does not require those agents to implement the ticket. Record any installation credential requirement as described below. Cross-model review is also required.

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

## Completion notes

### Implementation and verification

- Marketplace: `.claude-plugin/marketplace.json`; cached plugin root: `skills/cowsay/`, containing its own `.claude-plugin/plugin.json`. Only the shipped payload is installed. ADR 0010 records the distribution boundary and the retained dev-skill discovery symlinks.
- Version source: `skills/cowsay/.claude-plugin/plugin.json`'s `version`; `just format` derives `plugins[name=cowsay].version` in the marketplace. Deliberately changing the marketplace version to `9.0.0` made `just check` fail with `marketplace version differs from plugin.json; run just format`. `just format` reverted it to `0.1.0`.
- Pinned Claude Code `2.1.309` validates the marketplace and plugin with `--strict` inside `just check`. The optional directory-listing icon advisory does not affect its successful validation verdict.
- Pinned `skills@1.7.4` lists only cowsay without a skill filter. Default install-all commands pass for Claude Code, Codex and Pi. Existing dev-skill directory symlinks are skipped by the installer, so their placement and agent discovery configuration remain intact; the placement/listing criterion is closed.
- Round trips clone committed HEAD into isolated throwaway projects, add Git sources and exercise cached plugin installation. Claude rejects `file://` marketplace sources, so its documented `BiscuitBin/skills` shorthand is redirected by process-local Git `insteadOf` configuration to the local clone, with file-only transport. No published GitHub repository or agent credentials are used.
- Every installation checks its discovery path, exact payload bytes and whole-project inventory, then removes the source and marketplace clones. The installed Python script runs with source-file reads denied by an audit hook, allowing only the installed skill and pinned Python runtime. No agent model invocation is required.
- Per-agent installs use copies. The combined Claude Code/Codex case exercises a Claude symlink and canonical shared copy, and runs the script through both discovery paths. `just test` records modes in `ai_tmp/pytest.xml` and successful-test output in the CI log.
- HOME, agent homes, XDG state, npm cache and temporary files remain inside the project-local test workspace. The test subprocess environment inherits no agent credentials or user Git helpers. The existing PR CI runs the same credential-free `just check` gate.
- Staged, unstaged and untracked changes to distribution source directories are rejected before committed-tree installs. A regression proves an untracked `skills/cowsay/evals.json` cannot evade the gate.
- Validation after fixes: `just check` passed with 178 tests, strict mypy, all lint and lock checks, both source skills with zero diagnostics, strict plugin/marketplace validation and all pinned CLI version checks.

### Cross-model review

- **Implementer:** Codex (OpenAI family; runtime model ID not exposed).
- **Reviewer:** Claude Code `claude-opus-5-5` (fallback: no).
- **Reviewed:** `4c0d744...6175ea5`.
- **Findings:** `ai_tmp/review-20261024T064248Z-claude.md` · **Triage:** `ai_tmp/triage-distribution.md` (fresh separate subagent).
- The first run was rejected after Claude initialized its isolated `.claude.json` and empty sessions directory. Rejected output was not triaged; the unchanged runner succeeded on retry after initialization, with no allowlist changes.

| # | Severity | Finding | Verdict | Action |
| --- | --- | --- | --- | --- |
| 1 | medium | Throwaway project lies inside development checkout | invalid | File-open audit hook denies reads of development source; only installed skill and pinned interpreter are available. Project-local toolchain is required by ADR 0003. |
| 2 | medium | Discovery paths are checked without starting agents | invalid | Criterion requires correct install locations, which are checked with plugin registration/configuration and pinned strict validation. Pi trust is documented; live triggering belongs to later eval tickets. |
| 3 | medium | Symlink behavior unexercised | valid | Added combined Claude Code/Codex case; verifies symlink and copy and runs installed script through both. |
| 4 | low | Installation modes absent from ordinary gate results | valid | Persist JUnit properties in `ai_tmp/pytest.xml` and show passing-test output in CI logs. |
| 5 | low | README commands differ from test | valid in part | README now presents tested shell subcommands; test uses identical GitHub shorthand with local Git redirection. Pinned CLI help confirms the previously questioned one-step option exists; omitted it to keep examples aligned. |
| 6 | low | Leak checks inspect only skill subtree | valid | Added whole-project path allowlist, excluding only its own Git metadata; retained exact payload comparison. |
| 7 | low | Claude plugin manifest also ships through npx | invalid for current payload; future coupling out of scope | Required user-facing distribution metadata is not repo tooling. ADR 0010 records the future `agents/*.md` convention consideration. |
| 8 | low | Dirty distribution sources can evade committed-tree test | valid | Added commit-first source check to validation recipe and round trips, plus untracked-eval-file regression. |
| 9 | low | Listing assertion pins today's catalogue | out of scope | Ticket explicitly requires cowsay today. Extend exact expected names and payloads when adding another shipped skill. |
| 10 | low | Bare pytest can write outside project | invalid | Supported workflow requires `just`; its TMPDIR and isolated child environment keep all test state local. |

**Follow-ups:** Future skill authoring must extend exact distribution inventories when adding shipped skills and account for Claude's `agents/*.md` convention alongside Codex YAML metadata. Neither is an open criterion for this ticket.
