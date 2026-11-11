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
