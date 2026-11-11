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

- [x] An eval case can name a fixture, and the schema rejects a name that does not resolve. The field's name and shape, and whether the deferred `files` field stays rejected, come from the design checkpoint.
- [x] A fixture trial's workspace starts with the fixture's state in both arms:
  - a `main` branch with at least one commit, and a second branch, checked out
  - optional commits on that branch ahead of `main`, staged edits, unstaged edits and untracked files, each of which a fixture can have or leave out. Ticket 22 needs a fixture with nothing ahead and a clean tree, and one with uncommitted edits only.
- [x] A fixture is built the same way every time: fixed author, committer and dates, so commit hashes do not change between trials, runs or machines. It needs no network and nothing outside the trial's `PATH`.
- [x] Whatever builds the fixture leaves nothing in the workspace but the fixture: no build script, no recipe file, no expected output.
- [x] The installed skill is invisible to Git in both arms. In a fresh fixture trial, `git status --porcelain` prints the same lines in the skill arm and the baseline arm, and they are only the fixture's own edits. Both arms are set up alike, so the setup itself does not tell the arms apart.
- [x] The inventory check accepts a fixture's files and still fails anything else the workspace should not hold. A test plants an unexpected file beside a fixture and sees it fail.
- [x] The grader is sent only the files the agent made or changed. A fixture file the agent left alone is not in the blinded material, and a test shows both halves.
- [x] The secret sweep and trial teardown still cover every file in the workspace, fixture files included.
- [x] A fixture edit is visible to the harness:
  - `just eval-changed` selects the skill whose case names the fixture, and a test shows it.
  - Two benchmark runs made with different fixture contents cannot be recorded into one iteration as if their eval cases were equal. Either `evals_sha256` covers the fixtures a suite names, or the fixture's hash is recorded and compared beside it.
- [x] Cowsay is unaffected: `evals/cowsay/evals.json` is not edited, its trials still start in an empty workspace, and its recorded `evals_sha256` still matches.
- [x] One small neutral fixture ships with the ticket and is used by its tests:
  - It holds no `skill` or `skills` wording, in file contents, paths, branch names or commit messages.
  - Nothing a failing command in it could print contains one of Codex's denial keywords listed above.
  - Anything it runs needs only `python3` and `git`.
- [x] Shown working without a paid run: a fixture trial reaches each adapter's agent with the fixture in place, using the pinned CLIs against the local fake API where the existing tests do, and the contamination check passes for both arms.
- [x] Docs and records:
  - ADR 0011 is updated, or a new ADR records where fixtures live and how they are built.
  - `docs/reference/evals.md` (case schema, isolation, grader material) and `docs/explanation/eval-isolation.md` describe a fixture trial.
  - The "Ticket 05" residual in `.scratch/foundation/follow-ups.md` says what is still deferred, if anything.
  - `GLOSSARY.md` gains **Fixture**.
- [x] `just check` passes.

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

- **Git views: the boundary is accepted.** This answers round 1's maintainer question. `git status --porcelain` (the ticket's test) and Claude Code's startup context hide the installed skill in both arms. `git ls-files --others` without `--exclude-standard`, `git status --ignored` and `git clean -n -d -x` still list `.claude/` or `.agents/` in the skill arm, as `ls -a` does. `docs/explanation/eval-isolation.md` documents this as a known limit. (This said `git clean -n -x` until the implementation's probe showed that without `-d` it lists no directory, so it does not show the skill.)

**Follow-ups:** none from the review. One comes from the design and goes in `.scratch/foundation/follow-ups.md`: cowsay's skill arm still shows `?? .claude/` in Claude Code's startup git context, because writing the exclude in every trial would change every cowsay trial.

**Design as approved:** `ai_tmp/design-16.md` (gitignored), with both rounds' fixes. It corrects one line of **What is known**: the harness's own `workspace.git` calls read no global or system config, but the agent's `git` does, so fixture trials turn it off. An implementer follows these decisions:

