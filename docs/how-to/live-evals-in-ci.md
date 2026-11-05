# Run live evals in CI

The **Live evals** workflow (`.github/workflows/live-evals.yml`) runs `just eval` and `just eval-report` on a GitHub runner, by hand only. It never runs on a pull request or a push, so fork code never runs with its secrets ([ADR 0004](../adr/0004-eval-tiers-and-ci.md)). Each dispatch uploads the report and the raw results as a workflow artifact, and the job summary shows the agents-by-cases matrix and links the artifact.

## Configure the environment once

The secrets live in a deployment environment named `live-evals`, never in the repository's own secrets.

1. In the repository's **Settings → Environments**, create `live-evals`. The first dispatch creates it too, empty.
2. Protect it. A dispatch runs the code of the branch it is started from, with the secrets, so anyone who can push a branch and dispatch could run their own code with them. Add **required reviewers**, so each dispatch waits for a maintainer to approve it after reading the branch. Restricting **deployment branches** to `main` is stricter, but then only `main` can be dispatched, where `changed` selects nothing: name the skills instead.
3. Add the environment secrets:

| Secret | Used for | Without it |
| --- | --- | --- |
| `CLAUDE_CODE_OAUTH_TOKEN` | Claude Code runs, and the grader for every agent. Create one with `claude setup-token`. | Claude Code runs are skipped. Codex runs go ahead with grading skipped: cases with expectations are scored on their deterministic assertions only, and the graded and outcome pass rates read `no data`. |
| `OPENAI_API_KEY` | Codex runs. The job logs Codex in with `codex login --with-api-key`, into the project's `CODEX_HOME`. | Codex runs are skipped. |

Each skip is a notice in the job summary, not a failure. With neither secret the job succeeds and runs nothing.

## Dispatch a run

From the **Actions** tab, choose **Live evals**, then **Run workflow**, or from a terminal:

```sh
gh workflow run live-evals.yml --ref <branch> -f skills=changed -f agents=both -f trials=1 -f baseline=false
```

GitHub lists and dispatches the workflow only once it is on the default branch; `--ref` then picks the branch whose code runs. One dispatch runs at a time. A second waits, and a third replaces the second while it is still waiting.

| Input | Values | Default |
| --- | --- | --- |
| `skills` | A skill with `evals/<skill>/evals.json`, or `changed` | `changed` |
| `agents` | `both`, `claude` or `codex` | `both` |
| `trials` | Trials per case per arm, a whole number from 1 to 5 (`MAX_TRIALS` in `src/skills_tooling/evals/dispatch.py`) | `1` |
| `baseline` | Also run each case with an outcome to measure with no skill installed | `false` |

The inputs reach the shell only as environment variables, and `just eval-ci plan` validates them before anything runs. An invalid input fails the job at the **Plan** step, with nothing run.

`changed` selects the skills changed since the merge base of the dispatched commit with `origin/main`, the same rules as `just eval-changed` locally:

- A change under `skills/<skill>/` or `evals/<skill>/` selects that skill.
- A change to the shared eval code (`src/skills_tooling/evals/`, which holds the adapters and the grader), to the pinned agent CLIs or Node (`package.json`, `package-lock.json`, `.node-version`), or to the Python toolchain or the Justfile (`pyproject.toml`, `uv.lock`, `.python-version`, `Justfile`) selects every skill.
- A file moved out of a skill selects that skill too.
- Only skills with an eval suite are selected; a deleted one is not. When nothing is selected the summary says so and nothing runs. Dispatched on `main` itself, `changed` selects nothing.

## What the job does

1. Sets up the toolchain exactly as `ci.yml` does, then runs `just initialize`.
2. Plans the runs (`just eval-ci plan`): each selected skill on each agent whose secret is set. The summary lists them, and every skip.
3. Runs `just eval <skill> --agent <agent> --trials <n> [--baseline] [--no-grader]` for each, as a developer would. Every run goes ahead even when one fails, and the summary lists each exit code. The runs share a 90-minute step timeout inside the job's 120, so a dispatch that runs long still reports, scans and uploads what finished.
4. Runs `just eval-report <skill> --run <run-id>...` for each skill, which adds this dispatch's runs to the recorded history in `benchmarks/` as an unrecorded iteration, and appends the matrix and any regressions to the summary.
5. Scans `eval-results/` for secret values (below). On a hit the job fails and nothing is uploaded.
6. Uploads `eval-results/` as the artifact `live-evals-<run id>-<attempt>`, kept 30 days, and links it from the summary. The trial workspaces in `.eval-workspaces/` are never uploaded.
7. Fails the job if any `just eval` exited nonzero.

CI never records results to `benchmarks/`. To keep a dispatch's runs as an iteration, download the artifact into `eval-results/` and run `just eval-record <name> <run-id>...` locally.

## The secret scan

Every file `just eval` writes is already scrubbed of the run's credentials, and rechecked. Before upload, `just eval-ci scan eval-results` rereads every file's contents and path for:

- the values of the environment variables in `SCANNED_ENV` (`src/skills_tooling/evals/dispatch.py`): `CLAUDE_CODE_OAUTH_TOKEN` and `OPENAI_API_KEY`
- the secret fields of the Codex login, `$CODEX_HOME/auth.json`

It also fails on any symlink, because the upload would follow it. It prints only the names of the files that match, scrubbed, never a value, and exits 1. To scan for another secret, add its variable to `SCANNED_ENV` and to the **Scan** step's `env`.

## Cost

Print the spend cap of one agent's run before dispatching:

```sh
just eval cowsay --agent claude --dry-run
```

Claude Code's runs and the grader are capped per call by `--max-budget-usd`; Codex's runs have no per-call cap. For cowsay at one trial, without a baseline, the cap is $11.00 for Claude Code (nine agent calls and two grader calls) and $2.00 of grading for Codex plus its own nine calls. Real spend is usually well under the cap. The cost grows linearly with `trials`, the baseline adds a run of each case that has an outcome to measure, and `both` runs every skill twice. At the maximum of five trials with a baseline, the same cowsay dispatch is about seven times the one-trial figure.

The runner minutes add to this. In ticket 09 the two cowsay runs, one trial each with grading, started about nine minutes apart, and setup takes a few minutes more. The runs stop at 90 minutes, so the largest dispatches (five trials, a baseline, both agents, several skills) need splitting: one agent or one skill per dispatch.

## Locally

The same helpers run on a laptop:

```sh
just eval-changed                       # the skills `changed` would select
just eval-ci plan --skills changed --agents both --trials 1 --baseline false \
  --has-claude false --has-openai false --out eval-results/dispatch
just eval-ci scan eval-results          # with the secrets in the environment
```
