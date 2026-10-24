# 02: Project-local toolchain and green `just check`

**What to build:** A contributor clones the repo, runs `just initialize` and then `just check`, and gets a green result. Every tool, including the three agent CLIs, is pinned and installed inside the project directory, and the same gate runs on every PR in CI.

The repo also gets its agent instructions, a documentation skeleton, the first ADRs and a glossary, so later tickets have a shared vocabulary and a written record of decisions. Follow the toolchain style of `/Users/scutting/projects/pawdoku`. The research notes (`.scratch/foundation/research.md`) list the decisions to record.

**Blocked by:** None (can start immediately). Ticket 01 runs in parallel and also writes the agent instructions file. Whichever ticket lands second merges the other's section, and neither overwrites the other.

**Status:** done, except the CI criterion, which needs the first run on the PR

**Agent requirements:** Any implementing agent (Claude Code, Codex or Pi). All three pinned agent CLIs must be installed for version checks; authenticated live agent runs are not required outside the cross-model review checkpoint below.

## Acceptance criteria

- [x] In a fresh clone in a temporary directory, `just initialize` and then `just check` both pass. `just initialize` never stages, commits, tags or pushes. The README states the few host prerequisites `just initialize` relies on (such as just, uv and a Node install), and how the pinned Python and Node versions are obtained.
- [x] Python is managed by uv and Node by npm. Both use exact version pins and committed lockfiles. A lockfile drift check is part of `just check`.
- [x] `just` is the front door. At minimum it has `initialize`, `sync`, `lock`, `lock-check`, `install-hooks`, `format`, `lint`, `typecheck`, `test` and `check`. `just` with no arguments lists the recipes.
- [x] Claude Code, Codex and Pi are pinned to exact versions and installed project-locally.
  - A recipe prints each version without using any global install.
  - Any pinned binaries live in a gitignored tools folder inside the project.
- [x] `just check` covers ruff (lint and format check), mypy, pytest, markdownlint and prettier.
  - A deliberately broken input in each category makes it fail. Show this, then revert.
  - One trivial test proves the pytest wiring.
- [x] `just initialize` installs prek pre-commit hooks, which run the fast subset of the gate.
- [x] The agent instructions file is the single source, and the Claude instructions file only imports it.
  - It covers the front-door commands, the "everything stays in the project directory" rule, and the review protocol from ticket 01 (integrate that section if ticket 01 has landed, or leave a clearly marked placeholder for it).
- [x] The docs skeleton follows Diátaxis: tutorials, how-to guides, reference and explanation. It has an index that later tickets fill in.
- [x] ADRs record each decision in the research notes:
  - the local tracker
  - the Python-core / Node-tooling split, with Just as the front door
  - the project-local toolchain
  - the eval tiers and which ones run in CI
  - distribution channels
  - the cowsay example skill
  - cross-model review routing
  - the MIT licence
- [x] The glossary defines skill, dev skill, eval case, trial, run, adapter, grader, baseline, benchmark, trigger and contamination, each in a sentence or two.
- [x] A LICENSE file (MIT) is present, and the README describes the repo's purpose and how to start.
- [ ] A PR CI workflow runs `just check` on Linux. It uses pinned action versions and needs no secrets.
- [x] Agent scratch output, the tools folder, eval workspaces and eval results are gitignored.

## Review checkpoints

Use the repo's cross-model adversarial review skill from ticket 01. If it isn't available yet, follow the protocol written out in ticket 01:

- Pick the reviewer by the cross-model rule.
- A reviewer subagent saves its findings to the scratch folder.
- A separate triage subagent checks each finding against the code.
- Apply the valid fixes, rerun `just check`, and record every finding and how it was handled under **Completion notes**.

- **Implementation checkpoint:** before marking done, review the full diff against these acceptance criteria. Pay particular attention to anything that escapes the project directory, unpinned versions, and a gate that can pass while something is broken.

## Completion notes

Implemented on branch `02-project-local-toolchain` by Claude Code running Claude Opus 5.5 (`claude-opus-5-5`). Commits: `c6aaaf0` (toolchain), `f3121b8` (hook through just), `1cd2e3e` (review fixes), `0aae982` (code-review fixes), `24cad2f` (re-review fixes).

**Open:** the CI workflow (`.github/workflows/ci.yml`) has not run yet, because the branch has not been pushed. Its criterion stays unticked until the first PR run is green on `ubuntu-24.04`.

### Where things landed

- **ADRs** are in `docs/adr/` and the glossary is `GLOSSARY.md` at the root, following the domain-modeling skill's layout.
- **Ticket 01** had not landed, so `AGENTS.md` has a marked placeholder section, `## Cross-model review (ticket 01)`, for ticket 01 to replace.
- **The pre-commit hook** is not prek's shim. `just install-hooks` writes a hook that runs `just --justfile ./Justfile pre-commit`. See "Home-escape audit" for why.
- **Install scripts.** npm 11.17 `allowScripts` approves only `@anthropic-ai/claude-code@2.1.309`, whose `install.cjs` was read before approving: it hardlinks or copies the platform binary into its own `bin/` inside `node_modules` and writes nothing else. `@google/genai` (a no-op echo) and `protobufjs` (a version-scheme warning) are denied. `strict-allow-scripts=true` makes any other install script fail the install.

