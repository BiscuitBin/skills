# 17: Eval cases can invoke a skill by name

**What to build:** an eval case marked as invoked by name gets each agent's own invocation syntax in the skill arm and the bare request in the baseline arm, and the trace records the trigger. A plain request, with `should_trigger: false`, shows that a by-name-only skill stays quiet.

Why: the `change-viz` skill (ticket 18) loads only when the user names it. The harness cannot score that today. On Claude Code a trigger is a `Skill` tool call, which a by-name-only skill should never produce. And one prompt goes to both arms, so an invocation prefix written into the prompt reaches a baseline agent that has no such skill.

**Blocked by:** none (can start immediately, in parallel with 16).

Tickets 16 and 17 do not depend on each other, but both edit the case loader, `docs/reference/evals.md` and `GLOSSARY.md`. Whichever lands second rebases onto the first.

**Status:** ready-for-agent

**Agent requirements:** Any implementing agent (Claude Code or Codex). The spike prefers the pinned CLIs against the local fake API, which records each request and costs nothing. One live trial per agent then confirms it: the maintainer runs those in their own terminal, with the token, from absolute-path commands the agent hands over. Cross-model review is also required.

## What is known

As of 2026-11-10. Pinned CLIs: Claude Code 2.1.309, Codex 0.163.0 (`package.json`).

Read in the code and docs:

- **Claude Code's trigger rule** is an assistant `tool_use` named `Skill` whose `input.skill` is the skill, with a result that is not an error (`docs/reference/evals.md`, **Claude Code**). The adapter also keeps the slash commands the CLI lists at startup.
- **Codex's trigger rule** counts a successful read of the skill's `SKILL.md`, or a `codex.skill_invocation` event with `invocation_type="explicit"`. An explicit `$<name>` mention makes Codex inject the `SKILL.md` into the request, so the event is the only local evidence.
- **Codex's plugin prefix:** the shipped cowsay is named `cowsay:cowsay`, because Codex reads its `plugin.json` as a plugin manifest. The explicit mention is `$cowsay:cowsay`, and a bare `$cowsay` loads nothing explicitly.
- **The one explicit case today** is cowsay's `trigger-explicit-invocation`, whose prompt carries `$cowsay:cowsay`. Cowsay allows implicit invocation, so nothing shows what Codex does with an explicit mention of a skill that forbids it.
- **By-name-only settings:** the validator accepts `disable-model-invocation` in `SKILL.md` (Claude Code supports it, Codex ignores it) and `policy.allow_implicit_invocation` in `agents/openai.yaml`. humanlayer's `show-me` sets both.
- **One prompt per case.** The same `prompt` goes to both arms and to the grader's call (`grader.py` passes `case.prompt`).
- **Contamination:** Codex naming the skill under test in a baseline trial fails the trial.
- **Trigger** in `GLOSSARY.md` covers an agent loading a skill on its own, plus Codex's explicit `$<name>` mention. It says nothing about Claude Code by name.

Hypotheses for the spike, not tried:

- `claude -p "/<name> <request>"` loads a skill that sets `disable-model-invocation: true`.
- `$<name>:<name> <request>` loads a Codex skill that sets `allow_implicit_invocation: false`, and Codex logs the `explicit` event for it.
- A plain request that matches the description loads neither.

## The spike comes first

Make a throwaway by-name-only skill (both settings above) and answer these on both pinned CLIs. Do not commit the skill unless it becomes a test fixture.

- **Claude Code:** does `/<name> <request>` load the skill headlessly? Does the name need a plugin prefix? What does the event stream show: a `Skill` tool call, an injected message, an entry in the startup command list, or nothing?
- **Codex:** does `$<name>:<name> <request>` load it and log the `explicit` event? Is the plugin prefix still needed?
- **Both, plain request:** does the agent see the skill's description at all? Does it load the skill anyway? On Codex, can it still read the `SKILL.md` from the workspace on its own, which the trigger rule would count?
- **Both, baseline:** what does an agent with no skill do with the prefixed prompt? This is the case the new marking avoids, and the answer says how much it matters.

**Stop condition:** if either CLI cannot load a by-name-only skill headlessly, the ticket stops and comes back to the maintainer before 18 starts. Record what was tried and what each CLI did. The alternative the maintainer was offered is a skill that loads on matching requests, which needs none of this ticket.

## Acceptance criteria

