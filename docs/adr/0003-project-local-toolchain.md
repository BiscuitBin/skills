# Every tool is pinned and installed inside the project directory

Every tool the gate runs is pinned to an exact version, locked in a committed lockfile, and installed inside the project: the Python interpreter, Python dev tools, Node dev tools and the three agent CLIs. A contributor's global installs never stand in for a pinned one, so two machines running `just check` run the same tools.

## How

- **Python.** `.python-version` names an exact patch release. `[tool.uv] python-preference = "only-managed"` stops uv from using a host Python, and the Justfile's `UV_PYTHON_INSTALL_DIR` makes uv download the interpreter into `.tools/python`. Dev tools are locked in `uv.lock` and installed into `.venv/`.
- **Node.** Node itself is a host prerequisite, because no lockfile can install it. `.node-version` and `engines` name the exact version, and `.npmrc` sets `engine-strict` so any other version fails the install. npm packages are locked in `package-lock.json` and installed into `node_modules/`. The agent CLIs run from `node_modules/.bin`, never from `PATH`.
- **State and caches.** The Justfile points the uv, npm and prek caches into `.tools/cache/`. It gives each agent CLI its own home under `.tools/agent-homes/` (`CLAUDE_CONFIG_DIR`, `CODEX_HOME`, `PI_CODING_AGENT_DIR`) and turns off the Claude Code autoupdater.
- **Install scripts.** `package.json` `allowScripts` approves only Claude Code's postinstall, pinned to the reviewed version, which links the platform binary inside `node_modules`. Other install scripts are denied.
- **Drift.** `just initialize` and `just sync` install exactly what the lockfiles say and never relock or reformat, so drift reaches `just check`, where `just lock-check` reports it.

## Consequences

- **Tools run through `just`.** The environment above lives in the Justfile, so a tool started any other way does not see it. A bare `uv run` cannot find the interpreter in `.tools/python`, downloads a second one into the user's home and rebuilds `.venv/` against it, and a bare agent CLI writes to the user's agent home. `just run <command>` is the way to run a one-off command.
- **The pre-commit hook runs `just pre-commit`.** Git starts a hook with the user's environment, not the Justfile's. prek's own hook shim was rejected for that reason: tested from a fresh clone with an empty home, a commit through it downloaded Python into `~/.local/share/uv`, rebuilt `.venv/`, and filled `~/.cache/uv` and `~/.cache/prek`. The hook `just install-hooks` writes names no path, so it works in every worktree. It does need `just` on the `PATH` of whatever runs `git commit`.
- **Untracked files are not linted.** prek reads the files Git tracks, so `just lint` skips a new file until it is staged. CI checks a clean clone, where every file is tracked.
- **Host prerequisites.** just, uv and Node stay on the host, at the versions the README lists. CI pins the same versions.
