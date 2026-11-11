# skills

Agent skills for Claude Code and Codex, in the [Agent Skills](https://agentskills.io/specification) `SKILL.md` format. This repository is where they are developed, evaluated against both agents, and distributed. Pi can install them through `npx skills`, but they are not yet evaluated on Pi.

The shipped skills are `cowsay`, which makes an ASCII cow say your text with a bundled Python script, and `change-viz`, which describes what a branch changes as Markdown for a pull request and runs only when you invoke it by name. Work is tracked in `.scratch/foundation/issues/`.

## Install

cowsay needs Python 3 to run its bundled script. Run these commands in the project where you want the skills available.

Contributors working from a clone of this repository use [Check the install channels from a checkout](docs/reference/distribution.md#check-the-install-channels-from-a-checkout) instead, because these commands write to your real agent home.

### Claude Code marketplace

```sh
claude plugin marketplace add BiscuitBin/skills
claude plugin install cowsay@biscuitbin-skills --scope project
claude plugin install change-viz@biscuitbin-skills --scope project
```

These are shell commands for an installed Claude Code CLI. Each skill is its own plugin, so install the ones you want.
Invoke them with `/cowsay:cowsay Hello there`, and with `/change-viz:change-viz` on the branch you want described.

### npx skills

Choose your agent; these commands install every shipped skill in this repo:

```sh
npx skills@1.7.4 add BiscuitBin/skills --agent claude-code --yes
npx skills@1.7.4 add BiscuitBin/skills --agent codex --yes
npx skills@1.7.4 add BiscuitBin/skills --agent pi --yes
```

Claude Code discovers each skill in `.claude/skills/<name>`; Codex and Pi use `.agents/skills/<name>`.
Invoke one with `/<name>` in Claude Code, `$<name>:<name>` in Codex (it reads the skill's plugin manifest, so the name carries a prefix), or `/skill:<name>` in Pi: for example `/cowsay Hello there`, or `$change-viz:change-viz` on the branch you want described. `change-viz` never loads unless invoked this way.
Pi requires project trust before loading project skills.
List available skills without installing with `npx skills@1.7.4 add BiscuitBin/skills --list`.

The [distribution reference](docs/reference/distribution.md) describes the manifests, version updates and credential-free installation tests.

## Host prerequisites

`just initialize` relies on these being installed on the host. Everything else is pinned and installed inside the project.

| Tool | Version | Notes |
| --- | --- | --- |
| [Git](https://git-scm.com/) | any recent | |
| [just](https://just.systems/) | 1.59.0 | Required exactly: `just initialize` and `just check` check it. The pre-commit hook runs `just`, so it must be on the `PATH` of whatever runs `git commit`, including an editor's Git client. |
| [uv](https://docs.astral.sh/uv/) | 0.13.6 | Required exactly: `pyproject.toml` sets `required-version`. |
| [Node.js](https://nodejs.org/) | 26.5.1, with npm 11.17.0 | Required exactly: `.node-version` and `engines`, enforced by `engine-strict`. |

**How Python is obtained.** You do not need Python installed. uv downloads the exact version in `.python-version` into `.tools/python`, and never uses a Python found on the host.

**How Node is obtained.** Node is the one runtime you install yourself, at the exact version in `.node-version`. fnm reads `.node-version` as it stands. mise reads it only once you enable that with `mise settings add idiomatic_version_file_enable_tools node`, which changes your global mise config. nvm and Volta do not read it, so name the version yourself: `nvm install "$(cat .node-version)"`, or `volta install "node@$(cat .node-version)"`, which also changes your default Node. With any other version, `npm ci` stops with an engine error.

## Getting started

```sh
just initialize   # install the pinned tools into the project directory and set up hooks
just check        # the full gate, the same one CI runs
just              # list every recipe
```

`just initialize` never stages, commits, tags or pushes. The [getting started tutorial](docs/tutorials/getting-started.md) walks through it.

## Running the evals

The [run a skill's evals guide](docs/how-to/run-evals.md) covers the credentials, `just eval cowsay` on each agent and the report. These runs call paid models, so `just check` does not include them.

## Adding a skill

```sh
just new-skill <name>   # scaffold a skill, its placeholder evals and its marketplace entry
```

The [first skill tutorial](docs/tutorials/first-skill.md) takes a scratch skill from scaffold to evaluated and installed. The [contributing guide](CONTRIBUTING.md) covers the full workflow: evals first, then the skill, the cross-model review, versions and releases.

## Documentation

- [Documentation index](docs/README.md)
- [Contributing a skill](CONTRIBUTING.md)
- [Architecture decision records](docs/adr/README.md)
- [Glossary](GLOSSARY.md)
- [Agent instructions](AGENTS.md)

## Licence

[MIT](LICENSE).
