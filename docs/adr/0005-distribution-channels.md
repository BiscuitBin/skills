# Skills ship through a Claude Code plugin marketplace and `npx skills`

Shipped skills are installed in two ways: as a Claude Code plugin marketplace (`.claude-plugin/marketplace.json`) and through `npx skills` (skills.sh), which installs into the folders that Claude Code, Codex and Pi each discover. Between them, these reach all three target agents.

## Considered options

- **A custom installer.** Rejected for now: two maintained channels already reach every target agent.
- **A Codex plugin manifest.** Deferred: `npx skills` already installs into Codex's skill folder.
