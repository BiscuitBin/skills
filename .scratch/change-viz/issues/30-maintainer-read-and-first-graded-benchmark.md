# 30: The maintainer's read, and the first graded benchmark

**What to build:** what ticket 25 left undone when `change-viz` `0.2.0` was released as is:

- Claude Code's outputs on the four real changes;
- the maintainer's read of all eight outputs beside the four originals;
- a feedback round that also fixes the strict misses and false claims found on Codex, except E7 (ticket 29);
- the first graded runs of the skill on both agents, recorded as a benchmark iteration.

Why: `0.2.0` shipped without any of these (ticket 25, **Released as is (D9, 2026-11-17)**).

- Claude Code has never run the `0.2.0` text. It last ran in ticket 18, on the tracer's text.
- No run of the `0.2.0` text has been graded. On Codex, every measure is by pattern, plus a strict hand read that stood in for the grader (D2).
- The question ticket 25 was written for is still open: does the description give the maintainer "confidence and understanding" on a real change? Only the maintainer can judge that.

**Blocked by:** 25 (Review with the maintainer, then ship).

**Status:** needs-maintainer

**Agent requirements:** Any implementing agent (Claude Code or Codex).

- **The agent:** makes the Codex outputs and runs the Codex live evals with `--no-grader` (D2), in the lead's own session: a subagent's attempt was refused by its permission check (ticket 25, **The maintainer's confirmations**, 2). It reads `eval-results/` and never holds the token.
- **The maintainer:** runs Claude Code and the graded runs in their own terminal, with the token, then reads the outputs and gives feedback.
- Cross-model review is also required.

## What is known

As of 2026-11-17, from ticket 25's completion notes.

- **What shipped:**
  - `skills/change-viz/` as of `5d4eff9`, at `0.2.0`, released by merging PR #19, which the maintainer merges (D7).
  - `skill_sha256` is `6d4d615a2fc2361efd6a642a4d7170d0302c0dc867a33b58f8ca039748abde46`.
  - The eval suite is frozen at `evals_sha256` `d3890efe69ae903d6fc240aa70588b9af5ae8c8de52d686259e7a478c2ebb5be`.
- **Codex on that text, without the grader:**
  - The skill arm passed every pattern assertion in all 21 cases (run `20261117T064129Z-f47c`).
  - In the last full pass, every behaviour case's baseline failed an output assertion beyond the trigger (run `20261117T032603Z-bae2`, at `01b3817`).
  - Two readers judged every expectation strictly, and 17 of the 21 cases passed. Each case with a miss was rerun once, in `20261117T073227Z-3d49` and `20261117T073735Z-7a96`.
  - Three cases missed in both draws. The table is in ticket 25, **Outputs before the maintainer's session (2026-11-17)**:
    - the tracer's E7, which is ticket 29's;
    - `behaviour-describe-add-weekdays-2`'s C1 and C4: it names the release workflow, never PyPI;
    - `behaviour-branch-and-uncommitted`'s E1: it never says what `--longest` prints.
  - The readers also found false claims and misleading sketches that no expectation covers. Ticket 25's list, under **False claims no expectation covers**, names such faults in 10 of the 21 outputs. The full reads are `ai_tmp/stage4/final-skill/read-a.md` and `read-b.md`.
  - **Beyond ticket 25's list.** On 2026-11-17, each fault the two reads record was checked against ticket 25's list, and the faults ticket 25 leaves out were checked again against their fixtures (`ai_tmp/release/reads-gap.json`). These held:
    - **Visuals that draw more or less than the code:**
      - `behaviour-describe-add-holds`: the sketch draws `+if action == "hold": copy["hold"] = fields[1]` without the on-loan and one-hold check. Its lead-in promises "the reservation check", which the block leaves out. The state diagram draws `LoanWithHold` as a state, though the code keeps the copy `on_loan` and only fills its `hold` field.
      - `behaviour-describe-fix-due-today`: the sketch draws the new test method as a call, `+test_not_late_on_the_due_date()`.
      - `behaviour-branch-and-uncommitted`, in `f47c`: the lead-in says the path "changes the displayed unit", which the flowchart does not draw.
      - `behaviour-branch-and-uncommitted`, in the rerun `3d49`: "Print count and total via distance()" sends the count through `distance()`, though only the total goes through it.
      - The tracer, in `f47c`: the flowchart loops a dropped token back to "Split on whitespace", which mixes a per-token loop with the one split.
      - The tracer, in the rerun `7a96`: the flowchart asks "--top N supplied?", but the code tests `if args.top:`, so `--top 0` lists nothing.
    - **A claim wider than the code:** `behaviour-describe-fingerprint-branch` says "the tracked notes contain blank lines", but only `notes/plan.txt` has one.
    - **A walk-back that leaves out steps:** `behaviour-describe-retire-wishlist` does not say the revert must come before the restore, or that a restore loses the entries made after the drop.
    - **Runtime claims with no evidence label:**
      - `behaviour-describe-with-flowchart`'s example of what a malformed line "now prints".
      - `behaviour-describe-and-run-check`'s "Why medium" claim about recorded fingerprints.
    - **Two risk calls for one change:** the same pantry branch is rated Medium in `behaviour-describe-with-flowchart` and Low in `behaviour-describe-with-sequence`, both in `f47c`. The rerun of `with-sequence`, in `3d49`, rates it Medium.
    - **Notes that describe rather than warn,** in the readers' judgement: at least one note in each of these restates the feature instead of warning of what could catch the reader out:
      - the tracer;
      - `behaviour-describe-add-weekdays`;
      - `behaviour-describe-add-weekdays-2`, in both draws;
      - `behaviour-describe-fix-due-today`;
      - `behaviour-describe-add-holds`;
      - `behaviour-describe-uncommitted`.
    - **Borderline:** `behaviour-describe-changes-try-ideas` never names `hikes.py`. The reader passed F1, which asks for it.
    - **Reads before a size check:** in `behaviour-describe-uncommitted` (`f47c`), the trial read the untracked `summary.sh`, and dumped the first 64 bytes of the binary `tracks/ridge-loop.fit` with `od`, before any size check. Design 22 §6 records this rather than failing it, and `transcript_checks.md` misses it.
- **Codex on the four real changes:** made at `5d4eff9` with `run-codex.sh`, with the table in ticket 25. The maintainer has not read them yet.
- **The maintainer's confirmations of 2026-11-17 still hold** (ticket 25, **The maintainer's confirmations**):
  - PS2 stays frozen.
  - rove runs with its plugin setting.
  - The D6 reading stands.
  - The misses and false claims join the feedback round, and E7 stays with ticket 29.
