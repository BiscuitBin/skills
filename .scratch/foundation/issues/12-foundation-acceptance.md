# 12: Foundation acceptance: fresh-clone walkthrough and full-repo review

**What to build:** Proof that the foundation works for someone who has only the docs. A fresh-context agent, starting from a fresh clone, follows only the README and the docs to:

- get a green `just check`
- run the cowsay eval on Claude Code and Codex
- build the report
- install cowsay through each distribution channel

Then the whole repo gets a cross-model adversarial review. Valid findings are fixed, and anything left becomes a follow-up note, so the next round of skill specs starts from a known state.

**Blocked by:** 10 (Manual live-eval CI job), 11 (New-skill authoring workflow and docs).

**Status:** done, except ticket 10's Codex secret-present dispatch, which the user accepted as open (see Completion notes)

**Agent requirements:** Any implementing agent (Claude Code or Codex). A fresh-context subagent must perform the walkthrough with authenticated access to Claude Code and Codex, plus the configured grader when grading is enabled. Claude Code is also required for marketplace installation. The full-repo review and fix review require a reviewer from a different model family, plus separate reviewer and triage subagents.

## Acceptance criteria

**Walkthrough:**

- [x] A fresh-context subagent, given only the repo URL or a fresh clone and the instruction to follow the docs, completes these steps:
  - `just initialize` and `just check`, both green
  - `just eval cowsay` on Claude Code and Codex, all passing
  - `just eval-report`
  - installing cowsay through the marketplace and through `npx skills` into a throwaway project
- [x] Every point where the walkthrough agent got stuck, guessed, or had to read source code is fixed in the docs, and the walkthrough is repeated until it runs clean.
- [x] The walkthrough leaves nothing outside the project directory and throwaway projects. Compare the user's agent homes before and after.

**Carried-over checks:**

- [x] The ticket 01 dev skill is confirmed discoverable by Claude Code and Codex in this repo. Pi discovery moved to future ticket 07 ([ADR 0013](../../../docs/adr/0013-pi-deferred-past-mvp.md)).
- [x] Any gaps recorded by earlier tickets are closed or carried into the follow-up notes, for example the secret-present dispatch from ticket 10.

**Full-repo review:**

- [x] A cross-model adversarial review covers the whole repo, not just a diff. It is checked against the foundation goals in the research notes and every earlier ticket's acceptance criteria.
- [x] Every finding is triaged, valid fixes are applied, and `just check` is green afterwards.
- [x] Residual gaps, deferred items and out-of-scope findings are written as follow-up notes in the foundation scratch folder. The deferred items are description-routing evals, description optimisation, a catalogue site, a Codex package manifest, a custom installer, and the Pi adapter and evals (future ticket 07).
- [x] Every ticket in the foundation set has its completion notes and a done status, except where a mandatory criterion is still unmet. Those criteria are listed by ticket in this ticket's completion notes as open, not as follow-ups, and the user confirms them before the foundation is called done.

## Review checkpoints

Use the repo's cross-model adversarial review skill from ticket 01:

- Pick the reviewer by the cross-model rule.
- A reviewer subagent saves its findings to the scratch folder.
- A separate triage subagent checks each finding against the code.
- Apply the valid fixes, rerun `just check`, and record every finding and how it was handled under **Completion notes**.

- **Full-repo checkpoint:** this ticket's main review, described above.
- **Implementation checkpoint:** after the fixes, run one re-review round over the fix diff.

## Completion notes

### Walkthrough

Fresh `general-purpose` subagents, one per round, each given only a fresh clone under `.tools/tmp/walkthrough-<n>/skills` and the instruction to follow the docs. Reports are in `ai_tmp/walkthrough-<n>.md`, results in `ai_tmp/walkthrough-<n>-results/` (ignored by Git).

| Round | Commit | Claude Code | Codex | Log | Fixed in |
| --- | --- | --- | --- | --- | --- |
| 1 | 5e3ba9b | 9/9 `20261105T214704Z-938d` | 9/9 `20261105T214912Z-8f4a` | 12 gaps | f5af01d |
| 2 | f5af01d | 9/9 `20261106T015650Z-7ee8` | 9/9 `20261106T015840Z-b7bf` | 6 guesses, 2 observations | 7546349 |
| 3 | 7546349 | 9/9 `20261106T030043Z-f038` | 9/9 `20261106T030135Z-1a7a` | 9 entries, 3 real gaps | b31ffd2 |
| 4 | fb7f76e | 9/9 `20261106T055029Z-1647` | 9/9 `20261106T055141Z-31c2` | none | |

