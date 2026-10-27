# Foundation research

Background for whoever implements the tickets in `issues/`. Gathered on 2026-10-22 from the sources linked below. Agent CLIs change fast. If a fact here matters to your ticket, check it against the pinned CLI version before you build on it.

## Goal

`BiscuitBin/skills` develops, evaluates and hosts agent skills in the [Agent Skills](https://agentskills.io/specification) `SKILL.md` format. The target agents are Claude Code, Codex and Pi.

## Decisions already made

- **Tracker:** local markdown, one ticket per file in `.scratch/foundation/issues/`.
- **Languages:**
  - Python with uv is the core: validator, eval harness, graders, reports.
  - Node with npm covers dev tools and the project-local, pinned agent CLIs (claude-code, codex, pi), plus npx-skills, prettier and markdownlint.
  - Just is the front door.
- **Toolchain style:** copy `/Users/scutting/projects/pawdoku`.
  - Exact pins and committed lockfiles.
  - `just initialize` is the one first-run command. It never stages, commits, tags or pushes.
  - `just sync` installs exactly what the lockfiles say.
  - `just check` is the full gate.
  - Pinned binaries go in a gitignored `.tools/`.
  - prek runs the pre-commit hooks under uv.
  - `AGENTS.md` is the single source, and `CLAUDE.md` contains only `@AGENTS.md`.
  - Docs follow Diátaxis, and there are ADRs.
  - Dev state stays inside the project directory.
- **Evals:** the full harness.
  - It has deterministic assertions, LLM-graded rubrics, several trials per case, with-skill vs. without-skill baselines, and benchmark reports.
  - PR CI runs only the static and deterministic tiers.
  - Live evals run locally through `just eval`, or from a manual `workflow_dispatch` job that needs secrets.
- **Distribution:** a Claude Code plugin marketplace and `npx skills` (skills.sh). There is no custom installer and no Codex plugin manifest yet.
- **Example skill:** `cowsay`, which uses a bundled zero-dependency script so its output is deterministic.
- **Licence:** MIT.
- **Review routing:** cross-model, as set out in ticket 01.

## Agent Skills spec

Source: <https://agentskills.io/specification>

**Required fields:**

- **`name`:**
  - 1–64 characters of `[a-z0-9-]`.
  - No leading or trailing hyphen, and no `--`.
  - It must match the parent directory name.
  - The spec text says "unicode lowercase alphanumeric" but lists only `a-z0-9`, and skills-ref accepts Unicode letters. Treat ASCII-only as repo policy.
- **`description`:** 1–1024 characters. It should say what the skill does and when to use it.

**Optional fields:** these are the only other spec fields.

- `license`.
- `compatibility`: 1–500 characters.
- `metadata`: a map of strings to strings.
- `allowed-tools`: a space-separated list. It is experimental and support varies by agent.

**Layout and size:**

- `SKILL.md` is required. `scripts/`, `references/` and `assets/` are conventions.
- Use relative references, and keep them one level deep from `SKILL.md`.
- Keep the body under 500 lines and about 5,000 tokens.
- Name and description load for every skill at startup. The body loads when the skill activates, and other files load only when needed.

**Validators:**

- **`skills-ref`** (<https://github.com/agentskills/agentskills/tree/main/skills-ref>):
  - Python 3.11+, using click and strictyaml. Apache-2.0.
  - Its README says it is for demonstration only and not for production.
  - It checks the field allowlist, the name rules (NFKC, allowing Unicode letters), that the name matches the directory, and the length limits.
  - It does not check the body, line counts or file references.
- **skill-creator's `quick_validate.py`** (<https://github.com/anthropics/skills/tree/main/skills/skill-creator/scripts>): the same allowlist with ASCII-only names. It also rejects `<` and `>` in descriptions, but does not check that the name matches the directory.

**Client discovery guidance** (<https://github.com/agentskills/agentskills/blob/main/docs/client-implementation/adding-skills-support.mdx>): clients scan `<project>/.<client>/skills/`, `<project>/.agents/skills/`, `~/.<client>/skills/` and `~/.agents/skills/`, and project skills beat user skills.

**Eval guidance:** <https://github.com/agentskills/agentskills/blob/main/docs/skill-creation/evaluating-skills.mdx>

## Claude Code

Sources: <https://code.claude.com/docs/en/skills>, <https://code.claude.com/docs/en/headless>, <https://code.claude.com/docs/en/plugin-evals>

- **Skill paths:**
  - `~/.claude/skills/<name>/` (user), `.claude/skills/` (project), and nested `<subdir>/.claude/skills/`.
  - A plugin's `skills/`, and enterprise locations.
  - On a name clash, enterprise beats personal and personal beats project.
- **Verified against the pinned 2.1.309 (ticket 05, 2026-10-26).** These correct or extend the notes above. The canary sweep in `tests/evals/test_contamination_canaries.py` checks each one.
  - The user skill location is `$CLAUDE_CONFIG_DIR/skills`, not `~/.claude/skills`, whenever `CLAUDE_CONFIG_DIR` is set. `~/.agents/skills`, and `.claude/skills` or `.agents/skills` above the workspace's git root, are not read.
  - Nested `<subdir>/.claude/skills` is discovered only mid-session, after the agent touches a file in `<subdir>`. The debug log then shows `[skills] Dynamically discovered N skills`, and the stream gets a `system/commands_changed` event listing every slash command.
  - `--debug-file` logs `Loading skills from: managed=…, user=…, project=[…]` and `Loaded N unique skills (… managed: M, user: U, project: P, additional: A …)`. The managed root is fixed by platform: `/Library/Application Support/ClaudeCode` on macOS, `/etc/claude-code` on Linux.
  - Instruction files load across the workspace's git root: a parent `CLAUDE.md`, and `<ancestor>/.claude/CLAUDE.md` for every ancestor, which includes the user's `~/.claude/CLAUDE.md`. The built-in `cc-plugin-agents-md` loads `AGENTS.md` only when no `CLAUDE.md` is found up the tree. An ancestor `CLAUDE.md`'s `@AGENTS.md` import is not expanded. `CLAUDE_CODE_DISABLE_CLAUDE_MDS=1` blocks all of them and leaves skills loading. The init event does not report which instruction files loaded.
  - `CLAUDE_CODE_OAUTH_TOKEN` honours `ANTHROPIC_BASE_URL`, so a local fake API can stand in for the real one. `apiKeySource` reads `none` under OAuth. With no credential the result is `"Not logged in"`, with `is_error: true` and `subtype: "success"` (exit 1). The CLI strips the token from its Bash tool's environment.
  - With an OAuth token set, the init event lists one more built-in skill, `schedule`.
- **Headless:** `claude -p "…" --output-format stream-json --verbose`, with `--allowedTools` or `--permission-mode`.
  - `--bare` skips CLAUDE.md auto-discovery, plugin sync and keychain reads, and accepts only an API key (or `apiKeyHelper`) for Anthropic auth. Its help text (2.1.309) does not say it skips skill discovery: "Skills still resolve via /skill-name". Check against the pinned version before relying on it for isolation.
  - `--safe-mode` disables CLAUDE.md, skills, installed plugins and hooks.
  - `--plugin-dir` loads a local plugin.
  - The `system/init` event lists `plugins` and `plugin_errors`.
- **Trigger signal:** an assistant `tool_use` with `name: "Skill"` and input `{"skill": "<name>"}`. The name may carry a `plugin:` prefix.
- **Frontmatter:** Claude Code accepts extra keys such as `when_to_use`, `disable-model-invocation`, `user-invocable`, `context`, `model`, `hooks` and `paths`. The docs warn these cause errors in other products. `description` plus `when_to_use` is cut off at 1,536 characters.
- **Plugins:** `claude plugin validate . --strict` checks manifests. Marketplace shape, from anthropics/skills: `.claude-plugin/marketplace.json` with `name`, `owner`, `metadata` and `plugins[]`. Each plugin entry has `name`, `description`, `source` and `skills[]`.
- **`claude plugin eval`** exists (v2.1.269+). It is an alternative signal, not the harness we are building.

## Codex

Sources: <https://learn.chatgpt.com/docs/build-skills>, <https://learn.chatgpt.com/docs/non-interactive-mode>

- **Skill paths:**
  - `$CWD/.agents/skills`, then each parent folder up to `$REPO_ROOT/.agents/skills`.
  - `$HOME/.agents/skills`, `/etc/codex/skills`, and skills bundled with Codex.
  - Symlinked skill folders work.
  - `~/.codex/skills` is said to be deprecated, according to a secondary source only.
- **Config:** `[[skills.config]] path=… enabled=false` disables a skill. The skill list has a context budget (`skills.max_context_tokens`), and Codex shortens or drops skills when the list is over it.
- **Headless:** `codex exec --json` writes JSONL events (`thread.started`, `turn.*`, `item.started`/`item.completed`, with items `command_execution` and `agent_message`).
  - Useful flags: `--ignore-user-config`, `--ephemeral`, `--skip-git-repo-check`, `--sandbox`, `-o`, `--output-schema` and `-C`.
  - `CODEX_HOME` moves the config and auth home.
- **Trigger signal:** none is documented. The workaround is a `command_execution` whose command reads the skill's `SKILL.md` path. Also watch stderr for `failed to load skill`. Explicit invocation is `$name`.
- **Codex metadata:** `agents/openai.yaml` with `interface` (`display_name`, `short_description`), `policy.allow_implicit_invocation`, and `dependencies.tools`.
- **Verified locally on 2026-10-22:** codex-cli 0.163.0 is installed, and `~/.codex/config.toml` sets `model = "gpt-6-astra"`.

## Pi

Source: <https://github.com/earendil-works/pi> (badlogic/pi-mono redirects here). See `packages/coding-agent/docs/skills.md`, `cli.md`, `json.md` and `security.md`.

- **Skill paths:**
  - `~/.pi/agent/skills`. `PI_CODING_AGENT_DIR` moves the base folder.
  - `.pi/skills` in the project.
  - `~/.agents/skills` and `.agents/skills`, searched upward to the repo root.
  - Folders are scanned recursively.
  - The `--skill <path>` flag can be repeated. `--no-skills` turns discovery off.
- **Headless:** `pi --mode json "…"` writes JSONL: a `session` header, then `agent_start`, `message_*`, `tool_execution_start|end` and `agent_settled`.
  - Project skills need project trust. JSON and print modes skip them unless you pass `--approve`.
- **Trigger signal:** `tool_execution_start` with `toolName: "read"` and a path ending in `SKILL.md`. `/skill:name` forces a load, but Pi expands it itself: it reads the file and inlines the body into the prompt, so it produces no read-tool event (from the source, `_expandSkillCommand`).
- **Security:** project trust gates `.agents/skills` in the current directory or an ancestor. Context files (AGENTS.md, CLAUDE.md) load regardless of trust unless context loading is turned off. The working folder limits discovery, not file access.
- **Frontmatter:** follows the spec, plus `disable-model-invocation`.
  - A skill with no description is not loaded.
  - A name that differs from its folder gets no warning.
  - On a name clash the first skill found wins, with a warning.
- **Verified locally on 2026-10-22:** `pi` is not installed globally. The foundation pins it project-locally.

## Cross-agent installers

- **vercel-labs/skills** (<https://github.com/vercel-labs/skills>): `npx skills add <src> [--skill X] [-a <agent>]`.
  - `claude-code` installs to `.claude/skills/`.
  - `codex` and `pi` install to `.agents/skills/`.
  - Whether it copies or symlinks has not been confirmed. Check this in ticket 04.
  - It also scans the source repo's own agent skill folders (`.agents/skills`, `.claude/skills` and others) and any plugin-manifest skill paths. Its internal-skill filter needs a boolean `metadata.internal`, which the spec's string-only metadata forbids, and is bypassed when a skill is named explicitly (from `src/skills.ts`).
- **openskills** (<https://github.com/numman-ali/openskills>): an alternative, not adopted.

## Prior art and what we borrow

- **anthropics/skills** (<https://github.com/anthropics/skills>):
  - From the marketplace: grouping happens in `marketplace.json`, not in folders.
  - From skill-creator:
    - Cases in `evals.json`, shaped `{skill_name, evals:[{id, prompt, expected_output, files[], expectations[]}]}`.
    - Runs with the skill and without it.
    - `grading.json` with `expectations[{text, passed, evidence}]`.
    - `aggregate_benchmark`, which reports mean ± stddev and the delta.
    - `history.json` across iterations.
    - Trigger sets of `{query, should_trigger}`.
- **addyosmani/agent-skills** (<https://github.com/addyosmani/agent-skills>):
  - Three eval tiers: structural lint, TF-IDF routing (deferred here), and behavioural runs through `claude -p` in a throwaway git repo built from fixtures.
  - A second `claude -p` grades the trace into `grading.json`.
  - Its README notes that skill firing varies from run to run, so pin `--model` and record the CLI version.
  - CI round-trips the install with `claude plugin marketplace add ./` and then `claude plugin install`.
- **obra/superpowers** (<https://github.com/obra/superpowers>, evals at <https://github.com/prime-radiant-inc/superpowers-evals>):
  - Greps stream-json for `"name":"Skill"`.
  - Pressure tests that follow RED/GREEN: a baseline without the skill, then the skill, then closing loopholes.
  - Behavioural evals in an isolated `HOME`.
  - A skill-size limit.
  - Public CI runs only static checks.
- **humanlayer/skills** (<https://github.com/humanlayer/skills>): runs `codex exec --ignore-user-config --skip-git-repo-check --json` against git fixture repos, with the skill symlinked into `.agents/skills`. It asserts on JSONL events and on `git diff`.
- **mattpocock/skills** (<https://github.com/mattpocock/skills>):
  - Bucketed `skills/<bucket>/<name>/`.
  - An `agents/openai.yaml` for every skill.
  - `.claude-plugin/plugin.json` lists skill paths explicitly.
  - Changesets, with a script that syncs plugin versions.
  - ADRs and a `GLOSSARY.md`.
  - Run `claude plugin validate . --strict` after any manifest edit.
  - User-invoked skills set `disable-model-invocation: true` and `allow_implicit_invocation: false` together.

## Contamination risk

Codex and Pi walk up from the working directory to the repo root, and all three agents read user-level skill folders. An eval run started anywhere inside this repo, or with the real `HOME`, could therefore load any of these:

- the repo's own dev skills, such as the review skill from ticket 01
- the shipped skills in their source location
- the user's own skills in `~/.claude/skills`, `~/.agents/skills` and `~/.pi/agent/skills`

To prevent that:

- Each eval run uses a fresh git repo whose root is the workspace itself, so a walk up stops there.
- Each run gets an isolated agent home or config directory.
- A contamination check proves that only the skill under test, or none for a baseline, was visible to the agent, apart from skills built into the pinned agent.

A fresh git root stops discovery only. It does not stop an agent's tools from reading parent directories. Context files such as AGENTS.md and CLAUDE.md can still load from ancestors unless turned off, and Codex's user-level `~/.agents/skills` sits in the OS home, which a redirected `CODEX_HOME` does not move.

Isolating the home can also drop credentials (the Claude keychain or login state, Codex `auth.json`, Pi auth). The eval design must say how credentials reach the isolated run without user skills or config coming with them.