- **What the release changes:**
  - Once PR #19 is merged, `0.2.0` is on `main`, so a text fix changes a shipped skill. It goes in its own pull request, with a version bump by semver (`CONTRIBUTING.md`, **Versions**): a patch, `0.2.1`, if every change is a correction.
  - Both runs of a benchmark iteration must share one `skill_sha256` and one `evals_sha256` (ADR 0014), so the graded runs come after the last change to `skills/change-viz/`. The version in `skills/change-viz/.claude-plugin/plugin.json` is part of that tree, so the bump comes before the graded runs, not after.
  - A graded pair on `0.2.0`, taken before the feedback round and recorded as its own iteration, would give the report a before and an after. It is optional, and the maintainer decides.
- **The dry runs** (no token, at `c7c31a6`, with the cases and skill text as released):
  - Each agent plans 21 skill-arm and 20 baseline-arm agent calls. The quiet case, `no-trigger-unnamed-request`, has no baseline arm by design.
  - Each agent plans at most 40 grader calls, on `claude-opus-5-5`.
  - The spend caps are $81.00 for Claude Code, where `--max-budget-usd` caps each call, and $40.00 for Codex's grader. Codex agent calls have no per-call cap.
- **The `gh` login during the graded runs** (ticket 23, row 5c): log out with `gh auth logout` for the runs and back in after, or use a fine-grained token with read-only access to public repositories. A trial cannot reach the login as built. But Claude Code's Bash is not sandboxed, and an agent that repointed `HOME` could. Ticket 23 records which one was used.
- **Writes outside the project:** every Claude Code run writes a socket to `/tmp/cc-socks/<pid>.sock`. Ticket 25 records it, and the maintainer accepted it.
- **The local aids exist only in the `change-viz` worktree,** and Git ignores them. Keep that worktree until this ticket is done:
  - `ai_tmp/real/`:
    - `setup.sh` clones each change under `ai_tmp/real/<change>/repo/` and checks the pull request's head out as its own branch. It sets local `main` and `origin/main` to the commit the pull request was cut from, and saves the original description beside the clone. Its only network use is reads.
    - `run-codex.sh` and `run-claude.sh` run the pinned CLIs through `just run`. They install the skill from the committed `HEAD` with `git archive`, put `HOME` and `TMPDIR` under the change's folder, and stub `gh`.
    - `lib.sh`, and `make_readme.py`, which builds `READ-ME.md`.
    - The Codex outputs.
  - `ai_tmp/stage4/final-skill/`: the two hand reads, the outputs they read, and `transcript_checks.py`.
  - `eval-results/`: the runs above.
  - `ai_tmp/release/SESSION.md`: the runbook as it stood at `19587fb`.

  If they are gone, rebuild the clones with the method described under the `setup.sh` bullet. Ticket 25's notes give the branches, commit counts and file counts.

