# change-viz follow-ups

What `change-viz` leaves for later. None of these blocks the release.

- **`script_ran`'s command parser lags `python_not_run`'s.** It still misreads `/usr/bin/env python3 scripts/x.py`, `PATH=/usr/bin:/bin python3 scripts/x.py` and `if python3 scripts/x.py; then …`, so it can falsely fail a correct run of a shipped script. Sharing `python_not_run`'s parser would fix it but changes cowsay's scoring (ticket 25, **What is known**; ticket 21, **/code-review at the end of Stage 3**, finding 4).
- **Richer output formats,** such as HTML or artifacts, as an option of this skill or as a separate skill that composes with it (ticket 25, the follow-ups criterion).
- **A skill that creates or updates a pull request description,** built on this one (ticket 25, the follow-ups criterion; ticket 23, **Out of scope**).
- **The maintainer's follow-up tickets** (D5, `ai_tmp/stage3/decisions.md`, **Stage 4 decisions (2026-11-16)**):
  - [26](issues/26-pull-requests-read-live-with-a-read-only-token.md): the four pull requests read live, with a read-only token;
  - [27](issues/27-gh-without-a-login-on-a-linux-host.md): `gh` without a login, on a Linux host;
  - [28](issues/28-render-proof-in-a-github-post.md): the render proof in a GitHub post;
  - [29](issues/29-codex-says-which-way-a-count-moves.md): Codex says which way a changed count moves (E7).
- **[30](issues/30-maintainer-read-and-first-graded-benchmark.md): the maintainer's read and the first graded benchmark,** carried from ticket 25 when `0.2.0` was released as is (D9, 2026-11-17): Claude Code's outputs on the four real changes, the maintainer's read, a feedback round with the strict misses and false claims found on Codex, and the graded runs on both agents.

## Residuals from tickets 18 to 24

What each ticket's completion notes record as still open at `01b3817`, under **Residual risk** unless another section is named. Ticket 18's three harness items, the arm in the trial path, the grader's quote and expectations that fail in both arms, are in `.scratch/foundation/follow-ups.md`.

### Measuring the skill

- **One trial per case and arm.** The final runs use `--baseline --trials 1`, so no figure has a spread; three-trial reruns are left for later (ticket 20, **Stage 4 decisions**).
- **A reader stood in for the grader.** Every Stage 4 round ran Codex with `--no-grader`, and one fresh reader judged each expectation by hand (tickets 19 to 24, **Stage 4: skill text**). `0.2.0` shipped with no graded run; the first is ticket 30's.
- **Grader leniency.** Some expectations pass on loose wording: ticket 19's A4 ("because"), C3 ("both") and C5 ("daygap users"), and ticket 20's E3, whose "what to notice" in a lead-in is a hand read (tickets 19 and 20).
- **The 350-character note cap against E7.** The cap fails two of Claude Code's three recorded E7 passes, at 357 and 412 characters; a Claude Code E7 fail whose note the cap cut counts against the cap, never against E7 (ticket 20).
- **LEN1500** is the likeliest final-run fail on Claude Code, because agents count characters poorly (ticket 20).
- **Encoding.** The risk line's emoji and `·` are the first non-ASCII the output assertions read, so under a non-UTF-8 locale R1 and R2 would fail for a harness reason. The fix is reading with `encoding="utf-8"` in `cases.py` and the transcript reads (ticket 19).
- **Door calls close to lookups.** No case tests a one-way kind that `merge-risk.md`'s table leaves out, so a generalisation case is owed (ticket 19, review row 11).
- **B5 not adopted.** The triage's optional B5 for the retire-wishlist blast radius ("the saved wishes, or the people whose logs hold them") was not adopted, and nothing settles it (ticket 19).
- **`daygap` on PyPI.** The fixture's package name was unclaimed on 2026-11-15; a later registration would contradict the fixture (ticket 19).
- **Patterns fitted to their fixtures.** DIFF and NOFL hold for these fixtures only (ticket 20); N-D still fails "…including the year", and four cases share `hikelog-wip` (ticket 22).
- **PS2's entity exemption.** PS2 passes any `#[A-Za-z0-9]+;`, and Mermaid decodes every such run, so it passes `#42;` and `#word;`, which render as other text. Only a `;` straight after an issue number or a name hits it, which no recorded output has, so PS2 stays frozen (ticket 24, **Stage 4: skill text**).
- **PF1 and PS1 false fails.** A tilde fence, `Mermaid` capitalised or a fence indented in a list item fails them without breaking the render, so each fail is checked by hand (ticket 24).
- **RO-E2 against the grader prompt.** `grader.py` tells the grader to ignore statements about how an outcome was produced, and an evidence label is one. A grader-prompt change moves `grader_prompt_sha256` for every suite, so it needs its own ticket (ticket 21, review row 4).
- **No case for a request that only mentions tests** (ticket 21).
- **`python_not_run` is a lower bound,** with false fails on harmless Python; its limits are in `docs/reference/evals.md` (ticket 21).

