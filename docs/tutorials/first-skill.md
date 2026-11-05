# Your first skill

This tutorial takes a scratch skill from nothing to scaffolded, validated, evaluated on Codex and installed into a throwaway project. The skill, `biscuit-signoff`, teaches an agent a house convention it cannot guess: every message for the BiscuitBin team ends with the line `Fresh from the BiscuitBin oven.` Because no agent knows that line, a run without the skill fails and a run with it passes, which is the loop every real skill follows.

You will delete the skill at the end. Nothing in this tutorial is committed.

Run every command from the repository root. Each one is meant to be copied and pasted as it is. The commands that replace a scaffolded file use `>|`, which overwrites the file even when your shell has `noclobber` set; a plain `>` would fail there and leave the scaffold in place.

## Before you start

Finish [Getting started](getting-started.md), so `just initialize` has run and `just check` passes.

The live eval runs on Codex and calls a paid model. Log Codex in once; the login is kept in the project's own Codex home, `.tools/agent-homes/codex/`, never in `~/.codex`:

```sh
just run ./node_modules/.bin/codex login
```

## 1. Scaffold the skill

```sh
just new-skill biscuit-signoff
```

It prints the files it created:

```text
Created biscuit-signoff:
  skills/biscuit-signoff/SKILL.md
  skills/biscuit-signoff/agents/openai.yaml
  skills/biscuit-signoff/.claude-plugin/plugin.json
  evals/biscuit-signoff/evals.json
  .claude-plugin/marketplace.json
```

That is the skill itself, its Codex UI metadata, its Claude Code plugin manifest, its eval cases, and a new entry in the marketplace. Everything the scaffold could not know is marked `TODO(new-skill)`.

## 2. See what is still unwritten

The scaffold passes every check, but the checks tell you it is not finished:

```sh
just validate-skills
```

This ends with `0 errors, 3 warnings`. Each warning is a `[placeholder]` in one of the three skill files.

```sh
just validate-evals
```

This passes with `warning: biscuit-signoff is in .claude-plugin/marketplace.json but evals/biscuit-signoff/evals.json has only placeholder cases`.

The starter eval cases are placeholders, so `just eval` refuses to run them. `--dry-run` shows that without calling an agent:

```sh
just eval biscuit-signoff --agent codex --dry-run
```

It lists each case as `UNWRITTEN biscuit-signoff/<case>` and fails with exit code 2. Nothing ran.

## 3. Write the eval cases

Write the evals before the skill. Trigger cases say which requests should load the skill and which should not; the behaviour case says what the answer must contain. Replace the starter cases:

```sh
cat >| evals/biscuit-signoff/evals.json <<'EOF'
{
  "skill_name": "biscuit-signoff",
  "evals": [
    {
      "id": "trigger-team-announcement",
      "kind": "trigger",
      "prompt": "Draft a short announcement to the BiscuitBin team that Friday's standup is cancelled.",
      "should_trigger": true
    },
    {
      "id": "trigger-team-note",
      "kind": "trigger",
      "prompt": "Write a quick note to the BiscuitBin team saying the coffee machine is fixed.",
      "should_trigger": true
    },
    {
      "id": "no-trigger-biscuit-haiku",
      "kind": "trigger",
      "prompt": "Write a haiku about biscuits.",
      "should_trigger": false
    },
    {
      "id": "no-trigger-git-question",
      "kind": "trigger",
      "prompt": "Explain in two sentences what git rebase does.",
      "should_trigger": false
    },
    {
      "id": "behaviour-release-note",
      "kind": "behaviour",
      "prompt": "Write a two-sentence message to the BiscuitBin team saying the release has moved to Thursday.",
      "should_trigger": true,
      "expected_output": "A short message about the release date that ends with the house sign-off line.",
      "assertions": [
        { "type": "skill_triggered" },
        { "type": "output_contains", "value": "Fresh from the BiscuitBin oven." }
      ]
    }
  ]
}
EOF
```

None of the cases carries `"placeholder": true` any more, so they count as written. Check them:

```sh
just validate-evals
```

It prints `2 eval suites valid.` and no warning. If the placeholder warning is still there, the file was not replaced: rerun the `cat` command above and check it printed no error.

## 4. Run the baseline (RED)

Run the cases on Codex, with a baseline arm that has no skill installed:

```sh
just eval biscuit-signoff --agent codex --baseline
```

It prints its plan first (five agent calls for the skill arm, one for the baseline, with the four trigger cases skipped in the baseline), then runs. It exits 1, and that is the point. The line that matters is the behaviour case:

```text
FAIL behaviour-release-note/skill-1: output_contains failed (looked for 'Fresh from the BiscuitBin oven.')
```

No agent knows the sign-off line, with or without the stub. The trigger cases may already pass: Codex can load a skill whose name matches the request, even with a placeholder description. That does not matter yet; the behaviour case is the gap the skill has to close.

