set shell := ["sh", "-eu", "-c"]
set positional-arguments := true

# Everything a recipe installs or caches stays under .tools/, which Git
# ignores. These reach every recipe and everything a recipe runs, including
# the pre-commit hook, which runs `just pre-commit`. A tool run outside just
# does not see them, and writes to the user's home instead. See
# docs/adr/0003-project-local-toolchain.md.
tools := justfile_directory() / ".tools"
export UV_PYTHON_INSTALL_DIR := tools / "python"
# pyproject.toml says only-managed too, but a variable in the user's shell
# would outrank it, and these three would point uv at another interpreter or
# environment.
export UV_PYTHON_PREFERENCE := "only-managed"
unexport UV_PYTHON
unexport UV_PROJECT_ENVIRONMENT
export UV_PYTHON_BIN_DIR := tools / "python-bin"
export UV_CACHE_DIR := tools / "cache/uv"
export npm_config_cache := tools / "cache/npm"
export npm_config_update_notifier := "false"
export npm_config_fund := "false"
export npm_config_audit := "false"
export PREK_HOME := tools / "cache/prek"
# Node, uv and the agent CLIs put temporary files here rather than in the
# system temporary directory. Node uses TMPDIR whether or not it exists, so
# the backtick creates it before any recipe runs.
export TMPDIR := `mkdir -p .tools/tmp && cd .tools/tmp && pwd -P`

# The agent CLIs keep their state in an isolated home each, so a recipe never
# reads or writes the user's ~/.claude, ~/.codex or ~/.pi. Codex refuses to
# start when its home is missing, so the backtick creates all three.
agent_homes := `mkdir -p .tools/agent-homes/claude .tools/agent-homes/codex .tools/agent-homes/pi && cd .tools/agent-homes && pwd -P`
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

# lock-check first, because `npm ci` alone misses a dependency removed from
# package.json.
[doc('Install exactly what the lockfiles say. Fails rather than relocks on drift.')]
sync: lock-check
    uv python install --no-bin
    uv sync --locked
    npm ci

[doc('Rewrite both lockfiles from the manifests. Review the diff before committing.')]
lock:
    uv lock
    npm install --package-lock-only --ignore-scripts

# `npm ci --dry-run` catches a changed pin but not a removed dependency, so the
# npm half relocks a copy of the manifest and lockfile and compares the result.
[doc('Fail when a manifest and its lockfile disagree.')]
lock-check:
    uv lock --check
    @copy="$(mktemp -d)"; trap 'rm -rf "$copy"' EXIT; \
    cp package.json package-lock.json .npmrc "$copy/"; \
    (cd "$copy" && npm install --package-lock-only --ignore-scripts --no-audit --no-fund >/dev/null); \
    if ! cmp -s package-lock.json "$copy/package-lock.json"; then \
        diff -u package-lock.json "$copy/package-lock.json" | head -40 >&2; \
        printf '%s\n' 'package-lock.json disagrees with package.json; run just lock.' >&2; \
        exit 1; \
    fi; \
    printf '%s\n' 'package-lock.json matches package.json.'

# prek's own shim would run prek without this file's environment, so the hook
# runs `just pre-commit` instead. Git starts a hook at the root of the worktree
# being committed, so the hook names no path. Worktrees share one hooks
# directory, so the hook passes when the checkout has no Justfile (a branch
# from before this one), and names ./Justfile so just never finds another one
# in a parent directory. The recipe refuses a core.hooksPath, which usually
# names a hooks directory shared with other repositories, and a pre-commit hook
# it did not write itself.
[doc('Install the pre-commit hook, which runs `just pre-commit`.')]
install-hooks:
    @if hooks_path="$(git config --get core.hooksPath)"; then \
        printf '%s\n' "core.hooksPath is set to $hooks_path; not installing a hook there." >&2; \
        exit 1; \
    fi; \
    hook="$(git rev-parse --git-path hooks)/pre-commit"; \
    if { [ -e "$hook" ] || [ -L "$hook" ]; } && ! grep -qF '# Written by `just install-hooks`.' "$hook" 2>/dev/null; then \
        printf '%s\n' "$hook exists and was not written by just install-hooks; move it aside first." >&2; \
        exit 1; \
    fi; \
    mkdir -p "$(dirname "$hook")"; \
    printf '%s\n' '#!/bin/sh' '# Written by `just install-hooks`.' \
        '[ -f ./Justfile ] || exit 0' 'exec just --justfile ./Justfile pre-commit' >"$hook"; \
    chmod +x "$hook"; \
    printf 'Installed %s\n' "$hook"

