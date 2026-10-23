set shell := ["sh", "-eu", "-c"]

# Everything a recipe installs or caches stays under .tools/, which Git
# ignores. These reach every recipe, and everything a recipe runs, but not a
# Git hook: hooks are started by git, not by just, so .pre-commit-config.yaml
# calls only tools that are already installed. See
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

default:
    @just --list

# ------------------------------------------------------------------ setup ---

# One explicit first-run command. Never stages, commits, tags, or pushes.
initialize:
    ./scripts/initialize.sh

# Installs exactly what the lockfiles say. Fails rather than relocks on drift.
sync:
    uv python install --no-bin
    uv sync --frozen
    npm ci

# Rewrites both lockfiles from the manifests. Review the diff before committing.
lock:
    uv lock
    npm install --package-lock-only --ignore-scripts

# Fails when a manifest and its lockfile disagree.
lock-check:
    uv lock --check
    npm ci --ignore-scripts --dry-run

install-hooks:
    git rev-parse --is-inside-work-tree >/dev/null
    uv run --frozen prek install --overwrite --hook-type=pre-commit

# ----------------------------------------------------------------- format ---

format:
    uv run --frozen ruff check --fix-only .
    uv run --frozen ruff format .
    ./node_modules/.bin/markdownlint-cli2 --fix
    ./node_modules/.bin/prettier --write .

# ------------------------------------------------------------------ check ---

# Every pre-commit hook over every file: ruff, markdownlint, prettier and the
# builtin file checks. A commit runs the same hooks over the staged files.
lint:
    uv run --frozen prek run --all-files

typecheck:
    uv run --frozen mypy

test:
    uv run --frozen pytest

# Each pinned agent CLI, run from node_modules/.bin and never from PATH, so a
# global install cannot stand in for a broken local one.
agents-version:
    mkdir -p "$CLAUDE_CONFIG_DIR" "$CODEX_HOME" "$PI_CODING_AGENT_DIR"
    ./node_modules/.bin/claude --version
    ./node_modules/.bin/codex --version
    ./node_modules/.bin/pi --version

# The complete gate. Stops at the first recipe that fails.
check: lock-check lint typecheck test agents-version
