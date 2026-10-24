# 01: Cross-model adversarial review as a repo dev skill

**What to build:** Any agent working in this repo (Claude Code, Codex or Pi) can run one command or skill to get an adversarial review of its work from a *different* model family. The reviewer's findings are checked against the code by a separate triage pass, and the implementer applies only the valid ones. This is an internal dev skill, the first one in the repo. It is never shipped to users and must never leak into evals. Every later ticket points to it, so this ticket also writes the protocol into the repo's agent instructions.

Read the foundation research notes (`.scratch/foundation/research.md`) first. They list where each agent discovers skills.

**Blocked by:** None (can start immediately). Ticket 02 runs in parallel and also writes the agent instructions file. Whichever ticket lands second merges the other's section, and neither overwrites the other. Ticket 03 is blocked by this ticket, so this one is on the critical path.

**Status:** done. One criterion's placement half stays open until ticket 04 runs its listing test (see Completion notes).

**Agent requirements:** Any implementing agent (Claude Code, Codex or Pi). Claude Code and Codex access is required for the headless discovery checks and live review checks. Pi discovery may be deferred to ticket 12 as described below. Review requires a reviewer from a different model family, plus separate reviewer and triage subagents.

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

- [x] Each agent discovers the dev skill when started anywhere inside this repo.
  - Claude Code and Codex are each shown discovering it in a headless run.
  - Pi is verified once ticket 02's pinned Pi exists, or the gap is recorded for ticket 12 to recheck.
  - *Done:* Claude Code and Codex shown from `.scratch/`. The Pi gap is recorded for ticket 12.
- [x] The skill has one source of content. It is made visible to every agent's discovery location without duplicating that content.
- [x] The skill's frontmatter follows the Agent Skills spec. Its name and description are narrow enough that it triggers for review requests and not for ordinary coding.
- [ ] The skill is clearly marked repo-internal, and the agent instructions say that dev skills must be excluded from distribution (ticket 04) and from eval workspaces (ticket 05). Choose where the dev skill lives with ticket 04 in mind: `npx skills` scans this repo's agent skill folders (see the research notes), so the placement must let ticket 04 prove the dev skill is not offered.
  - *Done:* the marker (`metadata.scope: repo-internal`) and the agent instructions.
  - *Open, for ticket 04:* `npx skills` skips the symlinked folders, but its fallback recursive scan finds `dev-skills/` when no other skills exist or with `--full-depth`. Ticket 04's listing test decides whether this placement holds.
- [x] Reviewer selection follows the rule above. It is shown working when the preferred reviewer is unavailable (for example with the reviewer CLI hidden from `PATH`), and the fallback is reported, and a same-family fallback is refused and reported.
- [x] The reviewer cannot modify the worktree. Its read-only mode is set by the CLI's flags, not by the prompt. A review run leaves the worktree's contents unchanged apart from the scratch folder, compared by content rather than by `git status` alone.
- [x] The scratch folder is gitignored.
- [x] The repo's agent instructions summarise the protocol in a few lines and point to the skill.
- [x] Dogfood: the skill is used to review this ticket's own diff, and the completion notes record the findings and how each was handled.

## Review checkpoints

- **Implementation checkpoint:** before marking this done, run the protocol above on this ticket's diff. Use the new skill if it works, or follow the steps by hand if it doesn't. Record the result under Completion notes.

## Completion notes

### What landed