The baseline arm is read differently. A baseline trial is never judged pass or fail, because it measures what the agent does without the skill. It prints `VALID behaviour-release-note/baseline-1` when it ran cleanly, and the line `behaviour-release-note: skill scored 1/1; baseline scored 1/1` counts the trials that could be scored, not the ones that passed. The baseline's result is in the benchmark that follows: its `deterministic` and `outcome` pass rates are 0.00, because its answer had no sign-off line either.

The run is written to `eval-results/<run-id>/`, where `<run-id>` is the newest directory there. `results.json` holds every trial and `benchmark.json` the summary, including each case's `delta`, the skill arm minus the baseline. The [evals reference](../reference/evals.md#results) describes both.

## 5. Write the skill

Now write the skill that closes that gap. Replace the stub `SKILL.md`:

````sh
cat >| skills/biscuit-signoff/SKILL.md <<'EOF'
---
name: biscuit-signoff
description: Ends messages for the BiscuitBin team with the house sign-off line. Use when drafting any message, note, email or announcement addressed to the BiscuitBin team. Not for other writing.
license: MIT
---

# Biscuit sign-off

When you write a message, note, email or announcement for the BiscuitBin team,
write it as usual, then end it with this exact line on its own:

```text
Fresh from the BiscuitBin oven.
```

Add the line once, as the last line of the message. Do not add it to writing
that is not for the BiscuitBin team.
EOF
````

Replace the Codex UI metadata:

```sh
cat >| skills/biscuit-signoff/agents/openai.yaml <<'EOF'
interface:
  display_name: 'Biscuit Signoff'
  short_description: 'Sign off BiscuitBin team messages'
EOF
```

Replace the plugin manifest's placeholder description:

```sh
cat >| skills/biscuit-signoff/.claude-plugin/plugin.json <<'EOF'
{
  "name": "biscuit-signoff",
  "version": "0.1.0",
  "description": "Ends messages for the BiscuitBin team with the house sign-off line.",
  "author": {
    "name": "BiscuitBin"
  },
  "license": "MIT",
  "skills": ["./"]
}
EOF
```

The marketplace entry still has the old description. `plugin.json` is the source of a plugin's version and description, and `just format` copies both into the marketplace:

```sh
just format
```

Among its output is `Marketplace sources, plugin versions and descriptions match.`, printed after the copy. `git diff .claude-plugin/marketplace.json` shows the new description.

Check the skill again:

```sh
just validate-skills
```

It now ends with `0 errors, 0 warnings`. A `[placeholder]` warning means one of the three files still has the scaffold's text: rerun its `cat` command.

## 6. Run it again (GREEN)

```sh
just eval biscuit-signoff --agent codex --baseline
```

This time every skill-arm trial should pass: the two team requests trigger the skill, the haiku and the git question do not, and the release note ends with the sign-off line, so the behaviour case prints `PASS`. The baseline trial again prints `VALID`, with `deterministic` and `outcome` at 0.00, so the behaviour case's `delta` is +1.00: the skill is what made the difference. The run exits 0.

Agents are not deterministic, so a case can still fail. Find it in the newest `eval-results/<run-id>/results.json`, then close the gap in the skill rather than in the case:

- A trigger case that did not trigger, or triggered when it should not: make the `description` in `SKILL.md` say more plainly when to use the skill and when not to.
- A behaviour case whose answer missed the line: make the instructions in the body more direct.

Rerun the command after each change.

## 7. Install it into a throwaway project

Install the skill the way a user would, with the pinned `skills` installer, into a new project under `.tools/tmp/`. The installer works in its current directory, so the command changes into the throwaway project inside `just run`, which keeps the project's environment:

```sh
just run sh -c 'mkdir -p .tools/tmp/signoff-project && cd .tools/tmp/signoff-project && DO_NOT_TRACK=1 ../../../node_modules/.bin/skills add ../../../skills/biscuit-signoff --agent codex --yes'
```

Its summary reports `Installed 1 skill` and `✓ biscuit-signoff (copied)`. Codex finds project skills in `.agents/skills/`:

```sh
ls .tools/tmp/signoff-project/.agents/skills/biscuit-signoff
```

It lists `SKILL.md` and `agents`. A Codex session started in that project can now load the skill.

## 8. Clean up

Delete the scratch skill, its evals and the throwaway project, and restore the marketplace:

```sh
rm -rf skills/biscuit-signoff evals/biscuit-signoff .tools/tmp/signoff-project
git checkout -- .claude-plugin/marketplace.json
git status --short
```

`git status --short` prints nothing. The eval runs stay in `eval-results/`, which Git ignores.

## Why this tutorial skips `just check`

`just check` includes `validate-distribution`, which refuses uncommitted changes under `skills/` and `.claude-plugin/`, because the install tests install from the committed tree. A scratch skill is never committed, so `just check` would fail on it. A real skill is committed on a branch, and then `just check` covers it like any other.

## Next

[Contributing](../../CONTRIBUTING.md) covers the same loop for a real skill, with the cross-model review, recording a benchmark, versions and releases.
