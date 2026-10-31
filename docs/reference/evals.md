# Evals

The eval harness runs a skill's eval cases against a pinned agent CLI, headless, in several trials and optionally against a baseline, grades rubric expectations with an LLM, and writes a results file and a benchmark. This page covers the case schema, the adapter interface, isolation, credentials, the contamination check, the grader, the benchmark and the results format. [Eval isolation](../explanation/eval-isolation.md) explains why isolation is built this way and what it does not cover.

## Commands

| Command | What it does |
| --- | --- |
| `just validate-evals` | Validates every `evals/*/evals.json` against the schema below. It calls no agent and is part of `just check`. |
| `just eval <skill> --agent claude` | Runs every case of `evals/<skill>/evals.json` against the pinned Claude Code. |
| `just eval <skill> --agent codex` | Runs the same cases against the pinned Codex. |
| `… --case <id>` | Runs only that case. Repeat it to run several. An unknown id is a usage error. |
| `… --model <id>` | Overrides the pinned default model: `claude-sonnet-5-5` for Claude Code, `gpt-5.6-terra` for Codex. |
| `… --timeout <seconds>` | Per-trial timeout, default 300. |
| `… --trials <n>` | Runs every selected case n times per arm, default 1. |
| `… --baseline` | Also runs, n times, every selected case that has an outcome to measure, with no skill installed (the baseline arm). Trigger-only cases are skipped in the baseline and listed. |
| `… --grader-model <id>` | The grader's model, default `claude-opus-5-5`. |
| `… --dry-run` | Prints the plan and exits 0: agent calls per arm, the cases skipped in the baseline, the most grader calls the run can make, and the spend cap. It reads no credential, creates no workspace and writes nothing. A real run prints the same plan first. |

**Live evals need an authenticated agent and are never part of the PR gate.** `just eval` calls a paid model, so it runs only locally or from a manual job that holds the secret ([ADR 0004](../adr/0004-eval-tiers-and-ci.md)). `just check` and PR CI cover the harness without credentials: the tests drive the real pinned CLIs against local fake APIs (`tests/evals/fake_anthropic.py`, `tests/evals/fake_openai.py`) and parse recorded transcripts (`tests/fixtures/evals/claude/`, `tests/fixtures/evals/codex/`).