**Round 4, the clean round:** `just initialize` and `just check` green (869 passed, 2 skipped), `just eval cowsay` passed on both agents with no secret found, `just eval-report cowsay --run … --run …` built `eval-results/report.html`, and cowsay installed through the marketplace and `skills` into `.tools/tmp/install-check`, with the install paths confirmed. It ran after the review fixes, so it covers the changed code and docs.

**Gaps the walkthrough found**, all fixed in the docs: the stale "eval harness is under development" line; no route to running an existing skill's evals (`docs/how-to/run-evals.md` is new); plain `just eval-report` silently leaving out new runs; the token's creation and export; the skipped canaries; baseline and recording choices; a command for pass counts; a login check; which run is which; the install source, cleanup and two surprising output lines.

**Deviations and limits:**

- **Hand-off.** The criterion says the subagent completes the step. By your decision, the session never held the token: each round's agent wrote the credential and eval commands to a hand-off file, you ran them in your terminal, and the agent read `eval-results/`. So `read -rs` and `codex login` were run by you, and the agent saw neither them nor the exit codes.
- **Confirmed by you at sign-off:** `setup-token` through `just run` and `read -rs` both work as the guide says.
- **The one pre-emptive doc fix.** Before any walkthrough, commit 5e3ba9b added the "Check the install channels from a checkout" section, because the README's bare `claude` and `npx` would have written the marketplace to the real `~/.claude/plugins`. Every other gap was left for the walkthrough to find.
- **What "installed through `npx skills`" means here.** The agents used the pinned `node_modules/.bin/skills` from the checkout, the docs' route for a clone. The literal `npx skills@1.7.4` and the README's end-user commands were not run, to stay out of the real homes. `tests/test_distribution.py` covers the hosted Git-source shorthand. `BiscuitBin/skills` was tried by hand once before round 1.
- **Round 4's brief differed.** To stop logging choices the docs settle and agents' own extra checks, the brief narrowed what to log, and step 3 asked for a report showing the new runs. "None" therefore reads against that narrower rule.
- **Round 3 was not strictly clean.** By your decision the final clean round ran after the review fixes rather than before them.
- **macOS only.** All four rounds ran on macOS, so their live evals ran the python wrapper under bash and never under dash. They also predate the wrapper's stdin fix in eaac319 and the cleanup fixes from the final reviews, which have unit tests on both CI platforms but no live run.
- **Isolation limits.** Clones sit inside this worktree to keep paths in-project, so a walk-up can load the parent's `AGENTS.md`. Subagents also inherit the injected `CLAUDE.md`. "Docs only" rests on each agent's own log. In round 3 the first hand-off failed before running, probably because I had deleted the clone your shell was in; it was rerun with an absolute path.

### Agent homes

`ai_tmp/home-snapshot.sh` takes a path, size and hash manifest of `~/.claude/{plugins,skills,settings.json}`, `~/.agents`, `~/.pi` (absent) and non-runtime `~/.codex`, per-key hashes of `~/.claude.json`, and path and mtime listings of `~/.npm`, `~/.cache`, `~/.local`, `~/.config` and Codex runtime state. `ai_tmp/home-diff.sh` compares two snapshots. Each round was compared before and after, and the hand-tried install commands too.

**Result: no difference traced to this work.** Round 4's hashed manifest is identical before and after. Everything else that moved has another source:

| Path | Round | Source |
| --- | --- | --- |
| `~/.claude/skills/synced` (docx, pptx, xlsx) | 2 | Rewritten at 17:59 during the Codex eval. The pinned CLI's home has no `skills/synced`, so another Claude client is inferred, not proved. |
| `~/.codex/packages/app-server-daemon` | 3 | The Codex app updating itself from 0.166 to 0.167. |
| `~/.codex/sessions` | 1, 3 | Each file's `cwd` is an `alliumpy` or `biscuit_pics` worktree. |
| `~/.codex` runtime state | all | The Codex app, which was running throughout. Not hashed. |
| `~/.npm/_logs`, `_cacache` | 2, 3 | Each log's `cwd` is a `rove` worktree. |
| `~/.cache/uv`, `~/.cache/prek` | all | New `uv` archives are `alliumpy` packages. The `prek` log names `alliumpy` and never this worktree or a clone. Not every file was attributed. |
| `~/.claude.json` keys such as `tipsHistory`, `pluginUsage` | all | This live session and others; project entries were `alliumpy`. Hashed by key, so an unknown new key would show. None did. |
| `~/.local/share/nvim`, `~/.local/state/nvim`, `~/.cache/gh` | all | The user's editor, and `gh`. |

