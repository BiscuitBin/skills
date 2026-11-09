# The MVP evaluates Claude Code and Codex; Pi is installable but deferred

The MVP supports and evaluates Claude Code and Codex. Pi stays installable: `npx skills` puts shipped skills in the folder Pi discovers, and the offline install test covers that path. But Pi has no pinned CLI, no eval adapter and no live evals until future ticket 07 (`.scratch/future/issues/07-pi-adapter.md`) brings them back.

The defensive pieces stay, because they cost nothing and protect a user who runs Pi anyway: the eval harness's never-appear list still names `~/.pi`, the Justfile still points `PI_CODING_AGENT_DIR` into the project, and the skill validator still accepts Pi's frontmatter extensions.

This narrows [ADR 0005](0005-distribution-channels.md): the two channels still reach Pi, but Pi is no longer a target agent the repo evaluates. It supersedes the parts of [ADR 0002](0002-python-core-node-tooling-just-front-door.md) and [ADR 0003](0003-project-local-toolchain.md) that list Pi among the pinned agent CLIs. npm now carries two agent CLIs, Claude Code and Codex.

## Considered options

- **Drop Pi entirely.** Rejected: `npx skills` installs into Pi's folder at no cost, and removing the install test would let that path break unnoticed.
- **Keep the Pi pin without an adapter.** Rejected: an unused pin is weight in every install and every version bump, and nothing runs it.