## The runbook

The closing-session runbook (`ai_tmp/release/SESSION.md`) is kept here, changed for a skill that is already released.

- **Where commands run:** every command runs from the `change-viz` worktree, the one that holds the local aids. From another checkout, `just eval` would run that checkout's text and write to its `eval-results/`. In each of the maintainer's terminals, the Codex one included, give `cd <worktree>` as its own first line.
- **Paths:** they are from the worktree root here. Give the maintainer each command with absolute paths, on its own line.
- **No chaining:** never chain the commands with `&&`. A failing eval exits 1, and `run-claude.sh` exits 1 if any change fails.

0. **Before you start:**
   - Confirm that PR #19 is merged.
   - In the `change-viz` worktree, switch to a new branch from the updated `origin/main`. The ignored aids stay in place. Never commit this ticket's work to `change-viz`, which is PR #19's branch.
   - Check that `skills/change-viz/` still matches `5d4eff9`: `git diff --stat 5d4eff9 -- skills/change-viz` prints nothing. If it prints anything, say what changed before starting.
1. **Setup**, in the maintainer's terminal: `read -rs CLAUDE_CODE_OAUTH_TOKEN`, then `export CLAUDE_CODE_OAUTH_TOKEN`, then `gh auth logout` (or the read-only token).
2. **Claude Code on the four real changes,** which takes about 10 minutes: `sh ai_tmp/real/run-claude.sh all`. The agent then rebuilds `ai_tmp/real/READ-ME.md` with Claude Code's outputs beside Codex's. If the skill text has changed since `5d4eff9`, first rerun `sh ai_tmp/real/run-codex.sh all`, so both agents read the same text.
3. **The read:** the maintainer opens `ai_tmp/real/READ-ME.md`. For each change it shows the original description, then the Codex output, then the Claude Code output. The maintainer says what is wrong, what they would cut and what is missing. The agent records their words here as they give them.
4. **The feedback:**
   - The agent applies each point by its general reason, so that no rule fits only one of the four.
   - In the same round, it fixes the misses and false claims above in the same way, except E7.
   - Then:
     - a short cross-model review of only those changes;
     - the four Codex outputs rerun;
     - each eval case those misses and false claims came from, rerun on Codex with `--no-grader` and read strictly.
   - The maintainer reruns step 2 and confirms the result, or a second round is recorded.
   - Once it is confirmed, and before the dry runs:
     - bump `version` in `skills/change-viz/.claude-plugin/plugin.json` by semver, `0.2.1` if every change is a correction;
     - run `just format`;
     - commit everything, this ticket included, so the tree is clean.

     The bump is part of `skill_sha256`, so it is the last change before the graded runs.
