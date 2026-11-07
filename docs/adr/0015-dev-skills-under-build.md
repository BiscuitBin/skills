# Real dev skill folders live under dev-skills/build/

Real dev skill folders live at `dev-skills/build/<name>/`, with the same relative discovery symlinks under `.claude/skills/` and `.agents/skills/`. The pinned `skills@1.7.4` installer runs a recursive scan of the whole repository when it is given `--full-depth` or finds no shipped skills, and at `dev-skills/<name>/` that scan listed and installed the dev skill. It skips a fixed list of directory names, including `build`, and does not follow the symlinks, so the new placement keeps dev skills out of every listing and install that names no skill.

This supersedes the paragraphs of [ADR 0010](0010-distribution-boundaries.md) that keep the ticket 01 layout and put `--full-depth` outside the assertion, and the part of [ADR 0009](0009-flat-shipped-skills-layout.md) that places dev skills at `dev-skills/<name>/`. The validator now checks the direct child directories of `skills/` and `dev-skills/build/`. The rest of both records stands.

The guarantee covers unnamed discovery: the default, `--full-depth` and a repository with no shipped skills. An explicit path to a dev skill, such as `skills add <repo>/dev-skills/build/<name>`, can still reach it.

The name `build` does not mean generated output. The folder is tracked and nothing writes to it. It is there only because the installer skips that name.

The skipped names are an installer internal, not a documented contract. `tests/test_distribution.py` lists with and without `--full-depth`, installs with `--full-depth`, and lists a clone with no shipped skills, so a new pin that stops skipping `build` fails the round trips.

## Considered options

- **`dev-skills/dist/`.** Rejected: `dist` is also skipped, but `.gitignore` ignores it.
- **`metadata.internal: true`.** The installer drops such a skill before listing or installing it, even by explicit path, but the flag must be the boolean `true`, and the validator and ADR 0010 keep `metadata` values as strings, as the Agent Skills spec requires. Rejected: it would need an exception to the spec for dev skills.
- **Accept the leak and document `--full-depth` as out of contract.** Rejected: dev skills must be excluded from `npx skills`, and that flag names no skill.
