# Every tool is pinned and installed inside the project directory

Every tool the gate runs is pinned to an exact version, locked in a committed lockfile, and installed inside the project: the Python interpreter, Python dev tools, Node dev tools and the three agent CLIs. A contributor's global installs never stand in for a pinned one, so two machines running `just check` run the same tools.

## How

- **Python.** `.python-version` names an exact patch release. `[tool.uv] python-preference = "only-managed"` stops uv from using a host Python, and the Justfile's `UV_PYTHON_INSTALL_DIR` makes uv download the interpreter into `.tools/python`. Dev tools are locked in `uv.lock` and installed into `.venv/`.
- **Node.** Node itself is a host prerequisite, because no lockfile can install it. `.node-version` and `engines` name the exact version, and `.npmrc` sets `engine-strict` so any other version fails the install. npm packages are locked in `package-lock.json` and installed into `node_modules/`. The agent CLIs run from `node_modules/.bin`, never from `PATH`.
- **State and caches.** The Justfile points the uv, npm and prek caches into `.tools/cache/`. It gives each agent CLI its own home under `.tools/agent-homes/` (`CLAUDE_CONFIG_DIR`, `CODEX_HOME`, `PI_CODING_AGENT_DIR`) and turns off the Claude Code autoupdater.
- **Install scripts.** `package.json` `allowScripts` approves only Claude Code's postinstall, pinned to the reviewed version, which links the platform binary inside `node_modules`. Other install scripts are denied.
- **Drift.** `just initialize` and `just sync` install exactly what the lockfiles say and never relock or reformat, so drift reaches `just check`, where `just lock-check` reports it.

## Consequences

- **Hooks do not see the Justfile's environment.** Git starts a pre-commit hook, not just, so a hook gets the user's environment. The hooks therefore call only tools that are already installed (`uv run --frozen …` and `./node_modules/.bin/…`), and no hook names a remote repository, which prek would clone into a cache in the user's home. The residual: `uv run` inside a hook uses uv's default cache in the user's home. This only happens on the commit path, and the commit path is outside `just`.
- **Untracked files are not linted.** prek reads the files Git tracks, so `just lint` skips a new file until it is staged. CI checks a clean clone, where every file is tracked.
- **Host prerequisites.** just, uv and Node stay on the host, at the versions the README lists. CI pins the same versions.
