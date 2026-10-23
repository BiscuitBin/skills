# 01: Cross-model adversarial review as a repo dev skill

**What to build:** Any agent working in this repo (Claude Code, Codex or Pi) can run one command or skill to get an adversarial review of its work from a *different* model family. The reviewer's findings are checked against the code by a separate triage pass, and the implementer applies only the valid ones. This is an internal dev skill, the first one in the repo. It is never shipped to users and must never leak into evals. Every later ticket points to it, so this ticket also writes the protocol into the repo's agent instructions.

Read the foundation research notes (`.scratch/foundation/research.md`) first. They list where each agent discovers skills.

**Blocked by:** None (can start immediately). Ticket 02 runs in parallel and also writes the agent instructions file. Whichever ticket lands second merges the other's section, and neither overwrites the other. Ticket 03 is blocked by this ticket, so this one is on the critical path.

**Status:** ready-for-agent

## The protocol

The skill encodes this protocol, and this text stays its source of truth:

1. **Pick the reviewer by the cross-model rule.**
   - A Claude Code implementer asks Codex, using model `gpt-6-astra`, a read-only sandbox, and an ephemeral session.
   - A Codex implementer asks Claude Code, using Opus 5.5 (`claude-opus-5-5`) with read-only tools only.
   - A Pi implementer, or any other agent, picks the reviewer by the model family it is actually running: Codex (Astra) when it runs a Claude model, Claude Code (Opus 5.5) when it runs an OpenAI model, and Codex otherwise. It records the model it was running in the completion notes.
   - If the preferred reviewer is unavailable (CLI missing, not authenticated, model refused), fall back to the other reviewer only if its model family differs from the one the implementer is running, and say so in the completion notes. Otherwise treat cross-model review as unavailable.
   - If no reviewer from a different model family is available, stop and report. Never quietly review your own work, or use a same-family reviewer, instead.
2. **A reviewer subagent runs the external review.**
   - Its brief covers the ticket's acceptance criteria, the diff or design proposal under review, and an adversarial stance: find what is wrong, missing, unverifiable or unsafe, and do not summarise what is fine.
   - Each finding has a severity, a location, the claim, and evidence.
   - The brief tells the reviewer that it is a reviewer and must not start a review of its own.
   - The reviewer subagent captures the external reviewer's final output and saves it to the gitignored agent scratch folder (`ai_tmp/`). The external reviewer itself never writes files. The subagent hands back the file path, not the text.
3. **A separate triage subagent checks every finding.** It runs in a fresh context and is not the reviewer. Its brief also says it must not start a review of its own.
   - It reads the findings file and checks each finding against the actual code.
   - It marks each finding *valid*, *invalid* or *out of scope*, with evidence.
   - It proposes a concrete fix for each valid finding.
   - It saves its triage to the scratch folder and returns the path.
4. **Apply and record.**
   - The implementer, or a fix subagent, applies the valid fixes.
   - It reruns the focused checks, then `just check` if that exists yet.
   - It appends a **Completion notes** section to the ticket. Record the reviewer and model actually used, the commit or diff reviewed, and, for each finding, the verdict and what was done.
   - Out-of-scope findings become follow-up notes.
   - If the fixes were substantial, run one re-review round.

## Acceptance criteria

- [ ] Each agent discovers the dev skill when started anywhere inside this repo.
  - Claude Code and Codex are each shown discovering it in a headless run.
  - Pi is verified once ticket 02's pinned Pi exists, or the gap is recorded for ticket 12 to recheck.
- [ ] The skill has one source of content. It is made visible to every agent's discovery location without duplicating that content.
- [ ] The skill's frontmatter follows the Agent Skills spec. Its name and description are narrow enough that it triggers for review requests and not for ordinary coding.
- [ ] The skill is clearly marked repo-internal, and the agent instructions say that dev skills must be excluded from distribution (ticket 04) and from eval workspaces (ticket 05). Choose where the dev skill lives with ticket 04 in mind: `npx skills` scans this repo's agent skill folders (see the research notes), so the placement must let ticket 04 prove the dev skill is not offered.
- [ ] Reviewer selection follows the rule above. It is shown working when the preferred reviewer is unavailable (for example with the reviewer CLI hidden from `PATH`), and the fallback is reported, and a same-family fallback is refused and reported.
- [ ] The reviewer cannot modify the worktree. Its read-only mode is set by the CLI's flags, not by the prompt. A review run leaves the worktree's contents unchanged apart from the scratch folder, compared by content rather than by `git status` alone.
- [ ] The scratch folder is gitignored.
- [ ] The repo's agent instructions summarise the protocol in a few lines and point to the skill.
- [ ] Dogfood: the skill is used to review this ticket's own diff, and the completion notes record the findings and how each was handled.

## Review checkpoints

- **Implementation checkpoint:** before marking this done, run the protocol above on this ticket's diff. Use the new skill if it works, or follow the steps by hand if it doesn't. Record the result under Completion notes.
