# Commands

Every command goes through `just`. Run `just` on its own to list the recipes.

| Recipe | What it does |
| --- | --- |
| `initialize` | The first-run setup: checks the just version, runs `sync`, then `install-hooks` in the primary checkout only (skipped, with a warning, when `core.hooksPath` is set). It never relocks, reformats, stages, commits, tags or pushes. |
| `sync` | Runs `lock-check`, then installs the pinned Python into `.tools/python` and exactly what `uv.lock` and `package-lock.json` say. It fails rather than relocking when a lockfile is out of date. |
| `lock` | Rewrites both lockfiles from `pyproject.toml` and `package.json`. Run it after changing a pin, then review and commit the lockfile diff. |
| `lock-check` | Fails when either lockfile disagrees with its manifest. The npm half relocks a temporary copy and compares it with `package-lock.json`. |
| `install-hooks` | Installs a Git pre-commit hook that runs `just pre-commit`, so commits get the project environment. It refuses when `core.hooksPath` is set or a pre-commit hook it did not write is already there. |
| `pre-commit` | What the hook runs: the `lint` hooks over the staged files only. |
| `run <command>` | Runs a one-off command with the project environment, for example `just run uv add --dev <package>`. |
| `format` | Copies each plugin manifest's version and description into its marketplace entry, then applies ruff, markdownlint and Prettier fixes. This is the only recipe that rewrites source files. It leaves the tickets in `.scratch/` alone. |
| `lint` | Runs every pre-commit hook over every file that is not gitignored, untracked ones included: ruff lint and format check, markdownlint, Prettier and the builtin file checks. prek's `SKIP` and `PREK_SKIP` are ignored here. |
| `typecheck` | Runs mypy in strict mode over `src/` and `tests/`. |
| `test` | Runs pytest, records JUnit results (including installation modes) in `ai_tmp/pytest.xml`, and shows captured output from passing tests in the CI log. |
| `validate-skills` | Validates every shipped skill and dev skill against the [validator rules](skill-validator.md). Errors fail; warnings pass. |
| `new-skill <name>` | Scaffolds a shipped skill: `skills/<name>/` with `SKILL.md`, `agents/openai.yaml` and `.claude-plugin/plugin.json`, starter [placeholder cases](evals.md#placeholder-cases) in `evals/<name>/evals.json`, and a marketplace entry. It refuses an invalid name, or one already used in `skills/`, `evals/`, `dev-skills/build/` or the marketplace, and then writes nothing. See [CONTRIBUTING.md](../../CONTRIBUTING.md). |
| `validate-evals` | Validates every `evals/*/evals.json` against the [eval case schema](evals.md#case-schema), and warns about a distributed skill that still has placeholder cases. It calls no agent. |
| `eval <skill> --agent claude\|codex` | Runs a skill's eval cases against the pinned agent and writes `eval-results/<run-id>/results.json`. It needs `CLAUDE_CODE_OAUTH_TOKEN` (Claude Code) or a Codex login in the project's `CODEX_HOME` (Codex), and calls a paid model, so it is never part of `check`. Takes `--case`, `--model`, `--timeout`, `--trials`, `--baseline`, `--no-grader` and `--dry-run`. See [evals](evals.md). |
| `eval-record <name> <run-id>...` | Records finished runs, one per agent, as the named iteration `benchmarks/<skill>/<name>.json`, which is committed. It refuses an existing name and runs that measured different skills, skill versions or case files. See [evals](evals.md#history-and-report). |
| `eval-report [skill]` | Builds `eval-results/report.html` from the recorded iterations, offline, and prints any regressions. Runs you have not recorded appear only when passed with `--run`. Takes `--run`, `--threshold`, `--fail-on-regression`, `--out` and `--markdown`. See [evals](evals.md#history-and-report). |
| `eval-changed [--base REF]` | Prints the skills with evals changed since the merge base with `origin/main`. Calls no agent. See [live evals in CI](../how-to/live-evals-in-ci.md). |
| `eval-ci plan\|runs\|scan …` | The helpers `.github/workflows/live-evals.yml` runs around `eval` and `eval-report`. See [live evals in CI](../how-to/live-evals-in-ci.md). |
| `validate-distribution` | Checks marketplace sources and versions, requires committed install sources, then runs pinned Claude Code's strict validation on the marketplace and each shipped plugin. See [distribution](distribution.md). |
| `agents-version` | Prints the version of each pinned agent CLI (Claude Code and Codex), run from `node_modules/.bin` with isolated homes under `.tools/agent-homes/`. |
| `just-version` | Fails unless the running just is the pinned version. |
| `check` | The full gate, which CI also runs: `just-version`, `lock-check`, `lint`, `typecheck`, `validate-distribution`, `test` (including credential-free install round trips and the eval harness against a local fake API), `validate-skills`, `validate-evals`, then `agents-version`. It stops at the first failure. |