- [x] The spike's answers are recorded here, with the CLI versions and the transcripts or fake-API requests that showed them.
- [x] A case can be marked as invoked by name. The schema rejects the marking on a case whose `should_trigger` is `false`, and the field's name comes from the design checkpoint.
- [x] For a marked case the skill arm's prompt is the agent's own syntax followed by the request, built by the adapter. The case's `prompt` holds only the bare request, with no agent's syntax in it.
- [x] The baseline arm gets the bare request, and so does the grader in both arms. Nothing the grader is sent differs between the arms because of the prefix.
- [x] The trace records the trigger for a by-name invocation on both agents, so `skill_triggered` passes and the case counts in trigger accuracy. On Claude Code this needs whatever evidence the spike found, and the trigger rule in `docs/reference/evals.md` says what it is.
- [x] A plain request with `should_trigger: false` passes on both agents against a by-name-only skill: no trigger is recorded. A trial where the agent loads the skill anyway fails the case.
- [x] Results record the prompt each arm was actually given, or enough to rebuild it.
- [x] Cowsay's suite still passes. Whether `trigger-explicit-invocation` moves to the new marking is decided at the design checkpoint, because editing `evals/cowsay/evals.json` changes its `evals_sha256`.
- [x] Regression tests drive both parsers from recorded transcripts of a by-name invocation and of a quiet plain request, kept under `tests/fixtures/evals/`. They run in `just check` on any OS, with no agent and no network.
- [x] Docs and records:
  - `docs/reference/evals.md`: the case schema, both trigger rules, and what the baseline arm gets.
  - `GLOSSARY.md`: **Trigger** covers a by-name invocation on both agents.
  - An ADR, if the design changes what a trigger is.
- [ ] Shown working: one live trial per agent of a marked case, and one of a quiet plain request, with the run ids recorded here.
- [x] `just check` passes.

## Out of scope

Description-routing evals and description optimisation (deferred in `.scratch/foundation/follow-ups.md`), Pi, and the `change-viz` skill itself.

## Review checkpoints

Use the `cross-model-review` dev skill.

- **Design checkpoint:** after the spike and before building, write up the spike's answers, the schema field, how each adapter builds the skill arm's prompt, and the trigger evidence on each agent, and get them reviewed. Can a trial pass `skill_triggered` without the skill's text reaching the model? Can the prefix reach the baseline arm or the grader?
- **Implementation checkpoint:** before marking done, review the full diff against these acceptance criteria. Pay particular attention to triggers that rest on the prompt text alone, to anything that tells the grader which arm it is reading, and to cowsay's results changing.

## Spike answers

Run on 2026-11-10 against the pinned Claude Code 2.1.309 and Codex 0.163.0, through the adapters, against the local fake APIs (`tests/evals/fake_anthropic.py`, `fake_openai.py`). The throwaway skill set `disable-model-invocation: true` in `SKILL.md` and `policy.allow_implicit_invocation: false` in `agents/openai.yaml`, and had a `.claude-plugin/plugin.json`, as `just new-skill` writes. The recordings are committed as the `fake-by-name*` fixtures under `tests/fixtures/evals/{claude,codex}/`, which the parser tests drive. **The stop condition is not met:** both CLIs load a by-name-only skill headlessly.

**Claude Code.**

