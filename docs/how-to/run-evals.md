# Run a skill's evals

This guide runs an existing skill's eval cases on Claude Code and Codex, reads the results and builds the report. It uses `cowsay`; any skill in `evals/` works the same way. Run every command from the repository root. [Evals](../reference/evals.md) describes every option and file.

These runs call paid models. Run `just eval cowsay --agent claude --dry-run` to see what a run would call and its spend cap, and the same with `--agent codex`. It needs no credentials. Codex agent calls have no per-call cap, and the results do not record what a run cost. The `cowsay` cases took one to two minutes per agent when measured.

## 1. Set up the credentials

Finish [Getting started](../tutorials/getting-started.md) first.

Log Codex in. The login is kept in the project's own Codex home, `.tools/agent-homes/codex/`:

```sh
just run ./node_modules/.bin/codex login
just run ./node_modules/.bin/codex login status
```

The second command confirms the login before a paid run.

Create a Claude Code token, if you do not have one. This opens a browser and prints the token:

```sh
just run ./node_modules/.bin/claude setup-token
```

Put the token in your shell's environment. `read -rs` keeps it out of your shell history and off the screen: run the first line, paste the token and press Enter. `just` passes the variable on to the recipe. Both agents need it, because rubric expectations are graded by Claude whichever agent ran.

```sh
read -rs CLAUDE_CODE_OAUTH_TOKEN
export CLAUDE_CODE_OAUTH_TOKEN
```

Run every command below in that shell.

## 2. Run the evals

```sh
just eval cowsay --agent claude
just eval cowsay --agent codex
```

Each prints its plan, then a `PASS` or `FAIL` line per trial, and exits 0 when every trial passed. A failing skill exits 1.

This plain form checks that the skill passes its cases. Add `--baseline` when you need to know what the skill adds over no skill at all, as [Contributing](../../CONTRIBUTING.md) does when a skill changes.

## 3. Read the results

Each run writes `eval-results/<run-id>/`, and its `results.json` and `benchmark.json` are described under [results](../reference/evals.md#results). `ls -t eval-results` lists the newest run first, along with `report.html` once you have built a report. To count the passes of a run after the terminal output has gone:

```sh
just run uv run --frozen python -c 'import json, sys; r = json.load(open(sys.argv[1])); t = [x for x in r["trials"] if x["arm"] == "skill"]; print(r["agent"], sum(x["passed"] is True for x in t), "of", len(t), "trials passed")' eval-results/<run-id>/results.json
```

It prints, for example, `claude 9 of 9 trials passed`. It counts the skill arm, because baseline trials are never judged. The first word is the agent, so this is also how to tell which run is which for the next step.

## 4. Build the report

Plain `just eval-report` shows only the iterations recorded in `benchmarks/`, so it would leave out the runs you just made. Pass each run with `--run`, one per agent:

```sh
just eval-report cowsay --run <claude-run-id> --run <codex-run-id>
```

It writes `eval-results/report.html`. Your runs appear as the last iteration, labelled `unrecorded`. Without `--baseline`, that iteration's deltas read `no baseline`.

Do not run `just eval-record` to look at a result. It writes a file under `benchmarks/` to commit, which belongs to a skill change: see [Contributing](../../CONTRIBUTING.md).
