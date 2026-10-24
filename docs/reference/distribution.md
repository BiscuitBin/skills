# Distribution

The Claude Code marketplace and `npx skills` ship `skills/cowsay/`.
Dev skills stay in `dev-skills/`, exposed to repository agents through relative
symlinks in `.claude/skills/` and `.agents/skills/`. They are excluded from both
installation channels. See [ADR 0010](../adr/0010-distribution-boundaries.md).

## Manifests and versions

`.claude-plugin/marketplace.json` lists plugins in `plugins[]`. Each entry's
`name` matches a shipped skill and its `source` is `./skills/<name>`, so the
plugin cache contains only that skill's directory. In
`skills/cowsay/.claude-plugin/plugin.json`, `skills: ["./"]` tells Claude Code
to discover the skill at the plugin root.

The single source for the cowsay plugin version is
`skills/cowsay/.claude-plugin/plugin.json`'s top-level `version`.
`just format` derives `.claude-plugin/marketplace.json`'s
`plugins[name=cowsay].version` from it. Change the plugin version, run
`just format`, and commit both manifests. The Python tooling's version and
the npm development package's version are independent.

`just validate-distribution` rejects version drift, extra/missing plugins and
sources outside shipped skill directories. It runs the pinned
`claude plugin validate --strict` for the marketplace and each shipped plugin.
`just check` includes this recipe.

## Installation round trips

`just test` includes four installation round trips in `tests/test_distribution.py`;
`just check` and PR CI run the same tests. No agent credentials or published
GitHub repository are needed. After `just initialize`, installs use only local
Git sources and the locked tools. The installer is `skills@1.7.4`; the test uses
`npm exec --offline --no --prefix <checkout> -- skills`, the local equivalent
of `npx skills@1.7.4`.

Each test clones the committed tree. The skills installer accepts its `file://`
Git URL. Claude rejects that URL form, so its test supplies a reserved
`https://distribution.invalid/skills.git` source and uses Git's process-local
`url.<file-url>.insteadOf` configuration to redirect the clone to the local
source. `GIT_ALLOW_PROTOCOL=file` prevents network transport. This exercises
Claude's hosted Git-source behavior and installs into its plugin cache;
the other three installs use the default `skills add --agent <agent> --yes`
behavior without naming a skill, exercising installation of all shipped skills.
The listing assertion also names no skill. Symlink and copy installs are both
accepted, and the observed mode is printed with pytest `-s` and recorded as the
JUnit property `installation_mode`.

The tests check discovery paths and the complete installed file inventory,
including the bundled script. They remove the source clone and Claude's
marketplace clone, then execute the installed script. An isolated Python
subprocess (`-I -S`) with a file-open audit hook permits reads only from the
installed skill and the pinned Python standard library. This makes source
files in the development checkout unavailable to the script while retaining
the project-local Python runtime.

The subprocesses receive a fresh environment with throwaway `HOME`, agent
homes, XDG folders, npm cache and temporary directory, all beneath the test
workspace in `.tools/tmp/`. They inherit no agent credentials, Git helpers or
user configuration. Local installs need no login; the separate cross-model
development review still requires an authenticated reviewer.

Because the source is the committed tree, commit distribution changes before
running the round trips. The live manifest validation also checks the working
tree. Round trips deliberately do not install uncommitted files.

## Upstream references

- [Claude Code plugin manifest](https://code.claude.com/docs/en/plugins-reference)
- [Claude Code marketplaces](https://code.claude.com/docs/en/plugin-marketplaces)
- [skills installer](https://github.com/vercel-labs/skills)

Behavior is checked against the pinned CLI versions rather than inferred from
the latest documentation.
