# Agent instructions

This repository develops, evaluates and distributes agent skills in the Agent Skills `SKILL.md` format, for Claude Code, Codex and Pi. Tickets are in `.scratch/<effort>/issues/`. Use the terms in `GLOSSARY.md`, and read the relevant record in `docs/adr/` before changing a decision it covers.

## Commands

`just` is the front door. Run `just` to list the recipes.

- `just initialize`: first-run setup, safe to rerun.
- `just check`: the full gate. CI runs the same gate, so run it before calling any work done.
- `just format`: the only recipe that rewrites source files.
- `just lock`: run it after changing a pin in `pyproject.toml` or `package.json`, then commit the manifest and its lockfile together.

Pins are exact, in both manifests. `just sync` and `just initialize` install only what the lockfiles say.

## Everything stays in the project directory

Every tool, cache, agent home and scratch file lives inside this directory, and Git ignores all of them. When a task needs a tool, add it as a pinned dev dependency and run it through `just`, `uv run --frozen` or `./node_modules/.bin/`.

- `.tools/`: the pinned Python, the uv, npm and prek caches, and the agent CLIs' homes (`.tools/agent-homes/`).
- `ai_tmp/`: agent scratch output, such as review findings, triage notes and logs.
- `.eval-workspaces/` and `eval-results/`: eval trial workspaces and their results.

Global installs (`npm install -g`, `uv tool install`, `pip install --user`) and writes to the user's agent homes (`~/.claude`, `~/.codex`, `~/.pi`, `~/.agents`) are outside the project, so do neither. When a tool insists on writing outside the project, stop and record it in the ticket's completion notes.

## Cross-model review (ticket 01)

> **Placeholder.** Ticket 01 replaces this section with a summary of the cross-model review protocol and a pointer to the repo's review dev skill. Until it lands, follow the protocol written out in `.scratch/foundation/issues/01-cross-model-review-dev-skill.md`.
