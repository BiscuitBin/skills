# Commands

Every command goes through `just`. Run `just` on its own to list the recipes.

| Recipe | What it does |
| --- | --- |
| `initialize` | The first-run setup: `sync`, then `install-hooks` in the primary checkout only. It never relocks, reformats, stages, commits, tags or pushes. |
| `sync` | Installs the pinned Python into `.tools/python`, then exactly what `uv.lock` and `package-lock.json` say. It fails rather than relocking when a lockfile is out of date. |
| `lock` | Rewrites both lockfiles from `pyproject.toml` and `package.json`. Run it after changing a pin, then review and commit the lockfile diff. |
| `lock-check` | Fails when either lockfile disagrees with its manifest. |
| `install-hooks` | Installs the prek pre-commit hook. |
| `format` | Applies ruff, markdownlint and Prettier fixes. This is the only recipe that rewrites source files. |
| `lint` | Runs every pre-commit hook over every tracked file: ruff lint and format check, markdownlint, Prettier and the builtin file checks. |
| `typecheck` | Runs mypy in strict mode over `src/` and `tests/`. |
| `test` | Runs pytest. |
| `agents-version` | Prints the version of each pinned agent CLI (Claude Code, Codex and Pi), run from `node_modules/.bin` with isolated homes under `.tools/agent-homes/`. |
| `check` | The full gate, which CI also runs: `lock-check`, `lint`, `typecheck`, `test`, then `agents-version`. It stops at the first failure. |
