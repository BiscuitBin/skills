#!/bin/sh
# The first-run command behind `just initialize`. Run it through just, which
# exports the environment that keeps every install inside .tools/.
set -eu

project_root=$(CDPATH='' cd -- "$(dirname -- "$0")/.." && pwd -P)
cd "$project_root"

git rev-parse --is-inside-work-tree >/dev/null

# Installs exactly what the lockfiles say: the pinned Python into .tools/python,
# then .venv/ and node_modules/. Nothing here relocks or reformats, so a drifted
# lockfile or an unformatted file is left for `just check` to report.
just sync

# Hooks are installed only from the primary checkout. Every worktree of this
# repository shares one .git/hooks directory, and `prek install` writes a shim
# naming an absolute path into whichever worktree ran it, so a hook installed
# from a secondary worktree runs that worktree's virtual environment for commits
# made anywhere, and keeps doing so after the worktree is deleted. The test is
# the one git itself uses: in a secondary worktree the common directory and the
# git directory differ.
if [ "$(git rev-parse --git-common-dir)" = "$(git rev-parse --git-dir)" ]; then
    just install-hooks
else
    printf '%s\n' 'Secondary worktree: skipping install-hooks.' >&2
    printf '%s\n' 'Run just install-hooks once from the primary checkout.' >&2
fi

printf '\n%s\n' 'Ready. Next: just check.'
printf '%s\n' 'Nothing has been staged, committed, tagged, or pushed.'