`/tmp` was outside the comparison by your approval of the plan (2026-11-05). The plan also said anything recurring there would be carried as a residual, and the final review (S6) found that had not been done. Observed directly since:

- The pinned Claude CLI ignores `TMPDIR` and leaves an empty `tasks` folder per session under `/private/tmp/claude-501/<cwd-slug>/<uuid>/`. Rounds 1 to 3 left 16 each (6 from evals, 10 from pytest), round 4 left 22 (6 and 16). They hold no files.
- It also makes `claude-<uid>/fswatch-probe-XXXXXX/probe`: 3604 such directories in all, 2291 with a non-empty `probe`, and 68 inside round 4's window. Live sessions share that tree, so these cannot be attributed to this work.
- Sockets: none of the 124 recorded `/tmp/cc-socks/<pid>.sock` remain; they go when the CLI exits. `codex-daemon-501` is the Codex app.
- `CLAUDE_CODE_TMPDIR` moved the folders in one probe, but the CLI then created `/private/tmp/cc-socks-501`. Whether that persists, and setting it in the Justfile, are untested.

So the walkthrough left empty folders in the host `/tmp`. The criterion stays ticked by your decision on 2026-11-06, with this as an accepted deviation, and confining them is a follow-up. Ticket 08's unconfined Bash stays a residual too.

### Carried-over checks

- **Ticket 01 discovery**, rerun from `.scratch/` after the dev skill moved. Codex (0.163.0): named `.agents/skills/cross-model-review/SKILL.md`, no `failed to load skill` (`ai_tmp/discovery-codex-2.jsonl`). Claude Code (2.1.309): `init` lists the skill, and the prompt produced `tool_use Skill {"skill": "cross-model-review"}`, then stopped at the `--max-turns 3` cap I set (`ai_tmp/discovery-claude-2.jsonl`). You ran this with your token.
- **Ticket 01 placement:** closed by moving the skill. Its listing test had covered only the default listing.
- **Ticket 02 CI:** the `just check (ubuntu-24.04)` job of run 41983369769 is green, on `bd18420`, which predates this branch.
- **Ticket 02 rechecks:** agents writing outside their homes, see above. Socket-path length: every eval passed from a clone whose `TMPDIR` was about 115 characters, longer than the macOS Unix-socket limit. Claude Code's recorded socket is in `/tmp/cc-socks`, not `TMPDIR`, and it leaves empty task folders in the host `/tmp`, see Agent homes. Codex's sockets were not inspected, but its runs passed.
- **Ticket 06:** `trigger-explicit-invocation` passed on Claude Code in every round.
- **Ticket 10:** the Codex dispatch is carried, see the open items.
- **All other recorded gaps** are in `.scratch/foundation/follow-ups.md`.

### Cross-model review

- **Implementer:** Claude Code running `claude-opus-5-5`
- **Reviewer:** Codex `gpt-6-astra` (fallback: no), read-only sandbox, ephemeral. All runs exited 0.
- **Triage:** a Workflow with a fresh subagent per finding and a second subagent that tried to refute each one marked valid. Reviewer severity → triage severity in the table.

| Pass | Reviewed | Findings | Prefix |
| --- | --- | --- | --- |
| Whole repo | b31ffd2 | `ai_tmp/review-20261106T031302Z-codex.md` | F |
| Harness | b31ffd2 | `ai_tmp/review-20261106T032059Z-codex.md` | H |
| Tooling, CI, distribution | b31ffd2 | `ai_tmp/review-20261106T032619Z-codex.md` | T |
| Docs | b31ffd2 | `ai_tmp/review-20261106T033140Z-codex.md` | D |
| Tickets | b31ffd2 | `ai_tmp/review-20261106T033703Z-codex.md` | K |
| Re-review of the fix diff | b31ffd2...b4e15c5 | `ai_tmp/review-20261106T050029Z-codex.md` | R |

