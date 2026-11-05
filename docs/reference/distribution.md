# Distribution

The Claude Code marketplace and `npx skills` ship every skill in `skills/`, currently `skills/cowsay/`.
Dev skills stay in `dev-skills/`, exposed to repository agents through relative
symlinks in `.claude/skills/` and `.agents/skills/`. They are excluded from both
installation channels. See [ADR 0010](../adr/0010-distribution-boundaries.md).

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
the hosted Git-source behavior. Claude installs cowsay into its plugin cache and its
recorded `gitCommitSha` must match the local clone's HEAD;
the other three installs use the default `skills add --agent <agent> --yes`
behavior without naming a skill, exercising installation of all shipped skills.
The listing assertion also names no skill. The per-agent cases exercise copies;
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
The project's `.claude/settings.json` now enables the plugin, and the plugin
itself is cached in `.tools/agent-homes/claude/plugins/cache/`.

Install it through `skills`, once per agent:

```sh
just run sh -c 'cd .tools/tmp/install-check && DO_NOT_TRACK=1 ../../../node_modules/.bin/skills add ../../.. --agent claude-code --yes'
just run sh -c 'cd .tools/tmp/install-check && DO_NOT_TRACK=1 ../../../node_modules/.bin/skills add ../../.. --agent codex --yes'
ls .tools/tmp/install-check/.claude/skills/cowsay .tools/tmp/install-check/.agents/skills/cowsay
```

Each `skills` run reports `Found 1 skill` and `✓ cowsay (copied)`. Under an agent,
it first prints `Agent detected — installing non-interactively`, and its summary
may show the shared `.agents/skills/cowsay` path for Claude Code; the final line
shows where the skill landed. The `ls` lists `SKILL.md`, `agents` and `scripts`
for each agent.

`../../..` is this checkout, which is the form to use unless you are checking a
release. To check what is published on GitHub, replace it with `BiscuitBin/skills`
in the `marketplace add` and `skills add` commands. The pinned `skills` binary is
the same version as the README's `npx skills@1.7.4`.

Remove the plugin, the marketplace, the plugin's cache and the throwaway project
when you finish:

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
