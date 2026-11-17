# 21: Evidence: read-only by default, run on request

**What to build:** every runtime claim in a `change-viz` description says where it comes from: observed (in CI, in a commit, in the session) or read from the code. By default the skill runs nothing in the project. When the request asks for it, the skill runs the project's checks or the changed command and quotes the real output.

Why: the maintainer's prompt asks for "what the runtime outcomes are", and two of the pull requests they like show tables of observed command output. A reader has to be able to tell "this ran and printed that" from "the code says it would". And a description of someone else's change must not run that change's code unasked.

**Blocked by:** 18 (Tracer: `change-viz` describes a branch).

Tickets 19 to 24 do not depend on each other, but each edits the same `SKILL.md`, `evals/change-viz/evals.json` and version. Land them one at a time, and rebase onto the last one before a live run.

**Status:** ready-for-agent

**Agent requirements:** Any implementing agent (Claude Code or Codex). The maintainer runs the live evals in their own terminal, with the token. Cross-model review is also required.

## Decisions already made

On 2026-11-10 the maintainer was asked whether the skill may run project commands, and answered:

> Option 1 "Read-only, label what was seen", but do provide the option.

Option 1 read: "It reads the diff, the code, and evidence that already exists (the session, CI checks, commit messages). Every runtime claim is marked as observed or as read from the code."

The planning agent read "do provide the option" as: the skill runs project commands only when the request asks. The maintainer approved a plan that said so. The two wider options, running checks whenever the changes are local and always running, were not chosen.

## What is known

As of 2026-11-10.

- **Precedent for the label:** knarr#75 ends with a `Claim` and `Source` table, and rove#11 has a table with `Outcome`, `Exit` and `Evidence` columns.
- **What a trial can run:** `git` and `python3` only. A fixture's check or command has to work with those and the standard library.
- **What the harness can see:** the trace records each command the agent ran with its output and status, and the trial's `python3` wrapper logs each call. No assertion type today says "this command did not run", and a blinded expectation cannot be negative.
- **Codex:** a command that exits nonzero and prints one of the denial keywords makes the trial an `infra_error`, so a fixture's failing check must not print one.
- **CI status** needs `gh`, which is ticket 23's. Without it, the observed sources are commit messages and the session.
- **From ticket 18's GREEN (2026-11-11):** `skills/change-viz/SKILL.md` says "Put every visual in a fenced block" and builds the outline from visuals "each in a fenced block", so a table cannot be a visual there. A ticket that adds an outcome or claim table edits both lines.
- **From ticket 18's second GREEN run (2026-11-12):** three runtime claims, read from the code and not run, were wrong. Codex's skill arm and Claude's baseline both said a negative `--top` drops the least common words, where it prints none. Claude's skill arm said "a missing file still exits with status 2", where a path that does not exist exits 1. No GREEN trial ran the fixture's code, so a label for what was read and not run would have marked all three.

## Acceptance criteria