The first pass returned 3 findings in 6 minutes, so the plan's by-area passes followed. Each took about 5 minutes, far under the 90-minute limit, and static reading only, because the reviewer has no write access. That is a limit on how deep this review went. **Triage:** `ai_tmp/triage-20261106.md`.

| # | Severity | Finding | Verdict | Action |
| --- | --- | --- | --- | --- |
| F1 | high → high | The secret sweep does not safely handle unreadable trial output | valid | fixed in b4e15c5 |
| F2 | medium → low | Codex records a trigger when only filename headers reach the model | valid | fixed in b4e15c5; residual in follow-ups |
| F3 | medium → medium | The README gives the wrong explicit Codex invocation | valid | fixed in b4e15c5 |
| H1 | high → medium | SIGTERM bypasses process cleanup and credential removal | valid | fixed in b4e15c5 |
| H2 | high → low | Output-size caps do not bound memory consumption | out of scope | follow-up |
| H3 | medium → low | `script_ran` can pass when Python never opens the script | valid | fixed in b4e15c5, wrapper corrected in fb7f76e |
| H4 | medium → low | Generated reports discard exclusion and disclosure warnings | out of scope | follow-up |
| H5 | medium → medium | Changed case weights produce falsely comparable pooled regressions | out of scope | follow-up |
| H6 | medium → low | Interrupting a batch loses completed trials' result records | out of scope | follow-up |
| H7 | low → low | History validation accepts records that crash report generation | out of scope | follow-up |
| T1 | medium → low | Review timeouts leave the native Codex process running | out of scope | follow-up |
| T2 | medium → low | Scaffold rollback can corrupt the marketplace while claiming nothing was kept | out of scope (triager valid, refuted) | follow-up |
| T3 | medium → low | Direct hook installation writes outside a secondary worktree | out of scope | follow-up |
| T4 | medium → low | Distribution exclusion checks automatically approve internal files in new skills | out of scope | follow-up |
| T5 | medium → medium | Reviewer selection can silently substitute a global CLI for the pinned installation | valid | fixed in 7ea543a |
| T6 | medium → low | The full gate never validates committed benchmark history | out of scope | follow-up |
| D1 | medium → low | Trigger cases score assertions despite the documented schema | valid | fixed in b4e15c5 |
| D2 | medium → low | Expected-output scripts lose the environment that keeps writes inside the project | valid | fixed in b4e15c5 |
| D3 | medium → low | Installed skills omit the copyright and permission notices required by the repository licence | out of scope | follow-up |
| D4 | medium → low | The grader excludes nonempty replies that ADR 0012 says must count | valid | fixed in b4e15c5 |
| D5 | low → low | The Node setup instructions incorrectly promise nvm and Volta will read `.node-version` | valid | fixed in b4e15c5 |
| D6 | low → low | The documented iteration-name rules omit rejected names | valid | fixed in b4e15c5 |
| D7 | low → low | "Trigger" excludes explicit invocation in the glossary but includes it in reported metrics | valid | fixed in b4e15c5 |
| K1 | high → medium | Ticket 04 declares the dev-skill exclusion gap closed while the known leak remains | valid | fixed in e80397b, by your choice (ADR 0015) |
| K2 | medium → low | The ticked skill-content-hash criterion does not cover the payload actually installed | out of scope (triager valid, refuted) | follow-up |
| K3 | medium → low | Codex's required discovery-location canary proof is only partly implemented | out of scope | follow-up |
| K4 | medium → low | Ticket 09's recorded malformed-history fix still permits report-crashing records | valid | fixed in b4e15c5; values remain, see H7 |
| K5 | low → low | Ticket 09 doubles the number of trials in its live acceptance evidence | valid | fixed in 605349c |
| R1 | high → medium | `verify_clean` raised an unscrubbed error on an unreadable path before deleting leaks | valid | fixed in 99c9886 |
| R2 | medium → low | The scan accepted unreadable paths with no secrets configured | valid | fixed in 99c9886 |
| R3 | medium → low | A pending signal still launched the next subprocess | valid | fixed in 99c9886; the opens before a launch were still open until 5980e79 (S2) |

### Branch code review

`code-review high main`, on 67f8bd0. Ten unverified findings, checked by me against the triage.