- **Single source:** `dev-skills/cross-model-review/` (`SKILL.md`, `scripts/review.py`). Relative symlinks expose it to discovery: `.claude/skills/cross-model-review` and `.agents/skills/cross-model-review` both point to `../../dev-skills/cross-model-review`.
- **Frontmatter:** spec fields only (`name`, `description`, `license`, `metadata` with string values `scope: repo-internal`, `distribute: never`).
- **`scripts/review.py`** (stdlib, Python 3.9+):
  - `select` applies the cross-model rule. Model families are read from provider-prefixed IDs and aliases too. A known implementer keeps its default family when its model is unrecognised.
  - `run` runs the reviewer with read-only CLI flags. Codex gets `exec -m gpt-6-astra --sandbox read-only --ephemeral --ignore-user-config --ignore-rules --skip-git-repo-check`. Claude gets `-p --model claude-opus-5-5 --tools Read,Grep,Glob --restricted --strict-mcp-config --permission-prompts none --no-session-persistence`, and never `--bare`.
  - `run` snapshots the worktree by sha256 content and permission bits (the root included) with a filesystem walk (ignored files included; `.git/` and `ai_tmp/` excluded). It refuses to start if any path is unreadable, and exits 4 if anything changed. In that case the output is kept only as `ai_tmp/rejected-*.md`.
  - Exit codes: 0 ok, 1 setup error, 2 usage, 3 unavailable, 4 worktree changed.
- **Tests:** `tests/dev_skills/test_cross_model_review.py`, 36 stdlib `unittest` tests. Fake `codex`/`claude` shims on a PATH holding nothing else cover selection, fallback, same-family refusal, auth failure, the read-only flags, worktree tampering and setup errors.
- **Instruction files:** `.gitignore` (`ai_tmp/`, `__pycache__/`), `AGENTS.md` (independent `## Cross-model review` and `## Dev skills` sections, so ticket 02 can add its own), and `CLAUDE.md` (`@AGENTS.md` only).

### Acceptance evidence (artifacts in `ai_tmp/`, gitignored)

- **Claude Code discovery** (2.1.309, started in `.scratch/`):
  - `system/init` lists `cross-model-review` in `skills` and `slash_commands`. The prompt "Get me an adversarial review of my diff from another model before I mark it done." produced `tool_use Skill {"skill": "cross-model-review"}` (`discovery-claude.jsonl`).
  - Negative check: an ordinary coding prompt made no `Skill` call (`discovery-claude-negative.jsonl`).
- **Codex discovery** (0.163.0, started in `.scratch/`): a `command_execution` ran `cat …/.agents/skills/cross-model-review/SKILL.md`, and stderr had no `failed to load skill` (`discovery-codex.jsonl`).
- **Pi:** not installed, and ticket 02's pinned Pi has not landed. **Gap recorded for ticket 12 to recheck.** Pi needs `--approve` for project skills in JSON mode, according to the research notes.
- **Fallback demos** (`fallback-demo.txt`, real CLIs, codex hidden from PATH):
  - `select --implementer claude-code` refuses: codex is not found and claude is the same family.
  - `select --implementer other --model gemini-3-pro` falls back to claude, with `fallback_used: true` and a note.
  - With claude on a bare PATH, the auth probe correctly reported `loggedIn: false` (`claude auth status` exits 1 when logged out).
- **Read-only:** both live review runs left the content snapshot unchanged apart from `ai_tmp/`. `git check-ignore ai_tmp/x` matches `.gitignore:1`.
- **Checks:**
  - `python3 -m unittest discover -s tests -t .` passes, 36 tests.
  - `uvx mypy --strict dev-skills tests` is clean. This is a pre-ticket-02 compromise: uvx caches mypy outside the project, and ticket 02 replaces it with the pinned toolchain.
  - `just check` does not exist yet.

### Input for ticket 04: does `npx skills` follow symlinked skill folders?

- **Source read:** `vercel-labs/skills` `src/skills.ts` at `main` `a80e4c9`. This is not the pinned version, so recheck against the pin.
- **Priority walk:** `walkSkillDirs` uses `readdir({withFileTypes: true})` with `entry.isDirectory()`, which is false for symlinks. So the symlinked `.agents/skills` and `.claude/skills` entries are **skipped**.
- **Leak path:** the fallback `findSkillDirs` runs when no skills are found, or with `--full-depth`. It recurses from the repo root and **does** find the real directory `dev-skills/cross-model-review/`. While the repo has no shipped skills, a listing would therefore offer the dev skill. Ticket 04 must test the default, `--full-depth` and zero-skill listings.
- **Marker:** `metadata.scope` and `metadata.distribute` are not read by any installer. They mark the skill for humans and our own tooling only.