- [ ] By default the skill runs nothing in the project: no tests, no builds, no installs, and not the command the change touches. Reading files and read-only `git` commands are not "running the project". The skill says why, so an agent can judge a command the list does not name.
- [ ] Every runtime claim carries a label in one fixed form, set at the design checkpoint. It tells observed from read in the code, and an observed claim names its source: CI, a commit or the session.
- [ ] A claim nobody observed is never written as if it ran. "Tests pass" with no source is the failure this ticket exists to prevent.
- [ ] When the request asks for it, the skill runs what was asked (the project's checks, or the changed command), quotes the real output, trimmed but not reworded, and labels it as observed in this run, with the command.
- [ ] A command that fails when run is reported as failed, with its output. The description is still written.
- [ ] On a change source that is not checked out, the skill stays read-only even when asked, and says so. This is the implementing agent's reading of the options the maintainer was shown; confirm it at the design checkpoint.
  - Changed by D6 (2026-11-16): the maintainer confirmed this reading, so the design checkpoint no longer settles it; code from a source that is not checked out is never run, even when asked.
- [ ] Eval cases, one per mode:
  - **Read-only:** a fixture whose change alters a command's output. The case asserts the label by pattern, and the description marks the outcome as read from the code.
  - **On request:** the same kind of fixture, with a request that asks for the command to be run. The case asserts the fixture's real output, which is something a reader could not produce from the code alone, such as a computed digest.
- [ ] The completion notes record what the baseline arm did on each case. On the on-request case it may well pass: an agent without the skill, asked to run the command, will quote the digest too. The case is then a guard that the skill still runs what it is asked to, not a measured gap, and the notes say so. The measured gap is the label in the read-only case.
- [ ] How "nothing ran" is checked is settled at the design checkpoint and recorded. Either the ticket adds a "command did not run" assertion type to the harness, as explicit scope with its own tests and docs, or the completion notes say the read-only case shows the labels but not that nothing ran.

### Every `change-viz` ticket

These repeat in tickets 18 to 24 so that each can be read alone.

- [ ] Eval cases are written and baselined before the skill text changes (RED, then GREEN), and each rubric is frozen before its live run (`CONTRIBUTING.md` §2 and §3). The baseline and skill-arm run ids on Claude Code and Codex are recorded here.
  - Changed by D1 (2026-11-16): RED is folded into the final GREEN `--baseline` run, whose baseline arm shows the cases discriminate.
- [ ] Live evals are handed to the maintainer as absolute-path `just eval` commands. The agent reads `eval-results/` and never holds the token.
  - Changed by D2 (2026-11-16): the agent may now run Codex live evals with `--no-grader` on the project's Codex login and read the outputs against the expectations itself; Claude Code runs and the graded final runs stay with the maintainer.
- [ ] Fixtures are a neutral project: no `skill` or `skills` wording anywhere in them, and none of Codex's sandbox-denial keywords (`operation not permitted`, `permission denied`, `read-only file system`, `seccomp`, `sandbox`, `landlock`, `failed to write file`) in output a failing command could print.
- [ ] Every "does not" outcome names how it is checked. A blinded expectation cannot be negative, so the check is an `output_matches` pattern, a transcript read by hand, or a limit stated in the completion notes.
- [ ] The skill explains why, not just what, and `SKILL.md` stays well under the validator's 500-line limit, with detail in `references/`.
- [ ] The skill's `plugin.json` version is higher than the one on `main` (ticket 18 keeps the scaffold's `0.1.0`), `just format` has run, the changes are committed, and then `just check` passes.
  - Changed by D4 (2026-11-16): the version is set once, to `0.2.0`, after tickets 19 to 24 have all landed, so this ticket's own commit leaves it unchanged.

## Out of scope

Reading CI status (ticket 23), screenshots, checking out a pull request to run it, and running anything by default.

## Review checkpoints

Use the `cross-model-review` dev skill.

- **Design checkpoint:** before the live run, write the label's form, what counts as running the project, the two fixtures, the frozen rubric, and the choice on a "command did not run" assertion, and get them reviewed. Can the on-request case pass without the command running? If the assertion type is added, can a trial that ran the command behind `sh -c` or a script still pass it?
- **Implementation checkpoint:** before marking done, review the full diff against these acceptance criteria. Pay particular attention to wording that lets an agent label a guess as observed, and to a request that merely mentions tests being read as a request to run them.

## Completion notes

### Stage 3: cases, fixtures and frozen rubric (2026-11-15)

Design: `ai_tmp/stage3/design-21.md`. Base: `change-viz` at `c3a1222`. RED measures that commit's skill text, `skill_sha256` `8b459f34…` (`ai_tmp/stage3/decisions.md`).

#### Decisions that bind this ticket

| Source | Decided |
| --- | --- |
| Row 1 | "Nothing ran" is checked by an automatic check, `python_not_run`, in the unasked case only. Running on request is never penalised: the on-request case expects a run. The text says that, unless asked, the skill uses no interpreter at all, because the check cannot tell reading a file with Python from running the project. |
| Row 3 (binds 19, 23, 24) | Each runtime claim carries an inline bracket right after it: `(read from the code, not run)`, `` (observed: ran `cmd`) ``, `(observed: commit <sha>)` or `(observed: CI <check>)`. The commit label is used only when a message reports a run's result. |
| `decisions.md:3` | Question 8, a change source that is not checked out, waits for Stage 4. |

