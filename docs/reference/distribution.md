# Distribution

The Claude Code marketplace and `npx skills` ship every skill in `skills/`, one plugin per skill.
Dev skills stay in `dev-skills/build/`, exposed to repository agents through relative
symlinks in `.claude/skills/` and `.agents/skills/`. They are excluded from both
installation channels when no skill is named. See [ADR 0010](../adr/0010-distribution-boundaries.md)
and [ADR 0015](../adr/0015-dev-skills-under-build.md).

`build` is not generated output: the folder is tracked, and nothing writes to it.
The name matters because `skills@1.7.4` skips a fixed list of directory names
(`build` among them) in the recursive scan it runs for `--full-depth` or when it
finds no shipped skills. That list is an installer internal, so the round trips
below fail if a new pin stops skipping `build`. The exclusion covers unnamed
discovery: the default, `--full-depth` and a repository with no shipped skills.
An explicit path to a dev skill, such as `skills add <repo>/dev-skills/build/<name>`,
is outside it.

## Manifests and versions

`.claude-plugin/marketplace.json` lists plugins in `plugins[]`. Each entry's
`name` matches a shipped skill and its `source` is `./skills/<name>`, so the
plugin cache contains only that skill's directory. In each
`skills/<name>/.claude-plugin/plugin.json`, `skills: ["./"]` tells Claude Code
to discover the skill at the plugin root.

The single source for a plugin's version and description is its
`skills/<name>/.claude-plugin/plugin.json`. `just format` copies both into
the plugin's entry in `.claude-plugin/marketplace.json`, and removes the
entry's description when `plugin.json` has none. Change the plugin
version, run `just format`, and commit both manifests. `just new-skill` adds
the manifest and the marketplace entry for a new skill; [CONTRIBUTING.md](../../CONTRIBUTING.md)
says when to bump a version. The Python tooling's version and
the npm development package's version are independent.

`just validate-distribution` rejects version or description drift and
extra/missing plugins (naming the entry to add or remove),
sources outside shipped skill directories, and uncommitted changes to install
sources. It runs the pinned
`claude plugin validate --strict` for the marketplace and each shipped plugin.
`just check` includes this recipe.

## Installation round trips

`just test` includes the four required installation round trips plus a combined
Claude Code/Codex install in `tests/test_distribution.py`;
`just check` and PR CI run the same tests. No agent credentials or published
GitHub repository are needed. After `just initialize`, installs use only local
Git sources and the locked tools. The installer is `skills@1.7.4`; the test uses
`npm exec --offline --no --prefix <checkout> -- skills`, the local equivalent
of `npx skills@1.7.4`.

Each test clones the committed tree. Both installers use the README's
`BiscuitBin/skills` shorthand and Git's process-local
`url.<file-url>.insteadOf` configuration to redirect the clone to the local
source. `GIT_ALLOW_PROTOCOL=file` prevents network Git transport. This exercises
the hosted Git-source behavior. The marketplace round trip installs one plugin, cowsay, into
Claude's plugin cache, and its recorded `gitCommitSha` must match the local clone's HEAD;
the other three installs use the default `skills add --agent <agent> --yes`
behavior without naming a skill, exercising installation of all shipped skills.
The listing assertions also name no skill: `--list` and `--list --full-depth`
must both find exactly the shipped skills. Separate tests install with
`--full-depth` and list a clone with `skills/` removed, which must report
`No skills found` and exit 1. The per-agent cases exercise copies;
the combined-agent case exercises a Claude symlink and the shared canonical copy.
Observed modes are recorded as the JUnit property `installation_mode` in
`ai_tmp/pytest.xml` and printed in successful-test output in the `just check`
CI log. `just test` enables both outputs.

The tests check discovery paths, the complete installed file inventory and all
paths in the throwaway project (excluding its Git metadata). Only shipped
payloads and installer lock/settings files are allowed. Every accepted payload
copy is compared byte for byte, lockfile skill names and sources are checked,
and only the known Claude-to-shared discovery symlink is permitted. They remove the source clone and Claude's
marketplace clone, then execute the installed cowsay script. An isolated Python
subprocess (`-I -S`) with a file-open audit hook permits reads only from the
installed skill and the pinned Python standard library. This makes source
files in the development checkout unavailable to the script while retaining
the project-local Python runtime.

