set shell := ["sh", "-eu", "-c"]
set positional-arguments := true

# Everything a recipe installs or caches stays under .tools/, which Git
# ignores. These reach every recipe and everything a recipe runs, including
# the pre-commit hook, which runs `just pre-commit`. A tool run outside just
# does not see them, and writes to the user's home instead. See
# docs/adr/0003-project-local-toolchain.md.
tools := justfile_directory() / ".tools"
export UV_PYTHON_INSTALL_DIR := tools / "python"
export UV_PYTHON_BIN_DIR := tools / "python-bin"
export UV_CACHE_DIR := tools / "cache/uv"
export npm_config_cache := tools / "cache/npm"
export npm_config_update_notifier := "false"
export npm_config_fund := "false"
export npm_config_audit := "false"
export PREK_HOME := tools / "cache/prek"

# The agent CLIs keep their state in an isolated home each, so a recipe never
# reads or writes the user's ~/.claude, ~/.codex or ~/.pi.
agent_homes := tools / "agent-homes"
export CLAUDE_CONFIG_DIR := agent_homes / "claude"
export CODEX_HOME := agent_homes / "codex"
export PI_CODING_AGENT_DIR := agent_homes / "pi"
export DISABLE_AUTOUPDATER := "1"
export DISABLE_TELEMETRY := "1"
export CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC := "1"

[doc('List the recipes.')]
default:
    @just --list

# ------------------------------------------------------------------ setup ---

[doc('First-run setup. Never stages, commits, tags, or pushes.')]
initialize:
    ./scripts/initialize.sh

[doc('Install exactly what the lockfiles say. Fails rather than relocks on drift.')]
sync:
    uv python install --no-bin
    uv sync --frozen
    npm ci

[doc('Rewrite both lockfiles from the manifests. Review the diff before committing.')]
lock:
    uv lock
    npm install --package-lock-only --ignore-scripts

[doc('Fail when a manifest and its lockfile disagree.')]
lock-check:
    uv lock --check
    npm ci --ignore-scripts --dry-run

# prek's own shim would run prek without this file's environment, so the hook
# runs `just pre-commit` instead. Git starts a hook at the root of the worktree
# being committed, so the hook names no path.
[doc('Install the pre-commit hook, which runs `just pre-commit`.')]
install-hooks:
    hook="$(git rev-parse --git-path hooks)/pre-commit"; \
        mkdir -p "$(dirname "$hook")"; \
        printf '%s\n' '#!/bin/sh' '# Written by `just install-hooks`.' 'exec just pre-commit' >"$hook"; \
        chmod +x "$hook"; \
        printf 'Installed %s\n' "$hook"

[doc('Run a one-off command with the project environment: `just run uv add --dev <pkg>`.')]
run +command:
    @"$@"

# ----------------------------------------------------------------- format ---

[doc('Apply ruff, markdownlint and Prettier fixes. The only recipe that rewrites sources.')]
format:
    uv run --frozen ruff check --fix-only .
    uv run --frozen ruff format .
    ./node_modules/.bin/markdownlint-cli2 --fix
    ./node_modules/.bin/prettier --write .

# ------------------------------------------------------------------ check ---

# prek reads the files Git tracks, so a new file is linted once it is staged.
[doc('Run every pre-commit hook over every tracked file.')]
lint:
    uv run --frozen prek run --all-files

[doc('What the pre-commit hook runs: the same hooks over the staged files.')]
pre-commit:
    uv run --frozen prek run

[doc('Run mypy in strict mode.')]
typecheck:
    uv run --frozen mypy

[doc('Run pytest.')]
test:
    uv run --frozen pytest

# Run from node_modules/.bin and never from PATH, so a global install cannot
# stand in for a broken local one.
[doc('Print the version of each pinned agent CLI.')]
agents-version:
    mkdir -p "$CLAUDE_CONFIG_DIR" "$CODEX_HOME" "$PI_CODING_AGENT_DIR"
    ./node_modules/.bin/claude --version
    ./node_modules/.bin/codex --version
    ./node_modules/.bin/pi --version

[doc('The full gate, as CI runs it. Stops at the first recipe that fails.')]
check: lock-check lint typecheck test agents-version
