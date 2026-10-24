---
name: cross-model-review
description: Repo-internal dev skill for BiscuitBin/skills. Gets an adversarial review of your diff or design from a different model family (Codex or Claude Code), triages every finding, and records the fixes. Use only when asked for a review or a second opinion, or at a ticket's review checkpoint. Not for ordinary coding.
license: MIT
metadata:
  scope: repo-internal
  distribute: never
---

# Cross-model review

A repo-internal **dev skill**. It is never shipped and never visible in eval workspaces.

The protocol below follows ticket `.scratch/foundation/issues/01-cross-model-review-dev-skill.md`, which is its source of truth. Run every command from the repo root. `REVIEW` means `python3 dev-skills/cross-model-review/scripts/review.py`.

## 1. Pick the reviewer by the cross-model rule

```sh
REVIEW select --implementer claude-code            # you are Claude Code
REVIEW select --implementer codex                  # you are Codex
REVIEW select --implementer other --model <id>     # Pi or any other agent: the model you are actually running
```

- Claude Code implementer → Codex, `gpt-6-astra`, read-only sandbox, ephemeral session.
- Codex implementer → Claude Code, Opus 5.5 (`claude-opus-5-5`), read-only tools only.
- Any other agent → by the family of the model it is running: Codex for a Claude model, Claude Code for an OpenAI model, Codex otherwise. Record that model in the completion notes.
- Preferred reviewer unavailable (CLI missing, not authenticated, model refused): the script falls back to the other reviewer only when its model family differs from yours, and reports it under `fallback_used` and `notes`. An `other` implementer whose `--model` is not a recognised family gets no fallback, because a different family cannot be confirmed: pass the underlying model ID.
- Exit code 3 means no reviewer from a different model family is available. **Stop and report it.** Reviewing your own work, or using a same-family reviewer, does not count as a cross-model review. If a reviewer "failed at runtime" and you are in a sandboxed shell, rerun with network access first.
- Exit code 2 is a usage error: fix the command and rerun. Exit code 1 means the run could not start (unreadable brief, not in a git repo, or worktree paths it cannot read, which it lists).

## 2. Reviewer subagent runs the external review

Dispatch a subagent with the brief below. It writes the review brief to `ai_tmp/brief-<topic>.md` and runs:

```sh
REVIEW run --implementer <you> [--model <id>] --brief ai_tmp/brief-<topic>.md
```

`run` repeats the selection, runs the reviewer with read-only CLI flags (enforced by the flags, not the prompt), saves the reviewer's final output to `ai_tmp/review-<timestamp>-<reviewer>.md` (with a `-<n>` suffix if that name is taken) and prints JSON with `findings_path` and `selection`. It snapshots the worktree by content and permission bits before and after, and exits 4 with the changed paths if anything outside `ai_tmp/` and `.git/` changed, whether the reviewer or a concurrent process changed it. Treat that as a failed review: the output it keeps as `ai_tmp/rejected-*.md` is for inspection only and is never triaged. Leave the worktree alone while `run` is going, check the listed paths, and rerun. If the preferred reviewer fails at runtime, `run` tries the allowed fallback itself.

A run takes up to `--timeout` seconds (default 1800) per reviewer, twice that with a fallback. Run it in the background or detached rather than under a short shell-tool timeout, and wait for it to exit. The reviewer CLIs need network access and write to their own home folders, so a sandboxed shell (Codex) must run it with escalated permissions.

**Reviewer-runner subagent brief:**

> You run an external review. You are not the reviewer: do not review the code yourself and do not start a review of your own.
>
> 1. Write `ai_tmp/brief-<topic>.md` from the review brief template in `dev-skills/cross-model-review/SKILL.md`, filling in the acceptance criteria and the work under review: `git diff <base>...HEAD` for commits, `git diff HEAD` for staged and unstaged work, and the full contents of each file listed by `git ls-files --others --exclude-standard`, each headed by its path. For a design review, paste the proposal instead.
> 2. Run `python3 dev-skills/cross-model-review/scripts/review.py run --implementer <implementer> [--model <id>] --brief ai_tmp/brief-<topic>.md` in the background (it can take 30+ minutes; in a sandboxed shell, with network access) and wait until it exits.
> 3. Return only the `findings_path` and the `selection` JSON it prints, or its stderr and exit code if it failed. Do not paste the findings.

**Review brief template** (the text the external reviewer receives):

> You are the reviewer in a cross-model adversarial review. Do not start a review of your own and do not invoke the `cross-model-review` skill: this brief is the review. You have read-only access. Do not create or edit files; your final message is your entire output.
>
> Be adversarial: find what is wrong, missing, unverifiable or unsafe in the work below. Do not summarise what is fine. Check the work against every acceptance criterion and read the surrounding code where you need evidence.
>
> Report each finding as:
> `### <n>. [critical|high|medium|low] <one-line claim>` then **Location:** `path:line`, **Claim:** what is wrong, **Evidence:** the code, command output or criterion that shows it.
>
> If you find nothing, say so in one line.
>
> ## Acceptance criteria
>
> <the ticket's acceptance criteria>
>
> ## Under review
>
> <diff or design proposal; base commit and HEAD>

## 3. Separate triage subagent checks every finding

Dispatch a **fresh** subagent. It is not the reviewer subagent.

**Triage subagent brief:**

> You triage findings from a cross-model review. You are not the reviewer: do not start a review of your own or look for new issues.
>
> 1. Read the findings file `<findings_path>`.
> 2. Check each finding against the actual code in this repo. Run read-only commands where they settle it.
> 3. Give each finding a verdict, **valid**, **invalid** or **out of scope**, with the evidence (file:line, command output).
> 4. For each valid finding, propose a concrete fix: which file, and what change.
> 5. Save the triage to `ai_tmp/triage-<timestamp>.md` and return only that path.

Every finding gets a verdict. A finding without evidence either way is not *valid*.

## 4. Apply and record

1. Apply the valid fixes, yourself or through a fix subagent.
2. Rerun the focused checks, then `just check` if it exists.
3. Append **Completion notes** to the ticket (template below). Out-of-scope findings become follow-up notes.
4. If the fixes were substantial, run one re-review round on the new diff (back to step 2).

**Completion notes template:**

```markdown
## Completion notes

### Cross-model review

- **Implementer:** <agent> running <model>
- **Reviewer:** <reviewer> `<model>` (fallback: <no | yes, why>)
- **Reviewed:** <commit sha or base...head>
- **Findings:** `<findings_path>` · **Triage:** `<triage_path>`

| # | Severity | Finding | Verdict | Action |
|---|----------|---------|---------|--------|
| 1 | high | ... | valid | fixed in ... |

**Follow-ups:** <out-of-scope findings>
```