| Finding | Action |
| --- | --- |
| The python wrapper's loss of `exec` left the interpreter running after a signal | fixed in fb7f76e, test-first |
| The pass-count one-liner counted baseline trials | fixed in fb7f76e |
| The trigger rule omitted `dev-skills/build` | fixed in fb7f76e |
| ADR 0015 omitted `metadata.internal` | recorded in fb7f76e |
| No completion notes yet | this section |
| A signal-stopped run discards `secret_found`; `MemoryError` in the sweep; `restore_access` order; repeated signals swallowed; a directory or FIFO named after a token | follow-ups |
| History values not validated | follow-ups, H7 |

**Not re-reviewed until the final reviews:** the re-review round covered b31ffd2...b4e15c5 only. 99c9886, 67f8bd0 and fb7f76e had no review by a different model until the final reviews below. The branch code review above was by the same model family as the implementer.

### Final reviews

You asked for a last adversarial review after sign-off, because `99c9886`, `67f8bd0`, `fb7f76e`, `605349c` and `454cf29` had not been read by a different model. It ran in rounds. Each round's fixes were reviewed again until a round's valid findings changed no runtime code.

- **Implementer:** Claude Code running `claude-opus-5-5`
- **Reviewer:** Codex `gpt-6-astra` (fallback: no), read-only sandbox, ephemeral. Every run that reached the reviewer exited 0 on its first attempt. One more attempt of round V never reached it: `review.py` refused to start, exit 1, because a new test (fixed in `8825b28`) left an unreadable directory in the worktree.
- **Triage:** a Workflow with a fresh subagent per finding. A second fresh subagent tried to prove the verdict wrong for every finding in rounds U, V, W and X, whichever way it went, but in the final round only for the valid ones (S1, S2, S4, S6). The S3, S5 and S7 verdicts rest on the first triage alone. Reviewer severity → triage severity in the table.

| Round | Reviewed | Findings | Triage | Prefix |
| --- | --- | --- | --- | --- |
| Final | b4e15c5...454cf29 | `ai_tmp/review-20261106T114829Z-codex.md` | `ai_tmp/triage-final.md` | S |
| Fixes | 454cf29...5980e79 | `ai_tmp/review-20261106T190705Z-codex.md` | `ai_tmp/triage-fixes-*.md`, `ai_tmp/refute-fixes-*.md` | U |
| Fixes | 5980e79...8825b28 | `ai_tmp/review-20261107T075606Z-codex.md` | `ai_tmp/triage-f862-*.md`, `ai_tmp/refute-f862-*.md` | V |
| Fixes | 8825b28...8f702a4 | `ai_tmp/review-20261107T084801Z-codex.md` | `ai_tmp/triage-8f70-*.md`, `ai_tmp/refute-8f70-*.md` | W |
| Fixes and notes | 8f702a4...2f0a4eb | `ai_tmp/review-20261109T192037Z-codex.md` | `ai_tmp/triage-2f0a-*.md`, `ai_tmp/refute-2f0a-*.md` | X |

| # | Severity | Finding | Verdict | Action |
| --- | --- | --- | --- | --- |
| S1 | high → medium | Deleting a leak could raise an unscrubbed error that named the secret and stopped the other deletions | valid | fixed in 5980e79 |
| S2 | medium → low | A signal after the stop check still launched the agent | valid | fixed in 5980e79 for the output-file opens; the instant of the launch itself cannot be closed, so it is documented and pinned by a test |
| S3 | medium → low | The python wrapper starts Python before installing its traps | out of scope | follow-up; the group teardown bounds it |
| S4 | medium → low | An unreadable results directory was not deleted as documented | valid | fixed in 5980e79 |
| S5 | medium → none | The Codex canary gap was filed as a follow-up when it is a mandatory criterion | invalid | the criterion's "OS home" is `HOME` as against `CODEX_HOME`; K3 stays a follow-up |
| S6 | medium → medium | "The walkthrough leaves nothing outside the project" is ticked despite an exception | valid | recorded under Agent homes and accepted by you, see the sign-off |
| S7 | low → none | The new stdin test passes without its fix | out of scope | true only of the pre-fb7f76e wrapper; the test caught the dash bug below |
| U1 | high → low | `restore_access` could change modes outside the trial through a link | valid, narrowed | as written, about results directories, it gave an agent nothing; a refuter showed a leftover process swapping a directory for a link mid-walk redirected `chmod` out of a Codex trial in 4 of 10 trials. Fixed in f862cca |
| U2 | medium → low | Failed cleanup could be reported as deleted, because `exists()` is False on a denied stat | valid | fixed in f862cca, at `verify_clean` and both `run_trial` sites |
| V1 | high → low | On Linux, an entry swapped for a link after its stat still redirected `chmod`, and the docs limited this to files | valid | fixed in 8f702a4: CPython leaves `chmod` out of `os.supports_follow_symlinks` on Linux, but `fchmodat` honours no-follow |
| V2 | medium → low | `os.fwalk` holds a descriptor per level, so a tree past the open-file limit is only partly restored, silently | valid | documented and pinned in 8f702a4; `fwalk` kept, because the link defence rests on it, and the trial fails closed |
| V3 | medium → medium | No test pinned the `secret_found.deleted` site | valid | test added in 8f702a4 |
| W1 | medium → none | The descriptor-limit test never checks that the trial fails closed | invalid | the mutation it names is caught by three existing trial-level tests |
| W2 | medium → low | The docs promised "could not be deleted" whenever restoring falls short, but a locked file is still deleted with its directory | valid | fixed in c2fec97 |
| W3 | medium → low | Two tests unlock their locked directories only through `restore_access`, so a host without no-follow `chmod` would keep unreadable paths | valid | fixed in c2fec97; a third test with the same defect, X1, in a639ff8 |
| X1 | medium → low | `test_a_token_in_output_the_agent_locked_is_swept_and_deleted`, from b4e15c5, also relied on `restore_access` alone | valid | fixed in a639ff8 |
| X2 | low → low | The triage bullet claimed a refuter for every finding, but round S had one only for valid findings | valid | corrected in the Triage bullet above |