5. **The graded runs, on both agents.** Dry runs first. Stop if the plans or caps differ from **The dry runs** above.

   ```sh
   just eval change-viz --agent claude --baseline --trials 1 --dry-run
   ```

   ```sh
   just eval change-viz --agent codex --baseline --trials 1 --dry-run
   ```

   Then the two runs. They can run at the same time in two terminals. The grader is always Claude, so the Codex terminal needs step 1's `read -rs` and `export` too.

   ```sh
   just eval change-viz --agent claude --baseline --trials 1
   ```

   ```sh
   just eval change-viz --agent codex --baseline --trials 1
   ```

   The maintainer gives the agent the two run ids, which are the directory names under `eval-results/`.
   - A failure that is the skill's fault gets one fix-and-rerun loop. Rerun both agents on the fixed text, so the two runs still share one `skill_sha256`.
   - Codex's E7 is recorded as it is (ticket 29).
6. **After:**
   - The maintainer runs `gh auth login`.
   - The agent runs `just eval-record ticket-30 <claude-run-id> <codex-run-id>` and commits the file it writes.
   - The agent builds `just eval-report change-viz` and runs `just check`.
   - The agent pushes and opens the pull request, and the maintainer merges it.

## Acceptance criteria

- [ ] Claude Code runs on each of the four real changes:
  - as a branch against its base, with `gh` stubbed;
  - on the pinned CLI through `just run`, with the skill installed into the clone as a user would install it;
  - writing nothing to the maintainer's agent homes, and leaving each clone as it found it.

  Each output is saved under `ai_tmp/`, beside the original description and the Codex output.
- [ ] The maintainer reads the eight outputs beside the four originals. Their words are recorded here, by output.
- [ ] Each piece of feedback, and each strict miss and false claim above, is applied by finding its general reason and changing what the skill explains.
  - No rule is added that makes sense only for one of the four changes or one fixture.
  - For each, the notes say what changed and why it generalises, or why it was not applied.
  - E7 stays with ticket 29.
- [ ] After the changes:
  - the four Codex outputs are regenerated;
  - each eval case those misses and false claims came from is rerun on Codex with `--no-grader` and read strictly;
  - the maintainer reruns Claude Code and confirms the result, or a second round is recorded.
- [ ] The full suite is graded on Claude Code and Codex with `--baseline --trials 1`, with `gh` logged out or on a read-only token (recorded in ticket 23, row 5c).
  - It passes, apart from Codex's E7 (ticket 29).
  - The two runs are recorded as a benchmark iteration with `just eval-record`, and the file it writes is committed.
  - `just eval-report change-viz` builds.
- [ ] If the skill's files changed, the version is bumped by semver (`CONTRIBUTING.md`, **Versions**) and `just format` has run. The changes are committed, `just check` passes, and the pull request is ready for the maintainer to merge.

## Out of scope

- Ticket 29's work: E7, and any change to a frozen expectation, the rubric or the grader.
- The live pull request path (26), the Linux `gh` case (27) and the render post (28).
- New behaviours the feedback asks for that are larger than a correction. Each becomes its own ticket.

## Review checkpoints

Use the `cross-model-review` dev skill.

- **Maintainer checkpoint:** the read, above. The graded runs and the benchmark wait until the maintainer confirms the regenerated outputs.
- **Implementation checkpoint:** before the graded runs, review only the feedback round's changes, against these criteria and those of tickets 18 to 25. Pay particular attention to rules added for one of the four changes or one fixture, and to rules that contradict each other across references.