Exit codes: 0 when every skill-arm trial passed and every baseline trial is valid, 1 otherwise (a failed trial, an infrastructure error, contamination, a grading that is not `ok` in the skill arm, or a grader error in the baseline), 2 for a usage error (a missing credential, an invalid suite, an unknown case, a missing pinned CLI). Nothing is written on a usage error. A harness failure inside one trial is recorded as that trial's infrastructure error, and the other trials still run.

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
      ],
      "expectations": [
        "The speech bubble contains the text 'Ship it, team!' exactly.",
        { "text": "The agent ran a command before answering.", "needs_transcript": true }
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
| `expectations` | Optional rubric for the [grader](#grader), on `behaviour` cases only (skill-creator's field). Each item is a string, judged blinded, or `{"text": …, "needs_transcript": true}`, judged from the trace too and marked unblinded. Text must be nonempty and unique within the case; `needs_transcript: false` is rejected (use the string form). |

Unknown keys are rejected at every level, so a later field has to be added on purpose.

An expectation describes the outcome the user asked for, never how it was produced: "the bubble contains the text verbatim", not "the bundled script was run" (that is `script_ran`). It must be passable by quoting the material, so negative expectations ("does not mention X") are not allowed. Freeze a rubric before a live run, and never edit it after seeing the delta. An assertion's `args`, when present, must be a list of strings: `null` is rejected, and `[]` means no arguments.

### Assertions

Each type is a **skill-use** assertion (`skill_triggered`, `script_ran`), which the baseline arm never scores (`not_applicable`), or an **outcome** assertion (the rest), scored in both arms. `final_contains_script_output` runs the repo's copy of the script, so it needs nothing installed.

| Type | Fields | Passes when |
| --- | --- | --- |
| `skill_triggered` | none | The trace records a trigger of the skill under test. |
| `script_ran` | `script`, optional `args` | All three hold, so a command that merely names the script cannot pass. (1) A Bash command, split into simple commands on `;`, `&&`, `\|\|`, `\|`, `&` and newlines, runs `python`, `python3` or `python3.N` with `script` as its first non-option argument, matched on trailing path parts so `cd scripts && python3 cowsay.py` counts. A path inside `printf`, `echo`, `cat`, a comment or `sh -c '…'` does not count, and neither does a path after an option that runs no script: `-c` or `-m` (attached or clustered, as in `-Ic'…'`), `-`, `-h`, `-V`, `--help`, `--version` or any option the parser does not know. (2) That call's tool result, which the CLI writes, is not an error and contains the script's output for `args` as whole lines (with no `args`, it is nonempty). (3) The trial's `python3` wrapper logged a call of the installed copy, with `args` or with no arguments (text on stdin). |
| `final_contains_script_output` | `script`, `args` | The harness runs the shipped script itself (`python -I`, outside the workspace, stdin `/dev/null`, at most 30 seconds) and its output, minus the final newline, appears in the final message as a run of whole, unaltered lines. A trailing `\r` per line is ignored; nothing else is. |
| `output_contains` | `value` | The final message contains `value`. |
| `output_matches` | `pattern` | Python `re.search(pattern, final_message)` matches. The schema rejects a pattern that does not compile. |

`script` must be a file inside the skill directory.

## Adapter interface

An adapter drives one agent CLI. The interface is `skills_tooling.evals.adapter.Adapter`, a `Protocol`. Claude Code and Codex implement it, and Pi (ticket 07) will.

| Member | Purpose |
| --- | --- |
| `name`, `default_model` | The agent's name in results, and the pinned model used without `--model`. |
| `credential_env` | The caller's environment variables the credential comes from. `results.json` records these names, never a value. |
| `executable` | The pinned CLI binary. A missing one is a usage error. |
| `read_credentials(environ)` | Reads the credential from the caller, or raises `CredentialError`, which is a usage error. |
| `secrets(credentials)` | Every value in the credential that must never reach a results file. The scrub and the trial sweep use these. |
| `trial_secrets(trial)` | Credential values that appeared during the trial, such as a refreshed Codex login. The runner reads them after the run and again before teardown, on every path, and scrubs and sweeps for them too. If they cannot be read once the login is installed, it raises: the runner records the trial as an infrastructure error, deletes the whole trial and its transcript, and goes on to the next. Claude Code returns none. |
| `trial_credentials(trial, credentials)` | The credential the next trial starts from: the trial's own copy if the agent refreshed it, else `credentials`. It is never written back to the caller. Claude Code returns `credentials`. |
| `home_env`, `skills_dir` | The variables that move the agent's home (each must point inside the trial), and where a skill is installed relative to the workspace. |
| `reports_skills` | Whether the agent reports the skills and plugins it loaded. When it does, a missing report fails closed. When it does not, the contamination proof rests on the preflight and the canary sweep. |
| `builtin_skills`, `builtin_plugins` | The recorded allowlists of skills and plugins built into the pinned CLI, keyed by CLI version. |
| `discovery_locations(trial)` | Every location the research notes list for the agent, each with its mitigations (`redirected`, `suppressed`, `reported`, `controlled`, `not-a-location`) and the canary test that covers it. A location with no mitigation fails the preflight. |
| `context_isolation(env)` | Problems that would let instruction files load. Empty when isolated. |
| `prepare_homes(trial)` | Creates the isolated agent home and user home and returns the child's whole environment, built from scratch. |
| `install_skill(skill_dir, workspace)` | Copies the skill into the workspace, or installs nothing for a baseline (`None`). |
| `run(prompt, trial, homes, *, model, timeout, credentials)` | Runs the prompt headless and returns a `RawRun`: exit code, timeout flag, transcript path, stderr, the kept discovery lines, the `python3` calls, and whether any process survived teardown. |
| `discovery_report_problems(trace, trial, *, installed, system_root)` | Problems in the report of where the agent looked for skills. Claude Code reads its debug log. Codex reports nothing, so its adapter reads the locations themselves after the run. |
| `parse(raw)` | Normalises the event stream into a `Trace`: skills triggered and invoked, commands run with their output and status, the final message, CLI version, model, exit code, whether the stream ended normally, the run status and its reason, and the skills, plugins and commands the agent reported. |

`visible_skills` is `None` for an agent that does not report its skills. For such an agent (`reports_skills` false), the contamination proof rests on the redirected homes, the preflight's mitigated discovery locations and the canary sweep, and the results note it.

### Claude Code

- **Command:** `node_modules/.bin/claude -p <prompt> --output-format stream-json --verbose --model <model> --no-session-persistence --strict-mcp-config --permission-mode dontAsk --max-budget-usd 1.00 --debug-file <trial>/tmp/debug.log --allowedTools Skill Read Bash`. Stdin is `/dev/null`. `--bare` is not used because it accepts only an API key, and `--safe-mode` is not used because it disables skills.
- **Environment:** built from scratch. `HOME`, `CLAUDE_CONFIG_DIR` (`<home>/.claude`), the four `XDG_*` directories and `TMPDIR` point inside the trial. `PATH` is `<trial>/bin:/usr/bin:/bin`. `CLAUDE_CODE_DISABLE_CLAUDE_MDS`, `CLAUDE_CODE_DISABLE_POLICY_SKILLS`, `DISABLE_AUTOUPDATER`, `CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC` and `DISABLE_TELEMETRY` are all `1`. The Justfile's shared `CLAUDE_CONFIG_DIR` never reaches the child. `CLAUDE_CODE_SUBPROCESS_ENV_SCRUB` is not set: on Linux it requires `bubblewrap` and the CLI refuses to start without it. The CLI keeps the token out of its Bash tool's environment without it, which `test_secrets.py` checks on every platform.
- **Trigger rule:** an assistant `tool_use` named `Skill` whose `input.skill` is `<name>` or `<plugin>:<name>`, and whose matching `tool_result` is not `is_error`.
- **Run status:** `infra_error` when the run timed out, a process survived teardown, the last event is not a `result` or a line did not parse, the `result` has `is_error: true`, or the exit code is nonzero. A failed login reports `subtype: "success"` with `is_error: true`, so `subtype` is never used. `apiKeySource` is `none` under OAuth too, so it is never used either.
- **Built-in allowlist (2.1.309):** `batch claude-api code-review dataviz debug deep-research doctor fewer-permission-prompts loop plugin-authoring run run-skill-generator schedule simplify update-config verify workflow-authoring`. The plugins are `cc-plugin-agents-md@builtin` and `cc-plugin-plugin-authoring@builtin`. `schedule` is listed only when an OAuth token is set. A new CLI version fails the check with a hint to re-record the allowlist from the canary sweep.

### Codex

- **Command:** the pinned native binary that `node_modules/.bin/codex` would start (`node_modules/@openai/codex-<platform>/vendor/<triple>/bin/codex`), run directly so no Node is needed on the trial's `PATH`: `codex exec --json --ephemeral --ignore-user-config --ignore-rules --sandbox workspace-write --model <model> --cd <workspace> -c allow_login_shell=false -c project_doc_max_bytes=0 -c analytics.enabled=false --disable plugins --disable remote_plugin --disable apps -- <prompt>`. Stdin is `/dev/null`. The sandbox confines the agent's writes to the workspace and the trial's `TMPDIR`. On Ubuntu 23.10 and later, AppArmor blocks the unprivileged user namespaces the Linux sandbox needs, and Codex denies every command (`bwrap: loopback: Failed RTM_NEWADDR`); the fix is an AppArmor profile for the Codex binary, or `sysctl -w kernel.apparmor_restrict_unprivileged_userns=0`, which CI sets. `allow_login_shell=false` matters: a login shell runs the system profile, whose `path_helper` puts `/usr/bin/python3` ahead of the trial's `python3` wrapper. Plugins and apps are disabled because Codex otherwise syncs the account's remote plugins, with their skills, into its home mid-run.
- **Environment:** built from scratch, like Claude Code's. `HOME`, `CODEX_HOME` (`<home>/.codex`), the four `XDG_*` directories and `TMPDIR` point inside the trial. `PATH` is `<trial>/bin:/usr/bin:/bin` and `SHELL` is `/bin/bash`, though Codex runs commands in the account's login shell from the password database (`/bin/zsh` on macOS), with `-c` rather than `-lc`. `RUST_LOG=warn,codex_otel.log_only=info` makes Codex log its telemetry events to stderr. `--ephemeral` keeps session files off disk, but Codex still writes its SQLite state and a `config.toml` that trusts the workspace into the trial's `CODEX_HOME`.
- **Event stream:** `--json` writes JSONL: `thread.started`, `turn.started`, `item.started` and `item.completed` (items `command_execution`, `agent_message`, `error`), then `turn.completed` or `turn.failed`. A `command_execution` carries the command as `<shell> -c '<command>'`; the adapter removes the wrapper, so `script_ran` sees the agent's command. Its `aggregated_output` and `exit_code` are the tool result. The stream carries neither the CLI version nor the model.
- **Kept stderr lines:** three kinds, reduced to the fields named here, because telemetry lines can name the account. `codex.conversation_starts` gives `app.version` and `model`. `codex.skill_invocation` gives `skill.name`, `skill.scope` and `skill.invocation_type`. `failed to load skill <path>: <reason>` is logged for a `SKILL.md` Codex cannot parse. The rest of the telemetry, including any continuation lines of a record, is dropped from the stored stderr, and a `failed to load skill` inside a telemetry record (tool output, say) does not count. Codex copies a tool's output into its `codex.tool_result` record raw and unquoted, with the record's remaining fields on the line after it, so a tool can print a line that looks like a record of Codex's. A stderr line that matches a line in the JSONL event stream, or is the start of one, or starts with one, is therefore never a record's first line: it continues the record above. Both are split only on `\n`, so a `\r` a tool printed starts no line.
- **Trigger rule:** Codex has no skill tool, so a trigger is a read of the skill's `SKILL.md`. Any of these counts:
  - A completed `command_execution` with `exit_code` 0 and nonempty output, whose command (split into simple commands as `script_ran` does) runs `cat`, `head`, `tail`, `sed`, `nl`, `less`, `more` or `bat` with a file argument naming `<skill>/SKILL.md` in a skills directory (one whose name ends in `skills`, or `.system`). A `name=value` word is not a file argument. `awk` is not a reader, because whether it opens an operand depends on its program. The command's exit status and output must be the read's: the read is the last part, and only `cd <dir>` (not `cd -`, which prints the directory) and `pwd` may come before it, joined by `&&` (an operator at the end of a line counts too). `pwd` prints one line, so the output must have a line more than the `pwd`s print. After `||`, `;`, `&` or a pipe, or after any other command, the exit status and output no longer show what the read did, so such a read is left to Codex's own event. So is a reader with a redirection (any word holding `<` or `>`, quoted or not, including `2>&1`) or a help or version flag (`--help`, `--version`, `-h`, `-V`), which can make it print something else or write the path. The rule matches the skill by name in any skills directory, so a same-named skill elsewhere would count; the location checks, not the trigger rule, rule out a second copy. A preceding `cd <dir>` in the same command counts, so `cd .agents/skills/cowsay && sed -n 1,40p SKILL.md` is a read of `cowsay`. A failed read, a command that never completed, and a command that only names the path (`ls`, `test`, `echo`) do not count. A path whose skill directory the text cannot place (`../SKILL.md`, a glob, a variable) names no skill here, and is left to Codex's own event.
  - A `codex.skill_invocation` event with `invocation_type="implicit"`. Codex logs it when it sees a successful read of a listed skill's `SKILL.md`, which also covers a read whose command text cannot place the file, such as one run in another `workdir`. The recorded transcripts show it agreeing with the rule above.
  - A `codex.skill_invocation` event with `invocation_type="explicit"`. An explicit `$<name>` mention makes Codex inject the skill's `SKILL.md` into the request as a `<skill>` message, so no command reads it and nothing appears in the JSONL. The event is the only local evidence, which is why the adapter keeps it.

  The skill name may carry a plugin prefix: the shipped cowsay is named `cowsay:cowsay`, because Codex reads its `.claude-plugin/plugin.json` as a plugin manifest, so the explicit mention is `$cowsay:cowsay`. A bare `$cowsay` loads nothing explicitly. The adapter strips the prefix, as it does for Claude Code. A read and Codex's event for it are one trigger.
- **Run status:** `infra_error` when the run timed out, a process survived teardown, Codex failed to load a skill, the last event is `turn.failed` (a failed login ends this way, after retries) or not `turn.completed`, a line did not parse, or the exit code is nonzero. `error` events alone do not fail the run: Codex reports each reconnect as one.
- **Built-in allowlist (0.163.0):** the bundled skills Codex writes to `$CODEX_HOME/skills/.system` on startup: `imagegen openai-docs review-agent skill-creator skill-installer`. `review-agent` is written but not listed to the model. No plugins are allowed.

## Credentials

| Agent | Credential | How it reaches the run |
| --- | --- | --- |
| Claude Code | `CLAUDE_CODE_OAUTH_TOKEN`, from `claude setup-token` | Read from the caller's environment and placed only in the child's environment. The harness writes it nowhere. The pinned CLI does not pass it on to its Bash tool's processes. |
| Codex | `auth.json` in the project's `CODEX_HOME` (`.tools/agent-homes/codex`, which the Justfile sets), from `just run ./node_modules/.bin/codex login` | Only `auth.json` is copied, mode 0600, into each trial's own `CODEX_HOME`. No skills, config or instructions come with it, and the user's `~/.codex` is never read. `--ignore-user-config` would skip a `config.toml` there anyway. `results.json` records `CODEX_HOME` as the credential's source. |

The harness refuses to start without the token. Every file it writes under `eval-results/` passes through a scrub that replaces each credential value with `[REDACTED]`. The run then rereads every file, and deletes any that still holds a value and fails. After each trial, in a `finally`, the process group is killed and checked empty, and the trial's `home/`, `tmp/` and `bin/` are removed. The workspace is kept for inspection. If a credential value is found anywhere in the trial directory, the whole trial directory is deleted, the files are named in the trial's `secret_found`, and the trial fails. The `PASS`/`FAIL` lines printed at the end are scrubbed the same way as the files. `results.json` records the credential's variable name, never its value. Codex's `auth.json` sits in the per-trial agent home, which the same `finally` removes. Every string in it except `auth_mode` and `last_refresh` (the API key, or the ChatGPT tokens and account id) is a secret for the scrub and the sweep. The agent's tools can read the copy while the trial runs, as they can read any file. If Codex refreshes a ChatGPT login mid-trial, it rewrites the trial's copy. The runner reads that copy back after the run and again before teardown, even when the run raised, and its new values join the scrub and the sweep for that trial and the rest of the run. The next trial starts from the refreshed copy, held in memory, so a provider that rotates the refresh token does not strand the rest of the run. If that copy cannot be read, the trial fails as an infrastructure error and is deleted, transcript and all. The refreshed copy is never written back, so the refresh may still invalidate the project's own login; if it stops working, log in again. Pi's auth file belongs in its per-trial agent home too (ticket 07).

## Isolation

Each trial gets `.eval-workspaces/<run-id>/<case-id>/<arm>-<n>/` (for example `behaviour-ship-it/skill-1/`) with:

- `workspace/`, a fresh `git init` (no global or system Git config) that is its own git root, gitignored, and outside `skills/` and `dev-skills/`. It holds `.git/` and the installed skill, nothing else.
- `home/`, the user home and the agent home.
- `tmp/`, the agent's temporary directory, transcript and debug log.
- `bin/`, holding `python3` and `python`, wrappers that log each call and run the harness's pinned interpreter, and `git`.

The preflight checks all of this before the agent starts, and fails closed. A baseline trial installs nothing, so its workspace may hold only `.git/`.

Trials run in rounds. In round n every case's trials run back to back, the skill arm first when n is odd and the baseline first when n is even, so order effects balance over an even trial count. Each trial records its `order` in the run.

## Contamination check

Each trial passes only when all of these hold:

1. **Reported skills.** The init event's skills, plus any command a `system/commands_changed` event adds, plus every successful `Skill` call, minus the recorded built-ins, is exactly the skill under test (empty for a baseline, which uses the same allowlist; the skill under test anywhere in a baseline's report fails it). The init event's plugins equal the built-in plugins, and a missing skill or plugin report fails closed.
2. **Discovery report.** In the debug log, the `user=` location sits inside the trial home, every `project=` location inside the workspace, and the managed location is missing or empty. The per-location counts are `managed: 0, user: 0, additional: 0` and `project: 1` (0 for a baseline). A missing report fails closed. Only these lines are kept, and the debug log is deleted.
3. **Never-appear list.** The repo's dev skills, the other shipped skills, and the user's own skills (directory names under `~/.claude/skills`, `~/.agents/skills`, `~/.codex/skills`, `~/.pi/agent/skills` and the caller's agent homes) must not appear among the reported skills. The discovery report is checked by location instead (step 2), so any skill directory outside the trial fails there. A name that collides with a built-in is noted, not failed. The repo's `AGENTS.md`, `CLAUDE.md` and the user's `~/.claude/CLAUDE.md` are listed too. They are kept out by the preflight's instruction-file check, because a live run cannot observe the request.

The canary sweep (`tests/evals/test_contamination_canaries.py`) shows the check fails when a canary sits in each location the agent reads, and that every other location stays isolated. The managed-location canary runs only in CI, because it writes to `/etc/claude-code`.

### Codex

Codex lists its skills only inside the model request, which a live run cannot observe, so `reports_skills` is false and the results note it. The steps become:

1. **Triggered skills.** Every skill the trace records as triggered (a read of its `SKILL.md`, or a Codex `skill_invocation` event), minus the recorded built-ins, is at most the skill under test. Reading a never-appear skill, such as a dev skill reached through `../`, fails.
2. **Discovery report.** After the run and before teardown, the adapter reads every location Codex takes skills or instructions from:
   - `<workspace>/.agents/skills` holds exactly one skill (none for a baseline).
   - `<trial home>/.agents/skills`, the user-level shared folder in the OS home, is missing or empty.
   - `$CODEX_HOME/skills` holds only `.system`, which holds only the recorded bundled skills and Codex's marker file.
   - `$CODEX_HOME/plugins` and `$CODEX_HOME/.tmp/plugins` do not exist.
   - `$CODEX_HOME/AGENTS.md` and `AGENTS.override.md` do not exist. `project_doc_max_bytes=0` keeps out every other `AGENTS.md`, but not these global instructions.
   - `/etc/codex` is missing or empty.

   A location the check cannot list (`PermissionError`) is not taken as empty: Codex could still open a known path in it, so the error ends the trial as an infrastructure error.
3. **Never-appear list.** As above, over the triggered skills.

`tests/evals/test_codex_contamination.py` plants a canary in each of those locations, one at a time, and shows the check fails. `tests/evals/test_codex_adapter.py` runs the real pinned Codex against the fake API. It shows that a canary in the trial home's shared folder or global `AGENTS.md` reaches the model, so the check has something to catch. It also shows that canaries in the caller's `~/.agents/skills`, in the caller's own `CODEX_HOME` (skills, `AGENTS.md` and `config.toml`), and in a parent repository's `.agents/skills` and `AGENTS.md` never do, that the caller's `CODEX_HOME` is never written, and that a workspace `AGENTS.md` loads only with `project_doc_max_bytes=0` removed.

## Grader

Rubric expectations are graded by Claude through the pinned Claude Code CLI, whatever agent ran the trial ([ADR 0012](../adr/0012-llm-grader-and-benchmark-statistics.md)). [The design](../../.scratch/foundation/design/08-grading.md) explains each rule and what it does not cover.

- **When:** after the trial's teardown and secret sweep, only for a trial whose case has expectations and that is scorable (status `ok`, contamination passed, no secret found).
- **Command:** `node_modules/.bin/claude -p <prompt> --system-prompt <grader prompt> --tools "" --disable-slash-commands --output-format stream-json --verbose --model <grader model> --no-session-persistence --strict-mcp-config --max-budget-usd 1.00`, in `.eval-workspaces/<run-id>/_grader/<random>/`, with the environment `prepare_homes` builds for an agent trial. The directory is deleted after each call. Its name is random because the CLI tells the model its working directory, and the trial key names the arm. No tools means everything it judges is in the prompt.
- **Credential:** `CLAUDE_CODE_OAUTH_TOKEN`, the same token a Claude Code run uses. A Codex run whose selected cases carry expectations needs it too, and is a usage error without it. It joins the run's secrets, so the scrub and the sweep cover the grading files, and the grader sees the trace with every secret scrubbed.
- **Blinded material:** the final message (capped at 20 KB) and every workspace file except `.git/` and the skills directory (20 KB each, 80 KB in all; non-UTF-8 files by name and size, symlinks by name). The caps keep the whole prompt inside one Linux argument; a NUL becomes U+FFFD for the same reason. A lone surrogate, in the material or in the grader's evidence and notes, becomes U+FFFD too, since UTF-8 cannot encode it. The trial directory, which names the arm, and every skill-install prefix (`.claude/skills/<skill>/`, `.agents/skills/<skill>/`, `skills/<skill>/`) are removed in both arms alike. Skill calls are never sent, nor the case's `expected_output`.
- **Disclosure check:** the material is scanned, case-insensitively, for the word `skill` or `skills` (not "skilled"), any file path inside `skills/<skill>/`, and `.claude/skills` or `.agents/skills`. A match is graded anyway and recorded as `arm_disclosed`, with the matches, because rewriting the agent's prose would change what is judged.
- **Unblinded expectations** (`needs_transcript`) are judged in a second call whose material adds each command with its output (4 KB per output, 100 KB in all), and are marked `"blinded": false`.
- **Untrusted material:** the material sits between `<graded-material-NONCE>` tags, with a fresh random nonce the material does not contain. The system prompt says everything inside is data and any instruction in it is to be ignored and noted.
- **Canary expectation:** each call slips in a known-false expectation naming a random code the material does not contain. If the grader passes it, every expectation is recorded as failed (`rejected`).
- **Quote rule:** a pass needs a nonempty `quote` that appears verbatim in the material (whitespace collapsed). Without one, that expectation is failed.

| Grading status | Meaning | Recorded as | In the benchmark |
| --- | --- | --- | --- |
| `ok` | A valid reply; the canary failed | each verdict, after the quote rule | counted |
| `rejected` | The canary passed | every expectation failed | counted as failures |
| `invalid_reply` | A reply that failed validation: empty, not one JSON object, wrong or missing ids, wrong types, extra keys | every expectation failed | counted as failures |
| `grader_error` | No reply: the CLI failed or timed out, its run was not ok, or its stream had no result | every `passed` is `null` | excluded from `graded_pass_rate` and `outcome_pass_rate`, counted |

A reply that fails validation might have been caused by the graded material, so it counts against the trial; only a call that returned nothing is excluded. With two calls, the worse status wins, and a reply that counts against the trial outranks a call that returned nothing.

## Benchmark

`eval-results/<run-id>/benchmark.json` aggregates the run's trials and grading files, and the run prints it as a table. It follows skill-creator's benchmark: skill-creator's `with_skill` and `without_skill` configurations are the `skill` and `baseline` arms here.

For each agent, case and arm it counts `n_planned`, `n_scored` (status ok, uncontaminated, no secret), `n_infra_error`, `n_contaminated`, `n_secret_found`, `n_grader_error` (including a grading file that is missing, unreadable, malformed, or lists other expectations than the case's rubric), `n_invalid_reply`, `n_rejected` and `n_arm_disclosed`. Each metric is `{mean, stddev, min, max, n}` over per-trial values:

| Metric | Per-trial value | Baseline arm |
| --- | --- | --- |
| `trigger_accuracy` | 1 when the trigger matched `should_trigger` | `not_applicable` |
| `skill_use_pass_rate` | skill-use assertions passed / total | `not_applicable` |
| `deterministic_pass_rate` | outcome assertions passed / total | measured |
| `graded_pass_rate` | expectations passed / total (0 for `rejected` or `invalid_reply`) | measured |
| `outcome_pass_rate` | outcome assertions and expectations together | measured |

- The **delta** is the skill arm's mean minus the baseline's, for the deterministic, graded and outcome rates only, with both arms' n. It is `null` when either arm has no data, or the case was skipped in the baseline.
- **Intention to treat:** a skill-arm trial in which the skill did not trigger still counts in its arm's outcome metrics.
- An infrastructure error, contamination or a secret found removes a trial from every metric. A grader error removes it from the graded and outcome rates only. Every exclusion is counted, never turned into a 0.
- `stddev` is the sample standard deviation, `null` below two values. A metric with nothing to measure is `null`, never 0.
- **Notes** flag fewer than three trials ("spread not meaningful"), a flaky trigger, an expectation that passed in every trial of both arms (non-discriminating), and, on a delta, unequal n, excluded grader errors and trials whose material named the arm. A run without a baseline has no delta; its per-arm counts still show both.
- **Per agent:** the trial-weighted mean of each metric over all cases, and the agent's delta as the mean of the per-case deltas, with the number of cases.
- No significance test or confidence interval is reported. With a few trials per arm the figures are descriptive.
- In the printed table, a case's baseline reads `off` when the run had no baseline arm, and `skipped` when the baseline ran without that case.

**Provenance**, recorded at the start of the run: the agent CLI versions and models the trials reported, the grader model requested and reported and its CLI version, `git_commit` and `git_dirty` (`git status --porcelain` is not empty), `skill_sha256` (the sorted relative paths and bytes of `skills/<skill>/`, without `__pycache__`), `evals_sha256` (`evals/<skill>/evals.json`, cases and rubric), `grader_prompt_sha256`, the trial count, whether the baseline ran, and the cases it skipped.

## Results

`eval-results/<run-id>/` holds:

- `results.json`, the run record below
- `transcripts/<case>/<arm>-<n>.jsonl`, each trial's transcript, scrubbed
- `grading/<case>/<arm>-<n>.json`, each graded trial's grading
- `benchmark.json`

| Run field | Meaning |
| --- | --- |
| `run_id`, `skill`, `agent`, `requested_model` | What ran. |
| `credential_env` | The names of the caller's variables the credential came from: `CLAUDE_CODE_OAUTH_TOKEN`, or `CODEX_HOME` for Codex's `auth.json`. |
| `started_at`, `finished_at` | UTC, ISO 8601. |
| `passed` | Every skill-arm trial passed and every baseline trial is valid. |
| `trials_per_case`, `baseline`, `grader_model_requested` | The run's configuration. |
| `cases` | Each selected case's `id`, `kind`, `should_trigger`, `expectations` (`text`, `blinded`) and `in_baseline`. |
| `skipped_in_baseline` | Case ids with nothing for a baseline to measure. |
| `provenance` | The provenance above that is known at the start. |
| `trials` | One record per trial, below, in run order. |

| Trial field | Meaning |
| --- | --- |
| `case`, `kind`, `agent` | The case and the agent. |
| `arm`, `trial`, `order` | `skill` or `baseline`, the trial's number n in its arm, and its 0-based position in the run. |
| `cli_version`, `model` | What the agent reports running: Claude Code's init event, or Codex's `codex.conversation_starts` event. A `--model` alias shows the model it resolved to. |
| `started_at`, `finished_at` | UTC, ISO 8601. |
| `status`, `status_reason` | `ok` or `infra_error`, with the reason. |
| `trigger` | `expected`, `actual`, `matched`, `applicable`. `actual` and `matched` are `null` on an infrastructure error. In the baseline, `applicable` is false and `matched` is `null`: a trigger there is a contamination failure. |
| `contamination` | `passed`, `problems`, `notes`. |
| `assertions` | Each `type`, `class` (`skill_use` or `outcome`), `result` (`passed`, `failed`, `not_scored` or `not_applicable`) and `evidence`. Every assertion is `not_scored` on an infrastructure error, so a crash can never pass a should-not-trigger case. |
| `transcript` | The scrubbed transcript, relative to the repo root. |
| `stderr` | The last 2000 characters of the agent's stderr, scrubbed. |
| `secret_found` | `null`, or the `files` in the trial directory that held a credential value and whether the directory was `deleted`. |
| `grading`, `graded` | The grading file, relative to the repo root, and its `status`, `passed`, `failed`, `total`, `pass_rate` and `arm_disclosed`; both `null` when the trial was not graded. |
| `valid` | No secret was found, `status` is `ok`, contamination passed, and the grading (if any) is not a `grader_error`. |
| `passed` | Skill arm: valid, the trigger matched, every assertion passed, and the grading (if any) is `ok` with every expectation passed. `null` in the baseline arm, which never fails on its outcomes. |

`grading/<case>/<arm>-<n>.json` follows skill-creator's `grading.json`. `claims`, `user_notes_summary` and `eval_feedback` are not produced.

| Grading field | Meaning |
| --- | --- |
| `expectations` | Each `text`, `passed` (`null` on a grader error), `evidence` and `blinded`, in rubric order. The canary is never listed. |
| `summary` | `passed`, `failed`, `total`, `pass_rate` (`null` on a grader error). |
| `arm_disclosed`, `disclosure_matches` | Whether the material named the arm, and the matching strings. |
| `grader` | `model_requested`, `model` and `cli_version` as the grader reported them, `status`, `status_reason`, `canary_passed`, `notes` (what the grader flagged, such as instructions in the material) and `calls`. |
| `timing` | `grader_duration_seconds`. |
