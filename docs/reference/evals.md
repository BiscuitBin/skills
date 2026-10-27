# Evals

The eval harness runs a skill's eval cases against a pinned agent CLI, headless, and writes a results file. This page covers the case schema, the adapter interface, isolation, credentials, the contamination check and the results format. [Eval isolation](../explanation/eval-isolation.md) explains why isolation is built this way and what it does not cover.

## Commands

| Command | What it does |
| --- | --- |
| `just validate-evals` | Validates every `evals/*/evals.json` against the schema below. It calls no agent and is part of `just check`. |
| `just eval <skill> --agent claude` | Runs every case of `evals/<skill>/evals.json` against the pinned Claude Code. |
| `… --case <id>` | Runs only that case. Repeat it to run several. An unknown id is a usage error. |
| `… --model <id>` | Overrides the pinned default model, `claude-sonnet-5-5`. |
| `… --timeout <seconds>` | Per-trial timeout, default 300. |

**Live evals need an authenticated agent and are never part of the PR gate.** `just eval` calls a paid model, so it runs only locally or from a manual job that holds the secret ([ADR 0004](../adr/0004-eval-tiers-and-ci.md)). `just check` and PR CI cover the harness without credentials: the tests drive the real pinned CLI against a local fake Anthropic API (`tests/evals/fake_anthropic.py`) and parse recorded transcripts (`tests/fixtures/evals/claude/`).

Exit codes: 0 when every trial passed, 1 when any trial failed or hit an infrastructure error, 2 for a usage error (a missing token, an invalid suite, an unknown case, a missing pinned CLI). Nothing is written on a usage error. A harness failure inside one trial is recorded as that trial's infrastructure error, and the other trials still run.

## Case schema

Cases live at `evals/<skill>/evals.json`, outside the shipped skill's directory, so distribution can never ship them ([ADR 0011](../adr/0011-eval-case-location-and-isolation.md)). The format extends skill-creator's `evals.json`.

```json
{
  "skill_name": "cowsay",
  "evals": [
    { "id": "no-trigger-cow-facts", "kind": "trigger", "prompt": "Tell me three facts about cows.", "should_trigger": false },
    {
      "id": "behaviour-ship-it",
      "kind": "behaviour",
      "prompt": "Have a cow say: Ship it, team!",
      "should_trigger": true,
      "expected_output": "The bundled script's cow, shown verbatim.",
      "files": [],
      "assertions": [
        { "type": "skill_triggered" },
        { "type": "script_ran", "script": "scripts/cowsay.py", "args": ["--", "Ship it, team!"] },
        { "type": "final_contains_script_output", "script": "scripts/cowsay.py", "args": ["--", "Ship it, team!"] },
        { "type": "output_contains", "value": "(oo)" },
        { "type": "output_matches", "pattern": "<\\s*Ship it, team!\\s*>" }
      ]
    }
  ]
}
```

| Field | Rule |
| --- | --- |
| `skill_name` | Must equal the directory name, and `skills/<name>/SKILL.md` must exist. |
| `evals` | A nonempty list of cases. |
| `id` | Unique in the suite, a lowercase slug (`[a-z0-9][a-z0-9-]*`). |
| `kind` | `trigger` (only the trigger outcome is scored) or `behaviour` (assertions are scored too). |
| `prompt` | The nonempty prompt, passed to the agent as an argument. It is never written into the workspace. |
| `should_trigger` | Required on every case. The trial's trigger outcome must match it. A `behaviour` case needs `true`. |
| `expected_output` | Optional human description, kept from skill-creator. It is not graded. |
| `files` | Input files are not staged yet: anything but an empty list is rejected with a note that staging is deferred. |
| `assertions` | Deterministic assertions, below. A `behaviour` case needs at least one. |

Unknown keys are rejected at every level, so a later field, such as rubric `expectations`, has to be added on purpose.

### Assertions

| Type | Fields | Passes when |
| --- | --- | --- |
| `skill_triggered` | none | The trace records a trigger of the skill under test. |
| `script_ran` | `script`, optional `args` | All three hold, so a command that merely names the script cannot pass. (1) A Bash command, split into simple commands on `;`, `&&`, `\|\|`, `\|`, `&` and newlines, runs `python`, `python3` or `python3.N` with `script` as its first non-option argument. A path inside `printf`, `echo`, `cat`, a comment, `sh -c '…'` or after `-c`/`-m` does not count. (2) That call's tool result, which the CLI writes, is not an error and contains the script's output for `args` as whole lines (with no `args`, it is nonempty). (3) The trial's `python3` wrapper logged a call of the installed copy, with `args` or with no arguments (text on stdin). |
| `final_contains_script_output` | `script`, `args` | The harness runs the shipped script itself (`python -I`, outside the workspace, stdin `/dev/null`, at most 30 seconds) and its output, minus the final newline, appears in the final message as a run of whole, unaltered lines. A trailing `\r` per line is ignored; nothing else is. |
| `output_contains` | `value` | The final message contains `value`. |
| `output_matches` | `pattern` | Python `re.search(pattern, final_message)` matches. The schema rejects a pattern that does not compile. |

