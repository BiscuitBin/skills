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

- [ ] The spike's answers are recorded here, with the CLI versions and the transcripts or fake-API requests that showed them.
- [ ] A case can be marked as invoked by name. The schema rejects the marking on a case whose `should_trigger` is `false`, and the field's name comes from the design checkpoint.
- [ ] For a marked case the skill arm's prompt is the agent's own syntax followed by the request, built by the adapter. The case's `prompt` holds only the bare request, with no agent's syntax in it.
- [ ] The baseline arm gets the bare request, and so does the grader in both arms. Nothing the grader is sent differs between the arms because of the prefix.
- [ ] The trace records the trigger for a by-name invocation on both agents, so `skill_triggered` passes and the case counts in trigger accuracy. On Claude Code this needs whatever evidence the spike found, and the trigger rule in `docs/reference/evals.md` says what it is.
- [ ] A plain request with `should_trigger: false` passes on both agents against a by-name-only skill: no trigger is recorded. A trial where the agent loads the skill anyway fails the case.
- [ ] Results record the prompt each arm was actually given, or enough to rebuild it.
- [ ] Cowsay's suite still passes. Whether `trigger-explicit-invocation` moves to the new marking is decided at the design checkpoint, because editing `evals/cowsay/evals.json` changes its `evals_sha256`.
- [ ] Regression tests drive both parsers from recorded transcripts of a by-name invocation and of a quiet plain request, kept under `tests/fixtures/evals/`. They run in `just check` on any OS, with no agent and no network.
- [ ] Docs and records:
  - `docs/reference/evals.md`: the case schema, both trigger rules, and what the baseline arm gets.
  - `GLOSSARY.md`: **Trigger** covers a by-name invocation on both agents.
  - An ADR, if the design changes what a trigger is.
- [ ] Shown working: one live trial per agent of a marked case, and one of a quiet plain request, with the run ids recorded here.
- [ ] `just check` passes.

## Out of scope

Description-routing evals and description optimisation (deferred in `.scratch/foundation/follow-ups.md`), Pi, and the `change-viz` skill itself.

## Review checkpoints

Use the `cross-model-review` dev skill.

- **Design checkpoint:** after the spike and before building, write up the spike's answers, the schema field, how each adapter builds the skill arm's prompt, and the trigger evidence on each agent, and get them reviewed. Can a trial pass `skill_triggered` without the skill's text reaching the model? Can the prefix reach the baseline arm or the grader?
- **Implementation checkpoint:** before marking done, review the full diff against these acceptance criteria. Pay particular attention to triggers that rest on the prompt text alone, to anything that tells the grader which arm it is reading, and to cowsay's results changing.

## Spike answers

Run on 2026-11-10 against the pinned Claude Code 2.1.309 and Codex 0.163.0, through the adapters, against the local fake APIs (`tests/evals/fake_anthropic.py`, `fake_openai.py`). The throwaway skill set `disable-model-invocation: true` in `SKILL.md` and `policy.allow_implicit_invocation: false` in `agents/openai.yaml`, and had a `.claude-plugin/plugin.json`, as `just new-skill` writes. The recordings become the `fake-by-name*` fixtures under `tests/fixtures/evals/{claude,codex}/` when step 4's parser tests land; until then they are in `ai_tmp/spike-17/` (gitignored). **The stop condition is not met:** both CLIs load a by-name-only skill headlessly.

**Claude Code.**

- **`claude -p "/<name> <request>"` loads the skill**, with no plugin prefix. The first request's first user message holds two text blocks: `<command-message><name></command-message>` `<command-name>/<name></command-name>` `<command-args><request></command-args>`, then `Base directory for this skill: <workspace>/.claude/skills/<name>`, the `SKILL.md` body without its frontmatter, and `ARGUMENTS: <request>`.
- **The stream-json transcript shows none of it.** The events are `system/init`, `assistant`, `rate_limit_event` and `result`. There is no `user` event, `--include-hook-events` adds nothing, and the debug log says nothing about the expansion. So the hypothesis that the trigger would show in the stream was wrong.
- **Where the evidence is.** With `--no-session-persistence` dropped, the session file `<home>/.claude/projects/<cwd slug>/<session>.jsonl` holds the `<command-name>` user record and then a `user` record with `isMeta: true` whose text is the `Base directory for this skill: …` block: the injection itself. The fake-API request bodies with and without persistence are identical apart from the per-home random `device_id` in `metadata.user_id`, so persistence does not change what the model sees. `--input-format stream-json --replay-user-messages` (the prompt over stdin) replays only the `<command-name>` text, not the body.
- **What the stream does show.** `init.skills` and `init.slash_commands` both list the skill in the skill arm. `init.plugin_warnings` reports the installed copy's `.claude-plugin/` as a project-scope plugin directory skipped as untrusted.
- **Plain request:** the skill is in neither the `Skill` tool's listing nor anywhere else in the request, by name or description, so the model is not told it exists. A model-initiated `Skill` call is refused with an `is_error` result (`Skill <name> cannot be used with Skill tool due to disable-model-invocation…`), which the parser records as invoked, not triggered. A `Read` of the installed `SKILL.md` succeeds and is not a trigger under today's rule.
- **Baseline, prefixed prompt:** the CLI adds a reminder, "The user's message starts with the slash command /<name>, but no command with that name is available in this session, so it did not run…", and sends the raw text on.
- With session persistence on, none of the plain request, the refused call, the `Read`, the baseline and a Bash `printf` of the `Base directory for this skill: <workspace>/…` line wrote an `isMeta` record. The printed line appears only inside a `tool_result`.

**Codex.**

- **`$<plugin>:<skill> <request>` loads the skill** and logs `codex.skill_invocation … skill.invocation_type=explicit`. The prefix is the `name` in `.claude-plugin/plugin.json` and the suffix the skill's name: with the plugin renamed `brief-kit`, `$brief-kit:branch-brief` loads and both `$branch-brief:branch-brief` and `$branch-brief:brief-kit` load nothing. Codex injects the whole `SKILL.md`, frontmatter included, as a second user message `<skill><name><plugin>:<skill></name><path>…/SKILL.md</path>…`.
- Without `plugin.json`, the bare `$<name>` loads it and the prefixed form loads nothing.
- **Plain request:** the skill is not listed to the model, by name or description, and no event is logged. A `cat .agents/skills/<name>/SKILL.md` the model runs anyway is a trigger under today's rule, and Codex logs `implicit` for it, so a quiet case fails when the agent reads the skill.
- **Baseline, prefixed prompt:** passed through as text, with no event and no error.

**How much the baseline marking matters.** On both agents a prefixed prompt in the baseline tells the model a named tool or command was asked for and is missing: Claude Code says so in a reminder, and Codex passes the `$…` text through. A baseline sent the prefix would be measured on a different request, which is the case the marking avoids.
