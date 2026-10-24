# skills

Agent skills for Claude Code, Codex and Pi, in the [Agent Skills](https://agentskills.io/specification) `SKILL.md` format. This repository is where they are developed, evaluated against all three agents, and distributed.

The first shipped skill is `cowsay`, with a bundled Python script. The eval harness is under development. Work is tracked in `.scratch/foundation/issues/`.

## Install cowsay

Python 3 is required to run the bundled script. Run these commands in the project where you want the skill available.

### Claude Code marketplace

```sh
claude plugin marketplace add BiscuitBin/skills
claude plugin install cowsay@biscuitbin-skills --scope project
```

These are shell commands for an installed Claude Code CLI. Contributors verify
this checkout's pinned CLI with `just test`, which installs into isolated projects.
Invoke the installed skill with `/cowsay:cowsay Hello there`.

### npx skills

Choose your agent; these commands install every shipped skill in this repo, currently just `cowsay`:

```sh
npx skills@1.7.4 add BiscuitBin/skills --agent claude-code --yes
npx skills@1.7.4 add BiscuitBin/skills --agent codex --yes
npx skills@1.7.4 add BiscuitBin/skills --agent pi --yes
```

Claude Code discovers the result in `.claude/skills/cowsay`; Codex and Pi use `.agents/skills/cowsay`.
Invoke it with `/cowsay` in Claude Code, `$cowsay` in Codex, or `/skill:cowsay` in Pi.
Pi requires project trust before loading project skills.
List available skills without installing with `npx skills@1.7.4 add BiscuitBin/skills --list`.

The [distribution reference](docs/reference/distribution.md) describes the manifests, version updates and credential-free installation tests.

## Host prerequisites

`just initialize` relies on these being installed on the host. Everything else is pinned and installed inside the project.

| Tool | Version | Notes |
| --- | --- | --- |
| [Git](https://git-scm.com/) | any recent | |
| [just](https://just.systems/) | 1.51.0 | Required exactly: `just initialize` and `just check` check it. The pre-commit hook runs `just`, so it must be on the `PATH` of whatever runs `git commit`, including an editor's Git client. |
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