- **Schema.** A case may name `"fixture": "<name>"`, a slug (`[a-z0-9][a-z0-9-]*`), on any case kind. It resolves to `evals/<skill>/fixtures/<name>/`, which holds `fixture.json` (`branch`, `main`, `commits`, optional `staged` and `worktree`, and `executable`) and one full snapshot of the project per tree under `trees/<tree>/`. `load_suite` validates every fixture directory, named or not, and a name with no directory is a load error. `files` stays accepted only as `[]`, beside `fixture` or not; a nonempty `files` is rejected with a message that points to `fixture`.
- **Hash and selection.** `evals_sha256` stays the hash of `evals.json` when `evals/<skill>/fixtures/` does not exist, so cowsay's recorded value still matches. Otherwise it is SHA-256 over the `evals.json` digest, a `FIXTURE_FORMAT` constant (bumped whenever the builder's output for the same inputs changes) and `tree_sha256` of the fixtures directory. `select_changed` already selects the skill for any path under `evals/<skill>/`; a test pins it. The root `.gitattributes` gains `evals/*/fixtures/*/trees/** -text` and `tests/fixtures/evals/git/*/trees/** -text`.
- **Build.** A new `src/skills_tooling/evals/fixture.py` runs first in `runner._attempt`, in both arms (not in `create_trial`, which the grader also calls). It builds history with plumbing only: `git hash-object -w --no-filters` by file path, a temporary index, `git commit-tree`, `update-ref` with no reflog and `read-tree`, then writes the working tree with a fixed past mtime and runs `git update-index -q --refresh`. Every commit's author and committer is `Robin Hale <robin@example.com>`, dated `@<1767225600 + n*3600> +0000` with n counting from 0 across `main` then `commits`, in a `sha1` repository, and a test pins the HEAD hash. `workspace.git` gains a keyword-only `env`, merged last; without it the environment is exactly today's. A fixture has no remote and no `origin/main`, so ticket 18 finds the base from local `main`.
- **Hiding the skill.** Every fixture trial, in both arms, gets a `.git/info/exclude` holding exactly `/.claude/` and `/.agents/`. Validation keeps it effective and the fixture neutral: no negation line in any tree's root `.gitignore`; no `.gitattributes` or symlink anywhere under a fixture directory; no path component equal, ignoring case, to `.claude`, `.agents`, `.codex`, `.git`, `.gitattributes`, `CLAUDE.md`, `CLAUDE.local.md`, `AGENTS.md`, `AGENTS.override.md` or `SKILL.md`, and no directory ending in `skills`; no `skill` or `skills` wording and no Codex denial keyword anywhere; ASCII paths, unique ignoring case and not ignored by this repository; and a `branch` that is neither `main` nor `main/…`, ignoring case. Fixture trials also add `GIT_OPTIONAL_LOCKS=0`, `GIT_CONFIG_NOSYSTEM=1` and `GIT_CONFIG_GLOBAL=/dev/null` to the agent's environment. A flow that writes to Git (`git add`, `git commit`) cannot be scored on Codex, and the docs say so.
- **Inventory and grader.** `inventory_problems` gains `expected`, a `{path: (sha256, mode)}` map built from the fixture definition, not from the workspace. The workspace must be exactly that map plus `.git` and the installed skill. A fixture trial also fails the preflight if `git status --porcelain --untracked-files=all`, run with `GIT_OPTIONAL_LOCKS=0`, names a path under `.claude/` or `.agents/`. `blinded_material` gets the same map and lists only new or changed files. Deleted fixture files are not shown to the grader, so `FRAMING` and `grader_prompt_sha256` do not change. With no fixture, the inventory check and the material are exactly today's.
- **Shipped fixture and tooling.** `tests/fixtures/evals/git/small-tally/` has two `main` commits, one branch commit, a staged edit, an unstaged edit and an untracked file; a smaller fixture has nothing ahead and a clean tree. Fixture trees are excluded from ruff, mypy, pytest (`norecursedirs` adds `fixtures`), markdownlint, Prettier and the `check-executables-have-shebangs`, `check-shebang-scripts-are-executable` and `check-merge-conflict` hooks, by the regex `^(evals/[^/]+/fixtures|tests/fixtures/evals/git)/[^/]+/trees/` or the two globs above, and a test checks the wiring.

