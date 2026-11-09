# Each shipped skill is its own plugin; dev skills stay behind discovery symlinks

The marketplace points each plugin at `./skills/<name>`. Its plugin manifest
lives inside that shipped skill directory and declares `skills: ["./"]`.
This keeps the cached plugin independent of the repository and excludes dev
skills, evals, tests and tooling configuration without a separate build tree
or a second copy of the skill.

The plugin manifest's version is authoritative. `just format` copies it to the
matching marketplace entry; the read-only gate rejects a mismatch.

Keep the ticket 01 layout: real dev skill folders in `dev-skills/`, with relative
directory symlinks under `.claude/skills/` and `.agents/skills/`. The pinned
`skills@1.7.4` installer skips those symlinks when scanning agent skill
directories. With a shipped skill in `skills/`, its normal discovery does not
fall back to a recursive scan of the entire repo. Listing the unfiltered repo
therefore finds only cowsay; unfiltered installs are checked for all three
agents. No placement change or non-string `metadata.internal` is needed.

The installer can discover dev skills with explicit paths or `--full-depth`.
Those are outside the documented install commands. The round-trip assertion
uses the default whole-repo discovery and must stay strict when the installer
pin changes. Symlinks remain available for Claude Code, Codex and Pi's own
repository discovery; this decision does not change the ticket 01 setup.

Compared with a repo-root plugin, the per-skill root avoids caching repository
files merely because they are adjacent to the selected skill. Compared with
generated release directories, it keeps `npx skills` and the marketplace on
the same source files. This elaborates ADRs 0005 and 0009 without moving the
shipped skills.

The shipped `.claude-plugin/plugin.json` is part of the user-facing plugin,
not repository tooling configuration. Other agents can ignore it. The plugin
root's `agents/` directory is also Claude's subagent location: future authoring
work must keep Codex metadata in YAML and avoid unintentionally adding Claude
subagents through `agents/*.md`.