`script` must be a file inside the skill directory.

## Adapter interface

An adapter drives one agent CLI. The interface is `skills_tooling.evals.adapter.Adapter`, a `Protocol`. Codex (ticket 06) and Pi (ticket 07) implement the same interface.

| Member | Purpose |
| --- | --- |
| `name`, `default_model` | The agent's name in results, and the pinned model used without `--model`. |
| `credential_env` | The environment variables that carry the credential. Their values reach only the child process. |
| `home_env`, `skills_dir` | The variables that move the agent's home (each must point inside the trial), and where a skill is installed relative to the workspace. |
| `reports_skills` | Whether the agent reports the skills and plugins it loaded. When it does, a missing report fails closed. When it does not, the contamination proof rests on the preflight and the canary sweep. |
| `builtin_skills`, `builtin_plugins` | The recorded allowlists of skills and plugins built into the pinned CLI, keyed by CLI version. |
| `discovery_locations(trial)` | Every location the research notes list for the agent, each with its mitigations (`redirected`, `suppressed`, `reported`, `controlled`, `not-a-location`) and the canary test that covers it. A location with no mitigation fails the preflight. |
| `context_isolation(env)` | Problems that would let instruction files load. Empty when isolated. |
| `prepare_homes(trial)` | Creates the isolated agent home and user home and returns the child's whole environment, built from scratch. |
| `install_skill(skill_dir, workspace)` | Copies the skill into the workspace, or installs nothing for a baseline (`None`). |
| `run(prompt, trial, homes, *, model, timeout, credentials)` | Runs the prompt headless and returns a `RawRun`: exit code, timeout flag, transcript path, stderr, the kept discovery lines, the `python3` calls, and whether any process survived teardown. |
| `discovery_report_problems(trace, trial, *, installed, system_root)` | Problems in the agent's own report of where it looked for skills. Claude Code reads its debug log; an agent with no such report returns none. |
| `parse(raw)` | Normalises the event stream into a `Trace`: skills triggered and invoked, commands run with their output and status, the final message, CLI version, model, exit code, whether the stream ended normally, the run status and its reason, and the skills, plugins and commands the agent reported. |

`visible_skills` is `None` for an agent that does not report its skills. For such an agent (`reports_skills` false), the contamination proof rests on the redirected homes, the preflight's mitigated discovery locations and the canary sweep, and the results note it.

### Claude Code

- **Command:** `node_modules/.bin/claude -p <prompt> --output-format stream-json --verbose --model <model> --no-session-persistence --strict-mcp-config --permission-mode dontAsk --max-budget-usd 1.00 --debug-file <trial>/tmp/debug.log --allowedTools Skill Read Bash`. Stdin is `/dev/null`. `--bare` is not used because it accepts only an API key, and `--safe-mode` is not used because it disables skills.
- **Environment:** built from scratch. `HOME`, `CLAUDE_CONFIG_DIR` (`<home>/.claude`), the four `XDG_*` directories and `TMPDIR` point inside the trial. `PATH` is `<trial>/bin:/usr/bin:/bin`. `CLAUDE_CODE_DISABLE_CLAUDE_MDS`, `CLAUDE_CODE_DISABLE_POLICY_SKILLS`, `CLAUDE_CODE_SUBPROCESS_ENV_SCRUB`, `DISABLE_AUTOUPDATER`, `CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC` and `DISABLE_TELEMETRY` are all `1`. The Justfile's shared `CLAUDE_CONFIG_DIR` never reaches the child.
- **Trigger rule:** an assistant `tool_use` named `Skill` whose `input.skill` is `<name>` or `<plugin>:<name>`, and whose matching `tool_result` is not `is_error`.
- **Run status:** `infra_error` when the run timed out, a process survived teardown, the last event is not a `result` or a line did not parse, the `result` has `is_error: true`, or the exit code is nonzero. A failed login reports `subtype: "success"` with `is_error: true`, so `subtype` is never used. `apiKeySource` is `none` under OAuth too, so it is never used either.
- **Built-in allowlist (2.1.309):** `batch claude-api code-review dataviz debug deep-research doctor fewer-permission-prompts loop plugin-authoring run run-skill-generator schedule simplify update-config verify workflow-authoring`. The plugins are `cc-plugin-agents-md@builtin` and `cc-plugin-plugin-authoring@builtin`. `schedule` is listed only when an OAuth token is set. A new CLI version fails the check with a hint to re-record the allowlist from the canary sweep.

