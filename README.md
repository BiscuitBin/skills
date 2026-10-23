# skills

Agent skills for Claude Code, Codex and Pi, in the [Agent Skills](https://agentskills.io/specification) `SKILL.md` format. This repository is where they are developed, evaluated against all three agents, and distributed.

It is at the foundation stage: the toolchain, docs and decision records are in place, and the first skill, the eval harness and the distribution channels follow. Work is tracked in `.scratch/foundation/issues/`.

## Host prerequisites

`just initialize` relies on these being installed on the host. Everything else is pinned and installed inside the project.

| Tool | Tested version | Notes |
| --- | --- | --- |
| [Git](https://git-scm.com/) | any recent | |
| [just](https://just.systems/) | 1.51.0 | CI uses the same version. The pre-commit hook runs `just`, so it must be on the `PATH` of whatever runs `git commit`, including an editor's Git client. |
| [uv](https://docs.astral.sh/uv/) | 0.13.4 | Required exactly: `pyproject.toml` sets `required-version`. |
| [Node.js](https://nodejs.org/) | 26.5.1, with npm 11.17.0 | Required exactly: `.node-version` and `engines`, enforced by `engine-strict`. |

**How Python is obtained.** You do not need Python installed. uv downloads the exact version in `.python-version` into `.tools/python`, and never uses a Python found on the host.

**How Node is obtained.** Node is the one runtime you install yourself, at the exact version in `.node-version`. Any version manager that reads `.node-version` (fnm, nvm, mise, Volta) will pick it up. With any other version, `npm ci` stops with an engine error.

## Getting started

```sh
just initialize   # install the pinned tools into the project directory and set up hooks
just check        # the full gate, the same one CI runs
just              # list every recipe
```

`just initialize` never stages, commits, tags or pushes. The [getting started tutorial](docs/tutorials/getting-started.md) walks through it.

## Documentation

- [Documentation index](docs/README.md)
- [Architecture decision records](docs/adr/README.md)
- [Glossary](GLOSSARY.md)
- [Agent instructions](AGENTS.md)

## Licence

[MIT](LICENSE).