### Fresh-clone verification

Each run cloned the committed worktree into a scratch folder and ran with an empty home and only the pinned host tools on `PATH`:

```sh
env -i HOME=<empty dir> PATH=<just 1.51.0, uv 0.13.4, node 26.5.1, npm 11.17.0>:/usr/bin:/bin TERM=dumb \
  sh -c 'just initialize && just check'
```

- **Result.** Both passed on every run, the last one at `24cad2f`. `just initialize` ends with "Nothing has been staged, committed, tagged, or pushed." Afterwards `git status --porcelain --untracked-files=all` and `git diff` were empty, and `just` with no arguments lists the recipes.
- **Hook.** In the clone (a primary checkout) the hook was installed. A staged file with an unused import was rejected (`F401`), and a valid commit went through. A staged bad Markdown file was rejected (`MD018`), while an untracked bad Markdown file did not block an unrelated commit.
- **`just agents-version`** prints `2.1.309 (Claude Code)`, `codex-cli 0.163.0` and `1.4.0` from `node_modules/.bin`.

### Home-escape audit

After each run, everything under the fake home was listed:

- **First hook design (prek's shim), at `c6aaaf0`.** `just initialize` and `just check` left the home empty, but one commit through the hook downloaded Python into `~/.local/share/uv/python`, rebuilt `.venv/` against it, and filled `~/.cache/uv` and `~/.cache/prek`. The cause: git runs the hook without the Justfile's environment. Fixed in `f3121b8` by routing the hook through `just`.
- **From `f3121b8` onwards.** The home stayed empty after initialize, check, a rejected commit and a successful commit. `.venv/pyvenv.cfg` `home` pointed into `.tools/python`.
- **Remaining limits.** These are recorded in ADR 0003 and `AGENTS.md`:
  - A bare `uv`, `npm` or agent CLI call, outside `just`, does not get the environment. `just run <command>` is the way to run one.
  - The hook needs `just` on `PATH`.
  - `TMPDIR` moves into `.tools/tmp`. Its long path could exceed the macOS Unix-socket path limit for a tool that makes sockets there. Nothing does so today; recheck when the eval harness drives the agents.

### Broken-input demonstrations

Each one broke one input in the scratch clone, ran `just check`, and reverted with `git checkout -- .` (`git status` empty afterwards):

| Broken input | Failed at | Output |
| --- | --- | --- |
| `import os` appended to `src/skills_tooling/__init__.py` | `lint` | `Ruff lint ... Failed`, `F401` |
| `x = {  "a":1}` appended | `lint` | `Ruff format check ... Failed` |
| `count: int = "three"` | `typecheck` | `error: Incompatible types in assignment` |
| `__version__` changed to `0.2.0` | `test` | `AssertionError: assert '0.2.0' == '0.1.0'` |
| `#Bad heading` in `docs/how-to/README.md` | `lint` | `MD018/no-missing-space-atx` |
| `.prettierrc.json` misformatted | `lint` | `Prettier check ... Failed` |
| `ruff==0.17.1` in `pyproject.toml` without relocking | `lock-check` | `The lockfile at uv.lock needs to be updated` |
| `prettier` `3.9.9` in `package.json` without relocking | `lock-check` | `lock file's prettier@3.9.10 does not satisfy prettier@3.9.9` (later: lockfile diff) |
| `prettier` removed from `package.json` without relocking | `lock-check` | `package-lock.json disagrees with package.json` (`npm ci --dry-run` had passed this) |
| `node_modules/.bin/pi` removed | `agents-version` | `./node_modules/.bin/pi: No such file or directory` |
| Untracked `{bad` JSON file | `lint` | `check json ... Failed`, `Prettier check ... Failed` |
| Conflict markers in a tracked file | `lint` | `check for merge conflicts ... Failed` |
| 900 KB file | `lint` | `check for added large files ... Failed` |
| `docs/[x].md` with a bad heading | `lint` | `docs/[x].md:1:1 error MD018` |
| `SKIP=ruff-check` with an unused import | `lint` | `Ruff lint ... Failed` (SKIP ignored) |
| Pinned just changed to `9.9.9` | `just-version` | `just 9.9.9 is required` |

Further setup checks:

- **`just sync` and `just initialize` fail on drift.** A uv pin bumped without relocking fails `sync`. A removed npm dependency fails `initialize`.
- **`install-hooks` refusals.** It refuses when `core.hooksPath` is set, when a foreign pre-commit hook is present, and when a dangling symlink sits at the hook path; in each case nothing is written. With `core.hooksPath` set, `just initialize` warns, skips the hook and ends "Ready, without the pre-commit hook".
- **The hook on an old branch.** It passes in a worktree on a branch that has no Justfile.
- **Other behaviours.**
  - `uv add` writes `==` pins.
  - `UV_PYTHON_PREFERENCE=only-system` and `UV_PROJECT_ENVIRONMENT` in the caller's shell are overridden.
  - Codex starts with its isolated home (`Not logged in`).
  - `just format` fixes `docs/` and leaves `.scratch/` untouched.

### Cross-model review

- **Reviewer.** Codex `gpt-6-astra`, codex-cli 0.163.0, run as `codex exec --sandbox read-only --ephemeral -m gpt-6-astra -C <repo> -` by a reviewer subagent. The subagent saved the output to `ai_tmp/review-codex.md`. A separate triage subagent wrote `ai_tmp/review-triage.md`.
- **Read-only check.** For each review, content checksums of the worktree (outside `ai_tmp/`) taken before and after were identical.
- **Rounds.** Round 1 reviewed `main..f3121b8`. The fixes were substantial, so a re-review of `f3121b8..0aae982` followed (`ai_tmp/rereview-codex.md`, `ai_tmp/rereview-triage.md`).

**Round 1** (Codex, `main..f3121b8`):

| # | Finding | Verdict | Handling |
| --- | --- | --- | --- |
| 1 | `install-hooks` could write outside the project or overwrite unrelated hooks | partly valid | Refuses `core.hooksPath` and a pre-commit hook it did not write (`1cd2e3e`); refuses a dangling symlink (`24cad2f`). The worktree path is this repository's own common git dir, by design. |
| 2 | No `TMPDIR` override; Pi writes via `os.tmpdir()` | valid | `TMPDIR` set to `.tools/tmp` |
| 3 | `SKIP`/`PREK_SKIP` could drop hooks from the gate | valid | Cleared in `lint` |
| 4 | Untracked files escaped `lint` | valid | `lint` passes prek every file git does not ignore |
| 5 | `uv sync --frozen` did not fail on drift | valid | `uv sync --locked`, then `sync: lock-check` |
| 6 | No completion notes or recorded demonstrations | out of scope at review time | This section |
| 7 | Host just version not enforced | valid | `just-version` recipe, run by `initialize` and `check` |

**Code review** (Claude `code-review` skill, `main..1cd2e3e`):

| Finding | Verdict | Handling (`0aae982` unless noted) |
| --- | --- | --- |
| Hook fails in a checkout without a Justfile, and `just` can find a parent Justfile | valid | Hook exits 0 without `./Justfile` and uses `--justfile ./Justfile` |
| `check-merge-conflict` inert outside a merge | valid | `--assume-in-merge` |
| `check-added-large-files` inert outside a commit | valid | `--enforce-all` |
| `allowScripts` not enforced without strict mode | valid | `strict-allow-scripts=true` |
| `npm ci --dry-run` misses a removed dependency | valid | `lock-check` relocks a copy and compares |
| `uv add` writes `>=` bounds | valid | `add-bounds = "exact"` |
| Codex fails when `CODEX_HOME` is missing | valid | Agent homes created by a Justfile backtick |
| `just format` rewrites `.scratch/` tickets | valid | `format` excludes `.scratch/**` |
| `initialize` fails when `core.hooksPath` is set | valid | Warns and continues |
| uv env vars can override `only-managed` | valid | `UV_PYTHON_PREFERENCE` exported; `UV_PYTHON` and `UV_PROJECT_ENVIRONMENT` unexported |
| `lint` temp files at fixed paths | valid | `mktemp` plus `trap` |
| markdownlint hook linted every Markdown file on commit | valid | Hook passes filenames |
| Secondary-worktree guard is stale | disagreed | Kept: installing from a worktree still adds a hook to every checkout. Comment updated. |
| `package.json` scripts invite bare `npm run` | valid | Scripts removed |
| Ignore lists repeated in four files | valid | markdownlint `gitignore: true`; Prettier reads `.gitignore`; the hook `exclude` keeps only the lockfiles |
| (low) CI cancels runs on `main` | valid | `cancel-in-progress` only for pull requests |
| (low) Repeated version strings, mypy cache off, nested `uv run` | not changed | Left as is |

**Re-review** (Codex, `f3121b8..0aae982`):

| # | Finding | Verdict | Handling (`24cad2f`) |
| --- | --- | --- | --- |
| 1 | Hook path checks still incomplete | partly valid | Dangling symlink refused; the common-git-dir path is by design |
| 2–5 | Earlier #2–#5 | resolved | None |
| 6 | Completion notes missing | out of scope at review time | This section |
| 7 | just version checked only by initialize | partly valid | `just-version` added to `check` |
| 8 | markdownlint read hook filenames as globs | valid | `--` before the filenames; `CLAUDE.md` excluded in the hook |
| 9 | `gitignore: true` could hide tracked Markdown | valid | Fixed by `--`: literal paths bypass the filter |
| 10 | `initialize` reports Ready without the hook | invalid as a defect (documented trade-off) | Message now says "Ready, without the pre-commit hook" |
| 11 | `sync` docs claimed drift detection `npm ci` lacks | valid | `sync: lock-check` |

### Follow-ups

- Check the first CI run on Linux, then tick the CI criterion.
- Ticket 01 replaces the `AGENTS.md` placeholder.
- When the eval harness drives agents, recheck the `TMPDIR` socket-path length and whether each agent CLI writes outside its isolated home during a real run. This ticket verified only `--version`, and `codex login status`.
