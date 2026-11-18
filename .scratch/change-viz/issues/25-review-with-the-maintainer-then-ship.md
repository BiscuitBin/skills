# 25: Review with the maintainer, then ship

**What to build:** the finished `change-viz` skill is run on real changes, the maintainer reads what it wrote and says what is wrong, and the skill is corrected, benchmarked, reviewed as a whole and released. This is the human review step that the repo's `just eval` loop does not have on its own, and the last gate before the skill is called done.

Why: every earlier ticket checks one behaviour against small fixtures. Whether the whole description gives the maintainer "confidence and understanding" on a real change is a judgement only they can make.

**Blocked by:** 19 (Merge risk), 20 (Choosing visuals), 21 (Evidence), 22 (Local changes), 23 (Pull requests as a source), 24 (Output renders on GitHub).

**Status:** done, except Claude Code's outputs on the four real changes, the maintainer's read, the feedback round and the graded benchmark, which the maintainer carried to [ticket 30](30-maintainer-read-and-first-graded-benchmark.md) when releasing `0.2.0` as is (D9, 2026-11-17)

**Agent requirements:** Any implementing agent (Claude Code or Codex). The maintainer reads the outputs and gives feedback, runs the live evals in their own terminal, with the token, and has the `gh` login the pull request runs need. Cross-model review of the whole skill is also required.

## What is known

As of 2026-11-10.

- **The four pull requests the maintainer likes**, all public, each written in a session with the `show-me` and `visual-pr` personal skills:
  - BiscuitBin/knarr#75, "README for chart users, with a How it works diagram" (15 files)
  - BiscuitBin/skills#1, "Add foundation tickets for the skills repo" (14 files)
  - BiscuitBin/skills#4, "Add cowsay skill and skill validation gate" (31 files)
  - BiscuitBin/rove#11, "PROTOTYPE, do not merge: crawl4AI in a Smol Machines microVM" (13 files)