### Implementation checkpoint

#### What was built

Commits `6a08917..4a295e8`, then the review fixes `9ab646d` and `bed4ae0`.

- **Schema** (`cases.py`): a case may name `"fixture"`. A name that is not a slug, or has no directory, is a load error, and a nonempty `files` is rejected with a message that points to `fixture`.
- **Fixtures** (`src/skills_tooling/evals/fixture.py`, new): `load_fixtures` validates every fixture directory by the design's rules, plus a ban on `__pycache__` (review finding 1). `build` writes the history with plumbing only, with Robin Hale's fixed identity and dates, no reflog and the exclude, and returns `{path: (sha256, git mode)}` for the files it wrote. Small-tally's HEAD is pinned at `c63fc294563293a6dbacf229d040cc4dafc59f58`.
- **Runner** (`runner._attempt`): a fixture case builds its fixture first, in both arms, and adds eight Git variables to the agent's environment: four at first, then the author and committer identity from /code-review finding 1 (`a083291`). `workspace.git` takes a keyword-only `env`.
- **Inventory** (`workspace.inventory_problems(expected=...)`, through `contamination.preflight`): the workspace must be exactly the built map plus `.git` and the installed skill, and a fixture trial fails if `git status --porcelain -z` names a path under `.claude/` or `.agents/`. `workspace.unchanged` is the one test of "as built", shared with the grader. A directory at a fixture path counts as changed (review finding 2).
- **Grader** (`grader.blinded_material`, `grade(fixture_files=...)`): only new or changed files. A deleted fixture file is not shown, so `FRAMING` and `prompt_sha256` do not change.
- **Hash** (`benchmark.evals_sha256`): with no `evals/<skill>/fixtures/` it is the `evals.json` digest alone, so cowsay's recorded value still matches. Otherwise it also covers `FIXTURE_FORMAT` and `tree_sha256` of the fixtures.
- **Shipped fixtures and tooling:** `tests/fixtures/evals/git/small-tally` and `clean-branch`; a new root `.gitattributes` with the two `-text` lines; fixture trees kept out of ruff, mypy, pytest, markdownlint, Prettier and three pre-commit hooks.
- **Tests:** `test_cases.py`, `test_fixture.py` (new), `test_workspace.py`, `test_grader.py`, `test_benchmark.py`, `test_dispatch.py` and `test_repo_config.py` (new), plus the pinned CLIs against the fake APIs in `test_runner.py` and `test_trials_and_baselines.py` (Claude Code: the same git status and startup git context in both arms) and `test_codex_adapter.py` (Codex: Git reads not denied, a `git add` denied).
- **Docs and records:** `docs/reference/evals.md` (**Fixtures**, Isolation, Grader, Provenance, History), `docs/explanation/eval-isolation.md` (**Fixture trials** and three known limits), ADR 0011, `GLOSSARY.md` **Fixture**, and in `.scratch/foundation/follow-ups.md` the rewritten Ticket 05 residual and a new Ticket 16 entry.
- **Departures from the approved design:**
  - Four agent Git variables, not three. `GIT_ATTR_NOSYSTEM=1` joins them, because Apple Git 2.50.1 reads the system gitattributes even with `GIT_CONFIG_NOSYSTEM=1`. `workspace.GIT_ENV` has it too (`51fb829`), which leaves cowsay trials unchanged. /code-review finding 1 later added the four `GIT_AUTHOR_*` and `GIT_COMMITTER_*` variables, so there are eight.
  - The repository ignore check runs only when the root is its own Git top level. A copy of `evals/` outside any repository skips it.
  - A branch must pass both `git check-ref-format --branch` and the `refs/heads/` form, and a commit message may not start or end with whitespace.
  - `commits` and `executable` may be left out, and default to `[]`.
  - The accepted Git views boundary names `git clean -n -d -x`, not `git clean -n -x` (see Maintainer decisions).

#### Checks run

