# Evals

The eval harness runs a skill's eval cases against a pinned agent CLI, headless, in several trials and optionally against a baseline, grades rubric expectations with an LLM, and writes a results file and a benchmark. This page covers the case schema, its git fixtures and by-name cases, the adapter interface, isolation, credentials, the contamination check, the grader, the benchmark and the results format. [Eval isolation](../explanation/eval-isolation.md) explains why isolation is built this way and what it does not cover.

## Commands

| Command | What it does |
| --- | --- |
| `just validate-evals` | Validates every `evals/*/evals.json` against the schema below, and every [fixture](#fixtures) in `evals/*/fixtures/`. It calls no agent and is part of `just check`. |
| `just eval <skill> --agent claude` | Runs every case of `evals/<skill>/evals.json` against the pinned Claude Code. |
| `just eval <skill> --agent codex` | Runs the same cases against the pinned Codex. |
| `… --case <id>` | Runs only that case. Repeat it to run several. An unknown id is a usage error. |
| `… --model <id>` | Overrides the pinned default model: `claude-sonnet-5-5` for Claude Code, `gpt-5.6-terra` for Codex. |
| `… --timeout <seconds>` | Per-trial timeout, default 300. |
| `… --trials <n>` | Runs every selected case n times per arm, default 1. |
| `… --baseline` | Also runs, n times, every selected case that has an outcome to measure, with no skill installed (the baseline arm). Trigger-only cases are skipped in the baseline and listed. |
| `… --grader-model <id>` | The grader's model, default `claude-opus-5-5`. |
| `… --no-grader` | Skips grading: no grader call, and no grader token is read. A case with expectations rests on its assertions alone; its graded and outcome pass rates are not measured (`null`), and the plan shows `grader calls: 0 (grading skipped)`. The live-eval CI job uses it when `CLAUDE_CODE_OAUTH_TOKEN` is not set. |
| `… --dry-run` | Prints the plan and exits 0: agent calls per arm, the cases skipped in the baseline, the most grader calls the run can make, and the spend cap. It reads no credential, creates no workspace and writes nothing. A real run prints the same plan first. |
| `just eval-record <name> <run-id>...` | Records finished runs as a named iteration. See [history and report](#history-and-report). |
| `just eval-report [skill]` | Builds the offline benchmark report from the recorded iterations. Runs you have not recorded appear only when passed with `--run`. |
| `just eval-changed [--base REF]` | Prints the skills with evals changed since the merge base with `origin/main` (or `REF`). See [live evals in CI](../how-to/live-evals-in-ci.md) for the rules. Calls no agent. |
| `just eval-ci plan\|runs\|scan …` | The helpers the manual live-eval workflow runs: validate the dispatch inputs and plan the runs, list a skill's finished runs, and scan a directory for secret values. See [live evals in CI](../how-to/live-evals-in-ci.md). |

**Live evals need an authenticated agent and are never part of the PR gate.** `just eval` calls a paid model, so it runs only locally or from a manual job that holds the secret ([ADR 0004](../adr/0004-eval-tiers-and-ci.md)). `just check` and PR CI cover the harness without credentials: the tests drive the real pinned CLIs against local fake APIs (`tests/evals/fake_anthropic.py`, `tests/evals/fake_openai.py`) and parse recorded transcripts (`tests/fixtures/evals/claude/`, `tests/fixtures/evals/codex/`).

Exit codes: 0 when every skill-arm trial passed and every baseline trial is valid, 1 otherwise (a failed trial, an infrastructure error, contamination, a grading that is not `ok` in the skill arm, or a grader error in the baseline), 2 for a usage error (a missing credential, an invalid suite, an unknown case, a selected [placeholder case](#placeholder-cases), a missing pinned CLI). Nothing is written on a usage error. A harness failure inside one trial is recorded as that trial's infrastructure error, and the other trials still run.

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
| `prompt` | The nonempty prompt, passed to the agent as an argument. It is never written into the workspace. In a [by-name case](#by-name-cases) it is the bare request, and in the skill arm the adapter puts the agent's own invocation of the skill before it. |
| `should_trigger` | Required on every case. The trial's trigger outcome must match it. A `behaviour` case needs `true`. |
| `expected_output` | Optional human description, kept from skill-creator. It is not graded. |
| `files` | Accepted only as an empty list. Input files are staged with a fixture, so anything else is rejected with a message that points to `fixture`. |
| `fixture` | Optional, on either kind: the name of a [fixture](#fixtures), a lowercase slug, which the case's trials start in, in both arms. It must name a directory `evals/<skill>/fixtures/<name>/`. It may sit beside `files: []`. |
| `by_name` | Optional, on either kind: `true` marks a [by-name case](#by-name-cases), whose skill arm invokes the skill by name. It needs `should_trigger: true`, and its prompt must not start with `/` or `$` or hold an invocation of the skill. `false` is rejected; leave the key out. |
| `assertions` | Deterministic assertions, below. A `behaviour` case needs at least one; a `trigger` case must have none. |
| `placeholder` | `true` marks a starter case written by `just new-skill`, which is not written yet. `just eval` refuses to run it (see [placeholder cases](#placeholder-cases)). Delete the key once the case is written; `false` is rejected. |
| `expectations` | Optional rubric for the [grader](#grader), on `behaviour` cases only (skill-creator's field). Each item is a string, judged blinded, or `{"text": …, "needs_transcript": true}`, judged from the commands and the final message instead (no output files) and marked unblinded. Text must be nonempty and unique within the case; `needs_transcript: false` is rejected (use the string form). |

Unknown keys are rejected at every level, so a later field has to be added on purpose.

### Placeholder cases

`just new-skill` writes starter cases, a should-trigger case, a should-not-trigger case and a behaviour case, each with `"placeholder": true` and `TODO(new-skill)` text. They are valid, so a new skill passes `just validate-evals`, but they measure nothing:

- `just eval`, with or without `--dry-run`, prints `UNWRITTEN <skill>/<case>` for each selected placeholder case and exits 2 before it reads a credential or calls an agent. `--case` can still pick out the written cases of a suite that has placeholders.
- `just validate-evals`, and so `just check`, warns on stderr, and still passes, when a skill listed in `.claude-plugin/marketplace.json` has placeholder cases: `warning: <skill> is in .claude-plugin/marketplace.json but evals/<skill>/evals.json has only placeholder cases`, or `… still has placeholder cases: <ids>` when some cases are written.

A blinded expectation describes the outcome the user asked for, never how it was produced: "the bubble contains the text verbatim", not "the bundled script was run" (that is `script_ran`). It must be passable by quoting the material, so negative expectations ("does not mention X") are not allowed. Freeze a rubric before a live run, and never edit it after seeing the delta. An assertion's `args`, when present, must be a list of strings: `null` is rejected, and `[]` means no arguments.

### By-name cases

A skill that loads only when the user names it, such as one that sets `disable-model-invocation: true` in `SKILL.md` and `policy.allow_implicit_invocation: false` in `agents/openai.yaml`, is tested with by-name cases: `"by_name": true`, with a `prompt` that holds only the bare request. In the skill arm the adapter builds the prompt from the installed copy:

| Agent | Skill arm's prompt |
| --- | --- |
| Claude Code | `/<skill> <request>`, a slash command. A project skill needs no plugin prefix. |
| Codex | `$<plugin>:<skill> <request>`, where `<plugin>` is the `name` in the installed copy's `.claude-plugin/plugin.json`, which Codex reads as a plugin manifest. A copy with no `plugin.json` gets `$<skill> <request>`. A manifest that is not valid JSON or names no plugin makes the trial an infrastructure error, so no mention that loads nothing is sent. |

The baseline arm, which has no skill to invoke, gets the bare request, and so does every grader request in both arms: the harness sends the invocation to the skill arm's agent and nowhere else. Every trial records the exact string its agent was sent as `prompt` ([results](#results)). A skill arm with no installed copy to name is an infrastructure error. How each agent's trace records the by-name trigger is in its trigger rule: Claude Code's session record of the slash command's expansion ([Claude Code](#claude-code)), and Codex's `explicit` event ([Codex](#codex)).

The schema keeps the invocation out of the prompt. A by-name case is rejected when:

- its `should_trigger` is not `true`: invoking a skill by name asks for it;
- its prompt starts with `/` or `$` after any leading whitespace, whatever follows, so `/tmp/…` and `$HOME` are rejected there too;
- its prompt holds an invocation of the skill anywhere. An invocation is `/` or `$`, an optional `<plugin>:`, then the skill's name as a whole token, ignoring case. Nothing that can sit inside a path or a longer name comes before it (a letter, digit, `_`, `.`, `/`, `:`, `$`, `~` or `-`), and nothing that continues one comes after it (a letter, digit, `_`, `/`, `:` or `-`, or a `.` followed by a letter or digit). So `/cowsay`, `` `/cowsay` ``, `$COWSAY`, `$cowsay:cowsay,` and a sentence-ending `/cowsay.` are invocations, and `src/cowsay/x.py`, `docs/cowsay.md`, `~/cowsay`, `/cowsay/notes.txt`, `/cowsay-extra` and `$HOME` are not.

These checks apply to by-name cases only. An unmarked case's prompt is sent as written, invocation and all: cowsay's `trigger-explicit-invocation` keeps `$cowsay:cowsay` in its prompt, and on Claude Code it reaches the model as text.

**An agent's echo.** In a by-name case, the grader's [disclosure check](#grader) also flags an invocation of the skill in the material, because only the skill arm's agent was sent one. The material is graded as written and the trial recorded as `arm_disclosed`; nothing is removed.

**Quiet cases.** A by-name-only skill's should-not-trigger case is an ordinary unmarked case with `should_trigger: false` and a plain request. Its pass means the trace recorded no load, which is a lower bound: each agent's trigger rule counts only the reads its trace can confirm, and an agent can see the skill's text in ways it does not record, such as a pipe, `awk`, an interpreter or Claude Code's `Grep` tool. Read the quiet cases' transcripts by hand at each live run.

`results.json`'s `cases` entries do not record `by_name`; each trial's `prompt` shows what its agent was sent.

### Assertions

Each type is a **skill-use** assertion (`skill_triggered`, `script_ran`), which the baseline arm never scores (`not_applicable`), or an **outcome** assertion (the rest), scored in both arms. `final_contains_script_output` runs the repo's copy of the script, so it needs nothing installed.

| Type | Fields | Passes when |
| --- | --- | --- |
| `skill_triggered` | none | The trace records a trigger of the skill under test. |
| `script_ran` | `script`, optional `args` | All three hold, so a command that merely names the script cannot pass. (1) A Bash command, split into simple commands on `;`, `&&`, `\|\|`, `\|`, `&` and newlines, runs `python`, `python3` or `python3.N` with `script` as its first non-option argument, matched on trailing path parts so `cd scripts && python3 cowsay.py` counts. A path inside `printf`, `echo`, `cat`, a comment or `sh -c '…'` does not count, and neither does a path after an option that runs no script: `-c` or `-m` (attached or clustered, as in `-Ic'…'`), `-`, `-h`, `-V`, `--help`, `--version` or any option the parser does not know. (2) That call's tool result, which the CLI writes, is not an error and contains the script's output for `args` as whole lines (with no `args`, it is nonempty). (3) The trial's `python3` wrapper logged a call of the installed copy that exited 0, with `args` or with no arguments (text on stdin). The wrapper logs after the call ends, so a call that was killed leaves no record, and a script that fails behind `\|\| true` or `; echo` does not count even if it really ran. |
| `final_contains_script_output` | `script`, `args` | The harness runs the shipped script itself (`python -I`, outside the workspace, stdin `/dev/null`, `HOME` and `TMPDIR` pointing at a throwaway directory, at most 30 seconds) and its output, minus the final newline, appears in the final message as a run of whole, unaltered lines. A trailing `\r` per line is ignored; nothing else is. |
| `output_contains` | `value` | The final message contains `value`. |
| `output_matches` | `pattern` | Python `re.search(pattern, final_message)` matches. The schema rejects a pattern that does not compile. |

`script` must be a file inside the skill directory.

### Fixtures

A fixture is a small project with Git history that a case's trials start in, instead of an empty `git init`: a `main` branch, a second branch checked out, usually ahead of `main`, and optional staged, unstaged and untracked edits. It lives beside the cases, so distribution never ships it ([ADR 0011](../adr/0011-eval-case-location-and-isolation.md)), as a `fixture.json` and one full snapshot of the project per tree:

```text
evals/<skill>/fixtures/<name>/
  fixture.json
  trees/<tree>/...
```

The harness's own tests use two fixtures from `tests/fixtures/evals/git/`. `small-tally` has every state:

```json
{
  "branch": "add-average",
  "main": [
    { "tree": "start", "message": "Add the tally command" },
    { "tree": "tested", "message": "Test the totals" }
  ],
  "commits": [{ "tree": "average", "message": "Print the average after the total" }],
  "staged": "average-staged",
  "worktree": "average-wip",
  "executable": ["tally.py"]
}
```

| Key | Rule |
| --- | --- |
| `branch` | Required: the branch checked out. It must pass both `git check-ref-format --branch <branch>` and `git check-ref-format refs/heads/<branch>`, and, ignoring case, be neither `main` nor start with `main/`, which cannot sit beside `main`. |
| `main` | Required: the commits on `main`, oldest first, at least one. Each is `{"tree": <tree>, "message": <message>}`. |
| `commits` | The commits on the branch, on top of `main`'s last, in the same form. Default `[]`, which leaves the branch level with `main`. |
| `staged` | The tree the index holds. Without it, the index is the branch's last commit. |
| `worktree` | The tree the working directory holds. Without it, the working directory is the index. |
| `executable` | Paths that are mode `100755` in every tree that has them, each a file in at least one tree. Default `[]`. Every other file is `100644`, and modes on disk are ignored. |

Each `tree`, `staged` and `worktree` names a directory under `trees/`, and one tree can serve several. A message is one nonempty paragraph, with no blank line and no leading or trailing whitespace, because Git stores it byte for byte. Unknown keys are rejected, in a commit too.

The edits are the differences between the trees. Staged edits, deletions and renames are the index against the branch's last commit; unstaged ones are the working directory against the index; untracked files are files in the working directory that the index lacks. A branch with nothing ahead and a clean tree is `"commits": []` with neither `staged` nor `worktree`, and uncommitted edits only is `"commits": []` with `staged` or `worktree`.

**The build.** Each trial builds its fixture into the fresh workspace first, before the agent's homes are prepared or the skill installed, the same way in both arms, with Git plumbing run from the harness's Python:

1. The repository must use `sha1` object names.
2. Each tree's files are stored as blobs from their bytes on disk (`git hash-object -w --no-filters`) and written as a tree through a temporary index.
3. Each commit is made with `git commit-tree`, with `Robin Hale <robin@example.com>` as author and committer, dated 2026-01-01 00:00 UTC plus one hour per commit, counted across `main` and then the branch.
4. `main` and the branch are created with no reflog, and the branch is checked out.
5. The index is read from its tree, and the working files are written from the fixture's bytes, each with its mode and the first commit's date as its mtime. `git update-index -q --refresh` then records their stat data, so a later `git status` has nothing to write.
6. `.git/info/exclude` gets exactly `/.claude/` and `/.agents/`, which hide either agent's installed skill from Git ([isolation](#isolation)).

So a fixture's commits hash the same in every trial, run and machine. A fixture has no remote, so no `origin` and no `origin/main`: a skill finds a branch's base from local `main`. Nothing but the fixture's files and `.git/` is written to the workspace; `fixture.json`, the case and its expected output never reach it. A build that fails is the trial's infrastructure error.

**Rules.** `load_suite` validates every directory in `evals/<skill>/fixtures/`, named by a case or not, so `just validate-evals` and `just eval` both refuse a suite whose fixture breaks one of these. They keep the installed skill hidden, the fixture neutral between the arms, and its bytes the same on every machine.

- **No `.gitattributes`.** None, ignoring case, anywhere under the fixture's directory, in a tree or beside `fixture.json`: a fixture cannot carry Git attributes. The repository's root `.gitattributes` unsets `text` for every fixture tree, so Git stores their bytes as written, line endings included, and a nearer attributes file would outrank it.
- **No negation in a root `.gitignore`.** A tree's root `.gitignore`, its name compared ignoring case, may hold no line that starts with `!` once a byte-order mark and leading whitespace are dropped, which is wider than Git's own rule. A `.gitignore` outranks `.git/info/exclude`, so `!/.claude/` would show the installed skill to Git in the skill arm only. A negation can sit in a subdirectory's `.gitignore`, and an escaped `\!` is allowed.
- **Reserved names, ignoring case.** No path component may equal `.claude`, `.agents`, `.codex`, `.git`, `.gitattributes`, `CLAUDE.md`, `CLAUDE.local.md`, `AGENTS.md`, `AGENTS.override.md` or `SKILL.md`, and no directory's name may end in `skills`. On a file system that folds case, as macOS's does, a fixture's `.Claude/` is the directory the skill is installed in, and its `claude.md` is the CLI's `CLAUDE.md`.
- **Paths.** ASCII, and unique within a tree ignoring case, directories included. No symlink anywhere, and the fixture's directory may not be one.
- **Neutral text.** No `skill` or `skills` wording, which the grader's [disclosure check](#grader) looks for, in a path, a file (binary files included), the branch or a message. None of Codex's sandbox denial keywords ([run status](#codex)), ignoring case, in a path, a file, the branch or a message, because a failing command mostly prints the project's own text, and Git prints the branch and the messages. Both checks read every file as UTF-8, so keep text files UTF-8: a word in a UTF-16 file is missed.
- **Committed files only.** No file this repository ignores, such as `.DS_Store`, `.env` or `__pycache__/`, which would be on the author's disk but in no checkout. `git check-ignore --no-index` checks it when the suite's root is its repository's top level, as it is for `just validate-evals`; a copy of `evals/` outside any repository skips the check.
- **No `__pycache__`.** No file anywhere under the fixture's directory may have `__pycache__` in its path, as a directory or as its own name, whether or not the ignore check runs and whatever a nested `.gitignore` re-includes. `evals_sha256` leaves `__pycache__` out ([provenance](#benchmark)), so a fixture that differed only there would hash the same.

**Limits.**

- **One mode per path.** `executable` applies to every tree, so a fixture cannot change a file's mode between two commits.
- **Repository hooks.** Fixture trees are data, so ruff, mypy, pytest, markdownlint, Prettier and the `check-executables-have-shebangs`, `check-shebang-scripts-are-executable` and `check-merge-conflict` hooks skip them. `just lint`'s other hooks still check them: a tree's `.json`, `.toml` and `.yaml` files must parse (`check-json`, `check-toml`, `check-yaml`), so a fixture cannot ship a malformed one, and no file may be over 768 KB, hold a private key, or differ from another only in case.
- **Git writes on Codex.** Codex's sandbox does not let the agent write to `.git/`: a `git add` is reported as denied, and the trial is an infrastructure error ([run status](#codex)), so a flow that stages or commits cannot be scored on Codex. `git status` and `git diff` work. Observed on macOS only.
- **Deleted files and the grader.** The grader is not told about a fixture file the agent deleted ([grader](#grader)).

A change to anything in `evals/<skill>/fixtures/` changes the suite's `evals_sha256` ([provenance](#benchmark)), and `just eval-changed` selects the skill.

## Adapter interface

An adapter drives one agent CLI. The interface is `skills_tooling.evals.adapter.Adapter`, a `Protocol`. Claude Code and Codex implement it, and a future Pi adapter (`.scratch/future/issues/07-pi-adapter.md`) would too.

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
| `by_name_prompt(installed, request)` | A [by-name case](#by-name-cases)'s prompt in the skill arm: the agent's own invocation of the copy `install_skill` returned, then the request. |
| `run(prompt, trial, homes, *, model, timeout, credentials)` | Runs the prompt headless and returns a `RawRun`: exit code, timeout flag, transcript path, stderr, the kept discovery lines, the `python3` calls, the lines kept from Claude Code's session file, and whether any process survived teardown. |
| `discovery_report_problems(trace, trial, *, installed, system_root)` | Problems in the report of where the agent looked for skills. Claude Code reads its debug log. Codex reports nothing, so its adapter reads the locations themselves after the run. |
| `parse(raw)` | Normalises the event stream into a `Trace`: skills triggered and invoked, commands run with their output and status, the final message, CLI version, model, exit code, whether the stream ended normally, the run status and its reason, and the skills, plugins and commands the agent reported. |

`visible_skills` is `None` for an agent that does not report its skills. For such an agent (`reports_skills` false), the contamination proof rests on the redirected homes, the preflight's mitigated discovery locations and the canary sweep, and the results note it.

### Claude Code

- **Command:** `node_modules/.bin/claude -p <prompt> --output-format stream-json --verbose --model <model> --strict-mcp-config --permission-mode dontAsk --max-budget-usd 1.00 --debug-file <trial>/tmp/debug.log --allowedTools Skill Read Bash`. Stdin is `/dev/null`. `--bare` is not used because it accepts only an API key, and `--safe-mode` is not used because it disables skills. Session persistence stays on, in both arms, because the session file is the only local record of a slash command's expansion (**Session record**, below). Against the fake API, a run's request bodies with and without `--no-session-persistence` are the same apart from `metadata.user_id`, whose ids differ between any two trials anyway, and persistence adds no request. The [grader](#grader)'s runs keep `--no-session-persistence`.
- **Environment:** built from scratch. `HOME`, `CLAUDE_CONFIG_DIR` (`<home>/.claude`), the four `XDG_*` directories and `TMPDIR` point inside the trial. `PATH` is `<trial>/bin:/usr/bin:/bin`. `CLAUDE_CODE_DISABLE_CLAUDE_MDS`, `CLAUDE_CODE_DISABLE_POLICY_SKILLS`, `DISABLE_AUTOUPDATER`, `CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC` and `DISABLE_TELEMETRY` are all `1`. The Justfile's shared `CLAUDE_CONFIG_DIR` never reaches the child. `CLAUDE_CODE_SUBPROCESS_ENV_SCRUB` is not set: on Linux it requires `bubblewrap` and the CLI refuses to start without it. The CLI keeps the token out of its Bash tool's environment without it, which `test_secrets.py` checks on every platform. A [fixture](#fixtures) trial adds four Git variables ([isolation](#isolation)).
- **Session record:** the CLI writes each session to `<agent home>/projects/<directory>/<session id>.jsonl`. After the run, the adapter finds the file named by the init event's `session_id` in any project directory, so the CLI's directory name for the workspace path need not be rebuilt. The id must be letters, digits and `-`, and exactly one file may match. The adapter keeps only these lines and never stores the file; teardown removes it with the trial home:
  - `session <id>`, where `<id>` is the `sessionId` that every record carrying one shares. A file that is missing, unreadable or not JSONL, or whose records carry no id or different ones, gives no lines at all.
  - `skill_expanded <path>` for each `user` record with `isMeta: true` that comes before the session's first `assistant` record and has a text block starting `Base directory for this skill:`. `<path>` is the rest of that block's first line.

  `claude -p "/<name> <request>"` expands the skill into the first request's first user message: the `<command-name>` text, then `Base directory for this skill: <workspace>/.claude/skills/<name>`, the `SKILL.md` body without its frontmatter, and `ARGUMENTS: <request>`. The stream-json transcript has no event for this, and the debug log says nothing; the session file's `isMeta` record is the only local record of it. Text a tool prints, such as a Bash `printf` of the same `Base directory…` line, is stored in a `tool_result`, not an `isMeta` record, so it is not kept.
- **Trigger rule:** any of these counts, and a skill they record more than once is one trigger:
  - An assistant `tool_use` named `Skill` whose `input.skill` is `<name>` or `<plugin>:<name>`, and whose matching `tool_result` is not `is_error`. A model-initiated call of a skill that sets `disable-model-invocation` is refused with an `is_error` result, so it does not count.
  - A `skill_expanded` line whose path is exactly `{init.cwd}/.claude/skills/<name>`, compared as text, from the trial's own session record: the lines count only when they open with `session <id>` for the init event's `session_id`. This is the CLI's record that a [by-name](#by-name-cases) slash command injected the skill's text, written before the model replies.
  - A `Read` whose `file_path` is `{init.cwd}/.claude/skills/<name>/SKILL.md`, or that path relative to `cwd`, with a matching result that is not an error. The path is compared as text once normalised, never resolved: `./.claude/skills/<name>/../<name>/SKILL.md` and `{init.cwd}/./.claude/skills/<name>/SKILL.md` count, and `../.claude/skills/<name>/SKILL.md`, a nested `.claude/skills` or the trial home's skills do not.
  - A Bash command that passes Codex's read rule ([Codex](#codex), **Trigger rule**) for the skill, with a matching result that is not an error. The CLI reports a command that printed nothing as `(Bash completed with no output)`, and the rule reads that note as no output, so `tail -n 0 .claude/skills/<name>/SKILL.md` is not a read. As on Codex, the rule matches the skill by name in any skills directory, not only the installed copy.

  Together these are a lower bound on loads: the trace records only these shapes. `cat .claude/skills/<name>/SKILL.md | cat`, `awk`, an interpreter (`python3 -c 'print(open(…).read())'`), the `Grep` tool, or a copy read under another name can show the agent the skill's text and record no trigger, so a `should_trigger: false` pass means no confirmed load ([quiet cases](#by-name-cases)). One recorded read shows none of the text: `sed` is a reader whatever its script, so `sed -n = .claude/skills/<name>/SKILL.md`, which prints line numbers, counts. The session file sits in the trial home, which the agent's Bash tool can write, so an agent could in principle rewrite its own session record before its run ends.
- **Run status:** `infra_error` when the run timed out, a process survived teardown, the last event is not a `result` or a line did not parse, the `result` has `is_error: true`, or the exit code is nonzero. A failed login reports `subtype: "success"` with `is_error: true`, so `subtype` is never used. `apiKeySource` is `none` under OAuth too, so it is never used either. A run that is otherwise ok is also an `infra_error`, `no session record; failing closed`, unless its kept lines open with `session <id>` for the init event's `session_id`: with no session file, more than one, another session's, or one the adapter could not read, nothing shows whether a slash command expanded a skill. A record with no expansion in it is fine. An earlier reason, such as a timeout, is kept. The grader's runs are parsed without this check.
- **Built-in allowlist (2.1.309):** `batch claude-api code-review dataviz debug deep-research doctor fewer-permission-prompts loop plugin-authoring run run-skill-generator schedule simplify update-config verify workflow-authoring`. The plugins are `cc-plugin-agents-md@builtin` and `cc-plugin-plugin-authoring@builtin`. `schedule` is listed only when an OAuth token is set. A new CLI version fails the check with a hint to re-record the allowlist from the canary sweep.

### Codex

- **Command:** the pinned native binary that `node_modules/.bin/codex` would start (`node_modules/@openai/codex-<platform>/vendor/<triple>/bin/codex`), run directly so no Node is needed on the trial's `PATH`: `codex exec --json --ephemeral --ignore-user-config --ignore-rules --sandbox workspace-write --model <model> --cd <workspace> -c allow_login_shell=false -c project_doc_max_bytes=0 -c analytics.enabled=false --disable plugins --disable remote_plugin --disable apps -- <prompt>`. Stdin is `/dev/null`. The sandbox confines the agent's writes to the workspace and the trial's `TMPDIR`. On Ubuntu 23.10 and later, AppArmor blocks the unprivileged user namespaces the Linux sandbox needs, and Codex denies every command (`bwrap: loopback: Failed RTM_NEWADDR`), so every trial is an `infra_error` (see **Run status**). The fix is an AppArmor profile for the Codex binary, or `sysctl -w kernel.apparmor_restrict_unprivileged_userns=0`, which CI sets. `allow_login_shell=false` matters: a login shell runs the system profile, whose `path_helper` puts `/usr/bin/python3` ahead of the trial's `python3` wrapper. Plugins and apps are disabled because Codex otherwise syncs the account's remote plugins, with their skills, into its home mid-run.
- **Environment:** built from scratch, like Claude Code's. `HOME`, `CODEX_HOME` (`<home>/.codex`), the four `XDG_*` directories and `TMPDIR` point inside the trial. `PATH` is `<trial>/bin:/usr/bin:/bin` and `SHELL` is `/bin/bash`, though Codex runs commands in the account's login shell from the password database (`/bin/zsh` on macOS), with `-c` rather than `-lc`. `RUST_LOG=warn,codex_otel.log_only=info` makes Codex log its telemetry events to stderr. `--ephemeral` keeps session files off disk, but Codex still writes its SQLite state and a `config.toml` that trusts the workspace into the trial's `CODEX_HOME`. A [fixture](#fixtures) trial adds four Git variables ([isolation](#isolation)), and Codex sets `GIT_PAGER=cat` for the agent's commands.
- **Event stream:** `--json` writes JSONL: `thread.started`, `turn.started`, `item.started` and `item.completed` (items `command_execution`, `agent_message`, `error`), then `turn.completed` or `turn.failed`. A `command_execution` carries the command as `<shell> -c '<command>'`; the adapter removes the wrapper, so `script_ran` sees the agent's command. Its `aggregated_output` and `exit_code` are the tool result. The stream carries neither the CLI version nor the model.
- **Kept stderr lines:** four kinds, reduced to the fields named here, because telemetry lines can name the account. `codex.conversation_starts` gives `app.version` and `model`. `codex.skill_invocation` gives `skill.name`, `skill.scope` and `skill.invocation_type`. `codex.sandbox_outcome` gives `outcome`, plus `tool_name` and `call_id` for diagnosis; Codex logs it when a sandboxed command fails as denied, timed out or killed by a signal (`core/src/tools/orchestrator.rs` at `rust-v0.163.0`), and a working sandbox logged none in the recorded runs. `failed to load skill <path>: <reason>` is logged for a `SKILL.md` Codex cannot parse. The rest of the telemetry, including any continuation lines of a record, is dropped from the stored stderr, and a `failed to load skill` inside a telemetry record (tool output, say) does not count. Codex copies a tool's output into its `codex.tool_result` record raw and unquoted, with the record's remaining fields on the line after it, so a tool can print a line that looks like a record of Codex's. A stderr line that matches a line in the JSONL event stream, or is the start of one, or starts with one, is therefore never a record's first line: it continues the record above. Both are split only on `\n`, so a `\r` a tool printed starts no line.
- **Trigger rule:** Codex has no skill tool, so a trigger is a read of the skill's `SKILL.md`. Any of these counts:
  - A completed `command_execution` with `exit_code` 0 and nonempty output, whose command (split into simple commands as `script_ran` does) runs `cat`, `head`, `tail`, `sed`, `nl`, `less`, `more` or `bat` with a file argument naming `<skill>/SKILL.md` in a skills directory (one whose name ends in `skills`, or `.system`, or the path `dev-skills/build`). A `name=value` word is not a file argument. `awk` is not a reader, because whether it opens an operand depends on its program. The command's exit status and output must be the read's: the read is the last part, and only `cd <dir>` (not `cd -`, which prints the directory) and `pwd` may come before it, joined by `&&` (an operator at the end of a line counts too). `pwd` prints one line, so the output must have a line more than the `pwd`s print. Blank lines and the `==> <file> <==` headers `head` and `tail` print when given several files are not output here, so `tail -n 0 <skill>/SKILL.md README.md` does not count. After `||`, `;`, `&` or a pipe, or after any other command, the exit status and output no longer show what the read did, so such a read does not count, even alongside Codex's own event. Nor does a reader with a redirection (any word holding `<` or `>`, quoted or not, including `2>&1`) or a help or version flag (`--help`, `--version`, `-h`, `-V`), which can make it print something else or write the path. So the rule is a lower bound on reads: `cat .agents/skills/<skill>/SKILL.md | cat`, `awk`, an interpreter (`python3 -c 'print(open(…).read())'`) or a copy read under another name can show the agent the skill's text and record no trigger, and a `should_trigger: false` pass means no confirmed load ([quiet cases](#by-name-cases)). One read it counts shows none of the text: `sed` is a reader whatever its script, so `sed -n = <skill>/SKILL.md`, which prints line numbers, counts. The rule matches the skill by name in any skills directory, so a same-named skill elsewhere would count; the location checks, not the trigger rule, rule out a second copy. A preceding `cd <dir>` in the same command counts, so `cd .agents/skills/cowsay && sed -n 1,40p SKILL.md` is a read of `cowsay`. A failed read, a command that never completed, and a command that only names the path (`ls`, `test`, `echo`) do not count. A path whose skill directory the text cannot place (`../SKILL.md`, a glob, a variable) names no skill here, but can back Codex's implicit event (below).
  - A `codex.skill_invocation` event with `invocation_type="implicit"`, together with a completed command that passes the test above for the same skill, or whose reader names a `SKILL.md` the text cannot place (`cat SKILL.md` run with the skill's directory as `workdir`, `cat cowsay/SKILL.md` run in the skills directory, `../SKILL.md`, a glob or a variable) and whose output opens, after any `pwd` lines, with a `---` frontmatter block whose YAML `name` is the skill, as the validator reads it. Output that runs several files together shows only where the first starts, so only the first file's frontmatter counts; in a trial a glob prints the one installed skill. A placed `SKILL.md` of another skill, one outside a skills directory (`/tmp/cowsay/SKILL.md`), and an unplaced read that printed another file back no event. Codex logs the event while it parses the tool call, before the command runs (`core/src/tools/handlers/unified_exec/exec_command.rs` at `rust-v0.163.0`), from the command text and its skill list alone, and logs it for a run of a script in the skill's directory as well as for a read. So the event alone shows no read: under a sandbox that denies every command, Codex logs it for a read that never ran. An unplaced read that starts past the frontmatter (`sed -n '20,60p' SKILL.md` in the skill's directory) backs nothing, and a copy of the skill's frontmatter in another file would back the event.
  - A `codex.skill_invocation` event with `invocation_type="explicit"`. An explicit `$<name>` mention makes Codex inject the skill's `SKILL.md` into the request as a `<skill>` message, so no command reads it and nothing appears in the JSONL. The event is the only local evidence, which is why the adapter keeps it. A [by-name case](#by-name-cases)'s skill arm sends this mention, built from the installed copy's plugin name.

  The skill name may carry a plugin prefix: the shipped cowsay is named `cowsay:cowsay`, because Codex reads its `.claude-plugin/plugin.json` as a plugin manifest, so the explicit mention is `$cowsay:cowsay`. A bare `$cowsay` loads nothing explicitly. The adapter strips the prefix, as it does for Claude Code. A read and Codex's event for it are one trigger.
- **Run status:** `infra_error` when the run timed out, a process survived teardown, Codex failed to load a skill, Codex reported a command as denied by its sandbox (any `codex.sandbox_outcome` with `outcome=denied`), the last event is `turn.failed` (a failed login ends this way, after retries) or not `turn.completed`, a line did not parse, or the exit code is nonzero. `error` events alone do not fail the run: Codex reports each reconnect as one. A denied command leaves no `command_execution` item in the JSONL; its text is only in the `codex.tool_result` record, which the adapter drops whole because it carries raw tool output and account fields. A trace missing commands cannot be scored, as with a truncated stream, and recording the denial as a failed command would still let a `should_trigger: false` case pass on a run whose read the sandbox blocked. Any denial counts, including a legitimate one in a working sandbox, such as a write outside the workspace. Codex's test is a heuristic (`is_likely_sandbox_denied` in `sandboxing/src/denial.rs` at `rust-v0.163.0`): a sandboxed command that exits nonzero and whose output contains `operation not permitted`, `permission denied`, `read-only file system`, `seccomp`, `sandbox`, `landlock` or `failed to write file` is reported as denied, so an ordinary failure that prints `Permission denied` marks the trial too. A skill whose normal flow does that cannot be scored under Codex, and neither can one that writes to Git in a [fixture](#fixtures) trial: the sandbox denies a `git add` (observed on macOS).
- **Built-in allowlist (0.163.0):** the bundled skills Codex writes to `$CODEX_HOME/skills/.system` on startup: `imagegen openai-docs review-agent skill-creator skill-installer`. `review-agent` is written but not listed to the model. No plugins are allowed.

## Credentials

| Agent | Credential | How it reaches the run |
| --- | --- | --- |
| Claude Code | `CLAUDE_CODE_OAUTH_TOKEN`, from `just run ./node_modules/.bin/claude setup-token` ([how to export it](../how-to/run-evals.md#1-set-up-the-credentials)) | Read from the caller's environment and placed only in the child's environment. The harness writes it nowhere. The pinned CLI does not pass it on to its Bash tool's processes. |
| Codex | `auth.json` in the project's `CODEX_HOME` (`.tools/agent-homes/codex`, which the Justfile sets), from `just run ./node_modules/.bin/codex login` | Only `auth.json` is copied, mode 0600, into each trial's own `CODEX_HOME`. No skills, config or instructions come with it, and the user's `~/.codex` is never read. `--ignore-user-config` would skip a `config.toml` there anyway. `results.json` records `CODEX_HOME` as the credential's source. When the selected cases carry expectations, the run also needs `CLAUDE_CODE_OAUTH_TOKEN` for the [grader](#grader), and records that name too. |

The harness refuses to start without the token. Every file it writes under `eval-results/` passes through a scrub that replaces each credential value with `[REDACTED]`. The run then rereads every file, and deletes any that still holds a value and fails; a path it cannot read fails the run too, and its results directory is deleted. Owner access is restored first, and if anything still cannot be deleted, the run's error says so. After each trial, in a `finally`, the process group is killed and checked empty, the owner's access to the trial is restored, so output the agent locked can be swept and removed, and the trial's `home/`, `tmp/` and `bin/` are removed. The workspace is kept for inspection. If a credential value is found anywhere in the trial directory, in a file's contents or its path, the whole trial directory is deleted, the files are named in the trial's `secret_found`, and the trial fails. A path that stays unreadable fails the trial as an infrastructure error: it is deleted, transcript and all, and if the directory cannot be deleted, the trial's `status_reason` says so. The `PASS`/`FAIL` lines printed at the end are scrubbed the same way as the files. `results.json` records the credential's variable name, never its value. Codex's `auth.json` sits in the per-trial agent home, which the same `finally` removes, unless SIGKILL or power loss stops the harness first ([known limits](../explanation/eval-isolation.md#known-limits)). Every string in it except `auth_mode` and `last_refresh` (the API key, or the ChatGPT tokens and account id) is a secret for the scrub and the sweep. The agent's tools can read the copy while the trial runs, as they can read any file. If Codex refreshes a ChatGPT login mid-trial, it rewrites the trial's copy. The runner reads that copy back after the run and again before teardown, even when the run raised, and its new values join the scrub and the sweep for that trial and the rest of the run. The next trial starts from the refreshed copy, held in memory, so a provider that rotates the refresh token does not strand the rest of the run. If that copy cannot be read, the trial fails as an infrastructure error and is deleted, transcript and all. The refreshed copy is never written back, so the refresh may still invalidate the project's own login; if it stops working, log in again. A future Pi adapter (`.scratch/future/issues/07-pi-adapter.md`) would keep Pi's auth file in its per-trial agent home too.

## Isolation

Each trial gets `.eval-workspaces/<run-id>/<case-id>/<arm>-<n>/` (for example `behaviour-ship-it/skill-1/`) with:

- `workspace/`, a fresh `git init --initial-branch=main` that is its own git root, gitignored, and outside `skills/` and `dev-skills/`. It holds `.git/`, the installed skill and, in a [fixture](#fixtures) trial, the fixture's working files, nothing else.
- `home/`, the user home and the agent home.
- `tmp/`, the agent's temporary directory, transcript and debug log.
- `bin/`, holding `python3` and `python`, wrappers that run the harness's pinned interpreter, pass on a signal they receive as SIGTERM, and then log each call with its exit status, and `git`.

The preflight checks all of this before the agent starts, and fails closed. A baseline trial installs nothing, so its workspace may hold only `.git/` and its fixture's files.

**Git.** The harness's own Git calls, from the `git init` to a fixture's build, run with `HOME=/dev/null`, `GIT_CONFIG_GLOBAL=/dev/null`, `GIT_CONFIG_NOSYSTEM=1` and `GIT_ATTR_NOSYSTEM=1`, so they read no global or system config and no system attributes. The agent's Git runs in the trial's environment instead. Its global config would be in the trial home, which is empty, but without a fixture it reads the system config (Apple Git's sets `credential.helper=osxkeychain`, for one) and the system attributes. A fixture trial adds four variables to the agent's environment once the homes are prepared, in both arms and for both agents:

| Variable | Why |
| --- | --- |
| `GIT_CONFIG_NOSYSTEM=1`, `GIT_CONFIG_GLOBAL=/dev/null` | No machine's config changes what the agent's Git prints. |
| `GIT_ATTR_NOSYSTEM=1` | Git reads the system attributes even with `GIT_CONFIG_NOSYSTEM` set. Apple Git's, for one, change `git diff`'s hunk headers for `.m` files. |
| `GIT_OPTIONAL_LOCKS=0` | `git status` takes no optional lock, so it never tries to write the index, which Codex's sandbox does not allow. The build's refresh leaves it nothing to write anyway. |

The CLI is started with all four and passes them to the agent's commands (seen in Codex's, which also get `GIT_PAGER=cat`). A trial without a fixture keeps the environment it had.

**The preflight in a fixture trial.** The inventory compares the workspace with what the build wrote, each working file's SHA-256 and mode, and the workspace must be exactly that, plus `.git/` and the installed skill. The walk enters only directories that hold a fixture file, and never follows a link. Then `git status --porcelain -z --untracked-files=all`, run with `GIT_OPTIONAL_LOCKS=0` so that it leaves the index as the build left it, must name nothing under `.claude/` or `.agents/`, a rename's source included. The problems it reports:

| Problem | When |
| --- | --- |
| `unexpected in workspace: <path>` | A file or directory that is not the fixture's, `.git/` or the installed skill. Reported in every trial. |
| `changed in workspace: <path>` | A fixture file whose bytes or mode differ, or that is now a link, a directory or anything else but a regular file. |
| `missing from workspace: <path>` | A fixture file that is gone. |
| `git status lists paths under .claude/ or .agents/, which must be hidden: <entry>` | The installed skill shows in `git status`. `and <n> more` follows the first entry when there are several. |
| `git status failed in the workspace: <stderr>` | `git status` exited nonzero. |

A trial without a fixture runs neither the comparison nor the status check, so its skill arm's `git status` lists `?? .claude/` or `?? .agents/` ([known limits](../explanation/eval-isolation.md#known-limits)).

Trials run in rounds. In round n every case's trials run back to back, the skill arm first when n is odd and the baseline first when n is even, so order effects balance over an even trial count. Each trial records its `order` in the run.

## Contamination check

Each trial passes only when all of these hold:

1. **Reported skills.** The init event's skills, plus any command a `system/commands_changed` event adds, plus every skill the trace records as triggered (a successful `Skill` call, a slash command's expansion or a confirmed read, by the [trigger rule](#claude-code)), minus the recorded built-ins, is exactly the skill under test (empty for a baseline, which uses the same allowlist; the skill under test anywhere in a baseline's report fails it). The init event's plugins equal the built-in plugins, and a missing skill or plugin report fails closed.
2. **Discovery report.** In the debug log, the `user=` location sits inside the trial home, every `project=` location inside the workspace, and the managed location is missing or empty. The per-location counts are `managed: 0, user: 0, additional: 0` and `project: 1` (0 for a baseline). A missing report fails closed. Only these lines are kept, and the debug log is deleted.
3. **Never-appear list.** The repo's dev skills, the other shipped skills, and the user's own skills (directory names under `~/.claude/skills`, `~/.agents/skills`, `~/.codex/skills`, `~/.pi/agent/skills` and the caller's agent homes) must not appear among the reported skills. The discovery report is checked by location instead (step 2), so any skill directory outside the trial fails there. A name that collides with a built-in is noted, not failed. The repo's `AGENTS.md`, `CLAUDE.md` and the user's `~/.claude/CLAUDE.md` are listed too. They are kept out by the preflight's instruction-file check, because a live run cannot observe the request.

The canary sweep (`tests/evals/test_contamination_canaries.py`) shows the check fails when a canary sits in each location the agent reads, and that every other location stays isolated. The managed-location canary runs only in CI, because it writes to `/etc/claude-code`.

### Codex

Codex lists its skills only inside the model request, which a live run cannot observe, so `reports_skills` is false and the results note it. The steps become:

1. **Triggered skills.** Every skill the trace records as triggered (a successful read of its `SKILL.md`, an explicit `skill_invocation` event, or an implicit one backed by a successful read), and every skill a `skill_invocation` event names at all (the trace's `listed_skills`), minus the recorded built-ins, is at most the skill under test. Codex logs that event only for a skill in its own list, so it shows the skill was visible even when no read backs a trigger. A read alone does not: a failed read names a path the agent may have guessed. Reading a never-appear skill, such as a dev skill reached through `../`, fails, and so does Codex naming one, or naming the skill under test in a baseline.
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
- **Credential:** `CLAUDE_CODE_OAUTH_TOKEN`, the same token a Claude Code run uses. A Codex run whose selected cases carry expectations needs it too, and is a usage error without it. It joins the run's secrets, so the scrub and the sweep cover the grading files. A trial the sweep flags is never graded, and each finished material is scrubbed of every secret once more before it is sent, since removing a path can join the text on either side of it.
- **Blinded material:** the final message (capped at 20 KB) and every workspace file except `.git/` and the skills directory (20 KB each, 80 KB in all; non-UTF-8 files by name and size, symlinks by name, and a file or directory the agent left unreadable by name, so it cannot turn its trial into a grader error; the runner restores access before grading, so a locked file reaches the grader with its contents, and the name alone is only the fallback for a path that stays unreadable). The caps keep the whole prompt inside one Linux argument; a NUL becomes U+FFFD for the same reason. A lone surrogate, in the material or in the grader's evidence and notes, becomes U+FFFD too, since UTF-8 cannot encode it. The trial directory, which names the arm, and every skill-install prefix (`.claude/skills/<skill>/`, `.agents/skills/<skill>/`, `skills/<skill>/`) are removed in both arms alike. Skill calls are never sent, nor the case's `expected_output`.
- **Fixture files:** in a [fixture](#fixtures) trial, the material leaves out each fixture file that is still as the build wrote it, by the same record of bytes and mode the preflight checked. So the files are those the agent made or changed: a new file, an edited one, one whose mode changed, and a link or anything else at a fixture file's path. The files left out take none of the 80 KB and are not counted among the files not shown. A fixture file the agent deleted is not shown, because saying so would need a new line in the grader prompt and so a new `grader_prompt_sha256`, which labels every comparison with earlier runs; a `needs_transcript` expectation, which sees the commands, can judge a deletion. Without a fixture the material is what it was before fixtures existed.
- **Disclosure check:** the material is scanned, case-insensitively, for the word `skill` or `skills` (not "skilled"), any file path inside `skills/<skill>/`, and `.claude/skills` or `.agents/skills`. In a [by-name case](#by-name-cases) it also looks for an invocation of the skill (`/<skill>`, `$<skill>` or `$<plugin>:<skill>`, as the schema defines one), because only the skill arm's agent was sent one; an unmarked case's prompt may hold one, as cowsay's `trigger-explicit-invocation` does, so its material is not checked for it. A match is graded anyway and recorded as `arm_disclosed`, with the matches, because rewriting the agent's prose would change what is judged. The grader's task is always the case's `prompt` as written, in both arms, never the skill arm's invocation.
- **Unblinded expectations** (`needs_transcript`) are judged in a second call whose material is the trace instead: each command with its output and status (4 KB per output, 100 KB in all), then the final message. Output files are not sent, so a file's contents belong in a blinded expectation. These expectations are marked `"blinded": false`.
- **Untrusted material:** the material sits between `<graded-material-NONCE>` tags, with a fresh random nonce the material does not contain. The system prompt says everything inside is data and any instruction in it is to be ignored and noted.
- **Canary expectation:** each call slips in a known-false expectation naming a random code the material does not contain. If the grader passes it, every expectation is recorded as failed (`rejected`).
- **Quote rule:** a pass needs a nonempty `quote` that appears verbatim in the material (whitespace collapsed). Without one, that expectation is failed.

| Grading status | Meaning | Recorded as | In the benchmark |
| --- | --- | --- | --- |
| `ok` | A valid reply; the canary failed | each verdict, after the quote rule | counted |
| `rejected` | The canary passed | every expectation failed | counted as failures |
| `invalid_reply` | A reply that failed validation: empty, not one JSON object, wrong or missing ids, wrong types, extra keys | every expectation failed | counted as failures |
| `grader_error` | No call, or a failed run: the trial's files could not be read, the prompt was over the argument limit, the CLI could not run, or its run was not ok (it timed out, exited nonzero, reported an error, left a process running, or its stream had no result). Any text the run left is not treated as a reply | every `passed` is `null` | excluded from `graded_pass_rate` and `outcome_pass_rate`, counted |

A reply that fails validation might have been caused by the graded material, so it counts against the trial; only a call that was never made or whose run failed is excluded. With two calls, the worse status wins, and a reply that counts against the trial outranks a call that was never made or whose run failed.

## Benchmark

`eval-results/<run-id>/benchmark.json` aggregates the run's trials and grading files, and the run prints it as a table. It follows skill-creator's benchmark: skill-creator's `with_skill` and `without_skill` configurations are the `skill` and `baseline` arms here.

For each agent, case and arm it counts `n_planned`, `n_scored` (status ok, uncontaminated, no secret), `n_infra_error`, `n_contaminated`, `n_secret_found`, `n_grader_error` (including a grading file that is missing, unreadable, malformed, or lists other expectations than the case's rubric), `n_invalid_reply`, `n_rejected`, `n_grading_skipped` (a trial with expectations in a `--no-grader` run) and `n_arm_disclosed`. Each metric is `{mean, stddev, min, max, n}` over per-trial values:

| Metric | Per-trial value | Baseline arm |
| --- | --- | --- |
| `trigger_accuracy` | 1 when the trigger matched `should_trigger` | `not_applicable` |
| `skill_use_pass_rate` | skill-use assertions passed / total | `not_applicable` |
| `deterministic_pass_rate` | outcome assertions passed / total | measured |
| `graded_pass_rate` | expectations passed / total (0 for `rejected` or `invalid_reply`) | measured |
| `outcome_pass_rate` | outcome assertions and expectations together | measured |

- The **delta** is the skill arm's mean minus the baseline's, for the deterministic, graded and outcome rates only, as `{value, n_skill, n_baseline}` for each metric. `value` is `null` when either arm has no data. A case skipped in the baseline, and every case of a run without one, has an empty delta, `{}`. The agent's delta is `{value, n_cases}` for each metric.
- **Intention to treat:** a skill-arm trial in which the skill did not trigger still counts in its arm's outcome metrics.
- In a run with `grading_skipped`, a case with expectations has `null` graded and outcome pass rates, never an outcome rate over its assertions alone, which would not compare with a graded run; its notes say `grading skipped: graded and outcome rates not measured`, and the report shows `no data`.
- An infrastructure error, contamination or a secret found removes a trial from every metric. A grader error removes it from the graded and outcome rates only. Every exclusion is counted, never turned into a 0.
- `stddev` is the sample standard deviation, `null` below two values. A metric with nothing to measure is `null`, never 0.
- **Notes** flag fewer than three trials ("spread not meaningful"), a flaky trigger, an expectation that passed in every trial of both arms (non-discriminating), and, on a delta, unequal n, excluded grader errors, excluded infrastructure errors and trials whose material named the arm. Infrastructure errors are noted because an exclusion can depend on the arm: under Codex, a baseline agent that tries to install the tool it lacks can trip the sandbox's denial rule and become an infrastructure error. A run without a baseline has no delta; its per-arm counts still show both.
- **Per agent:** the trial-weighted mean of each metric over all cases, and the agent's delta as the mean of the per-case deltas, with the number of cases.
- No significance test or confidence interval is reported. With a few trials per arm the figures are descriptive.
- In the printed table, a case's baseline reads `off` when the run had no baseline arm, and `skipped` when the baseline ran without that case.

**Provenance**, recorded at the start of the run: the agent CLI versions and models the trials reported, the grader model requested and reported and its CLI version, `git_commit` and `git_dirty` (`git status --porcelain` is not empty; git runs without the user's config, except their global ignore file), `skill_sha256` (the sorted relative paths and bytes of `skills/<skill>/`, without `__pycache__`), `evals_sha256` (what the cases start from and are judged by: the SHA-256 of `evals/<skill>/evals.json` when the suite has no `fixtures/` directory, as cowsay's has not; otherwise the SHA-256 over that digest, the fixture format number, which changes whenever the build makes something else of the same fixture, and the sorted relative paths and bytes of everything in `evals/<skill>/fixtures/`, without `__pycache__`, so every fixture counts, named by a case or not, and so does a stray file such as `.DS_Store` that a clean checkout lacks), `grader_prompt_sha256`, the trial count, whether the baseline ran, and the cases it skipped.

## History and report

`just eval-record <name> <run-id>...` records finished runs, one per agent, as an **iteration** of their skill: `benchmarks/<skill>/<name>.json`, committed ([ADR 0014](../adr/0014-benchmark-history.md)). It holds each run's `run_id`, `agent`, `started_at`, `trials_per_case`, `baseline`, `provenance`, the `cases` from `results.json`, and the agent's block of `benchmark.json`. It refuses a name that is already recorded, a run already recorded in another iteration of the skill, a name that does not start with a letter or digit, that has characters other than letters, digits, `.`, `_` and `-`, or that is `unrecorded`, which the report reserves for runs shown with `--run`, a run without a `benchmark.json`, two runs of one agent, and runs that differ in skill, `skill_sha256` or `evals_sha256`, so two runs whose fixtures differ are two iterations. Runs of one case file that selected different cases with `--case` are allowed; a case one agent did not run shows as `case not run`. Iterations are ordered by their latest run's `started_at`, then `recorded_at`, then name, so a backfilled run takes its true place.

`just eval-report [skill]` reads `benchmarks/`, every skill or the one named, and writes one self-contained page, `eval-results/report.html` (or `--out <path>`): inline CSS, no script, nothing fetched. It calls no agent and no network. For each skill it shows:

- **Agents by cases**, for the latest iteration, with a column for every agent the harness runs, benchmarked or not: each case's expectation (trigger or no trigger), and per agent its trigger accuracy, its pass rate (`outcome_pass_rate`: outcome assertions and expectations together) and that pass rate's delta against the baseline, each as mean ± stddev (n), with a row over all cases.
- **Delta against the baseline** per agent: the agent's deterministic, graded and outcome deltas, with the number of cases behind each.
- **Provenance** per iteration and agent: the run, the agent CLI versions, the requested and reported agent models, the requested and reported grader models, the grader CLI versions, trials per case, whether the baseline ran, and the commit.
- **History** per agent: every metric and delta, over all cases and per case, in every iteration that measured it.

Missing data is shown by its reason, never as 0, never averaged and never compared: `not run` (the agent was not in that iteration), `case not run` (its run did not include the case), `no scored trials` (every trial was excluded), `n/a` (nothing of that kind to measure, such as a pass rate for a trigger-only case), `no baseline` (the run had no baseline arm), and `no data` (trials were scored but none measured it, such as when every grading failed).

**Regressions.** For each agent, the report compares the agent's last two benchmarks of the skill, by when the agent's own run started, which need not be the last two iterations. A run that appears twice, such as a recorded run passed again with `--run`, counts once. Any metric or delta that fell by more than `--threshold` (default 0.1, between 0 and 1) is flagged, in the page and on stdout. A value missing on either side is never flagged. Each flag carries labels when the comparison is not like-for-like, and the page's line for each agent's comparison lists every label that applies to all its figures, plus `case changed` when any case it ran on both sides changed, or says `like-for-like`:

| Label | When | On |
| --- | --- | --- |
| `cases or rubric changed` | `evals_sha256` differs: the cases, the rubric, a fixture or the fixture format | every metric |
| `agent model changed` | the requested model or the reported models differ | every metric |
| `agent CLI version changed` | the reported CLI versions differ | every metric |
| `grader prompt changed`, `grader model changed`, `grader CLI version changed` | the grader's prompt hash, requested or reported model, or CLI version differs | graded and outcome metrics and their deltas |
| `case changed` | the case's kind, `should_trigger` or expectations differ | that case |
| `case set changed` | the runs ran different cases | the figures over all cases |
| `measured over different cases` | the cases with a value for that metric differ, such as a case whose every trial was excluded on one side | the figures over all cases |

A new `skill_sha256` or commit is the change being measured and carries no label. A reported list that is empty on one side (no grading ran) is not a difference. A flag on fewer than three values on either side also says `thin sample`. `--fail-on-regression` exits 1 when any metric is flagged, labelled or not; without it the report exits 0. A usage error exits 2.

`--markdown <path>` also writes each skill's agents-by-cases matrix and its regressions as Markdown, which the live-eval CI job appends to its summary.

`--run <run-id>` (repeatable, one per agent) adds finished runs from `eval-results/` as a last, unrecorded iteration, without writing it, so a change can be checked against the last recorded benchmark before it is recorded.

## Results

`eval-results/<run-id>/` holds:

- `results.json`, the run record below
- `transcripts/<case>/<arm>-<n>.jsonl`, each trial's transcript, scrubbed
- `grading/<case>/<arm>-<n>.json`, each graded trial's grading
- `benchmark.json`

| Run field | Meaning |
| --- | --- |
| `run_id`, `skill`, `agent`, `requested_model` | What ran. |
| `credential_env` | The names of the caller's variables the credentials came from: `CLAUDE_CODE_OAUTH_TOKEN`, or `CODEX_HOME` for Codex's `auth.json`, plus the grader's `CLAUDE_CODE_OAUTH_TOKEN` when the cases carry expectations and grading is not skipped. |
| `started_at`, `finished_at` | UTC, ISO 8601. |
| `passed` | Every skill-arm trial passed and every baseline trial is valid. |
| `trials_per_case`, `baseline`, `grader_model_requested`, `grading_skipped` | The run's configuration. `grader_model_requested` is `null` when no case was graded; `grading_skipped` is `true` for a `--no-grader` run (absent from runs before it existed, which read as `false`). |
| `cases` | Each selected case's `id`, `kind`, `should_trigger`, `expectations` (`text`, `blinded`) and `in_baseline`. |
| `skipped_in_baseline` | Case ids with nothing for a baseline to measure. |
| `provenance` | The provenance above that is known at the start. |
| `trials` | One record per trial, below, in run order. |

| Trial field | Meaning |
| --- | --- |
| `case`, `kind`, `agent` | The case and the agent. |
| `arm`, `trial`, `order` | `skill` or `baseline`, the trial's number n in its arm, and its 0-based position in the run. |
| `cli_version`, `model` | What the agent reports running: Claude Code's init event, or Codex's `codex.conversation_starts` event. A `--model` alias shows the model it resolved to. |
| `prompt` | The exact string the agent was sent: the case's `prompt`, or in a [by-name case](#by-name-cases)'s skill arm the agent's invocation followed by it. `null`, like `cli_version` and `model`, when the trial stopped before its run was recorded: after a failed preflight, or a harness error during or after the run. |
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