- **`claude -p "/<name> <request>"` loads the skill**, with no plugin prefix. The first request's first user message holds two text blocks: `<command-message><name></command-message>` `<command-name>/<name></command-name>` `<command-args><request></command-args>`, then `Base directory for this skill: <workspace>/.claude/skills/<name>`, the `SKILL.md` body without its frontmatter, and `ARGUMENTS: <request>`.
- **The stream-json transcript shows none of it.** The events are `system/init`, `assistant`, `rate_limit_event` and `result`. There is no `user` event, `--include-hook-events` adds nothing, and the debug log says nothing about the expansion. So the hypothesis that the trigger would show in the stream was wrong.
- **Where the evidence is.** With `--no-session-persistence` dropped, the session file `<home>/.claude/projects/<cwd slug>/<session>.jsonl` holds the `<command-name>` user record and then a `user` record with `isMeta: true` whose text is the `Base directory for this skill: …` block: the injection itself. The fake-API request bodies with and without persistence are identical apart from the per-home random `device_id` in `metadata.user_id`, so persistence does not change what the model sees. `--input-format stream-json --replay-user-messages` (the prompt over stdin) replays only the `<command-name>` text, not the body.
- **What the stream does show.** `init.skills` and `init.slash_commands` both list the skill in the skill arm. `init.plugin_warnings` reports the installed copy's `.claude-plugin/` as a project-scope plugin directory skipped as untrusted.
- **Plain request:** the skill is in neither the `Skill` tool's listing nor anywhere else in the request, by name or description, so the model is not told it exists. A model-initiated `Skill` call is refused with an `is_error` result (`Skill <name> cannot be used with Skill tool due to disable-model-invocation…`), which the parser records as invoked, not triggered. A `Read` of the installed `SKILL.md` succeeds and is not a trigger under today's rule.
- **Baseline, prefixed prompt:** the CLI adds a reminder, "The user's message starts with the slash command `/<name>`, but no command with that name is available in this session, so it did not run…", and sends the raw text on.
- With session persistence on, none of the plain request, the refused call, the `Read`, the baseline and a Bash `printf` of the `Base directory for this skill: <workspace>/…` line wrote an `isMeta` record. The printed line appears only inside a `tool_result`.

**Codex.**

- **`$<plugin>:<skill> <request>` loads the skill** and logs `codex.skill_invocation … skill.invocation_type=explicit`. The prefix is the `name` in `.claude-plugin/plugin.json` and the suffix the skill's name: with the plugin renamed `brief-kit`, `$brief-kit:branch-brief` loads and both `$branch-brief:branch-brief` and `$branch-brief:brief-kit` load nothing. Codex injects the whole `SKILL.md`, frontmatter included, as a second user message `<skill><name><plugin>:<skill></name><path>…/SKILL.md</path>…`.
- Without `plugin.json`, the bare `$<name>` loads it and the prefixed form loads nothing.
- **Plain request:** the skill is not listed to the model, by name or description, and no event is logged. A `cat .agents/skills/<name>/SKILL.md` the model runs anyway is a trigger under today's rule, and Codex logs `implicit` for it, so a quiet case fails when the agent reads the skill.
- **Baseline, prefixed prompt:** passed through as text, with no event and no error.

**How much the baseline marking matters.** On both agents a prefixed prompt in the baseline tells the model a named tool or command was asked for and is missing: Claude Code says so in a reminder, and Codex passes the `$…` text through. A baseline sent the prefix would be measured on a different request, which is the case the marking avoids.

## Completion notes

### Design checkpoint

- **Implementer:** Claude Code running Claude Opus 5.5 (`claude-opus-5-5`)
- **Reviewer:** Codex `gpt-6-astra` (fallback: no)
- **Reviewed:** design proposal `ai_tmp/design-17.md` at base `bd67179`, after the spike and before any code
- **Findings:** `ai_tmp/review-20261111T053533Z-codex.md` · **Triage:** `ai_tmp/triage-design-17.md`

The section numbers in the table are the design doc's.

| # | Severity | Finding | Verdict | Action |
| --- | --- | --- | --- | --- |
| 1 | high | The shared read rule permits false triggers (`sed -n = …/SKILL.md`) and misses actual loads (`cat …/SKILL.md \| cat`) | valid (medium is closer) | Section 4: a trigger is now the CLI's injection record, a `Skill` call or a confirmed read, stated as a lower bound (apart from the `sed` exception) with the confirmed shapes listed; ADR 0017 retitled; section 5 points at the open `sed` choice; section 8 item 3 tests the piped read; section 9 states the lower bound in the docs and GLOSSARY. The transforming-`sed` false trigger is left to the maintainer, (a) tighten or (b) state the limit (questions 1 and 2). Decided 2026-11-10: (b), and the lower bound accepted (see Maintainer decisions). |
| 2 | medium | Checking only the first word does not keep invocation syntax out of marked prompts | valid (low is closer) | Section 1: a `by_name` prompt holding `/<skill>`, `$<skill>` or `$<plugin>:<skill>` anywhere, as a whole token, is rejected, through one shared `invocation_mentions` pattern with its boundary spelled out; by-name cases only. Section 8 item 1: mid-prompt rejections, path and `$HOME` acceptances, and an unmarked case accepted. |
| 3 | medium | Disclosure detection does not stop the prefix reaching the grader | valid, as a wording and test gap (low is closer) | Section 2: narrowed to "the harness never sends the prefix to the grader: every grader request's prompt is `case.prompt`". Section 6: an agent's echo is arm-revealing prose, preserved under ADR 0012 and flagged `arm_disclosed` through `disclosure_matches(..., invocation_of=)`; redaction ruled out. Section 8 item 6: a grader test. Ticket line 52's wording is maintainer question 3. Decided 2026-11-10: accepted (see Maintainer decisions). |
| 4 | medium | Claude's expansion evidence is discarded before results can be audited | out of scope | No design change. No criterion requires the raw trigger evidence to persist, and Codex's `explicit` evidence is not persisted today either (`stored_stderr` drops telemetry, `codex.py:338`, `codex.py:453-455`). A trial-record field holding both agents' kept trigger lines is a follow-up for its own ticket. |