## Credentials

| Agent | Credential | How it reaches the run |
| --- | --- | --- |
| Claude Code | `CLAUDE_CODE_OAUTH_TOKEN`, from `claude setup-token` | Read from the caller's environment and placed only in the child's environment. The harness writes it nowhere. The pinned CLI does not pass it on to its Bash tool's processes. |

The harness refuses to start without the token. Every file it writes under `eval-results/` passes through a scrub that replaces each credential value with `[REDACTED]`. The run then rereads every file, and deletes any that still holds a value and fails. After each trial, in a `finally`, the process group is killed and checked empty, and the trial's `home/`, `tmp/` and `bin/` are removed. The workspace is kept for inspection unless it holds a credential value, in which case it is deleted too. `results.json` records the credential's variable name, never its value. Codex's `auth.json` and Pi's auth file belong in the per-trial agent home, which the same `finally` removes (tickets 06 and 07).

## Isolation

Each trial gets `.eval-workspaces/<run-id>/<case-id>/` with:

- `workspace/`, a fresh `git init` (no global or system Git config) that is its own git root, gitignored, and outside `skills/` and `dev-skills/`. It holds `.git/` and the installed skill, nothing else.
- `home/`, the user home and the agent home.
- `tmp/`, the agent's temporary directory, transcript and debug log.
- `bin/`, holding `python3` and `python`, wrappers that log each call and run the harness's pinned interpreter, and `git`.

The preflight checks all of this before the agent starts, and fails closed.

## Contamination check

Each trial passes only when all of these hold:

1. **Reported skills.** The init event's skills, plus any command a `system/commands_changed` event adds, plus every successful `Skill` call, minus the recorded built-ins, is exactly the skill under test (empty for a baseline). The init event's plugins equal the built-in plugins, and a missing skill or plugin report fails closed.
2. **Discovery report.** In the debug log, the `user=` location sits inside the trial home, every `project=` location inside the workspace, and the managed location is missing or empty. The per-location counts are `managed: 0, user: 0, additional: 0` and `project: 1` (0 for a baseline). A missing report fails closed. Only these lines are kept, and the debug log is deleted.
3. **Never-appear list.** The repo's dev skills, the other shipped skills, and the user's own skills (directory names under `~/.claude/skills`, `~/.agents/skills`, `~/.codex/skills`, `~/.pi/agent/skills` and the caller's agent homes) must not appear among the reported skills. The discovery report is checked by location instead (step 2), so any skill directory outside the trial fails there. A name that collides with a built-in is noted, not failed. The repo's `AGENTS.md`, `CLAUDE.md` and the user's `~/.claude/CLAUDE.md` are listed too. They are kept out by the preflight's instruction-file check, because a live run cannot observe the request.

The canary sweep (`tests/evals/test_contamination_canaries.py`) shows the check fails when a canary sits in each location the agent reads, and that every other location stays isolated. The managed-location canary runs only in CI, because it writes to `/etc/claude-code`.

## Results

`eval-results/<run-id>/results.json`, with each trial's transcript at `eval-results/<run-id>/transcripts/<case-id>.jsonl`, scrubbed.

| Run field | Meaning |
| --- | --- |
| `run_id`, `skill`, `agent`, `requested_model` | What ran. |
| `credential_env` | The credential's variable names. |
| `started_at`, `finished_at` | UTC, ISO 8601. |
| `passed` | Every trial passed. |
| `trials` | One record per case, below. |

| Trial field | Meaning |
| --- | --- |
| `case`, `kind`, `agent` | The case and the agent. |
| `cli_version`, `model` | From the agent's init event. `model` is what the agent ran, so a `--model` alias shows the model it resolved to. |
| `started_at`, `finished_at` | UTC, ISO 8601. |
| `status`, `status_reason` | `ok` or `infra_error`, with the reason. |
| `trigger` | `expected`, `actual`, `matched`. `actual` and `matched` are `null` on an infrastructure error. |
| `contamination` | `passed`, `problems`, `notes`. |
| `assertions` | Each `type`, `result` (`passed`, `failed` or `not_scored`) and `evidence`. Every assertion is `not_scored` on an infrastructure error, so a crash can never pass a should-not-trigger case. |
| `transcript` | The scrubbed transcript, relative to the repo root. |
| `stderr` | The last 2000 characters of the agent's stderr, scrubbed. |
| `passed` | `status` is `ok`, contamination passed, the trigger matched and every assertion passed. |
