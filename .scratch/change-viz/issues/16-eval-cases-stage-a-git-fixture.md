# 16: Eval cases can stage a git fixture

**What to build:** an eval case names a fixture, and both arms' trials start in a small neutral project with real history: a `main`, a branch that is usually ahead of it, and optional staged, unstaged and untracked edits. Today a trial starts in an empty `git init`, so a skill that describes changes has nothing to describe. This is the prefactor for the `change-viz` skill (tickets 18 to 25), and it must leave cowsay's suite and results untouched.

Why the installed skill needs care: once the workspace has history, `git status` lists the installed skill's folder as untracked, in the skill arm only. A description of "what changed" would then include the skill itself, and the grader would see which arm it is reading.

**Blocked by:** none (can start immediately, in parallel with 17).

Tickets 16 and 17 do not depend on each other, but both edit the case loader, `docs/reference/evals.md` and `GLOSSARY.md`. Whichever lands second rebases onto the first.

**Status:** ready-for-agent

**Agent requirements:** Any implementing agent (Claude Code or Codex). No paid agent run is needed: the work is shown with unit tests and with the pinned CLIs against the local fake API, as the canary sweep does. Cross-model review is also required.

## What is known

As of 2026-11-10.

Read in the code and docs:

- `create_trial` (`src/skills_tooling/evals/workspace.py`) makes the workspace with `git init --initial-branch=main` and nothing else: no commits, no branch, no edits.
- The case loader (`src/skills_tooling/evals/cases.py`) rejects any nonempty `files` with "input files are not staged yet (deferred to a later ticket)". `.scratch/foundation/follow-ups.md` lists it under ticket 05's residuals.
- `inventory_problems` (`workspace.py`) fails a workspace that holds anything but `.git` and the installed skill, because anything more "could carry expected outputs, other cases, or a nested skills directory".
- Both adapters' `install_skill` copy the skill into the workspace: `.claude/skills/<name>` for Claude Code, `.agents/skills/<name>` for Codex. A baseline trial installs nothing.
- The grader's blinded material is the final message plus every workspace file except `.git/` and the skills directory, capped at 20 KB each and 80 KB in all (`docs/reference/evals.md`, **Grader**). Fixture files would fill that budget unless they are left out.
- The grader records `arm_disclosed` when the material holds the word `skill` or `skills`, or a skill-install path.
- A trial's `PATH` is `<trial>/bin:/usr/bin:/bin`, and `bin/` holds only the `python3` and `python` wrappers and `git`. The trial's home is empty and Git reads no global or system config, so a commit made inside a trial has no identity unless one is given.
- `evals_sha256` is the hash of `evals/<skill>/evals.json` alone (`benchmark.py`). Changed-skill selection (`select_changed` in `dispatch.py`) picks a skill by any path under `skills/<name>/` or `evals/<name>/`, and picks every skill when `src/skills_tooling/evals/` changes. So where fixtures live decides both.
- Codex reports a sandboxed command as denied when it exits nonzero and its output contains `operation not permitted`, `permission denied`, `read-only file system`, `seccomp`, `sandbox`, `landlock` or `failed to write file`, and a denied command makes the trial an `infra_error` (`docs/reference/evals.md`, **Codex**, **Run status**).
- Prior art: `.scratch/foundation/research.md` notes that humanlayer/skills runs `codex exec` against git fixture repos.

Follows from the above, not tried:

- A fixture cannot be a checked-in `.git` directory inside this repository, so its history has to be built for each trial, or unpacked from something Git can store.
- A fixture has no remote unless the design gives it one. Ticket 18's skill has to find a branch's base, so the design must say whether `origin/main` exists in a fixture.

## Acceptance criteria

- [ ] An eval case can name a fixture, and the schema rejects a name that does not resolve. The field's name and shape, and whether the deferred `files` field stays rejected, come from the design checkpoint.
- [ ] A fixture trial's workspace starts with the fixture's state in both arms:
  - a `main` branch with at least one commit, and a second branch, checked out
  - optional commits on that branch ahead of `main`, staged edits, unstaged edits and untracked files, each of which a fixture can have or leave out. Ticket 22 needs a fixture with nothing ahead and a clean tree, and one with uncommitted edits only.
- [ ] A fixture is built the same way every time: fixed author, committer and dates, so commit hashes do not change between trials, runs or machines. It needs no network and nothing outside the trial's `PATH`.
- [ ] Whatever builds the fixture leaves nothing in the workspace but the fixture: no build script, no recipe file, no expected output.
- [ ] The installed skill is invisible to Git in both arms. In a fresh fixture trial, `git status --porcelain` prints the same lines in the skill arm and the baseline arm, and they are only the fixture's own edits. Both arms are set up alike, so the setup itself does not tell the arms apart.
- [ ] The inventory check accepts a fixture's files and still fails anything else the workspace should not hold. A test plants an unexpected file beside a fixture and sees it fail.
- [ ] The grader is sent only the files the agent made or changed. A fixture file the agent left alone is not in the blinded material, and a test shows both halves.
- [ ] The secret sweep and trial teardown still cover every file in the workspace, fixture files included.
- [ ] A fixture edit is visible to the harness:
  - `just eval-changed` selects the skill whose case names the fixture, and a test shows it.
  - Two benchmark runs made with different fixture contents cannot be recorded into one iteration as if their eval cases were equal. Either `evals_sha256` covers the fixtures a suite names, or the fixture's hash is recorded and compared beside it.
- [ ] Cowsay is unaffected: `evals/cowsay/evals.json` is not edited, its trials still start in an empty workspace, and its recorded `evals_sha256` still matches.
- [ ] One small neutral fixture ships with the ticket and is used by its tests:
  - It holds no `skill` or `skills` wording, in file contents, paths, branch names or commit messages.
  - Nothing a failing command in it could print contains one of Codex's denial keywords listed above.
  - Anything it runs needs only `python3` and `git`.
- [ ] Shown working without a paid run: a fixture trial reaches each adapter's agent with the fixture in place, using the pinned CLIs against the local fake API where the existing tests do, and the contamination check passes for both arms.
- [ ] Docs and records:
  - ADR 0011 is updated, or a new ADR records where fixtures live and how they are built.
  - `docs/reference/evals.md` (case schema, isolation, grader material) and `docs/explanation/eval-isolation.md` describe a fixture trial.
  - The "Ticket 05" residual in `.scratch/foundation/follow-ups.md` says what is still deferred, if anything.
  - `GLOSSARY.md` gains **Fixture**.
- [ ] `just check` passes.

## Out of scope

- A remote, a pull request or any GitHub state in a fixture (ticket 23 handles a missing `gh`).
- Invoking a skill by name (ticket 17).
- The fixtures the `change-viz` cases need. Each of tickets 18 to 23 adds its own.

## Review checkpoints

Use the `cross-model-review` dev skill.

- **Design checkpoint:** before building, write the proposal and get it reviewed. It covers:
  - the schema: the field a case uses, and what happens to `files`
  - where fixtures live, and what that does to `evals_sha256` and to changed-skill selection
  - how history is built deterministically, with what identity and dates
  - whether a fixture has an `origin/main`
  - how the skill is hidden from Git in both arms
  - how the grader's material is cut to files the agent made or changed

  Is anything here a way for the two arms to differ? Can a fixture leak an expected output to the agent?
- **Implementation checkpoint:** before marking done, review the full diff against these acceptance criteria. Pay particular attention to anything that differs between the arms, to fixture files reaching the grader, and to cowsay's results changing.