The subprocesses receive a fresh environment with throwaway `HOME`, agent
homes, XDG folders, npm cache and temporary directory, all beneath the test
workspace in `.tools/tmp/`. Dead local HTTP proxies also block direct HTTP
fetches (including Node fetch via `NODE_USE_ENV_PROXY`); Git transport is
restricted to files. They inherit no agent credentials, Git helpers or
user configuration. Local installs need no login; the separate cross-model
development review still requires an authenticated reviewer.

Because the source is the committed tree, commit distribution changes before
running the round trips. Both the tests and `just validate-distribution` enforce
this for `skills/`, `.claude-plugin/`, `dev-skills/` and the two dev-skill discovery
directories; unrelated documentation edits remain allowed. The live manifest
validation also checks the working tree. Round trips deliberately do not install
uncommitted files.

## Check the install channels from a checkout

Use this section, not the README's commands, when you try an install from a
clone of this repository. The README's commands are for end users: a bare
`claude` or `npx` runs outside the Justfile's environment, so it writes to your
real `~/.claude/plugins` and `~/.npm`. These commands run the pinned `claude`
and `skills` through `just run`, which keeps the Claude Code home and the npm
cache under `.tools/`. Neither install needs an agent login. Run them from the
repository root.

Create a throwaway project and install cowsay through the marketplace:

```sh
just run sh -c 'mkdir -p .tools/tmp/install-check && cd .tools/tmp/install-check && git init -q && ../../../node_modules/.bin/claude plugin marketplace add ../../.. && ../../../node_modules/.bin/claude plugin install cowsay@biscuitbin-skills --scope project'
```

It reports `Successfully installed plugin: cowsay@biscuitbin-skills (scope: project)`.
Its `declared in user settings` line refers to the project's Claude Code home,
`.tools/agent-homes/claude/settings.json`, not your own. The project's `.claude/settings.json` now enables the plugin, and the plugin
itself is cached in `.tools/agent-homes/claude/plugins/cache/`.

Install every shipped skill through `skills`, the binary that `npx skills@1.7.4` runs, once per agent:

```sh
just run sh -c 'cd .tools/tmp/install-check && DO_NOT_TRACK=1 ../../../node_modules/.bin/skills add ../../.. --agent claude-code --yes'
just run sh -c 'cd .tools/tmp/install-check && DO_NOT_TRACK=1 ../../../node_modules/.bin/skills add ../../.. --agent codex --yes'
ls .tools/tmp/install-check/.claude/skills .tools/tmp/install-check/.agents/skills
```

Each `skills` run reports `Found <n> skills`, one for each directory in
`skills/`, and a `✓ <name> (copied)` line for each. Under an agent, it first
prints `Agent detected — installing non-interactively`, and its summary may show
the shared `.agents/skills/<name>` paths for Claude Code; the final lines show
where each skill landed. The `ls` lists each shipped skill for each agent.

`../../..` is this checkout, which is the form to use unless you are checking a
release. To check what is published on GitHub, replace it with `BiscuitBin/skills`
in the `marketplace add` and `skills add` commands.

When you have checked the results, remove the plugin, the marketplace, the
plugin's cache and the throwaway project:

```sh
just run sh -c 'cd .tools/tmp/install-check && ../../../node_modules/.bin/claude plugin uninstall cowsay@biscuitbin-skills --scope project && ../../../node_modules/.bin/claude plugin marketplace remove biscuitbin-skills'
rm -rf .tools/tmp/install-check .tools/agent-homes/claude/plugins/cache/biscuitbin-skills
```

## Upstream references

- [Claude Code plugin manifest](https://code.claude.com/docs/en/plugins-reference)
- [Claude Code marketplaces](https://code.claude.com/docs/en/plugin-marketplaces)
- [skills installer](https://github.com/vercel-labs/skills)

Behavior is checked against the pinned CLI versions rather than inferred from
the latest documentation.
