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

Every tool, cache, agent home and scratch file lives inside this directory, and Git ignores all of them. The Justfile's environment is what keeps them there, so every tool runs through `just`: a recipe, or `just run <command>` for a one-off (`just run uv add --dev <package>`, `just run ./node_modules/.bin/claude …`). A bare `uv`, `npm` or agent CLI call misses that environment and writes into the user's home. When a task needs a new tool, add it as a pinned dev dependency.

- `.tools/`: the pinned Python, the uv, npm and prek caches, temporary files (`.tools/tmp/`, the recipes' `TMPDIR`), and the agent CLIs' homes (`.tools/agent-homes/`).
- `ai_tmp/`: agent scratch output, such as review findings, triage notes and logs.
- `.eval-workspaces/` and `eval-results/`: eval trial workspaces and their results.

Global installs (`npm install -g`, `uv tool install`, `pip install --user`) and writes to the user's agent homes (`~/.claude`, `~/.codex`, `~/.pi`, `~/.agents`) are outside the project, so do neither. When a tool insists on writing outside the project, stop and record it in the ticket's completion notes.

## Cross-model review

Every ticket's review checkpoint uses the `cross-model-review` dev skill (`dev-skills/cross-model-review/SKILL.md`):

- A reviewer from a **different model family** reviews the work: Codex (`gpt-6-astra`) for Claude models, Claude Code (`claude-opus-5-5`) for OpenAI models. If none is available, stop and report it; do not review your own work instead.
- A reviewer subagent runs the read-only external review and saves the findings to `ai_tmp/`. A separate triage subagent marks each finding valid, invalid or out of scope, with evidence.
- Apply the valid fixes, rerun the checks, and record the reviewer, model, reviewed commit and every finding's verdict and action under **Completion notes** in the ticket.

## Dev skills

Dev skills are repo-internal skills for working on this repo. They live in `dev-skills/<name>/`, and relative symlinks in `.claude/skills/` and `.agents/skills/` make them discoverable. Every dev skill is marked `metadata.scope: repo-internal` and must be excluded from distribution (marketplace, plugin and `npx skills`; ticket 04) and from eval workspaces (ticket 05).
