# Python is the core, Node carries the tooling, and Just is the front door

The repository's own code (the skill validator, the eval harness, graders and reports) is Python, managed by uv. Node, managed by npm, is there only for tools that ship as npm packages: the three agent CLIs (Claude Code, Codex and Pi), Prettier, markdownlint and the `npx skills` installer. Just is the one entry point over both, so a contributor runs `just <recipe>` and never needs to know which ecosystem a tool comes from.

## Considered options

- **All Node.** This would avoid a second toolchain. It was rejected because the harness is data processing and reporting, where Python is the better fit, and prek, ruff and mypy have no Node equivalents of the same quality.
- **All Python.** This was not possible, because the agent CLIs and the skill installer are published only to npm.