- **Those descriptions had more to work with.** The agent that wrote each one had just done the work, and quotes command output and timings from its own session. A read-only run of `change-viz` on the same diff cannot reproduce that, so the comparison is of shape, choice of visuals and risk call, not of evidence.
- **This repository's own changes cannot be eval material**, because the grader flags the word `skill` as disclosing the arm. Reading the skill's output on skills#1 and skills#4 by hand involves no grader, so it is fine here.
- **The skill is by-name-only**, so skill-creator's description optimisation does not apply.
- **Benchmarks:** `just eval-record` writes one iteration from one run per agent, and both runs must share the same `skill_sha256` and `evals_sha256` (ADR 0014).
- **Codex E7 is an open gap** (ticket 18, **GREEN rerun on `c397d04`** and **The maintainer's decisions (2026-11-14)**). E7 passed in 1 of 3 graded Codex trials, and 0 of 3 by hand: the notes name the new counting rule, but not that the printed counts can be lower. Under `CONTRIBUTING.md` §3, `just eval-record` waits until E7 passes on Codex, or until the maintainer decides how to record it.
  - Changed by D5 (2026-11-16): the maintainer has decided how to record it, with Codex's E7 shown as it is, and the gap is [ticket 29](29-codex-says-which-way-a-count-moves.md).
- **`script_ran`'s command parser lags `python_not_run`'s** (ticket 21, **/code-review at the end of Stage 3**, finding 4). It still misreads `/usr/bin/env python3 scripts/x.py`, `PATH=/usr/bin:/bin python3 scripts/x.py` and `if python3 scripts/x.py; then …`, so it can falsely fail a correct run of a shipped script. Sharing `_program` and the whole-word lexer would fix it, but changes cowsay's scoring, so it belongs in `.scratch/change-viz/follow-ups.md`.

## Acceptance criteria

- [ ] The skill is run on the changes behind each of the four pull requests, and on each fixture the suite uses:
  - knarr and rove are cloned under `ai_tmp/`, and the two skills pull requests are read from a clone there too, so nothing here changes this checkout.
  - Each is run as a branch against its base and, where `gh` works, as a pull request.
    - Changed by D5 (2026-11-16): the pull request runs move to [ticket 26](26-pull-requests-read-live-with-a-read-only-token.md), so here each change is run only as a branch against its base, with `gh` stubbed.
  - The runs use the project's pinned agent CLIs through `just run`, with the skill installed into the clone as a user would install it. Nothing is written to the maintainer's own agent homes.
  - Each output is saved under `ai_tmp/`, beside the pull request's original description.
  - Changed by D9 (2026-11-17): the Codex outputs and the fixture passes are done (**Outputs before the maintainer's session**); Claude Code's four outputs move to [ticket 30](30-maintainer-read-and-first-graded-benchmark.md).
- [ ] The maintainer reads each output beside the original and gives feedback. Their words are recorded here, by output.
  - Changed by D9 (2026-11-17): moves to [ticket 30](30-maintainer-read-and-first-graded-benchmark.md).
- [ ] Each piece of feedback is applied by finding the general reason behind it and changing what the skill explains. No rule is added that only makes sense for one of the four. The notes say, for each, what changed and why it generalises, or why it was not applied.
  - Changed by D9 (2026-11-17): moves to [ticket 30](30-maintainer-read-and-first-graded-benchmark.md), with the strict misses and false claims of **Outputs before the maintainer's session**.
- [ ] After the changes, the outputs are regenerated and the maintainer confirms the result, or a second round is recorded.
  - Changed by D9 (2026-11-17): moves to [ticket 30](30-maintainer-read-and-first-graded-benchmark.md).
- [ ] The full suite passes on Claude Code and Codex with `--baseline`, and the two runs are recorded as a benchmark iteration with `just eval-record`. The file it writes is committed, and `just eval-report change-viz` builds.
  - Changed by D5 (2026-11-16): E7 on Codex need not pass, since the benchmark records it as it is and the gap is [ticket 29](29-codex-says-which-way-a-count-moves.md).
  - Changed by D9 (2026-11-17): `0.2.0` shipped with no graded run and no benchmark; both move to [ticket 30](30-maintainer-read-and-first-graded-benchmark.md).
- [x] A cross-model review covers the whole skill as a user would install it: `SKILL.md`, every reference, any script, the eval suite and the fixtures. It is not limited to this ticket's diff.
- [x] The version is set for release, by semver, and agreed with the maintainer: whether this is `1.0.0` or stays below it.
  - Changed by D4 (2026-11-16): the maintainer chose `0.2.0`, one bump for the whole pull request (`CONTRIBUTING.md:89-95`).
- [x] Docs are current: `README.md`, `docs/reference/distribution.md`, and anything the earlier tickets changed in `docs/reference/evals.md`, `GLOSSARY.md` and the ADRs. Each term the tickets added is used the same way everywhere.
- [x] Follow-ups are written to `.scratch/change-viz/follow-ups.md`, including:
  - richer output formats (HTML, artifacts), as this skill's option or as a separate skill that composes with it
  - the skill that creates or updates a pull request description, built on this one
  - every residual the earlier tickets recorded, such as a "does not" outcome with no automated check
- [x] `just format` has run, the changes are committed, and `just check` passes.

## Out of scope

Building either follow-up, new behaviours the maintainer's feedback asks for that are larger than a correction (each becomes a ticket), and merging the pull request, which the maintainer does.

## Review checkpoints

Use the `cross-model-review` dev skill.

- **Maintainer checkpoint:** the review of the outputs, above. Do not record the benchmark iteration or start the whole-skill review until the maintainer has confirmed the regenerated outputs.
  - Changed by D8 (2026-11-16): the whole-skill review runs before the maintainer's session, on the full Stage 4 text, and only the feedback's changes are reviewed in the session; the benchmark still waits for the maintainer's confirmation.
  - Changed by D9 (2026-11-17): `0.2.0` shipped before this checkpoint, which moves to [ticket 30](30-maintainer-read-and-first-graded-benchmark.md) with the benchmark.
- **Implementation checkpoint:** before marking done, review the whole skill against the acceptance criteria of tickets 18 to 24 as well as this one. Pay particular attention to instructions added for one of the four pull requests, to rules that contradict each other across references, and to anything the skill tells an agent to do without saying why.

## Completion notes

### Stage 4 decisions (2026-11-16)

From `ai_tmp/stage3/decisions.md`, **Stage 4 decisions (2026-11-16)**. The plan is `ai_tmp/stage4/plan.md`.

- **D2:** the agent makes the Codex outputs on the four changes itself, on the project's Codex login, and runs Codex live evals with `--no-grader`. The maintainer runs Claude Code and the graded final runs, in one closing session.
- **D4:** ship at `0.2.0`, one bump for the whole pull request (`CONTRIBUTING.md:89-95`).
- **D5:** these become follow-up tickets, not release blockers:
  - [26](26-pull-requests-read-live-with-a-read-only-token.md): ticket 23's live `gh` path on the four pull requests, with a read-only token;
  - [27](27-gh-without-a-login-on-a-linux-host.md): ticket 23's Linux "`gh` present, not logged in" case, through the `live-evals` dispatch;
  - [28](28-render-proof-in-a-github-post.md): ticket 24's render proof, as a GitHub post;
  - [29](29-codex-says-which-way-a-count-moves.md): the Codex E7 gap. The benchmark is recorded with Codex's E7 shown as it is.
- **D7:** the agent may push `change-viz`, edit PR #19's title and description, and take it out of draft at the end. The merge stays with the maintainer (**Out of scope**).
- **D8:** the whole-skill cross-model review runs before the session, on the full Stage 4 text. Only the feedback's changes are reviewed in the session. This relaxes the maintainer checkpoint's ordering for the review, not for the benchmark.

### Stage 4 implementation review, for tickets 19 to 24 (2026-11-17)

The plan's one cross-model review of the six tickets' text, after all six had landed and before the version bump (plan Phase 2, "Once the six are in", item 2). The whole-skill review of D8 follows separately.

- **Implementer:** Claude Code running `claude-opus-5-5`.
- **Reviewer:** Codex `gpt-6-astra`, through `review.py run --implementer claude-code`, no fallback, exit 0.
- **Reviewed:** `741510e..01b3817` (the Mermaid checker, the six tickets' text and the consolidation), with `package-lock.json` and the tickets left out of the pasted diff, every file under `skills/change-viz/` pasted whole, and seven named questions. The brief is `ai_tmp/brief-stage4.md`.
- **Findings:** `ai_tmp/review-20261117T041521Z-codex.md` · **Triage:** `ai_tmp/stage4/triage-s4.md`, by a separate agent, which reproduced findings 1, 2 and 5.

| # | Severity | Finding | Verdict | Action |
| --- | --- | --- | --- | --- |
| 1 | medium | `python_not_run`'s case-pattern reading takes an escaped or quoted `)` as the pattern's end, so it can miss a run (`case x in a\)\|x) /usr/bin/python3 …`) or falsely fail a read (`a\)\|*.py\|x) echo ok`) | valid | Fixed test first: a quote-state pass marks every quoted or escaped `)` before the lexer splits, following its rules and its `#` comments, and fails closed when quoting does not resolve. Five new cases failed before the fix; a differential check against `shlex` found 0 differences over 121 pinned and 200,000 fuzzed commands. `docs/reference/evals.md` says so. |
| 2 | high | `local-changes.md:88`: "a file a diff lists and `status` does not is unchanged" is false for the diff against `<fork>`, so committed work would be dropped | valid | `local-changes.md`: the changed files come from `--stat`; `status` settles a file whose only change is its timestamp only against `HEAD` or the staged version, never against `<fork>`, since it never sees the commits. |
| 3 | medium | No rule makes a visual's marks, order, paths and context lines agree with the code; the Stage 4 reads recorded invented signatures, unchanged lines marked `+` and reversed order | valid | `views.md` gains **Draw only what the code does**, with its reason: each mark is a claim about the two versions compared; context lines are never code the project lacks; steps in the order they run, under their conditions; no arrow the code lacks; leaving out never reorders. `SKILL.md`'s outline "Done when" checks it at the point of answering. |
| 4 | medium | Examples the agent is told to follow carry unlabelled runtime claims | valid | Labels added inline to every runtime claim in `example.md`, `views.md`, `merge-risk.md`, `rendering-on-github.md` and `local-changes.md`, and to `SKILL.md`'s good-note example. |
| 5 | medium (triage: low) | The Mermaid checker reads an HTML comment's fence-looking lines as fences, so it can hide a real block or check one GitHub never renders | valid | Fixed test first: a comment that starts a line outside a fence runs through the first line holding `-->`, and is skipped. Four new tests, three failing before the fix. The other HTML block kinds are named as a limit in the script and in ADR 0018. |
| 6 | low | The pull request fallback's transcript expectations accept `command -v gh` without a `gh` read | out of scope | The fix would change frozen expectations, and the rubric is not wrong: design 23 records a lookup that finds no path as proof that `gh` was tried (`design-23.md:427-428`, `:467`). |

- **The named questions:** PS2 left frozen is "defensible under the recorded, bounded probe decision", provided a PS2 pass is never shown as proof a label renders faithfully (question 1); no allowed `gh` form writes GitHub content or repository state (question 4); no rule was lost in the consolidation (question 5); no install or cache escapes the project (question 7). Question 2 became finding 3, question 3 finding 1.
- **Not re-reviewed on its own:** the fixes go to the whole-skill review (D8), which reads the skill as it then stands.

### Whole-skill cross-model review (D8, 2026-11-17)

Ticket 25's implementation checkpoint, run before the maintainer's session as D8 allows, on the skill as a user installs it at `0.2.0`.

- **Implementer:** Claude Code running `claude-opus-5-5`.
- **Reviewer:** Codex `gpt-6-astra`, through `review.py run --implementer claude-code`, no fallback, exit 0 on the first run.
- **Reviewed:** `skills/change-viz/` at `f0b57ce` whole (every file pasted), the marketplace entry, the whole `evals.json` and a list of the 12 fixtures for reading from disk, and the code half of the Stage 4 review's fixes (`git diff 01b3817 f0b57ce -- src scripts tests …`), against tickets 18 to 25 with D1 to D8 and eight named questions. The brief is `ai_tmp/brief-whole-skill.md`.
- **Findings:** `ai_tmp/review-20261117T061857Z-codex.md` · **Triage:** `ai_tmp/stage4/triage-whole.md`, by a separate agent, which reproduced finding 1 in a throwaway repository.

| # | Severity | Finding | Verdict | Action |
| --- | --- | --- | --- | --- |
| 1 | medium | The risk call's search for what merging sets off misses automation the base gained after the fork, which no read of the branch sees and the merge runs | valid | `merge-risk.md`: the merged tree keeps the base's version of every file the branch leaves alone, so list what the base changed since the fork (`diff --name-status HEAD...<base>`) and read the files that decide what merging sets off at `<base>`; stated as the one exception to reading in the scope's state. |
| 2 | medium | The `@`, `#` and closing-word rules apply to every description but sit only in the rendering reference, read before a diagram or table | valid | `SKILL.md` gains one paragraph with the three rules and their reasons; the full form stays in `rendering-on-github.md`. |
| 3 | medium (triage: low) | `pull-requests.md` forbids any run on a pull request, even one that is checked out, contradicting `evidence.md` | valid | Only code read from a pull request that is not checked out is never run (D6); a checked-out pull request is the checkout, so a requested run follows the evidence rules. The maintainer confirmed this reading on 2026-11-17 (**The maintainer's confirmations**). |
| 4 | low | The pull request scope line's hard 250 characters cannot hold its mandatory fields with a long base name | valid | "About 250", as for a branch: only the checks shorten, every field stays, and the line may run longer. |
| 5 | low | PF1 and PS1 fail a tilde-fenced diagram the skill allows | out of scope | A known limit of the frozen rubric, recorded in ticket 24's residuals and `follow-ups.md`. |

- **The named questions:** no teaching to the test (1); no trivial pass, since every behaviour case's baseline fails an output assertion (5); no further write, unasked run or credential read (6); the `0.2.0` manifests, invocation settings and notices are consistent (7); no defect in the Stage 4 code fixes, by static reading (8).
- **Claude Code outside the project:** a fake-API check of `run-claude.sh` (`ai_tmp/stage4/probe-rove/result.md`) found that every Claude Code run, with or without rove's plugin setting, writes a socket to `/tmp/cc-socks/<pid>.sock`. AGENTS.md asks for any such write to be recorded; it is the pinned CLI's own, and no setting the harness uses moves it.

### Outputs before the maintainer's session (2026-11-17)

Everything the first acceptance criterion asks that needs no Claude token, made on the skill at `5d4eff9`, the commit the whole-skill review's fixes landed in.

- **The four real changes, on Codex (D2):** each clone under `ai_tmp/real/<change>/repo/` was run as a branch against its base, with `gh` stubbed and `HOME` and `TMPDIR` under `ai_tmp/real/<change>/`, by `ai_tmp/real/run-codex.sh`, on the pinned `codex-cli 0.163.0` with `gpt-5.6-terra`, the eval harness's Codex model. Every run exited 0, invoked the skill, and left its clone as it found it (`codex-before.txt` and `codex-after.txt` identical).

  | Change | Branch, base | Duration | Output |
  | --- | --- | --- | --- |
  | knarr-75 | `readme-diagram`, 3 commits, 15 files | 110 s | 2,181 bytes |
  | skills-1 | `mk-bootstrap-tickets`, 2 commits, 14 files | 91 s | 2,367 bytes |
  | skills-4 | `ticket/03-cowsay-skill-and-validator`, 4 commits, 31 files | 92 s | 2,514 bytes |
  | rove-11 | `crawl4AI-smolmachine-prototype`, 7 commits, 13 files | 101 s | 2,777 bytes |

- **The reading pack:** `ai_tmp/real/READ-ME.md`, built by `ai_tmp/real/make_readme.py`, puts each original description beside the Codex output, with the Mermaid checker's verdict and rendered labels, and leaves a place for Claude Code's. `ai_tmp/real/run-claude.sh` makes the Claude Code four, with the pinned CLI and `claude-sonnet-5-5`, in the session.
- **The fixtures, on Codex:** the final skill-arm pass `eval-results/20261117T064129Z-f47c` (21 trials, `--no-grader`, skill at `5d4eff9`, tree clean, `evals_sha256` `d3890efe…`) passed every pattern assertion and `python_not_run`. Its transcripts were checked case by case (`ai_tmp/stage4/final-skill/transcript_checks.md`): no write, `--no-optional-locks` on every skill-arm `git`, the `-c` prefix on every `git diff`, `gh` only in the two pull request cases and an interpreter only in `behaviour-describe-and-run-check`. The one flag, seven `git show <base>:path` reads without the diff flags in `behaviour-describe-retire-wishlist`, is the checker over-matching: probed with a textconv driver set, `show` of a blob prints it raw unless `--textconv` is given. The baseline arm, which runs no skill text, was last run in the full pass `20261117T032603Z-bae2` at `01b3817`: every behaviour case's baseline failed an output assertion beyond the trigger. That pass's tracer outputs were read by hand against E1 to E8 (`ai_tmp/stage4/full/`).
- **The hand read of the final text, standing in for the grader (D2):** two readers who did not read `skills/change-viz/` judged every expectation of `f47c` strictly against its fixture (`ai_tmp/stage4/final-skill/read-a.md`, `read-b.md`). 17 of the 21 cases passed every expectation. Each case with a strict miss was rerun once on the same text, in `20261117T073227Z-3d49` and `20261117T073735Z-7a96`. Every pattern passed in both, and the same readers judged the reruns. Three cases miss in both draws:

  | Case | Expectation | `f47c` | Rerun | Reading |
  | --- | --- | --- | --- | --- |
  | `behaviour-describe-branch` | E7, existing counts can be lower | fail: "can report different word and distinct counts" | fail: "can change" | The Codex gap of [ticket 29](29-codex-says-which-way-a-count-moves.md), recorded as it is (D5). |
  | `behaviour-describe-branch` | E5, each word with its count | fail, strictly: "frequency list" | pass, through the diff sketch only | Borderline in both draws; a lenient grader likely passes them. |
  | `behaviour-describe-add-weekdays-2` | C1 and C4, PyPI named | fail: "publishes version 1.4.0" | fail: "published by `.github/workflows/release.yml` on merge to `main`" | Names the workflow and the publishing, never where the package goes. Ticket 19's round 3 passed C1 on earlier text. |
  | `behaviour-branch-and-uncommitted` | E1, what `--longest` prints | fail: "print the longest hike" | fail: "name its longest entry" | Ticket 22's guard miss, open since its round 3. |
  | `behaviour-describe-with-sequence` | S-E1, the skip in the diagram | fail: the skip only in prose | pass: `skip blank and comment lines` | Variance. |

- **False claims no expectation covers,** found by checking every output against its fixture:
  - `split-modules` says code importing `replay` or `report` from `desk` breaks. `desk.py` still imports both, as the output's own sketch shows.
  - `add-holds`' second diff sketch drops the `else` branch, so every return seems to go to held.
  - `behaviour-describe-uncommitted`'s flowchart puts the `--miles` choice after printing, but the code chooses the unit inside each print (`hikes.py:38`, `:41`).
  - `retire-wishlist` says every `readlog` invocation applies migration 003, but `wish X` exits 2 before opening the log. It also says a revert restores the commands, but on a migrated log `wishes` then fails with `no such table: wishlist`.
  - `with-sequence` says in `f47c` that malformed records get a numbered error, but `rice|two` still raises an uncaught `ValueError`. The rerun drops the claim.
  - `behaviour-branch-and-uncommitted`'s sketch shows `hikes = read_hikes(args.file)` as an unchanged line, but on `main` it was `read_hikes(argv[1])` (`start/hikes.py:21`).
  - The `diff` blocks of `behaviour-describe-staged` and `behaviour-describe-changes-try-ideas` turn a hunk header's `def main(argv):` into a context line, then drop the lines between it and the hunk with no mark.
  - The sketches of `behaviour-describe-add-weekdays`, `behaviour-describe-add-weekdays-2` and `behaviour-describe-add-holds` keep the old line as unchanged context beside its `+` replacement.
  - These are the kinds of fault that **Draw only what the code does** and the evidence rules address. No text round was opened for them: a text change now would make both reviews, this pass and the four real outputs stale. They join the session's feedback round (**The maintainer's confirmations**, 5).
- **Left for the session:** Claude Code's four outputs, the maintainer's read, the feedback round with the misses above, the graded final runs on both agents and the benchmark. The runbook is `ai_tmp/release/SESSION.md`.
  - Since D9 (2026-11-17), all of it is [ticket 30](30-maintainer-read-and-first-graded-benchmark.md)'s, which keeps the runbook.

### The maintainer's confirmations (2026-11-17)

Before the closing session, the maintainer answered the runbook's five questions, choosing the recommended option each time:

1. **PS2 stays frozen** (ticket 24, **Stage 4: skill text**): its entity exemption passes `#42;` and `#word;`, but no recorded output writes either, and `evals_sha256` stays `d3890efe…`.
2. **The lead ran the Codex evals under D2**, including the reruns `3d49` and `7a96`: fine.
3. **rove runs with its plugin setting as it is,** and the `/tmp/cc-socks/<pid>.sock` write recorded above is accepted.
4. **The D6 reading stands:** a run the request asks for, on a pull request that is checked out, follows the evidence rules, and a fork's pull request the person checked out counts as checked out (whole-skill review, finding 3).
5. **The strict misses and false claims join step 4's feedback round:** `add-weekdays-2`'s C1 and C4, `branch-and-uncommitted`'s E1 and the false claims above. Each is fixed by its general reason, with the maintainer's own points, under one short Codex review. Each affected eval case is then rerun on Codex with `--no-grader` and read strictly before the graded final runs. The tracer's E7 stays with ticket 29 (D5).
   - Since D9 (2026-11-17), this round is [ticket 30](30-maintainer-read-and-first-graded-benchmark.md)'s.

### Released as is (D9, 2026-11-17)

The maintainer decided to release `0.2.0` before the closing session. Their words: "Lets save all that stuff in @ai_tmp/release/SESSION.md for later. Create a follow up ticket. Lets go ahead and release the skilll as is."

- **What ships:** the skill text as of `5d4eff9` (`skill_sha256` `6d4d615a…`, `evals_sha256` `d3890efe…`). Every later commit changes only tickets.
- **What backs it:**
  - On Codex, every pattern assertion passed in all 21 cases (`f47c`).
  - A strict hand read passed 17 of the 21 cases.
  - Two cross-model reviews (the Stage 4 implementation review and the whole-skill review) were triaged and applied.
  - Every Mermaid diagram in the skill's files passes the offline check that `just check` runs (ticket 24, ADR 0018).
- **What it ships without:**
  - Claude Code has not run the `0.2.0` text, only ticket 18's tracer text.
  - No run of the `0.2.0` text was graded, and no benchmark is recorded.
  - The maintainer has not read the outputs on the four real changes.
- **Known faults that ship:** the three both-draw misses and the false claims listed under **Outputs before the maintainer's session**, and the Codex E7 gap of ticket 29.
- **Carried to [ticket 30](30-maintainer-read-and-first-graded-benchmark.md):** Claude Code's outputs, the maintainer's read, the feedback round with those misses and false claims, the regenerated outputs, the graded runs on both agents, and the benchmark. Ticket 30 keeps the runbook and the local aids it needs. Those aids are git-ignored and exist only in the `change-viz` worktree.
- **Unchanged:**
  - D7: the maintainer merges PR #19.
  - The confirmations above, which carry to ticket 30.
- **PR #19's CodeQL check fails** on code-scanning alert #1 (`py/clear-text-logging-sensitive-data`, `src/skills_tooling/evals/runner.py:639`).
  - The alert was opened on `main` on 2026-11-09, before this work.
  - The flagged line prints `results.scrub(…, secrets)`, which redacts every secret first.
  - `main` has no branch rules, so the alert does not block the merge.
  - Dismissing it is the maintainer's call.