No second round: the fixes narrow claims, add a `by_name`-only prompt check and a disclosure keyword, and add tests. No trigger rule, mechanism or data format moved, and the maintainer's choice of (b) below keeps the read rule unchanged on both agents.

**Maintainer decisions (2026-11-10):** the three questions round 1 left open, each decided as recommended.

1. **The read rule.** Keep the shared read rule (`skills_read` and `outcome_is_the_read`) unchanged and state its limits (option (b)): a transforming `sed` such as `sed -n = SKILL.md` counts as a read, and a read through a pipe does not count. Codex's rule and cowsay's results do not change. Option (a), tightening the `sed` test, is not taken.
2. **Quiet cases.** The criterion "A trial where the agent loads the skill anyway fails the case" is accepted as a lower bound: it holds for the loads the trace can confirm, which are a `Skill` call, the slash expansion record, or a read whose output shows it read. The docs say so, and the quiet cases' transcripts get a hand read at each live run.
3. **Grader echo.** The criterion "Nothing the grader is sent differs between the arms because of the prefix" is accepted in this form: the harness never sends the prefix to the grader. An agent's own echo of the invocation is graded as it is and flagged `arm_disclosed` by the invocation match (`/<skill>`, `$<skill>` or `$<plugin>:<skill>`), as ADR 0012 requires.

**Follow-ups:**

- A trial-record field holding both agents' kept trigger lines (Claude Code's `skill_expanded` line, Codex's `explicit` event), so a trigger can be audited after teardown (finding 4). It needs its own ticket.

**Design as approved:** `ai_tmp/design-17.md` (gitignored), with round 1's fixes and the decisions above. An implementer follows these decisions:

- **Schema.** A case may set `"by_name": true`, on a trigger or a behaviour case. It is true-only (`false` is rejected; leave the key out) and rejected beside `should_trigger: false`. A marked case's prompt is the bare request: it is rejected when its first word starts with `/` or `$`, or when it holds an invocation of the suite's skill anywhere. One shared `invocation_mentions(text, skill)` in `cases.py` finds an invocation: `/` or `$`, an optional `<plugin>:`, then the skill's name as a whole token, ignoring case, so `src/<skill>/x.py`, `docs/<skill>.md`, `~/<skill>` and `$HOME` do not match. Unmarked cases are not checked.
- **Prompts.** The `Adapter` protocol gains `by_name_prompt(installed, request)`. Claude Code gives `/<name> <request>`. Codex gives `$<plugin>:<name> <request>`, where `<plugin>` is the `name` in the installed copy's `.claude-plugin/plugin.json`, or `$<name> <request>` when the copy has none. `runner._attempt` uses it in a marked case's skill arm only; the baseline arm gets `case.prompt`, and so does every grader request. Every trial record gains `"prompt"`, the exact string the agent was sent.
- **Claude Code's by-name evidence.** The agent's run drops `--no-session-persistence`, in every trial and both arms; the grader keeps it. After the run the adapter reduces the session file `<agent home>/projects/<slug>/<session_id>.jsonl`, with `session_id` from `system/init`, to a new `RawRun.session_lines`, and never stores the file. The first line is `session <session_id>`, then one `skill_expanded <path>` line per `user` record that has `isMeta: true`, comes before the first `assistant` record and has a text block starting `Base directory for this skill:`. `ClaudeCode.parse` makes the trial `infra_error` ("no session record; failing closed") unless the lines open with `session <id>` for the init event's id. A `skill_expanded` path equal to `{init.cwd}/.claude/skills/<skill>` is a trigger. Stated limit: the agent's Bash tool could rewrite its own session file.
- **Confirmed reads on Claude Code.** A non-error `Read` of `{init.cwd}/.claude/skills/<skill>/SKILL.md`, or that path relative to `cwd`, is a trigger, and so is a non-error Bash command that passes Codex's read rule (`skills_read` and `outcome_is_the_read`, moved unchanged from `codex.py` to a shared module). ADR 0017, **A trigger is the CLI's injection record or a confirmed read of the skill**, records the rule as a lower bound with its limits: a transforming `sed` counts, and a pipe, `awk`, an interpreter or the `Grep` tool does not. Codex's rule does not change.
- **Disclosure and cowsay.** `disclosure_matches` gains a keyword-only `invocation_of`. For a marked case the grader passes the skill's name, so an echoed `/<skill>`, `$<skill>` or `$<plugin>:<skill>` is flagged `arm_disclosed` and not redacted. Contamination is unchanged. Cowsay's `trigger-explicit-invocation` keeps its `$cowsay:cowsay` prompt and stays unmarked, so `evals/cowsay/evals.json` and its `evals_sha256` do not change.
- **Live trials.** They run in ticket 18's RED run (the maintainer's Hand-off 1), which includes a marked case and a quiet plain request on `change-viz`. This ticket stays open until that run is read, with the quiet cases' transcripts read by hand, and its run ids are recorded here.

