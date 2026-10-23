# BiscuitBin/skills

This repo develops, evaluates and hosts agent skills in the [Agent Skills](https://agentskills.io/specification) `SKILL.md` format for Claude Code, Codex and Pi. Tickets live in `.scratch/foundation/issues/`, and background research in `.scratch/foundation/research.md`.

Put agent scratch output in `ai_tmp/`, which is gitignored.

## Cross-model review

Every ticket's review checkpoint uses the `cross-model-review` dev skill (`dev-skills/cross-model-review/SKILL.md`):

- A reviewer from a **different model family** reviews the work: Codex (`gpt-6-astra`) for Claude models, Claude Code (`claude-opus-5-5`) for OpenAI models. If none is available, stop and report it; do not review your own work instead.
- A reviewer subagent runs the read-only external review and saves the findings to `ai_tmp/`. A separate triage subagent marks each finding valid, invalid or out of scope, with evidence.
- Apply the valid fixes, rerun the checks, and record the reviewer, model, reviewed commit and every finding's verdict and action under **Completion notes** in the ticket.

## Dev skills

Dev skills are repo-internal skills for working on this repo. They live in `dev-skills/<name>/`, and relative symlinks in `.claude/skills/` and `.agents/skills/` make them discoverable. Every dev skill is marked `metadata.scope: repo-internal` and must be excluded from distribution (marketplace, plugin and `npx skills`; ticket 04) and from eval workspaces (ticket 05).
