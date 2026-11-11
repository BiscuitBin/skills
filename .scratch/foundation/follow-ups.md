# Foundation follow-ups

What the foundation leaves for later, gathered by ticket 12 so the next skill specs start from a known state. None of these is an open acceptance criterion: those are listed by ticket in ticket 12's completion notes.

## Deferred on purpose

- Description-routing evals.
- Description optimisation.
- A catalogue site.
- A Codex package manifest.
- A custom installer.
- The Pi adapter and evals (future ticket 07, `.scratch/future/issues/07-pi-adapter.md`).

Also planned: `.scratch/future/issues/14-claude-workload-identity-federation.md` replaces `CLAUDE_CODE_OAUTH_TOKEN` in the live-eval workflow.

## Waiting on the maintainer

- **Ticket 10, Codex secret-present dispatch.** `OPENAI_API_KEY` is not in the `live-evals` environment, so a dispatch of cowsay on Codex with the secret present has not been shown. That includes the unverified check that a trial authenticates from an API-key login (`codex login --with-api-key`). Local Codex runs use a ChatGPT login. Add the key, dispatch cowsay on Codex, and tick ticket 10.

## From the full-repo review

Each was confirmed against the code and marked out of scope: real, but nothing in the foundation requires it. The triage is summarised in ticket 12's completion notes.

| Finding | What is left |
| --- | --- |
| H2 | Output-size caps do not bound memory: the sweep and the grader read a whole file before capping, so a huge or sparse agent-made file can exhaust the harness. Also ticket 08's "bounded prefix" follow-up. |
| H4 | Reports drop the per-arm exclusion and arm-disclosure counts and the benchmark notes that `benchmark.json` records. |
| H5 | A pooled regression can come from changed case weights alone, and carries no label. |
| H6 | A run stopped or killed before its last trial writes no `results.json`, so completed trials cannot be reported. |
| H7 | History validation checks that a run's keys exist, not their values, so `"cases": null` still crashes `eval-report` with a traceback. |
| T1 | A review timeout kills the launcher but not the native Codex process. |
| T2 | A failed marketplace write in `just new-skill` can leave the manifest truncated if the restore also fails. |
| T3 | `just install-hooks` run directly from a secondary worktree writes to the shared `.git/hooks`. Only `initialize.sh` guards this. |
| T4 | Install tests take a new skill's expected files from its own directory, so an accidentally bundled `evals.json` passes. Only cowsay has an independent allowlist. |
| T6 | `just check` never loads `benchmarks/`, so valid JSON that breaks `eval-report` passes the gate. |
| D3 | Installed skills carry `license: MIT` but not the licence's copyright and permission notices. |
| K2 | `skill_sha256` does not follow a symlinked directory that installation copies, so two payloads can share a hash. Also ticket 08's O4. |
| K3 | Codex's discovery canaries use injected or redirected homes, so a location Codex finds independently of `HOME` would not be caught. |

## From the final reviews

- **S3:** the python wrapper starts Python before installing its traps, so a signal in that instant reaches the shell before the trap and leaves Python to the group teardown. A simple reorder hung under `sh` in a trial, so any fix needs a sweep across bash, dash and zsh. Triage: `ai_tmp/triage-final.md`.
- Observed by a V2 refuter and not tested end to end: on Linux, `shutil.rmtree` on a very deep tree used memory that grew about quadratically with depth (43 MB at 5500 levels, 925 MB at 30500), and a run at about a million levels was killed. An agent could build such a tree in a trial to stall cleanup.

## From the branch code review

- A signal-stopped run can discard a trial's `secret_found` record and skips `verify_clean`.
- `_sweep` catches `OSError` only, so a `MemoryError` from a huge file escapes `run_trial`. See H2.
- `restore_access` runs after credential collection, so a home the agent locked still fails the trial.
- After the first terminating signal, later ones are swallowed with no message, so a hang outside an agent wait needs SIGKILL, which leaves `home/` on disk.
- `files_holding` tests names only for files and symlinks, so an empty directory or FIFO named after a token is not reported.

## Residuals from earlier tickets

- **Ticket 01:** `review.py` does not snapshot `.git/hooks` or `.git/config` (L12). An `other` implementer with an unrecognised model goes to Codex first, and the third-family allow-list is a heuristic. `codex exec` blocks on an open stdin, so a hand run needs `</dev/null`.
- **Ticket 03:** Codex icon resources are not validated. Unicode rendering is not terminal-cell aware.
- **Ticket 04:** A new shipped skill's inventory and Claude's `agents/*.md` convention need care in future authoring.
- **Ticket 05:** Input files are staged as git fixtures since ticket 16: a case names one with `fixture`, and `files` is accepted only as `[]`. Still deferred: a remote, or any GitHub state, in a fixture (ticket 23), and showing the grader a fixture file the agent deleted, which needs a new line in the grader prompt and so a new `grader_prompt_sha256`.
- **Tickets 06 and 11:** `review.py` treats Codex's first-run home setup as a worktree change, so the first review in a fresh worktree can exit 4. It did not recur in ticket 12's worktree, where Codex was already logged in and had run.
- **Ticket 06:** A masked read of a canary skill shows only through Codex's event. A read with `2>&1` is not counted by the text rule.
- **Ticket 06, new in ticket 12:** `sed -n 1p README.md skills/cowsay/SKILL.md` exits 0 and prints only the first file's line, yet still counts as a read of the skill, because output from a multi-file read cannot be attributed.
- **Ticket 08:** One helper for the skill's file list. `prompt_sha256` does not cover the expectation format. The harness's framing text can be quoted to satisfy the quote rule. Some tests assert on `Verdict.claimed` or CPython's JSON errors. `redact()` handles an old path shape. Two grader models are not noted.
- **Ticket 08, host `/tmp`:** Claude Code's Bash is not confined, so a literal `/tmp` path in a trial writes to the host. Confine it, for example with Claude Code's sandbox settings. `/tmp` is outside ticket 12's home comparison.
- **Ticket 12, host `/tmp` leftovers:** the pinned Claude CLI ignores `TMPDIR` and leaves empty `tasks` folders under `/private/tmp/claude-<uid>/<cwd-slug>/`, 16 to 22 per walkthrough round (ticket 12, Agent homes). The user accepted this on 2026-11-06. `CLAUDE_CODE_TMPDIR` moved them in one probe, but the CLI then made `/private/tmp/cc-socks-<uid>`. Check whether that persists, then set it in the Justfile and the eval adapter, and cover each with a test.
- **Ticket 09:** Compute pooled values once, and share the matrix and history formatting.
- **Ticket 11:** Claude Code's docs advise against setting `version` in both manifests. The repo does so on purpose (ADR 0010).
- **Ticket 13:** Unplaced reads pair by printed name and must open with the frontmatter. Codex's denial test is a keyword heuristic. Reads that fail `outcome_is_the_read` no longer trigger through the event.
- **Ticket 16:** Cowsay's skill arm still shows `?? .claude/` in Claude Code's startup Git context, and its baseline arm does not. Only a fixture trial gets the `.git/info/exclude` that hides the installed skill, and the preflight's `git status` check. Giving every trial both would close this arm difference, which predates ticket 16, but it changes what every cowsay trial's agent sees, and no report label would mark that change.
