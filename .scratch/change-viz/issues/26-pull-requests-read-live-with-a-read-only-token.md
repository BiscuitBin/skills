# 26: Pull requests read live, with a read-only token

**What to build:** ticket 23's live path. The released `change-viz` describes the four pull requests the maintainer likes, read as pull requests with `gh` and a read-only GitHub token. Every `gh` and `git` command in the four transcripts is listed, to show that nothing writes. A pull request whose base is not the default branch is shown described against that base.

Why: no eval trial has a `gh` login, so no trial exercises the pull request read path (ticket 23, **What no trial exercises**). How good a pull request description is, and whether the skill ever writes, rest on this path. The maintainer made it a follow-up, not a release blocker (D5, `ai_tmp/stage3/decisions.md`, **Stage 4 decisions (2026-11-16)**).

**Blocked by:** 23 (Pull requests as a source) and 25 (Review with the maintainer, then ship). The runs use the released skill.

**Status:** needs-maintainer

**Agent requirements:** Any implementing agent (Claude Code or Codex). The maintainer creates the token: fine-grained, public repositories only, read-only. The agent hands the maintainer absolute-path commands, the maintainer runs them with the token in their own terminal, and the agent reads the saved transcripts and never holds the token. Cross-model review is also required.

## What is known

As of 2026-11-16.

- **The four pull requests,** all public (ticket 25, **What is known**):
  - BiscuitBin/knarr#75 (15 files), merged
  - BiscuitBin/skills#1 (14 files), merged
  - BiscuitBin/skills#4 (31 files), merged
  - BiscuitBin/rove#11 (13 files), open
- **Every base is `main`, each repository's default branch** (`gh pr view --json baseRefName`, 2026-11-16). So none of the four can show a base other than the default branch.
- **How a pull request is read (D6):** only with `gh` GET calls: `gh pr view`, `gh pr diff`, `gh pr checks` and `gh api --method GET`. Code around the change is read from the pull request's own refs, never by checking it out. Code from a source that is not checked out is never run.
- **Ticket 25's runs stub `gh`** (plan Phase 3), so they describe each change as a branch against its base, never as a pull request.
- **Ticket 21 asks this path for one run request** on a pull request that is not checked out (ticket 21, **Residual risk**). Under D6 the skill declines and says so.
- **Owed no later than these runs** (ticket 23, design review row 1a): a cross-model review of design 23's §2, §3 and question 8's answer.
- **The runner does not scrub a GitHub token from transcripts** (ticket 23, **Residual risk**). Ticket 23's scan prints file names only: `rg -l -e '\bgh[opsur]_[A-Za-z0-9]{20,}' -e '\bgithub_pat_[A-Za-z0-9_]{20,}'`. A hit means the token is revoked at once.
- **No eval assertion can show that nothing writes.** Only a hand read of the commands can.

## Acceptance criteria

- [ ] The token is fine-grained, limited to public repositories, and read-only. Its scope is recorded here, never its value.
- [ ] The released skill is run on each of the four pull requests, by number or URL, and each run is recorded here: the command, the agent, and where its output and transcript are saved under `ai_tmp/`.
- [ ] At least one run is on a pull request that is not checked out, and its description says how much of the surrounding code it could read (ticket 23, the not-checked-out criterion).
- [ ] Every `gh` and `git` command in the four transcripts is listed here, and none writes:
  - no `gh pr edit`, `comment`, `review`, `merge`, `close` or `checkout`, and no `gh api` call with a writing method;
  - no `git` command that writes to the repository, by design 23's verdict 9 list, which includes `fetch`.
- [ ] The notes say that no eval assertion can show "never writes", and that this hand read is the check.
- [ ] The pull request's own base is shown working on a pull request whose base is not the default branch. None of the four qualifies, so it is another public pull request, or the notes say it was not shown.
- [ ] One request asks the skill to run a check on a pull request that is not checked out. The skill declines and says why, and the transcript shows that nothing ran.
- [ ] After the runs, ticket 23's token scan runs over every saved transcript and output. Only file names are recorded.
- [ ] A fault the runs show is recorded here, and fixed by its general reason or carried to a new ticket.

## Out of scope

Creating or updating a pull request or its description, review comments and discussion threads, hosts other than GitHub, private repositories, and a `gh` login inside an eval trial.

## Review checkpoints

Use the `cross-model-review` dev skill.

- **Before the runs:** row 1a's review of design 23's §2, §3 and question 8's answer, if it has not run already, with the commands handed to the maintainer. Can any of them write?
- **Implementation checkpoint:** before marking done, review the command lists and the outputs against these acceptance criteria. Pay particular attention to any command that writes, to a base taken from the default branch instead of the pull request, and to check status reported from memory instead of from `gh`.
