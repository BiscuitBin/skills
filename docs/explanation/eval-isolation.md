# Eval isolation

An eval trial should show what a skill does for a user who has installed only that skill. The agent CLIs make that hard: they read skills and instructions from the user's home, from parent directories and from system locations. A trial started inside this repository with the real home could see the repo's dev skills, the other shipped skills, the user's own skills, and the instruction files of every ancestor directory. This page explains how the harness keeps those out, how it proves it, and where the proof stops. The mechanics are in the [evals reference](../reference/evals.md).

## Three layers

**Redirect.** Each trial gets its own home, agent home, temporary directory and `PATH`, all inside `.eval-workspaces/<run-id>/<case-id>/`. The child's environment is built from scratch, so nothing in the caller's environment comes with it, including the Justfile's shared `CLAUDE_CONFIG_DIR`. The workspace is a fresh git repository and its own git root, so a walk up the tree for skills stops there.

**Suppress.** What cannot be redirected is switched off. For Claude Code that means instruction files: `CLAUDE_CODE_DISABLE_CLAUDE_MDS=1` blocks every `CLAUDE.md`, `CLAUDE.local.md`, `.claude/rules` file and `AGENTS.md`, wherever it sits. For Codex, `project_doc_max_bytes=0` blocks `AGENTS.md` in the workspace and above it, and plugins and apps are disabled. The preflight refuses to start a trial without instruction suppression.

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

## Codex's discovery locations

Verified against the pinned CLI, 0.163.0. Rows marked "real CLI" ran it against a fake Responses API that records every request; the location-check rows plant a canary and run the check over a recorded trace. Codex does not report the skills it loaded: they appear only in the request, which a live run cannot see. So the check reads the locations themselves after each trial, and Codex's own telemetry events report each skill it saw read or explicitly invoked.

| Location | Under the harness | Canary |
| --- | --- | --- |
| `<workspace>/.agents/skills` | Controlled: the harness installs exactly one skill. Read after the run. | Detected by the location check: a second skill fails it. Not run through the real CLI. |
| Parent directories' `.agents/skills`, up to the repository root | The workspace is its own git root, so there are none. | Isolated: a parent repository's canary never reaches the model. |
| `$HOME/.agents/skills`, the user-level shared folder in the OS home | `HOME` is the trial home. The caller's real home is never referenced. Read after the run. | Detected in the trial home, where the real CLI shows it reaches the model. Isolated in the caller's home. |
| `$CODEX_HOME/skills`, including the deprecated `~/.codex/skills` | Redirected into the trial. Holds only the bundled `.system` skills, which are allowlisted by CLI version. | Detected by the location check, which is not shown to reach the model. The caller's `CODEX_HOME` canary is isolated (real CLI). |
| `/etc/codex` (system skills and config) | Fixed by platform and not redirectable. Checked missing or empty on every trial. | Detected by the location check, which is not shown to reach the model. No real canary: planting it needs root outside the project. |
| Plugin skills | Plugins, remote plugins and apps are disabled, so nothing is synced into `$CODEX_HOME`. The plugin directories must not exist. | Detected by the location check, which is not shown to reach the model. |
| `$CODEX_HOME/AGENTS.md`, `AGENTS.override.md` | Redirected into the trial and checked absent. `project_doc_max_bytes=0` does not cover these global instructions. | Detected: one reaches the model even with suppression on, and fails the check. |
| `AGENTS.md` in the workspace and every ancestor | Suppressed. | Loads with suppression off. None loads with it on. |
| `config.toml` in `CODEX_HOME` | `--ignore-user-config`, and `CODEX_HOME` is the trial's. | Isolated: a `developer_instructions` canary in the caller's config never reaches the model. |

Only `auth.json` is copied into the trial's `CODEX_HOME`, from the project's own Codex home, so a login brings no skills or config with it.

## What is observed and what is enforced

Skills are observed in every trial. Instruction files are not, because a live run never exposes the request the model receives: their absence is enforced by the preflight and observed only in the sweep. A new CLI version that ignored `CLAUDE_CODE_DISABLE_CLAUDE_MDS` would pass the preflight. The sweep in `just check` would catch it, which is why every pin bump must pass `just check`.

## Known limits

- **The workspace limits discovery, not file access.** An agent with `Read` or `Bash` can still read `../../../AGENTS.md` or anything else in the repository. Isolation stops the agent from being *given* other skills and instructions, not from *going looking* for them. A trial in which the agent browses outside its workspace is a finding about the agent, and the transcript shows it.
- **Teardown covers the process group.** The harness kills the CLI's process group on every exit and checks it is empty. A descendant that calls `setsid` leaves the group and is not caught. The credential does not reach the CLI's Bash tool processes anyway.
- **Codex's skill list is not observed.** For Codex the proof is the location check and the telemetry events, not a report of what the model was shown. A Codex version that read skills from a new location would pass until the location is added. Pin bumps must re-check the locations against the release notes and the fake-API tests.
- **Built-ins are recorded, not derived.** The allowlist is what the pinned CLI reported when it was recorded. A CLI update fails every trial until it is re-recorded, which is deliberate.
- **The managed canary needs CI.** Locally the managed location is checked from the CLI's own report on every trial, but no canary is planted there.
