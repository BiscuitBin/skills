# Contributing a skill

This guide takes a new shipped skill from scaffold to a merged pull request. It assumes you have finished [Getting started](docs/tutorials/getting-started.md). For a first walk through the same loop with a scratch skill, follow the [first skill tutorial](docs/tutorials/first-skill.md).

Every command goes through `just` and runs from the repository root. [AGENTS.md](AGENTS.md) has the repository's ground rules, and the [commands reference](docs/reference/commands.md) lists every recipe.

## 1. Scaffold

Work on a branch, then scaffold the skill:

```sh
just new-skill <name>
```

The name follows the Agent Skills rule: 1 to 64 lowercase letters, digits and single inner hyphens. The command refuses a name that breaks the rule or that `skills/`, `evals/`, `dev-skills/build/` or the marketplace already uses, and writes nothing when it refuses. Otherwise it writes:

| File | What it is |
| --- | --- |
| `skills/<name>/SKILL.md` | The skill: spec-valid frontmatter and a stub body. |
| `skills/<name>/agents/openai.yaml` | Codex UI metadata: a display name and a short description. |
| `skills/<name>/.claude-plugin/plugin.json` | The skill's Claude Code plugin manifest, at version `0.1.0`. |
| `evals/<name>/evals.json` | Starter trigger and behaviour cases, each marked `"placeholder": true`. |
| `.claude-plugin/marketplace.json` | A new entry for the plugin. |

The scaffold passes every check, but it is not a skill yet. Everything you still have to write is marked `TODO(new-skill)`, and the checks keep pointing at it:

- `just validate-skills` warns `[placeholder]` for every skill file that still holds `TODO(new-skill)`.
- `just eval` refuses placeholder cases. It lists each one as `UNWRITTEN <skill>/<case>` and exits 2 before calling any agent.
- `just validate-evals`, and so `just check`, warns when a skill in the marketplace still has placeholder cases, naming the skill.

If you create a skill by hand instead, `just check` fails until the marketplace lists it, and the message gives the exact entry to add.

## 2. Write the evals first (RED)

A skill earns its place by changing what an agent does. Prove the gap before you write the skill:

1. Write the eval cases in `evals/<name>/evals.json`: trigger cases for requests that should and should not load the skill, and behaviour cases whose assertions check the outcome. Delete `"placeholder": true` from each case you write. The [case schema](docs/reference/evals.md#case-schema) lists every field.
2. Run `just validate-evals`.
3. Run a baseline, which runs each outcome case a second time with no skill installed:

   ```sh
   just eval <name> --agent codex --baseline
   ```

   Run it on `--agent claude` too, which needs `CLAUDE_CODE_OAUTH_TOKEN`; Codex needs a login in the project's Codex home (`just run ./node_modules/.bin/codex login`). Rubric `expectations` are graded by Claude, so a case with expectations needs the Claude token on either agent. See [credentials](docs/reference/evals.md#credentials).

The baseline arm should fail the behaviour cases. If it passes them, the agent already does the job without your skill: change the cases to measure what it gets wrong, or drop the skill.

## 3. Write the skill and close the gaps (GREEN)

1. Write `SKILL.md`. The `description` decides when an agent loads the skill, so say what it does, when to use it and when not to. Replace the `TODO(new-skill)` text in `agents/openai.yaml` and in the `description` of `plugin.json`, then run `just format`, which copies the plugin's version and description into the marketplace.
2. Run `just validate-skills` until it reports no errors and no `[placeholder]` warnings for the skill. The [validator reference](docs/reference/skill-validator.md) explains each rule.
3. Rerun the eval on each agent, with `--baseline`. A failing case is a gap in the skill: a missed or wrong trigger is usually the description, a failed behaviour case is usually the instructions. Fix the skill, not the case, unless the case is wrong.
4. When the skill passes on each agent, record the runs, one per agent, as a benchmark iteration, and commit the file it writes:

   ```sh
   just eval-record <iteration-name> <claude-run-id> <codex-run-id>
   ```

   The run ids are the directory names under `eval-results/`. `just eval-report <name>` builds the report. See [history and report](docs/reference/evals.md#history-and-report).

Live evals call paid models, so they never run in `just check` or PR CI ([ADR 0004](docs/adr/0004-eval-tiers-and-ci.md)). The recorded benchmark is how a reviewer sees the result.

## 4. Run the gate

Commit the skill, its evals, the marketplace and the benchmark, then run:

```sh
just check
```

The install tests install from the committed tree, so `just check` fails on uncommitted changes under `skills/` or `.claude-plugin/`. The `npx skills` round trips install every shipped skill, yours included; the marketplace round trip installs cowsay, and `claude plugin validate --strict` checks every shipped plugin.

## 5. Get a cross-model review

Before you open the pull request, and at every ticket's review checkpoint, get an adversarial review from a different model family. Follow the [cross-model review dev skill](dev-skills/build/cross-model-review/SKILL.md), which AGENTS.md makes the rule:

1. Pick the reviewer by the cross-model rule: Codex reviews work by Claude models, Claude Code reviews work by OpenAI models. If no reviewer from another family is available, stop and say so; never review your own work instead.
2. A reviewer subagent runs the read-only review and saves its findings to `ai_tmp/`.
3. A separate triage subagent marks each finding valid, invalid or out of scope, with evidence from the code.
4. Apply the valid fixes, rerun `just check`, and record the reviewer, model, reviewed commit and every finding's verdict and action under **Completion notes** in the ticket.

The reviewer needs its own login: Codex in the project's Codex home, or `CLAUDE_CODE_OAUTH_TOKEN` for Claude Code.

## Versions

Each shipped skill has one version: `version` in `skills/<name>/.claude-plugin/plugin.json`. The marketplace entry carries a copy, which `just format` writes and `just check` keeps equal ([ADR 0010](docs/adr/0010-distribution-boundaries.md)).

Bump the version in every pull request that changes a shipped skill's files. Claude Code finds plugin updates by comparing versions, so a change merged without a bump never reaches people who installed the plugin from the marketplace ([Claude Code: release a new version](https://code.claude.com/docs/en/plugins/host-marketplace#release-a-new-version)). Use [semantic versioning](https://semver.org/): a patch for a fix, a minor version for new behaviour, a major version when the skill stops doing something users relied on.

To bump it:

1. Change `version` in the skill's `plugin.json`.
2. Run `just format`.
3. Commit `plugin.json` and `.claude-plugin/marketplace.json` together.

The Python tooling's version in `pyproject.toml` and the npm package's version in `package.json` are separate, and a skill change does not bump them.

## Dependency updates

Renovate opens a pull request for each pin bump on Monday mornings, once the release is at least 7 days old, and never merges one itself ([ADR 0016](docs/adr/0016-dependency-updates-via-renovate.md)). To review one:

1. Wait for CI to pass on both Ubuntu and macOS. A bump that misses a copy of its pin fails there, at `required-version`, `just-version`, `engine-strict` or `npm ci`.
2. Read the release notes the PR links, then merge or close it.
3. For a PR labelled `agent-cli`, work through the checklist in its body before you approve it.

Renovate relocks `uv.lock` and `package-lock.json` itself. uv resolves only releases at least 7 days old (`exclude-newer` in `pyproject.toml`), so `uv add` cannot pick a newer one either. When you change a pin by hand, run `just lock` and commit the manifest and its lockfile together. If you reword a README row, workflow step or Justfile line that holds a pin, keep `renovate.json`'s regex managers matching it; `tests/test_renovate.py` fails until they do.

## Releases

There is no release recipe and no tag. A release is a version bump merged to `main`:

1. Bump the version as above, in the pull request that changes the skill.
2. Pass `just check` and the cross-model review.
3. Merge the pull request to `main`.

Once it is on `main`, users get it the next time they install or update. Claude Code users who installed from the marketplace get it through marketplace auto-update, when they have turned it on, or by running `claude plugin update <name>@biscuitbin-skills`. `npx skills` installs whatever the default branch, `main`, holds when it runs.
