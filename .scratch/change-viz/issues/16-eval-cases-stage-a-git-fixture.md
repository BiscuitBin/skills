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

## Completion notes

### Design checkpoint

- **Implementer:** Claude Code running Claude Opus 5.5 (`claude-opus-5-5`)
- **Reviewer:** Codex `gpt-6-astra` (fallback: no)
- **Reviewed:** design proposal `ai_tmp/design-16.md` at base `bd67179`, before any code
- **Findings:** `ai_tmp/review-20261111T053226Z-codex.md` · **Triage:** `ai_tmp/triage-design-16.md`

The section numbers (§) in the tables are the design doc's.

| # | Severity | Finding | Verdict | Action |
| --- | --- | --- | --- | --- |
| 1 | high | A fixture's root `.gitignore` can re-include the installed skill, because a `.gitignore` outranks `.git/info/exclude`. | valid | §4 rejects a negation line in any tree's root `.gitignore`. §7's preflight runs `git status` in fixture trials and fails on `.claude/` or `.agents/`. §5 now limits its claim to fixtures §4 accepts. §11 items 1 and 4 add the regression tests. |
| 2 | medium | `git ls-files --others` lists ignored files, so §5's claim was false. | valid (triage rates it low; the reviewer ran it on this repo, and the triage confirmed it from `gitignore(5)` and `git-ls-files(1)`) | §5 names `--exclude-standard` and lists the commands that still show the skill. §11 item 3 also asserts `ls-files --others --exclude-standard`. §12 puts the boundary in `eval-isolation.md`. Whether the boundary is enough is a maintainer question. Decided 2026-11-10: accepted (see Maintainer decisions). |
| 3 | medium | `workspace.git` cannot pass `GIT_INDEX_FILE`, the fixture identity, the dates or stdin, so the builder could not be written as specified. | valid | §3: `workspace.git` gains a keyword-only `env`, merged last, with defaults unchanged for every existing caller. Step 2 hashes from file paths, so no stdin is needed. §11 item 2 tests the environment without `env` and each commit's identity and dates. |
| 4 | medium | `main/topic` passes validation but cannot coexist with `refs/heads/main`. | valid (documented, not run) | §4 rejects `main` and `main/…` ignoring case, which also covers `Main` on a case-insensitive file system. §11 item 1 adds `main/topic` and `Main`. |

A second round was warranted: the fixes added two validation rules and a preflight check, changed a shared helper's signature, and changed how step 2 hashes files.

#### Round 2

- **Reviewer:** Codex `gpt-6-astra` (fallback: no)
- **Reviewed:** the revised `ai_tmp/design-16.md` at base `bd67179`
- **Findings:** `ai_tmp/review-20261111T070009Z-codex.md` · **Triage:** `ai_tmp/triage-design-16-round2.md`

| # | Severity | Finding | Verdict | Action |
| --- | --- | --- | --- | --- |
| 1 | medium | A `.gitattributes` inside a fixture tree outranks the root `-text` line, so it can change the committed bytes, and in the trial an unedited CRLF file stored raw shows as modified. | valid (the host half from `gitattributes(5)`; the trial half documented, not run) | §4 rejects a `.gitattributes`, ignoring case, anywhere under a fixture directory, as a stated limit. That is wider than the triage's "any tree", because one beside `fixture.json` also outranks the root line. §2 names both root `-text` lines and says they hold because of the ban. §11 item 1 adds the rejections. Item 2 builds a CRLF file in the clean shape and expects empty `git status --porcelain` and equal blob bytes. Item 9 runs `git check-attr` over every fixture file in both layouts. §12 documents the limit. |
| 2 | medium | The reserved-name rule compares names exactly, so `.GIT/config`, `.CLAUDE/settings.json` or `claude.md` pass load and collide with Git's or the agent's own paths on macOS. | valid | §4 compares every component of every tree path with the reserved names ignoring case, `.gitattributes` included, and says why. §11 item 1 adds `.GIT/config`, `.Claude/settings.json`, `claude.md` and `sub/Agents.md`. |
| 3 | low | §10's one exclusion regex misses the shipped fixture under `tests/fixtures/evals/git/small-tally/trees/`. | valid | §10 names both layouts in each tool's syntax. One anchored regex serves mypy and the three hooks, and is folded into markdownlint's `CLAUDE.md` exclude. Two globs serve ruff, Prettier and markdownlint's `ignores`. §11 item 9 checks the wiring. |

No third round: the fixes add one reserved name, compare the reserved names ignoring case, and correct a lint exclusion pattern. No builder step, hash input, environment variable, preflight check or schema field changed.

**Not yet run:** some claims behind the fixes rest on documentation or inference alone: hashing by path with `git hash-object --no-filters`, the `refs/heads/main/…` clash, `git ls-files --others` listing the installed skill in a trial, a text-attributed CRLF file showing as modified, the macOS case-folding collisions, and the ruff, Prettier and markdownlint glob spellings. The design's first tests (§11 items 1 to 3 and 9) and `just check` with the fixture committed confirm or refute them.

**Maintainer decisions (2026-11-10):**