**Not re-reviewed:** a639ff8 and the commit that records round X, which change one test's cleanup and these notes. No runtime code changed after round W.

**Found by CI, not by review:** Ubuntu CI failed on 454cf29. `/bin/sh` is dash there, which gives a background job `/dev/null` as stdin, so the python wrapper lost the agent's stdin. macOS runs bash as `/bin/sh`, so local `just check` passed. Fixed in eaac319 through fd 9, with tests under each available shell, and reviewed in round U. All four walkthrough rounds ran on macOS before eaac319, so their live evals never ran the wrapper under dash.

**Linux check of the `ValueError` guard,** run on 2026-11-09 after round W: in a `python:3.13-slim` container (Debian 13, glibc 2.41), as a non-root user with no network, the swap-after-stat scenario left the outside target unchanged and locked trees opened. With the guard removed, `restore_access` raised `ValueError: chmod: cannot use dir_fd and follow_symlinks together`, which would abort trial cleanup, so the test, which calls `restore_access`, would fail on Ubuntu; the test itself was not run in the container. The repo's code was run on Python 3.13 with deferred annotations added to a scratch copy, since the image has no 3.14.

**Probes outside the project during triage:** a refuter's Claude CLI runs left `/private/tmp/claude-501/<slug>` folders and `/private/tmp/cc-socks-501`, both removed; a baseline probe may have left one `fswatch-probe` directory. The S5 probe ran the pinned Codex with `HOME` redirected and wrote nothing to the real `~/.agents/skills`, which `find -newer` confirmed. Round U and V triagers ran Linux probes in Docker containers. Every image listed afterwards predates this work, so none was pulled for it, and no probe container remained.

### Checks

`just check` in this worktree on a639ff8, the last test change: 892 passed, 2 skipped. Only ticket text changed after it. CI's `just check` on macOS-15 and ubuntu-24.04 passed on 2f0a4eb, and on 8f702a4, where ubuntu showed the no-follow `chmod` opening locked trees on Linux. Round 4 also ran `just check` in a clean clone at fb7f76e: 869 passed, 2 skipped.

### Open items and sign-off

**Ticket 10, mandatory criterion, recorded by your decision:** the Codex secret-present dispatch has not been shown, because `OPENAI_API_KEY` is unset, and neither has an API-key login's trial auth. Ticket 10 stays "done, except", and it is also in the follow-ups as the action to take.

**Ticket 12, confirmed by you on 2026-11-05:**

- The hand-off meets "a fresh-context subagent completes these steps". It stays recorded as a deviation under Walkthrough.
- `setup-token` through `just run` and `read -rs` both work as `docs/how-to/run-evals.md` says.
- The foundation is done with ticket 10's open item still open.

**Ticket 12, confirmed by you on 2026-11-06:**

- The walkthrough's empty folders in the host `/tmp` are accepted as a deviation from "leaves nothing outside the project directory", which stays ticked. Confining them is in the follow-ups.
