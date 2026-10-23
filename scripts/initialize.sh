#!/bin/sh
# The first-run command behind `just initialize`. Run it through just, which
# exports the environment that keeps every install inside .tools/.
set -eu

project_root=$(CDPATH='' cd -- "$(dirname -- "$0")/.." && pwd -P)
cd "$project_root"

git rev-parse --is-inside-work-tree >/dev/null

# uv and Node check their own versions (`required-version` in pyproject.toml,
# `engine-strict` in .npmrc). Nothing checks just, so this does. CI installs the
# same version.
required_just='just 1.51.0'
found_just=$(just --version)
if [ "$found_just" != "$required_just" ]; then
    printf '%s\n' "$required_just is required; found $found_just." >&2
    exit 1
fi

# Installs exactly what the lockfiles say: the pinned Python into .tools/python,
# then .venv/ and node_modules/. It fails on a lockfile that disagrees with its
# manifest, and never relocks or reformats: an unformatted file is left for
# `just check` to report.
just sync

# Hooks are installed only from the primary checkout. Every worktree of this
# repository shares one hooks directory, so installing from a secondary
# worktree would change what a commit runs in every other checkout too. The
# test is the one git itself uses: in a secondary worktree the common directory
# and the git directory differ.
if hooks_path=$(git config --get core.hooksPath); then
    printf '%s\n' "core.hooksPath is set to $hooks_path: skipping install-hooks." >&2
    printf '%s\n' 'Commits will not run the gate. Unset it and run just install-hooks to add the hook.' >&2
elif [ "$(git rev-parse --git-common-dir)" = "$(git rev-parse --git-dir)" ]; then
    just install-hooks
else
    printf '%s\n' 'Secondary worktree: skipping install-hooks.' >&2
    printf '%s\n' 'Run just install-hooks once from the primary checkout.' >&2
fi

printf '\n%s\n' 'Ready. Next: just check.'
printf '%s\n' 'Nothing has been staged, committed, tagged, or pushed.'