[doc('Run a one-off command with the project environment: `just run uv add --dev <pkg>`.')]
run +command:
    @"$@"

# ----------------------------------------------------------------- format ---

[doc('Apply ruff, markdownlint and Prettier fixes. The only recipe that rewrites sources.')]
format:
    uv run --frozen python -m skills_tooling.distribution --write
    uv run --frozen ruff check --fix-only .
    uv run --frozen ruff format .
    ./node_modules/.bin/markdownlint-cli2 --fix '**/*.md' '!.scratch/**'
    ./node_modules/.bin/prettier --write .

# ------------------------------------------------------------------ check ---

# prek's --all-files means tracked files only, so the list comes from git:
# tracked files that still exist, plus untracked ones that are not ignored.
# Each step is its own command rather than a pipeline, so a failing `git` fails
# the recipe instead of handing prek an empty list. SKIP and PREK_SKIP are
# cleared because either one would drop hooks from the gate; a deliberate skip
# still works on `git commit`.
[doc('Run every pre-commit hook over every file that is not gitignored.')]
lint:
    @listed="$(mktemp)"; present="$(mktemp)"; trap 'rm -f "$listed" "$present"' EXIT; \
    git ls-files -z --cached --others --exclude-standard --deduplicate >"$listed"; \
    xargs -0 sh -c 'for f; do [ ! -e "$f" ] || printf "%s\0" "$f"; done' sh <"$listed" >"$present"; \
    test -s "$present" || { printf '%s\n' 'lint: git listed no files to check.' >&2; exit 1; }; \
    xargs -0 env -u SKIP -u PREK_SKIP uv run --frozen prek run --files <"$present"

[doc('What the pre-commit hook runs: the same hooks over the staged files.')]
pre-commit:
    uv run --frozen prek run

[doc('Run mypy in strict mode.')]
typecheck:
    uv run --frozen mypy

[doc('Run pytest.')]
test:
    uv run --frozen pytest

[doc('Validate every shipped skill and dev skill.')]
validate-skills:
    uv run --frozen python -m skills_tooling.validator

[doc('Check distribution versions and validate the marketplace and shipped plugins strictly.')]
validate-distribution:
    uv run --frozen python -m skills_tooling.distribution
    ./node_modules/.bin/claude plugin validate . --strict
    @for skill in skills/*; do ./node_modules/.bin/claude plugin validate "$skill" --strict; done

# Run from node_modules/.bin and never from PATH, so a global install cannot
# stand in for a broken local one.
[doc('Print the version of each pinned agent CLI.')]
agents-version:
    ./node_modules/.bin/claude --version
    ./node_modules/.bin/codex --version
    ./node_modules/.bin/pi --version

# uv and Node check their own versions (`required-version` in pyproject.toml,
# `engine-strict` in .npmrc). Nothing checks just's, so this does. CI installs
# the same version.
[doc('Fail unless this is the pinned just.')]
just-version:
    @required='just 1.51.0'; found="$("{{ just_executable() }}" --version)"; \
    [ "$found" = "$required" ] || { printf '%s\n' "$required is required; found $found." >&2; exit 1; }

[doc('The full gate, as CI runs it. Stops at the first recipe that fails.')]
check: just-version lock-check lint typecheck validate-distribution test validate-skills agents-version