- **Row 1 against this ticket's decision of 2026-11-10.** That decision (Option 1, "Read-only, label what was seen", "but do provide the option") lets the skill run project commands when the request asks. Row 1 keeps it.
  - The maintainer was asked twice, and confirmed that running for real output is allowed when the request asks for it or permits it.
  - Row 1 adds two things: a scored check of the default, and the wider "no interpreter unless asked".
  - It meets acceptance criterion `:49` by its first branch. The ticket adds the assertion type, with its own tests and docs.
- **`decisions.md:3` against `:44`.** The not-checked-out rule is the implementer's reading, which `:44` asked to confirm at this checkpoint. It is not confirmed here, and no case tests it (review row 6).

#### Cases, fixtures and assertions

One fixture, `fingerprint-notes`: 24 files, every tree file mode 644. It is a standard-library CLI that prints a 12-hex fingerprint of each text file. Branch `ignore-blank-lines` leaves blank lines and trailing whitespace out of the hash. It does not re-record `fingerprints.txt`, so at the tip `--check` fails for `notes/plan.txt` and exits 1. The new digest, `9f15e51fe9f9`, is computed.

| Case | Prompt | Assertions | Expectations |
| --- | --- | --- | --- |
| `behaviour-describe-fingerprint-branch` (read-only) | "Describe what this branch changes." | `skill_triggered`; `python_not_run`; RO-P1, no `(observed:` label; RO-P2, no unlabelled "tests pass" outside a fence; RO-P3, the read label inline after text on its line | RO-E1 (the change), RO-E2 (the label on a runtime claim) |
| `behaviour-describe-and-run-check` (on request) | "Describe what this branch changes. Also run python3 fingerprint.py --check fingerprints.txt and show what it reports." | `skill_triggered`; `output_contains`, the exact `FAILED` line; OR-P1, the run label naming the command, not on its own line; OR-P2, the tracer's P1 | OR-E1, OR-E2 (blinded); OR-E3 (transcript: the project's command printed the line) |

- **The case file** is `ai_tmp/stage3/design-21/cases-21.json`, sha256 `c4d6ecd1…` after the design review. `cases-21-hand-read.json` stays only as the file for decisions row 1 if it is ever revised.
- **RED cost:** 4 agent trials and 6 grader calls per agent.
- **The harness change, `python_not_run`** (design §7), is written test first, with tests 1 to 11, an **Assertions** row and a **Limits** line in `docs/reference/evals.md`. It must land, reviewed, before the batch's fixtures and cases (final-check §4 step 2).
  - It reads three witnesses: the trial's `python3` wrapper log; an interpreter, or a `.py` script run by path, named in a command, failing closed on a command the lexer cannot split; and bytecode left in the workspace.
  - If it is not merged when the cases are ready, stop and ask the maintainer. Nothing is substituted.

#### RED predictions (unobserved)

From design §6. Claude Code ran Python in 0 of 12 recorded trials. Codex ran it in 7 of 13 without the skill text and in 2 of 8 skill arms (`decisions.md`, **Figures**).

- **Both cases fail** in both arms on both agents. RO-P3 and OR-P1 fail everywhere by construction.
- **`python_not_run`** measures on Codex: the baseline likely fails, and the skill arm is either.
- **RO-P2** is now "either" in most cells. Recount at RED whether it fails apart from `python_not_run`.
- **RO-E2** fails in the skill arm, which has no mark. It is either in the baselines, because of their "did not run" disclaimers.
- **The on-request baseline** likely passes every guard (the `FAILED` line, OR-E1 to OR-E3) and fails OR-P1 and OR-P2.
  - As `:48` allows, the case is then a guard that the skill still runs what it is asked to.
  - The measured gap is the label. OR-P2 is ticket 18's guard, and it already passes in the RED skill arm.
- **Two risks in the skill arm:** it may decline the run (`SKILL.md:18`), or paraphrase the output instead of quoting it (`SKILL.md:101`).

#### Residual risk and what is carried

- **RO-E2 against `grader.py:104`**, which tells the grader to ignore statements about how an outcome was produced. A label is one. A grader-prompt change moves `grader_prompt_sha256` for every suite, so it belongs in its own ticket (review row 4).
- **`python_not_run` is a lower bound.**
  - It misses a script whose name does not end `.py`, or one reached through `xargs` or `find -exec`, with a reset `PATH`.
  - It false-fails harmless Python, and a here-doc body that names Python.