### Implementation checkpoint

#### What was built

Commits `4a295e8..de9d947`, then the review fix `115ba26` and a test, `37ec5a1`.

- **Schema** (`cases.py`): a case may set `"by_name": true` on a trigger or a behaviour case. Any other value is rejected, and so is the marking beside a `should_trigger` that is not `true`. A marked prompt is rejected when it starts with `/` or `$`, or holds an invocation of the skill. `invocation_mentions` is defined in `grader.py`, because `cases` imports `fixture`, which imports `grader`. The loader and the disclosure check share it.
- **Prompts** (`adapter.py`, `claude_code.py`, `codex.py`, `runner.py`): `Adapter.by_name_prompt(installed, request)` gives `/<name> <request>` on Claude Code. On Codex it gives `$<plugin>:<name> <request>` from the installed `plugin.json`, the bare `$<name>` with no manifest, and a `ValueError` for a manifest that names no plugin. `runner._prompt` uses it in a marked case's skill arm only. The baseline arm and every grader request get `case.prompt`. Every trial record gains `"prompt"`, null when no run was recorded. A marked skill arm with no installed copy is an `infra_error`.
- **Claude Code's evidence** (`claude_code.py`): the agent's run drops `--no-session-persistence`, and the grader keeps it. `session_lines` reduces the one session file named by init's `session_id` to `session <id>` and `skill_expanded <path>` lines in `RawRun.session_lines`. Nothing else is stored. `ClaudeCode.parse` fails an otherwise-ok trace closed without them. A trigger is a `Skill` call, a `skill_expanded` path of `{init.cwd}/.claude/skills/<skill>`, a non-error `Read` of the installed `SKILL.md` (compared once normalised, never resolved; review finding 1), or a Bash read that passes the shared rule, with the CLI's `(Bash completed with no output)` note counted as no output.
- **Shared read rule** (`src/skills_tooling/evals/reads.py`, new): `skills_read` and `outcome_is_the_read` moved unchanged from `codex.py`. Codex's trigger rule does not change.
- **Disclosure** (`grader.py`): `disclosure_matches(..., invocation_of=)` flags an echoed `/<skill>`, `$<skill>` or `$<plugin>:<skill>` in a marked case as `arm_disclosed`. Nothing is redacted, and `prompt_sha256` does not change.
- **Recordings:** the spike's runs, as `tests/fixtures/evals/claude/fake-by-name{,-quiet,-refused,-read,-forged,-baseline}.{jsonl,session.jsonl}` and `tests/fixtures/evals/codex/fake-by-name{,-quiet,-read,-baseline}.{jsonl,log}`.
- **Tests:** `test_cases.py`, `test_claude_parser.py`, `test_codex_parser.py`, `test_grader.py`, `test_runner.py`, `test_contamination.py` and `test_codex_adapter.py` (the Codex prompt forms). `test_claude_adapter.py` runs the pinned Claude Code against the fake API: the slash expansion triggers through the session record, the session file is found by init's id, and with persistence on only `metadata.user_id` differs between request bodies.
- **Docs and records:** `docs/reference/evals.md` (**By-name cases**, the schema, both trigger rules, the session record, the trial's `prompt`, the disclosure check), `docs/explanation/eval-isolation.md`, `GLOSSARY.md` **Trigger**, and ADR 0017, **A trigger is the CLI's injection record or a confirmed read of the skill**, with its row in `docs/adr/README.md`.
- **Cowsay:** `evals/cowsay/evals.json` is not edited, and `trigger-explicit-invocation` stays unmarked.
- **Departures from the approved design:**
  - The session file is found by glob, `<agent home>/projects/*/<session_id>.jsonl` with exactly one match, not by rebuilding the CLI's slug. The `session <id>` line comes from the records' `sessionId`.
  - Failing closed applies only to an otherwise-ok trace, so an earlier reason, such as a timeout or a nonzero exit, is kept.
  - On Claude Code a `Read` or Bash read also adds to `skills_invoked`, and both skill lists are deduplicated, as on Codex.
  - The Bash tool's no-output note counts as no output. A probe of the real CLI found it: without the rule, `tail -n 0 SKILL.md` counted as a read.
  - Codex's `by_name_prompt` refuses a manifest that names no plugin.

#### Checks run

- `just check` on `a083291` (this branch, with ticket 16, both tickets' review fixes and ticket 16's /code-review fixes; this ticket had none): passed, exit 0. pytest: 1202 passed, 4 skipped. The skips are the two runs of the on-disk case-clash test, because macOS folds case, and the two CI-only canaries. Every other step passed, including `validate-evals` (1 suite valid) and the version check (Claude Code 2.1.309, Codex 0.163.0). Log: `ai_tmp/gate-cr.log`.
- Before the /code-review, `just check` passed on `37ec5a1`: 1195 passed, 4 skipped (`ai_tmp/gate-16-17.log`).
- Before the cross-model review, `just check` passed on `de9d947`: 1184 passed, 4 skipped (`ai_tmp/verify-17-check.log`). Each criterion was checked against the code and the tests (`ai_tmp/impl-17-progress.md`, **Verify**).
- The review fix was red first: the three new absolute `Read` rows gave `([], [])`, and the guard row passed before and after. `37ec5a1`'s test passed on arrival, because the code already existed, and failed with `skills_triggered` taken out of contamination's `seen`.
- Not run: Ubuntu CI, because nothing was pushed, and the live trials (below).

#### Cross-model review

- **Implementer:** Claude Code running Claude Opus 5.5 (`claude-opus-5-5`)
- **Reviewer:** Codex `gpt-6-astra` (fallback: no)
- **Reviewed:** `4a295e8..de9d947`
- **Findings:** `ai_tmp/review-20261111T103637Z-codex.md` · **Triage:** `ai_tmp/triage-impl-17.md`
- **Preconditions:** a `pytest` process from another session, in a different repository, was running. It had no file open in this worktree, and the worktree was clean after the review, so the run counts.

| # | Severity | Finding | Verdict | Action |
| --- | --- | --- | --- | --- |
| 1 | medium (triage: low) | `_skill_md_read` removed the `{cwd}/` prefix before normalising, so a `Read` of the installed `SKILL.md` by an absolute path with `.`, `..` or `//` around the prefix was not a trigger, and a quiet case could pass a trial that read the skill | valid: no recording shows such a path, and it only adds to a lower bound the maintainer accepted | fixed in `115ba26`: the path and `cwd` are normalised, then the prefix is removed. The docstring says "once normalised, never resolved", and `docs/reference/evals.md` adds `{init.cwd}/./.claude/skills/<name>/SKILL.md` as a path that counts. Four rows in `test_claude_parser.py`: three that failed before the fix, and `<TRIAL>/workspace/../.claude/…`, which must not count |

Also closed, though not a finding: the docs say a confirmed Bash read of a dev skill's `SKILL.md` fails contamination on Claude Code, and no test showed it. `37ec5a1` adds `test_a_confirmed_bash_read_of_a_dev_skill_fails_and_a_read_tool_call_of_it_does_not` (`test_contamination.py`).

No second round: the fix reorders one line, as the triage proposed, so the code does what the reference already said. The mechanism, the rule and the data format are unchanged, and `37ec5a1` adds only a test.

**/code-review (high, Stage 1):** a separate stage from the cross-model review. Claude Code's `/code-review` skill, model `claude-fable-5-2`, reviewed branch `change-viz` against `main` at `5bf7fe0`. Findings: `ai_tmp/code-review-stage1.json` · Triage: `ai_tmp/triage-code-review-stage1.md`. The numbers are the findings file's, from 1; findings 1 to 3, 5, 6, 8 and 9 are ticket 16's. No finding of this ticket's was fixed.

| # | Finding | Verdict | Action |
| --- | --- | --- | --- |
| 4 | Every ok Claude Code run fails closed without its session record, not only by-name runs, so a CLI change to the session file would fail every trial | invalid | none: pins are exact, and `test_claude_adapter.py` runs the pinned CLI with a plain prompt and expects `ok`, so a CLI that moved the file fails `just check` at the pin bump. The design applies the record to every trial on purpose, so both arms take the same path. Gating on the prompt sent would exclude skill-arm trials only |
| 7 | The slash expansion rule compares raw paths, while the `Read` rule normalises them | invalid | none: both paths in the expansion rule are the CLI's own, the runner starts it in a resolved workspace, and `test_claude_adapter.py` shows the pinned CLI writes them in normal form. A miss could only fail a by-name skill arm loudly. If the two rules are ever unified, the shared helper keeps the empty-`cwd` guard |
| 10 | `_kept_session_lines` parses the whole transcript to find init's `session_id`, and `parse_stream` parses it again | out of scope | none: it costs milliseconds a trial, and each way to remove it changes a design decision, which event counts as init, or a shared data type. No follow-up filed |

**Follow-ups:**

- Still open from the design checkpoint: a trial-record field holding both agents' kept trigger lines, so a trigger can be audited after teardown. It needs its own ticket.
- Left as the triage scoped it: a relative `../workspace/.claude/…` `Read` path, and an absolute one that starts with exactly two slashes (which `normpath` keeps as `//`), still do not count. Both are conservative misses.
- Closed here: `just check` has run on `115ba26` and `37ec5a1` (above), and this record adds the review entry and ticks the boxes.
- No cross-model review finding was out of scope.
- /code-review finding 10: none filed. Reading the transcript once would keep its meaning only by duplicating the transcript reader, for milliseconds a trial.

**Residual risk:**

- **The live-trials criterion is not met, so the ticket stays open.** The live trials run in ticket 18's RED run (the maintainer's Hand-off 1), with a hand read of the quiet cases' transcripts. Their run ids go here.
- **The by-name trigger and quiet-case criteria are met offline only.** No test runs the real Codex CLI with a by-name prompt: Codex's trigger is shown from the recorded run. The runner-level test triggers through a scripted `Skill` call, and the expansion is shown end to end only in `test_claude_adapter.py`. No live trial has shown `skill_triggered` pass or a quiet case stay quiet.
- **Quiet cases are a lower bound** (maintainer decision 2). A read through a pipe, `awk`, an interpreter, the `Grep` tool or a copy records no trigger, and a transforming `sed` such as `sed -n = SKILL.md` counts as one.
- **Cowsay could move in a live run.** Its criterion is met offline. Claude Code now counts a confirmed `Read` or Bash read and keeps session persistence on in every trial, so cowsay's three `should_trigger: false` cases could change. ADR 0017's "cowsay's recorded results do not change" holds for the recorded files only.
- **The agent can write the session file.** Its Bash tool could rewrite its own session file in the trial home. `eval-isolation.md` states this as a known limit.
- **The persistence comparison covers one scenario**, a by-name run with a `Read`. The spike compared four.
- **The `Read` rule is exact-path, the Bash rule is not.** The shared Bash rule names a skill in any skills directory, as on Codex.
- **Linux is unrun.** Ubuntu CI has not run, because nothing was pushed. The parser tests' "any OS" rests on macOS, and Ubuntu CI is the first run of dash under the two adapter tests' `/bin/sh` stand-in scripts, of Codex's bwrap or Landlock sandbox on `.git`, of the on-disk case-clash test and of `GIT_ATTR_NOSYSTEM` on a non-Apple Git.
- **Fixture trials, as in ticket 16:** deleted fixture files are not shown to the grader; cowsay's skill arm still shows `.claude/` in Claude Code's startup git status (a follow-up); and `git status --ignored`, `git ls-files --others` without `--exclude-standard` and `git clean -n -d -x` still list the skill.