- `just check` on `a083291` (this branch, with ticket 17, both tickets' review fixes and the /code-review fixes): passed, exit 0. pytest: 1202 passed, 4 skipped. The skips are the two runs of the on-disk case-clash test, because macOS folds case, and the two CI-only canaries. Lint, mypy (58 files), the distribution check, `validate-skills` (2 skills, 0 errors), `validate-evals` (1 suite valid) and the version check (Claude Code 2.1.309, Codex 0.163.0) passed. Log: `ai_tmp/gate-cr.log`.
- Before the /code-review, `just check` passed on `37ec5a1`: 1195 passed, 4 skipped (`ai_tmp/gate-16-17.log`).
- The /code-review fixes: each new test failed first for the stated reason, finding 1's with the host's identity in place of Robin Hale and the others with `DID NOT RAISE CaseError`. After the last fix, `test_cases.py`, `test_fixture.py`, `test_benchmark.py`, `test_workspace.py`, `test_grader.py` and `test_dispatch.py` gave 523 passed, 2 skipped (the case-clash skips). For finding 1, `test_fixture.py`, `test_runner.py`, `test_trials_and_baselines.py`, `test_codex_adapter.py` and `test_claude_adapter.py`, with the pinned CLIs and fake APIs, gave 94 passed. Cowsay is unchanged: `git diff 5bf7fe0..a083291 -- evals/` is empty, its `evals_sha256` pin passes and `grader.py` was not touched.
- Before the cross-model review, `just check` passed on `4a295e8`: 1084 passed, 4 skipped (`ai_tmp/verify-16-check.log`). Each criterion was checked against the code and the tests that pin it (`ai_tmp/impl-16-progress.md`, **Verify**).
- Each review fix was red first: the five new `__pycache__` cases loaded, and the new `now-a-dir` case raised `IsADirectoryError`.
- Not run: Ubuntu CI, because nothing was pushed, so the two canaries and the case-clash test have not run. No live eval, which this ticket does not need.

#### Cross-model review

- **Implementer:** Claude Code running Claude Opus 5.5 (`claude-opus-5-5`)
- **Reviewer:** Codex `gpt-6-astra` (fallback: no)
- **Reviewed:** `6a08917..4a295e8`
- **Findings:** `ai_tmp/review-20261111T103027Z-codex.md` · **Triage:** `ai_tmp/triage-impl-16.md`

| # | Severity | Finding | Verdict | Action |
| --- | --- | --- | --- | --- |
| 1 | medium (triage: low) | A file under `__pycache__` in a fixture is built into the workspace but left out of `evals_sha256`, so two fixtures that differ only there share an iteration. A nested `!__pycache__/` negation, or a root outside any repository, gets it past the ignore check | valid: it needs a deliberate negation, or a root that is not a repository top level | fixed in `9ab646d`: `_walk` in `fixture.py` refuses any file under the fixture directory with a `__pycache__` path part, compared as `tree_sha256` compares it, whether or not the ignore check runs. That is wider than the triage's `_tree_path`, which never sees the tree name and would miss `trees/__pycache__/a.txt`. `docs/reference/evals.md` gains the rule. Five cases in `test_cases.py` loaded before the fix, the nested negation among them |
| 2 | low | `unchanged` raises `IsADirectoryError` when a directory replaces a fixture file, so the preflight records a harness error instead of `changed in workspace`, and the descriptor leaks | valid: the preflight cannot reach it today, and the trial fails closed either way | fixed in `bed4ae0`: `fstat` on the raw descriptor before wrapping it with `closefd=False`, and one `os.close` in a `finally`. A `now-a-dir` case in `test_workspace.py` raised before the fix |

No second round: neither fix changes a mechanism, a rule set in substance or a data format. Fix 1 adds one load-time refusal, for a path no committed fixture can hold, and fix 2 moves the mode check in `unchanged` ahead of the wrap. The hash, the build, the map and the existing messages are unchanged.

**/code-review (high, Stage 1):** a separate stage from the cross-model review. Claude Code's `/code-review` skill, model `claude-fable-5-2`, reviewed branch `change-viz` against `main` at `5bf7fe0`. Findings: `ai_tmp/code-review-stage1.json` · Triage: `ai_tmp/triage-code-review-stage1.md`. The numbers are the findings file's, from 1; findings 4, 7 and 10 are ticket 17's. The fixes are `5fa644c`, `8226ae3`, `cc4fad8` and `a083291`.

| # | Finding | Verdict | Action |
| --- | --- | --- | --- |
| 1 | The agent's Git has no identity, so a commit the agent makes takes the machine's account name and `<login>@<host>`, or is refused where Git cannot guess an email | valid (low) | fixed in `a083291`: `fixture.AGENT_GIT_ENV` adds `IDENTITY`, `Robin Hale <robin@example.com>` as author and committer, with no dates. `test_fixture.py::test_a_commit_the_agent_makes_is_robin_hales_on_any_machine` failed first with the host's identity. The env pins in `test_trials_and_baselines.py` and `test_codex_adapter.py:552` now check all eight variables. `evals.md` says eight and has a row for the identity, and `eval-isolation.md` gains a sentence on it |
| 2 | The ignore check skips the author's global ignore file, so a file only that file ignores passes validation and is built and hashed locally, but no checkout has it | valid (low) | fixed in `cc4fad8`: `workspace.global_excludes()`, moved from `benchmark`, and a new `workspace.is_toplevel()` serve both `benchmark.git_state` and `fixture._ignored`, which passes the global file to `git check-ignore`. The message now says "Git ignores it". `test_cases.py::test_a_path_the_authors_global_ignore_file_ignores_is_rejected` (`core.excludesFile` and XDG cases) loaded first. `evals.md` names the global ignore file |
| 3 | Commit messages and the branch are not checked for Codex's denial keywords, though `git log` and `git status` print them | valid (low) | fixed in `5fa644c`: `_denial` checks each message and the branch. `test_cases.py::test_a_sandbox_denial_keyword_in_the_branch_or_a_message_is_rejected` (`sandbox-cleanup`, "Fix Permission Denied on read") loaded first. The **Neutral text** rule in `evals.md` covers both |
| 5 | The grader material shows no trace of a fixture file the agent deleted | known residual | none: the design left it out, because it needs a new `FRAMING` line and so a new `grader_prompt_sha256`. It is in Residual risk below and in `.scratch/foundation/follow-ups.md` (Ticket 05) |
| 6 | An empty `evals/<skill>/fixtures/` changes `evals_sha256`, and an empty `trees/<t>/` validates, though Git keeps neither | valid (low) for the empty tree; known residual for the empty `fixtures/` | fixed in `8226ae3`, the empty tree only: `_spec` takes the tree names from `_walk`, which holds only trees with a file, and `_tree_names` is gone. The tree, `staged` and `worktree` messages now say "is not a directory under trees/ that holds a file (Git keeps no empty directory)", as a checkout gives. `test_cases.py::test_an_empty_tree_is_rejected_as_a_checkout_would_be` (`worktree` and commit cases) loaded first. The empty `fixtures/` was not touched |
| 8 | `Fixture.files()` walks each tree again at build, though load's walk already collected it | out of scope | none: a few files cost nothing next to an agent run, and load rejects symlinks, so both walks see the same files. Follow-up below |
| 9 | The install directories are written down three times, in `HIDDEN_PARTS`, `EXCLUDE` and the adapters' `skills_dir`, and nothing ties them together | out of scope | none: the three agree, and only a third adapter, Pi, which is deferred, could make them differ. Follow-up below |

**Re-review of the /code-review fixes:** a focused cross-model round, shared with ticket 18's P4.

- **Implementer:** Claude Code running Claude Opus 5.5 (`claude-opus-5-5`), per the commits' trailers. The review script recorded no implementer model.
- **Reviewer:** Codex `gpt-6-astra` (fallback: no)
- **Reviewed:** `5bf7fe0..a083291`, the fixes `5fa644c`, `8226ae3`, `cc4fad8` and `a083291`, at `227eb93`, against this ticket's acceptance criteria and the triage of /code-review findings 1, 2, 3 and 6. The brief asked whether the fixes are right and complete, whether they set the arms apart, whether they change cowsay's results, and whether the docs match the code.
- **Findings:** `ai_tmp/review-20261111T185340Z-codex.md` · **Triage:** `ai_tmp/triage-pre-red.md`

The review reported no finding on `5bf7fe0..a083291`, so this round has no table, no fix and no second round here. Its three findings are all on P4, in ticket 18's **P4 review**.

**Follow-ups:**

- The descriptor close in `unchanged` has no test of its own. A fix that only caught `OSError` around `fdopen` would also pass the `now-a-dir` case.
- The nested-negation test asserts an exact problem list that depends on how Git re-includes ignored paths, seen only with Apple Git 2.50.1. Ubuntu CI is its first Linux run, and the `now-a-dir` case's.
- Closed here: the design and the Maintainer decisions now say `git clean -n -d -x`, as the docs do. The progress note's claim that the repository ignore check rejects `__pycache__` is superseded by finding 1's rule, as the note says. `just check` has run on the fix commits (above).
- No cross-model review finding was out of scope.
- /code-review finding 5 is a known residual, already filed in `.scratch/foundation/follow-ups.md:58` (Ticket 05). So is finding 6's empty `fixtures/` half, under **Stray files** in Residual risk below.
- /code-review finding 8, optional: keep the validated per-tree map on `Fixture`, so a build does not walk the trees again.
- /code-review finding 9, for the Pi adapter ticket: build `HIDDEN_PARTS` and `EXCLUDE` from one ordered tuple in `workspace.py`, which keeps `EXCLUDE`'s bytes, and add a test over every adapter `adapter_for` returns.
- Closed after the re-review: the agent's Git variables are eight, with /code-review finding 1's identity, and **What was built**, its departures and the two Residual risk lines below now say so. All eight are seen reaching Codex's commands, through `test_codex_adapter.py:552`.
- Claude Code was not checked passing `GIT_AUTHOR_*` and `GIT_COMMITTER_*` to its Bash tool's commands, as with the other four variables. /code-review finding 1's test shows what Git does with them, not that the CLI passes them on.
- /code-review finding 2 changed a validation message from "the repository ignores it, so a checkout would not have it" to "Git ignores it, so a checkout would not have it". Notes in `ai_tmp/` that quote the old text are stale.
- Fixture validation now reads the global ignore file of whoever runs it, as `git_state` already did. A maintainer whose global ignore file lists a shipped fixture's file sees a validation failure locally. That is correct, but local results depend on that file.

**Residual risk:**

- **Linux is unrun.** Ubuntu CI has not run, because nothing was pushed. It is the first run of dash, Codex's bwrap or Landlock sandbox on `.git` (the `git add` denial, and the eight variables reaching its commands), the on-disk case-clash test, and `GIT_ATTR_NOSYSTEM` on a non-Apple Git.
- **Deleted fixture files are not shown to the grader.** A case that judges a deletion needs a `needs_transcript` expectation.
- **Cowsay's skill arm still shows `?? .claude/`** in Claude Code's startup git status, as before this ticket. The follow-up is in `.scratch/foundation/follow-ups.md`.
- **The Git views boundary.** `git status --ignored`, `git ls-files --others` without `--exclude-standard` and `git clean -n -d -x` still list the skill in the skill arm, as `ls -a` does.
- **The secret-sweep criterion is met by inspection.** The sweep and teardown are unchanged code, and no test plants a secret in a fixture file.
- **A Git write cannot be scored on Codex.** `git add` in a fixture trial is denied and the trial is `infra_error`, observed on macOS only.
- **The eight variables were seen reaching Codex's commands only.** For Claude Code, the check is the environment the CLI starts with and its startup git context, not a Bash command's environment.
- **The wording check reads UTF-8.** `skill` wording in a UTF-16 file would pass validation.
- **Stray files.** A file directly in `evals/<skill>/fixtures/`, such as a Finder `.DS_Store`, or an empty fixtures directory, changes `evals_sha256` locally but not in a clean checkout. Runs then refuse to share an iteration; they never wrongly share one.