### Cross-model review

- **Implementer:** Claude Code running `claude-opus-5-5`.
- **Round 1:**
  - Reviewer: Codex `gpt-6-astra`, no fallback.
  - Reviewed: `main...7b5e84a`.
  - Findings: `ai_tmp/review-20261023T045059Z-codex.md` (C1–C2).
  - Supplementary same-family review: `ai_tmp/review-local-code-review.md` (L1–L15, Claude `/code-review`). It is not a substitute for the cross-model review, and was triaged in the same pass.
  - Triage: `ai_tmp/triage-20261023T0510Z.md`. One fresh agent per finding, then an independent challenger per verdict.
  - Fixes in `d764a7e`.
- **Round 2 (re-review, since the fixes were substantial):**
  - Reviewer: Codex `gpt-6-astra`, no fallback.
  - Reviewed: `7b5e84a..d764a7e`.
  - Findings: `ai_tmp/review-20261023T051733Z-codex.md` (R1).
  - Triage: `ai_tmp/triage-20261023T0520Z-rereview.md`.
  - Fixed in the final commit.
- **Round 3 (PR #3 review):**
  - Reviewers: GitHub Copilot (2 inline comments, CP1–CP2) and Codex `gpt-6-astra`, no fallback (K1–K2).
  - Reviewed: `6fca094` (`main...6fca094`).
  - Findings: Copilot threads on PR #3; `ai_tmp/review-20261023T055944Z-codex.md`.
  - Triage: `ai_tmp/triage-pr3.md`. One fresh agent per finding, then an independent challenger per verdict. All agreed, so no tiebreak.
- **Round 4 (re-review, since K1 changed reviewer selection):**
  - Reviewer: Codex `gpt-6-astra`, no fallback.
  - Reviewed: `6fca094` plus the uncommitted round 3 fixes.
  - Findings: `ai_tmp/review-20261023T062007Z-codex.md` (K3).
  - Triage: `ai_tmp/triage-pr3.md` (re-review section).
  - Rounds 3 and 4 were fixed in the "Apply PR #3 review fixes" commit.

| # | Severity | Finding | Verdict | Action |
| --- | ---------- | --------- | --------- | -------- |
| C1 / L1 | high | Provider-prefixed or alias model IDs were classed as "other", so a same-family review could get through | valid | `model_family` matches family markers after `/ : . @ _ -`, plus aliases (opus, sonnet, haiku, fable, astra). Regression tests added. |
| C2 / L15 | medium | The runner brief's diff missed staged and untracked changes | valid | The brief now uses `git diff <base>...HEAD`, `git diff HEAD`, and the contents of each untracked file headed by its path |
| L2 | high | Codex execpolicy `.rules` could allow commands outside the sandbox | valid | Added `--ignore-rules`, asserted in the test |
| L3 | medium | An unrecognised `--model` overrode a known implementer's family | valid | The implementer's default family is kept for unrecognised models. Test added. |
| L4 | medium | Exit 2 (unavailable) clashed with argparse usage errors | valid | Unavailable is now 3, modified is 4. SKILL.md updated. Test added. |
| L5 | medium | The snapshot crashed on unreadable paths | valid | Records `error:<errno>` through `onerror` and try/except. Test added. |
| L6 | medium | The repo-internal marker is not read by installers, and npx-skills' fallback scan finds `dev-skills/` | out of scope | Handed to ticket 04 (see above) |
| L7 | medium | Concurrent changes discarded the paid output and blamed the reviewer | valid | Output kept as `rejected-*.md` (inspection only). Neutral message. Test asserts this. |
| L8 | medium | The brief ignored shell timeouts and sandboxed network | valid | SKILL.md: run in the background and wait, escalate the sandbox for network, rerun before reporting unavailable |
| L9 | low | Claude reviews persisted session transcripts | valid | Added `--no-session-persistence` |
| L10 | low | Setup errors were tracebacks with an ambiguous exit code | valid | `SetupError` gives exit 1 with a message. Test added. |
| L11 | low | No `--skip-git-repo-check` despite `--root` | out of scope (triage) | Applied anyway (one flag, safe), so `--root` behaves as documented |
| L12 | low | Writes to `.git/hooks` and `.git/config` are not snapshotted | out of scope | Follow-up below |
| L13 | low | The snapshot read whole files and re-walked on fallback | valid | 1 MiB chunked sha256, and the after-snapshot is reused as the next before-snapshot |
| L14 | low | The flag test was weak (`-p` substring, missing flags, `!= 0`) | valid | Whole-argument flag assertions for every read-only flag. Asserts `EXIT_MODIFIED`. |
| R1 | medium | Unreadable paths compared equal (`error:13 == error:13`), so verification passed open | valid | `run` refuses before any probe or reviewer runs when a path is unreadable. Test added. |
| CP1 | — | The snapshot ignored permission bits, so a chmod-only change (0755 → 0644) passed | valid | File and directory entries record `stat.S_IMODE` from `lstat` (`sha256:<hex> mode:<octal>`, `dir mode:<octal>`). Symlinks stay `link:<target>`. Test added. |
| CP2 | — | `_output_path` checked `exists()` and the caller wrote later, so same-second runs overwrote each other's report | valid | The name is reserved with `touch(exist_ok=False)` (O_EXCL), and `-<n>` is retried on `FileExistsError`. Test with a frozen clock added. |
| K1 | medium | An unrecognised `other` model was treated as a confirmed third family, so a same-family Claude fallback could get through | valid | A fallback needs a recognised family (`_THIRD_FAMILY_MODEL` allow-list). An unconfirmed model is refused with a note, giving exit 3. SKILL.md updated. Test added. |
| K2 | medium | `npx skills`' fallback scan still finds `dev-skills/` and ignores our markers | out of scope | Duplicate of L6, owned by ticket 04 (04:32–36). `metadata.internal` is ruled out by 04:34. Follow-up below. |
| K3 | medium | The CP1 fix did not record the worktree root's own mode | valid | The root is recorded as `.` using `root.stat()`. An unreadable root is still `error:<errno>`. Test added. |

All new regression tests from round 1 fail against `7b5e84a` and pass after the fixes (checked by swapping in the old script). The R1 test fails on `d764a7e` (checked by triage in a scratch export). The four round 3–4 tests (CP1, CP2, K1, K3) fail against `6fca094` and pass after the fixes (checked in a `git archive 6fca094` export with the new test file).

**Follow-ups:**

- K2 (ticket 04): with zero shipped skills, or with `--full-depth`, `discoverSkills` falls back to `findSkillDirs` (`skills.ts:310` at `a80e4c9`) and reaches `dev-skills/cross-model-review/SKILL.md`. Once ticket 04 ships skills, the default listing stops reaching that fallback, but `--full-depth` still does, so always assert `--full-depth`. Test the zero-skill listing in a fixture repo.
- L12: snapshot `git rev-parse --git-path hooks` and `--git-path config` (and `config.worktree`) with a `git:` prefix.
- Residual risk (narrowed by K1): an `other` implementer whose model the classifier does not recognise still goes to Codex first under "Codex otherwise", so an unrecognised OpenAI alias could get a same-family Codex review. It no longer gets a Claude fallback. The third-family allow-list (`_THIRD_FAMILY_MODEL`) is a heuristic: a wrapper name containing e.g. `gemini` is trusted as a third family.
- `codex exec` blocks when stdin is inherited and left open. `review.py` always passes the brief on stdin, but agents running `codex exec` by hand should pass `</dev/null`.
