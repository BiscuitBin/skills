# 02: Project-local toolchain and green `just check`

**What to build:** A contributor clones the repo, runs `just initialize` and then `just check`, and gets a green result. Every tool, including the three agent CLIs, is pinned and installed inside the project directory, and the same gate runs on every PR in CI.

The repo also gets its agent instructions, a documentation skeleton, the first ADRs and a glossary, so later tickets have a shared vocabulary and a written record of decisions. Follow the toolchain style of `/Users/scutting/projects/pawdoku`. The research notes (`.scratch/foundation/research.md`) list the decisions to record.

**Blocked by:** None (can start immediately). Ticket 01 runs in parallel and also writes the agent instructions file. Whichever ticket lands second merges the other's section, and neither overwrites the other.

**Status:** ready-for-agent

## Acceptance criteria

- [ ] In a fresh clone in a temporary directory, `just initialize` and then `just check` both pass. `just initialize` never stages, commits, tags or pushes. The README states the few host prerequisites `just initialize` relies on (such as just, uv and a Node install), and how the pinned Python and Node versions are obtained.
- [ ] Python is managed by uv and Node by npm. Both use exact version pins and committed lockfiles. A lockfile drift check is part of `just check`.
- [ ] `just` is the front door. At minimum it has `initialize`, `sync`, `lock`, `lock-check`, `install-hooks`, `format`, `lint`, `typecheck`, `test` and `check`. `just` with no arguments lists the recipes.
- [ ] Claude Code, Codex and Pi are pinned to exact versions and installed project-locally.
  - A recipe prints each version without using any global install.
  - Any pinned binaries live in a gitignored tools folder inside the project.
- [ ] `just check` covers ruff (lint and format check), mypy, pytest, markdownlint and prettier.
  - A deliberately broken input in each category makes it fail. Show this, then revert.
  - One trivial test proves the pytest wiring.
- [ ] `just initialize` installs prek pre-commit hooks, which run the fast subset of the gate.
- [ ] The agent instructions file is the single source, and the Claude instructions file only imports it.
  - It covers the front-door commands, the "everything stays in the project directory" rule, and the review protocol from ticket 01 (integrate that section if ticket 01 has landed, or leave a clearly marked placeholder for it).
- [ ] The docs skeleton follows Diátaxis: tutorials, how-to guides, reference and explanation. It has an index that later tickets fill in.
- [ ] ADRs record each decision in the research notes:
  - the local tracker
  - the Python-core / Node-tooling split, with Just as the front door
  - the project-local toolchain
  - the eval tiers and which ones run in CI
  - distribution channels
  - the cowsay example skill
  - cross-model review routing
  - the MIT licence
- [ ] The glossary defines skill, dev skill, eval case, trial, run, adapter, grader, baseline, benchmark, trigger and contamination, each in a sentence or two.
- [ ] A LICENSE file (MIT) is present, and the README describes the repo's purpose and how to start.
- [ ] A PR CI workflow runs `just check` on Linux. It uses pinned action versions and needs no secrets.
- [ ] Agent scratch output, the tools folder, eval workspaces and eval results are gitignored.

## Review checkpoints

Use the repo's cross-model adversarial review skill from ticket 01. If it isn't available yet, follow the protocol written out in ticket 01:

- Pick the reviewer by the cross-model rule.
- A reviewer subagent saves its findings to the scratch folder.
- A separate triage subagent checks each finding against the code.
- Apply the valid fixes, rerun `just check`, and record every finding and how it was handled under **Completion notes**.

- **Implementation checkpoint:** before marking done, review the full diff against these acceptance criteria. Pay particular attention to anything that escapes the project directory, unpinned versions, and a gate that can pass while something is broken.