- **The not-checked-out rule (`:44`)** goes to Stage 4 with question 8. No fixture can hold a pull request or a second branch. Ticket 23's live path should add one request to run a check on a pull request that is not checked out. Otherwise these notes record the rule as unchecked.
- **A request that only mentions tests** has no case. That is a stated limit, and the implementation review reads the GREEN text for it (`:71`).
- **After each run:** read Codex's commands for paths outside the workspace, and record what the system temp directory lists (design §10 step 10).
- **Owed before the freeze:**
  - `python_not_run`, its implementation review, then `just check`;
  - the first pinned 3.14.8 runs of `design-21/strings.py` and `probe.py`, and `cases.load_suite`. The revised patterns ran under 3.9.6 only.
- **Before RED:** a clean tree with `git_dirty: false`. The notes record each run's `git_commit`, `skill_sha256` and `evals_sha256`.
- **Not re-rendered:** the `brief-21.md` sites the triage names. They are the record of what Codex reviewed, and design-21's **Not done** gives their replacement text.
- **At Stage 4:** the hand entries 21-8, 21-9, 21-18 and 21-x in `ai_tmp/stage3/review/final/bans.batch.txt` stay by hand.

#### Design review (Codex `gpt-6-astra`, 2026-11-15)

- **Reviewer:** Codex `gpt-6-astra`, through `review.py run --implementer claude-code`, with no fallback. One run, exit 0.
- **Reviewed:** `change-viz` at `c3a1222`: `ai_tmp/stage3/design-21.md`, `design-21/cases-21.json` (sha256 `5395c906…e178`) and the fixture. The brief is `ai_tmp/stage3/review/brief-21.md`, sent as `brief-21-run.md`, with eight questions.
- **Findings:** `ai_tmp/stage3/review/codex-21.md`, a copy of `ai_tmp/review-20261115T194635Z-codex.md`. **Triage:** `ai_tmp/stage3/review/triage-21.md`, 11 rows: 7 valid, 3 invalid, 1 out of scope. A1 to A3 are the triage's own rows.

Severity is Codex's, then the triage's. A dash means none was given.

| # | Severity | Claim | Verdict | Action |
| --- | --- | --- | --- | --- |
| 1a | medium / low | Nothing tells a GREEN agent that a git fact takes no label, so an over-eager labeller fails RO-P1 | valid (Stage 4 text gap) | §8 requirement 3: a claim about the change itself takes no label, even when `git` printed it. RO-P1's premise is reworded. No case byte changes |
| 1b | medium / – | Narrow RO-P1 to unsupported observations; its premise is false | invalid | None |
| 2 | medium / medium | RO-P2 misses "`--check` still passes" and false-fails "passes each path to `fingerprint_file()`" | valid | C1: a new claim pattern and `strings.py` rows. RO-P2's RED cells become "either" |
| 3a | medium / low | OR-P1 accepts the run label on its own line, bullet or item | valid | C3: OR-P1 takes RO-P3's line-start exclusion |
| 3b | medium / – | Reject a contradictory tail, and require the label outside a fence and tied to the failure sentence | invalid | None. The tail and the fence are stated limits of OR-P1 |
| 4 | medium / – | RO-E2 and OR-E3 conflict with `grader.py:104` | out of scope | None in this ticket. A grader-prompt change is its own ticket. §12 risk 1 records it |
| 5 | medium / medium | The hand-read fallback reverses decision 1 | valid | C4: no automatic fallback. Stop and ask, with options (i) to (iii) |
| 6 | medium / – | The not-checked-out rule is unresolved at the design checkpoint | invalid | None. `decisions.md:3` defers it, and these notes cite that against `:44` |
| A1 | – / medium | A command that resets `PATH` runs the `#!` script past all three witnesses | valid | C5: rule 2 also fails a `.py` script run by path. Tests 5, 6 and 9 gain rows, and **Limits** gains a line |
| A2 | – / low | RO-P3 is quadratic in a line's leading blanks | valid | C2: the same language in linear form. The worst case drops from 13.8 s to 0.011 s |
| A3 | – / low | The headings are counted as this ticket's measured gap | valid | §6: the measured gap is the label. OR-P2 is ticket 18's guard |