### Outcomes no assertion checks

- **Changes nothing, never writes.** No assertion shows that no command wrote to the index, the working tree, a ref or GitHub, so each live run's commands are listed and read by hand (tickets 22 and 23).
- **Never runs code from a pull request that is not checked out.** No fixture can hold a pull request, so no run checks it until ticket 26's live path asks for one (ticket 21, **Stage 4 decisions**).
- **An unclosed `mermaid` fence** followed by prose passes every pattern, so it is a hand read (ticket 24).
- **No false or unlabelled runtime claim.** No expectation covers either: ticket 21's runs left several runtime claims unlabelled, and the Stage 4 reads record false claims about the fixtures that failed no item (tickets 19 to 22, **Stage 4: skill text**). The final text's list is in ticket 25, and ticket 30's feedback round takes it.
- **No load in a quiet case.** A pass means the trace recorded no load, which is a lower bound, so the quiet case's transcripts are read by hand at each live run (ticket 17; `docs/reference/evals.md`, **Quiet cases**).
- **The hand entries** in `.scratch/change-viz/bans.txt`, and ticket 24's "invent every example" read, stay by hand at every skill commit (tickets 19, 20, 21 and 24).

### Reading the change

- **Base detection in forks and remotes.** A local `main` with unpushed commits counts fewer and wins, so those commits stay out; a branch that counts above 0 against `origin/main`, and more against the branch `origin/HEAD` names, is described against `origin/main`; a remote named `upstream` is taken as the fork's parent even when it is someone else's; a parent under another name, or with a default other than `main` or `master`, is not a candidate; and a fork whose `main` has commits of its own asks for the base more often. A request that names the base avoids each (ticket 18).
- **Smaller base gaps.** A remote `HEAD` naming `origin/main/x` is dropped; a branch and a tag that share the base's name resolve to the tag; a rename Git does not detect shows as a delete and an add; and with no remote, on `main` with `master` as the right base or on a stale `master` with `main` ahead, the skill asks rather than describes (ticket 18, **Residual, not fixed**).
- **Reads that run the person's own config.** In a partial clone, `diff` and `show` can fetch missing objects from the promisor remote; step 1's `status` runs a configured `core.fsmonitor` hook or daemon and a configured clean filter such as git-lfs's, and ticket 22's working-tree reads run that filter on every changed file (tickets 18 and 22).
- **`-G` with `--no-textconv`** skips a binary file it would have read through a converter, and the text-conversion probes ran on Apple Git 2.50.1 only (ticket 18).
- **`probe_reads.sh` has not run on Linux Git,** so the reads ticket 22 chose are shown to leave the index alone on Apple Git 2.50.1 only, and `grep … HEAD` was never probed (ticket 22, **Stage 4: skill text**).
- **Untested forms:** a branch too large to read in full, the no-base and detached-`HEAD` scope lines, which no run has checked (each real-change run, in ticket 25 and in ticket 30, is a branch against its base), and case B's account of `--year` (ticket 22).
- **Reading in full** makes a large branch slower and dearer (ticket 18, **Residual risks** of `c397d04`).
- **`merge-risk.md`'s `git ls-tree -r --name-only HEAD`** lists the checkout's files, not those of a pull request that is not checked out, so a risk call on one can miss what merging it sets off. It belongs with ticket 26 (ticket 23, **Stage 4: skill text**).
- **The pull request read path is unexercised** until ticket 26, and the cross-model review of design 23's §2, §3 and question 8's answer (row 1a) is owed no later than ticket 26's runs (ticket 23, **Stage 4 decisions**).

### The eval harness

- **GitHub tokens.** The runner does not scrub a GitHub token from transcripts, and Claude Code's unsandboxed Bash could point `HOME` or the `gh` config back at the host's login. Credential isolation, by sandboxing Claude Code's Bash or scrubbing tokens in the runner, is the follow-up; until then each run's results and workspaces get the token scan, by file name (ticket 23, row 5d).
- **The kept trigger lines.** No trial record keeps the line that set a trigger, Claude Code's `skill_expanded` line or Codex's `explicit` event, so a trigger is deduced rather than audited after teardown (ticket 17, design finding 4; ticket 18's trigger audit).
- **A write moved out of the workspace** leaves no trace in the record: the status, the contamination check and the grader material all miss it. After each Codex run, the system temp directory is listed for leftovers (ticket 18, inferred; tickets 20 and 21).
- **Running a fixture's code on Codex,** such as `pip`, `python -m build`, a test run or a baseline's `git checkout`, can make a trial an `infra_error`; the batch's one-rerun rule applies (tickets 19 and 20).
