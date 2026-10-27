# Eval isolation

An eval trial should show what a skill does for a user who has installed only that skill. The agent CLIs make that hard: they read skills and instructions from the user's home, from parent directories and from system locations. A trial started inside this repository with the real home could see the repo's dev skills, the other shipped skills, the user's own skills, and the instruction files of every ancestor directory. This page explains how the harness keeps those out, how it proves it, and where the proof stops. The mechanics are in the [evals reference](../reference/evals.md).

## Three layers

**Redirect.** Each trial gets its own home, agent home, temporary directory and `PATH`, all inside `.eval-workspaces/<run-id>/<case-id>/`. The child's environment is built from scratch, so nothing in the caller's environment comes with it, including the Justfile's shared `CLAUDE_CONFIG_DIR`. The workspace is a fresh git repository and its own git root, so a walk up the tree for skills stops there.

**Suppress.** What cannot be redirected is switched off. For Claude Code that means instruction files: `CLAUDE_CODE_DISABLE_CLAUDE_MDS=1` blocks every `CLAUDE.md`, `CLAUDE.local.md`, `.claude/rules` file and `AGENTS.md`, wherever it sits. The preflight refuses to start a trial without it.

**Observe.** Claude Code reports what it loaded: the init event lists its skills and plugins, a `system/commands_changed` event lists skills discovered mid-run, and the debug log names every skill location and how many skills came from each. Every trial checks those reports against the recorded built-ins. A trial with something extra fails.

## Claude Code's discovery locations

Verified against the pinned CLI, 2.1.309, by the canary sweep. The sweep plants one canary at a time and runs the real CLI against a fake API that records every request.

| Location | Under the harness | Canary |
| --- | --- | --- |
| `$CLAUDE_CONFIG_DIR/skills` | Redirected into the trial home, and reported. | Detected. |
| `~/.claude/skills`, `~/.agents/skills` | `~/.claude` is `CLAUDE_CONFIG_DIR` under the harness. `~/.agents/skills` is not a Claude location. The caller's real home is never referenced. | Isolated: canaries in the caller's home and config dir never appear. |
| `<workspace>/.claude/skills` | Controlled: the harness installs exactly one skill there. Reported. | Detected: a second skill fails the check. |
| `<workspace>/<subdir>/.claude/skills` | Discovered only mid-run, when the agent touches a file in `<subdir>`. Controlled: the workspace holds no other directories. Reported through `commands_changed`. | Detected mid-run. |
| Parent directories' `.claude/skills`, `.agents/skills` | Not read above the workspace's git root. | Isolated. |
| Managed (`/Library/Application Support/ClaudeCode`, `/etc/claude-code`) | Fixed by platform and not redirectable. Reported and checked empty on every trial. `CLAUDE_CODE_DISABLE_POLICY_SKILLS=1` is set as well. | Detected, in CI only: planting it needs root outside the project. |
| Plugins' `skills/` | No plugins are installed in the trial home. Reported through the init event's plugin list. | Covered by the plugin allowlist. |
| Instruction files, here and in every ancestor | Suppressed. | Each loads with suppression off, and none loads with it on. |

The sweep also found three things about instruction files that make suppression essential:

- A parent directory's `CLAUDE.md` loads across the workspace's git root.
- With loading on, the CLI walks every ancestor directory and reads `<dir>/.claude/CLAUDE.md`. The user's home is an ancestor of this repository, so the user's `~/.claude/CLAUDE.md` would reach every trial as "project instructions".
- The built-in `cc-plugin-agents-md` loads `AGENTS.md` only when it finds no `CLAUDE.md` up the tree. Inside this repository the root `CLAUDE.md` always exists, so the sweep checks the parent `AGENTS.md` case through that root `CLAUDE.md`. A parent `AGENTS.md` outside any `CLAUDE.md` tree was verified by probe to load.

## What is observed and what is enforced

Skills are observed in every trial. Instruction files are not, because a live run never exposes the request the model receives: their absence is enforced by the preflight and observed only in the sweep. A new CLI version that ignored `CLAUDE_CODE_DISABLE_CLAUDE_MDS` would pass the preflight. The sweep in `just check` would catch it, which is why every pin bump must pass `just check`.

## Known limits

- **The workspace limits discovery, not file access.** An agent with `Read` or `Bash` can still read `../../../AGENTS.md` or anything else in the repository. Isolation stops the agent from being *given* other skills and instructions, not from *going looking* for them. A trial in which the agent browses outside its workspace is a finding about the agent, and the transcript shows it.
- **Teardown covers the process group.** The harness kills the CLI's process group on every exit and checks it is empty. A descendant that calls `setsid` leaves the group and is not caught. The credential does not reach the CLI's Bash tool processes anyway.
- **Built-ins are recorded, not derived.** The allowlist is what the pinned CLI reported when it was recorded. A CLI update fails every trial until it is re-recorded, which is deliberate.
- **The managed canary needs CI.** Locally the managed location is checked from the CLI's own report on every trial, but no canary is planted there.