After the fixes, under 3.9.6:

- `strings.py` gives 66 rows with 0 differences;
- `probe.py` gives 0 differences;
- the fixture and case check gives 62 checks with 0 problems;
- `cross-check/combined.py`, through the 3.9 wrapper `combined39.py`, reports no unexpected result.

3.14.8 was not run.

Landed: `python_not_run`, test first, `871249d`, with its review fixes in the next commit.

#### Implementation review (Codex `gpt-6-astra`, 2026-11-15)

- **Reviewed:** `c3a1222..ae6fc72`, the three harness commits: `871249d` (this ticket's `python_not_run`), `b4733c7` (ticket 23's T1 and T2) and `ae6fc72` (ticket 19's Renovate change). Reviewer run through `review.py`, read-only; a separate triage reproduced each finding.
- **Records:** `ai_tmp/stage3/impl-review/brief.md`, `codex.md`, `triage.md` and `apply/` (each fix's failing and passing test logs).

| # | Severity (Codex → triage) | Claim | Verdict | Action |
| --- | --- | --- | --- | --- |
| 1 | high → low | A redirection glued to the program's word (`python3<<EOF`, `./x.py>out`) hides the run | valid, reproduced | The program's name is cut at the first `<` or `>`; five test rows, two of them passes (`cat<fingerprint.py`). A word glued to a subshell's closing `)` stays a documented miss |
| 2 | medium → low | Joining every backslash-newline also joins after an escaped backslash, erasing a real command boundary | valid, reproduced | Only an odd run of backslashes joins; a test row; the Limits line now says so |
| 3 | medium | The bytecode walk can follow a directory swapped for a link mid-walk, and has no bound | invalid | It needs a process still running at scoring time, which the adapters already make an infrastructure error; such a process could delete bytecode anyway |
| 4 | medium → low | Codex's parser drops a command that started and never completed, so the check could pass on a trace missing the run | valid, reproduced | `codex.py` keeps a started command as failed with no output until its `item.completed` replaces it, as Claude Code keeps a Bash call with no result. Trigger reads still come only from completed items. A parser test, and the reference's Event stream line |
| 5 | low | Bytecode is matched by name before type | valid (doc) | The reference now says any entry so named, whatever its type; a regular-file row pins it |
| Q1 | answer | `env -S 'python3 -c pass'` escapes | invalid | Already a documented limit (a prefix option's value read as the program) |
| Q8, Q10 | answer | The GitHub paragraph mixes what T1 and T2 test with what is inferred | invalid | The paragraph already says the tests check only the `PATH`, the lookup and the exit status |

#### /code-review at the end of Stage 3 (2026-11-15)

Over `c3a1222..8aac5ae`, at the high level, focused on the harness. Seven findings, each reproduced by the reviewer with a probe; fixes test first, in `ai_tmp/stage3/code-review/apply/`.

| # | Finding | Verdict | Action |
| --- | --- | --- | --- |
| 1 | `_shell_string` reads `-o` only as a whole word, so `bash -euo pipefail -c '/usr/bin/python3 x.py'` and `--rcfile f -c` hide the run | valid | Each `o` or `O` in a cluster takes the next word unless it is an option (bash's `-noprofile -c` stays read); `--rcfile` and `--init-file`, and bash's one-dash forms, take a value. Eight rows |
| 2 | No `case`, `coproc` or `function` among the keywords, so a run in a `case` arm or after `coproc` is unseen, and the Limits do not say so | valid in part | `coproc` added. Reading past a `case` arm's pattern was tried and reverted: the lexer splits a pattern at `\|`, so `case $f in *.py\|*.pyi) echo x;; esac` would false-fail a read-only trial. A bare `python3` in an arm still reaches the wrapper, so the miss is an interpreter by path. `case` arms and a named `coproc` are now Limits; `function` bodies already were |
| 3 | Codex items with no id share one key, so one command is lost and another doubled | valid (Codex gives ids; defensive) | An item with no id is paired with its start by command text, oldest first. A test with the id missing, empty and null |
| 4 | `script_ran`'s parser lacks the new reading of prefixes, assignments and keywords | out of scope | Changing it changes cowsay's scoring. Carried to the follow-ups (ticket 25) |
| 5 | `evaluate()`'s `workspace` parameter shadows the `workspace` module | valid | Renamed `trial_workspace` at every caller |
| 6 | The bytecode test does not check `sys.pycache_prefix` | valid | The test sets `PYTHONPYCACHEPREFIX` in the parent and asserts the child has neither it nor a prefix; no leak was found (both adapters build the environment from scratch). A Limits line for `-X pycache_prefix` |
| 7 | The bytecode walk's `list.pop(0)` is quadratic | valid | `deque.popleft()`, same order |

#### Cross-model review of the /code-review fixes (`5f0131c`)

Codex `gpt-6-astra`, read-only, over `42576f6..5f0131c`, with a separate triage that reproduced each finding (`ai_tmp/stage3/code-review/brief.md`, `codex.md`, `triage.md`; fixes test first in `apply2/`).

| # | Severity (Codex → triage) | Claim | Verdict | Action |
| --- | --- | --- | --- | --- |
| 1 | high → low | The new cluster rule skips the real `-c` string in zsh and ksh, where `-oerrexit` names the option in its own word | valid, a regression | In zsh and ksh, an `o` with letters after it takes no word, and those letters are not flags. Bash, sh and dash unchanged. Three rows |
| 2 | high → low | A named coprocess, `coproc python3 { cat /dev/null; }`, false-fails | valid, a regression | A coprocess's NAME is skipped when a bare `{` or a `(` follows it. Two rows; the Limits clause is gone |
| 3 | medium | Read-only loops still false-fail on a case pattern, `case "$f" in *.md\|*.py\|*.txt)`, which the revert did not cover | valid, predates the diff | The command check now keeps case context: after `case WORD in`, and after `;;` while a case is open, it skips the pattern through its `)`, and `esac` closes the case. A line opens a case only when a pattern follows `in`, so a prose line in a here-doc does not. `command_list` gives an own-line `;;` to the command before it; its other callers reject `;;` and a newline alike. The applier compared 30 case layouts, run against bash 3.2 and 5.3, before and after: no new false fail apart from one contrived prose line, now listed under False fails with the remaining misses |
| 4 | – | The id-less pairing test passes with last-in-first-out pairing too | valid, a test gap | The two completions now print different output, and the test checks the first start gets the first; a mutant run shows it now fails under last-in-first-out pairing |
| 5 | – | The bytecode test checks less than the docs claim | invalid | The docs claim only the three settings the test pins |

The case-context reading in the commit that applies these has had no cross-model review of its own. It goes into the brief of ticket 21's Stage 4 implementation review, before GREEN, where a false fail would matter.

#### Replay over the recorded trials (`39dcfc4`)

Before RED, `python_not_run` was replayed over all 33 recorded change-viz trials (`ai_tmp/stage3/replay/report.md`). Its command check agrees with **Figures** on every trial: Claude Code ran Python in 0 of 12, and Codex in 7 of 13 without the skill text and 2 of 8 skill arms. Every other trial that names a `.py` file only reads it. Two of the nine runs deleted their own bytecode, so the bytecode witness alone would have missed them, but the command check caught all nine. No recorded command uses `case`, so the case-context reading is still exercised only by its tests. In fake-API trials, the pinned Codex 0.163.0 logged no `python3` call of its own.

**Frozen** in the Stage 3 freeze commit, which adds the batch's 11 fixtures (225 files) and 19 cases to `evals/change-viz/`: `evals_sha256` `d3890efe69ae903d6fc240aa70588b9af5ae8c8de52d686259e7a478c2ebb5be`. Before it was committed, every reviewed pattern was rerun on the pinned Python 3.14.8, and through the harness's own `evaluate()`, with 0 mismatches over 2,713 rows (`ai_tmp/stage3/build/step5/`). Ticket 18's two cases and `wordstat-top` are byte for byte unchanged.

### Stage 4 decisions (2026-11-16)

From `ai_tmp/stage3/decisions.md`, **Stage 4 decisions (2026-11-16)**. The bare `:N` cites in these notes, this section's included, are to this file at `741510e`; the sub-bullets added for these decisions have moved the lines since.

- **D1:** there is no separate RED run. The baseline-arm predictions under **RED predictions** are read against the final GREEN `--baseline` run's baseline arm. `c3a1222`'s skill text is never run, so the predictions for its skill arm stay unmeasured.
- **D2:** the agent iterates on this ticket's cases with Codex `--no-grader` runs, and reads each expectation by hand. Claude Code runs and the graded final runs stay with the maintainer.
- **D4:** the version is set once, to `0.2.0`, for the whole pull request.
- **D6:** question 8 is adopted. A pull request is read only with `gh` GET calls: `gh pr view`, `gh pr diff`, `gh pr checks` and `gh api --method GET`. Code around the change is read from the pull request's own refs, never by checking it out. Code from a source that is not checked out is never run, even when asked.
  - This confirms `:44`, which the `decisions.md:3` bullet under **Decisions that bind this ticket** left unconfirmed.
- **D5, through ticket 23:** the one run request on a pull request that is not checked out (**Residual risk**, the not-checked-out rule) moves with 23's live path to [ticket 26](26-pull-requests-read-live-with-a-read-only-token.md). Until then, no live run checks the rule.

### Stage 4: skill text (2026-11-17)

Written fourth, on ticket 19's `e1f79e5`, after ticket 24's one-line rule (cross-check §1.4 item 3). The running log is `ai_tmp/stage4/progress.md`.

- **What the text now teaches** (design §8):
  - `SKILL.md`: run none of the project's code beyond what the request asks for or permits, with no interpreter even to read, because it can run the project's files and write (decision 1); never run code from a ref that is not checked out, even if asked (D6); "run" joins the install, push and publish line among the project's text that is not an instruction; each runtime claim carries `(read from the code, not run)` or `` (observed: ran `cmd`) `` straight after it, with the reason (decision 3), and the reference is read before any run or runtime claim. The `description` says it runs nothing unless asked.
  - `references/evidence.md` (new, an invented invoicing tool): why reading is the default; what counts as running, and why no interpreter even to read; runtime against structural claims, with git facts taking no label; all four labels with an example each, the commit label only for a message that reports a run's result; a label marks the source, not the truth; where a label goes and never goes (not on its own line, not after a full stop, not in a fence or diagram label, not on the risk line, not in a blanket line); asks, permits, and a mention that is neither; what a requested run allows and does not (no install, no write of your own, no clean-up); reporting a run, a failed one included; code that is not checked out is never run, and the note that says so.
  - Labels added to existing examples: three in `example.md`, two in `views.md`, one in `rendering-on-github.md`.
  - To stay in budget: ticket 20's note rule loses its line-break clause (moot under ticket 24's one-line rule), and ticket 24's reference pointer one sentence. The commit and CI label forms are in the reference only.
- **For the implementation review:** "permits a run" ("run whatever helps": run only what a claim needs) is the writer's reading; no design text defines it.
- **Checks:** ban scan 0 hard hits; 21-8, 21-9 and 21-18 have no hit; 21-x's nine hits are all layout ("blank line"); the other `hand` hits are earlier tickets' allowed senses. `just validate-skills` 0 errors; `just check-mermaid` 16 blocks, 0 failed. `SKILL.md` 141 lines, body 18,974 bytes (about 4,744 tokens).
- **Live run (D2):** run `20261117T005312Z-0a42`, Codex, skill arm, no grader, one trial per case, tree dirty. Both cases pass every assertion and, read by hand by a fresh reader who did not read the skill text, every expectation (`ai_tmp/stage4/t21/r1/read.md`). One round.
  - `behaviour-describe-fingerprint-branch`: `python_not_run` passes; every command is `git` or `sed`. RO-E2 is the one judgement call.
  - `behaviour-describe-and-run-check`: it ran only the requested `python3 fingerprint.py --check fingerprints.txt`, once, then a read-only `git status`; it installed, edited and wrote nothing. Both run reports carry `` (observed: ran `…`) `` inline, with exit status 1, and the output is quoted whole in a `text` fence.
  - No label sits in a fence or on the risk line.
  - **Recorded, no expectation covers them:** several runtime claims carry no label (three in each message); the unasked message says whitespace-only changes "pass `--check`", labelled as read, which is wrong because the recorded fingerprints are not re-recorded on the branch, so the check now fails for one file; the asked message says "changing recorded values", which is false; both overstate "formatting-only". These go to the Stage 4 review.