- **Git views: the boundary is accepted.** This answers round 1's maintainer question. `git status --porcelain` (the ticket's test) and Claude Code's startup context hide the installed skill in both arms. `git ls-files --others` without `--exclude-standard`, `git status --ignored` and `git clean -n -x` still list `.claude/` or `.agents/` in the skill arm, as `ls -a` does. `docs/explanation/eval-isolation.md` documents this as a known limit.

**Follow-ups:** none from the review. One comes from the design and goes in `.scratch/foundation/follow-ups.md`: cowsay's skill arm still shows `?? .claude/` in Claude Code's startup git context, because writing the exclude in every trial would change every cowsay trial.

**Design as approved:** `ai_tmp/design-16.md` (gitignored), with both rounds' fixes. It corrects one line of **What is known**: the harness's own `workspace.git` calls read no global or system config, but the agent's `git` does, so fixture trials turn it off. An implementer follows these decisions:

- **Schema.** A case may name `"fixture": "<name>"`, a slug (`[a-z0-9][a-z0-9-]*`), on any case kind. It resolves to `evals/<skill>/fixtures/<name>/`, which holds `fixture.json` (`branch`, `main`, `commits`, optional `staged` and `worktree`, and `executable`) and one full snapshot of the project per tree under `trees/<tree>/`. `load_suite` validates every fixture directory, named or not, and a name with no directory is a load error. `files` stays accepted only as `[]`, beside `fixture` or not; a nonempty `files` is rejected with a message that points to `fixture`.
- **Hash and selection.** `evals_sha256` stays the hash of `evals.json` when `evals/<skill>/fixtures/` does not exist, so cowsay's recorded value still matches. Otherwise it is SHA-256 over the `evals.json` digest, a `FIXTURE_FORMAT` constant (bumped whenever the builder's output for the same inputs changes) and `tree_sha256` of the fixtures directory. `select_changed` already selects the skill for any path under `evals/<skill>/`; a test pins it. The root `.gitattributes` gains `evals/*/fixtures/*/trees/** -text` and `tests/fixtures/evals/git/*/trees/** -text`.
- **Build.** A new `src/skills_tooling/evals/fixture.py` runs first in `runner._attempt`, in both arms (not in `create_trial`, which the grader also calls). It builds history with plumbing only: `git hash-object -w --no-filters` by file path, a temporary index, `git commit-tree`, `update-ref` with no reflog and `read-tree`, then writes the working tree with a fixed past mtime and runs `git update-index -q --refresh`. Every commit's author and committer is `Robin Hale <robin@example.com>`, dated `@<1767225600 + n*3600> +0000` with n counting from 0 across `main` then `commits`, in a `sha1` repository, and a test pins the HEAD hash. `workspace.git` gains a keyword-only `env`, merged last; without it the environment is exactly today's. A fixture has no remote and no `origin/main`, so ticket 18 finds the base from local `main`.
- **Hiding the skill.** Every fixture trial, in both arms, gets a `.git/info/exclude` holding exactly `/.claude/` and `/.agents/`. Validation keeps it effective and the fixture neutral: no negation line in any tree's root `.gitignore`; no `.gitattributes` or symlink anywhere under a fixture directory; no path component equal, ignoring case, to `.claude`, `.agents`, `.codex`, `.git`, `.gitattributes`, `CLAUDE.md`, `CLAUDE.local.md`, `AGENTS.md`, `AGENTS.override.md` or `SKILL.md`, and no directory ending in `skills`; no `skill` or `skills` wording and no Codex denial keyword anywhere; ASCII paths, unique ignoring case and not ignored by this repository; and a `branch` that is neither `main` nor `main/…`, ignoring case. Fixture trials also add `GIT_OPTIONAL_LOCKS=0`, `GIT_CONFIG_NOSYSTEM=1` and `GIT_CONFIG_GLOBAL=/dev/null` to the agent's environment. A flow that writes to Git (`git add`, `git commit`) cannot be scored on Codex, and the docs say so.
- **Inventory and grader.** `inventory_problems` gains `expected`, a `{path: (sha256, mode)}` map built from the fixture definition, not from the workspace. The workspace must be exactly that map plus `.git` and the installed skill. A fixture trial also fails the preflight if `git status --porcelain --untracked-files=all`, run with `GIT_OPTIONAL_LOCKS=0`, names a path under `.claude/` or `.agents/`. `blinded_material` gets the same map and lists only new or changed files. Deleted fixture files are not shown to the grader, so `FRAMING` and `grader_prompt_sha256` do not change. With no fixture, the inventory check and the material are exactly today's.
- **Shipped fixture and tooling.** `tests/fixtures/evals/git/small-tally/` has two `main` commits, one branch commit, a staged edit, an unstaged edit and an untracked file; a smaller fixture has nothing ahead and a clean tree. Fixture trees are excluded from ruff, mypy, pytest (`norecursedirs` adds `fixtures`), markdownlint, Prettier and the `check-executables-have-shebangs`, `check-shebang-scripts-are-executable` and `check-merge-conflict` hooks, by the regex `^(evals/[^/]+/fixtures|tests/fixtures/evals/git)/[^/]+/trees/` or the two globs above, and a test checks the wiring.
