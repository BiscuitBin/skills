# 11: New-skill authoring workflow and docs

**What to build:** A contributor can start a new skill with `just new-skill <name>` and follow written guidance to take it from scaffold to validated, evaluated, reviewed and installable. The guidance covers eval-driven RED/GREEN development, the cross-model review protocol, and how versions and releases work.

**Blocked by:** 04 (Installable via Claude marketplace and npx skills), 09 (Cross-agent benchmark report and history).

**Status:** done

**Agent requirements:** Any implementing agent (Claude Code or Codex). A fresh-context subagent must follow the tutorial, with authenticated access to at least one supported agent for its live eval. No particular agent is required for that walkthrough. Cross-model review is also required.

## Acceptance criteria

- [x] `just new-skill <name>` creates a skill with spec-valid frontmatter, a stub body, Codex UI metadata and an eval directory with starter trigger and behaviour cases.
  - The result passes the validator straight away.
  - The command rejects invalid names and names that already exist, with a clear message.
- [x] A new skill is either added to the distribution manifests automatically, or `just check` fails with a message that says exactly what to add.
- [x] Starter eval cases are marked as placeholders, so `just eval` reports them as unwritten rather than passing. `just check` warns, naming the skill, when a skill in the distribution manifests still has only placeholder cases.
- [x] Scaffolding is tested in `just check`: a valid name, an invalid name, a duplicate name, and cleanup.
- [x] A contributing guide covers:
  - RED/GREEN skill development: write the eval cases and run a baseline first, then write the skill, then close the gaps the evals find.
  - When and how to run the cross-model review (pointing to the ticket 01 skill).
  - How versions are bumped and kept in sync.
  - How a release is cut, matching an actual `just` recipe or stating plainly that it is a manual version bump and merge.
- [x] A tutorial takes a scratch skill from scaffold to validated, evaluated on at least one agent, and installed into a throwaway project. Every command in it is copy-pasteable.
- [x] The tutorial is shown working: a fresh-context subagent follows it exactly in a scratch clone and succeeds. Every place it got stuck is fixed in the docs, and the scratch skill is not committed.
- [x] The docs index and README link to the guide and the tutorial.

## Review checkpoints

Use the repo's cross-model adversarial review skill from ticket 01, or the protocol written out there:

- Pick the reviewer by the cross-model rule.
- A reviewer subagent saves its findings to the scratch folder.
- A separate triage subagent checks each finding against the code.
- Apply the valid fixes, rerun `just check`, and record every finding and how it was handled under **Completion notes**.

- **Implementation checkpoint:** before marking done, review the full diff against these acceptance criteria. Pay particular attention to docs that disagree with the actual commands, and to scaffolds that pass checks while being useless.

## Completion notes

- **Command:** `just new-skill <name>` (`src/skills_tooling/scaffold.py`) writes `skills/<name>/SKILL.md`, `agents/openai.yaml`, `.claude-plugin/plugin.json`, `evals/<name>/evals.json` (a should-trigger, a should-not-trigger and a behaviour case, each `"placeholder": true`) and a marketplace entry. It refuses invalid names (the validator's `name_error`) and names already in `skills/`, `evals/`, `dev-skills/` or the marketplace, and writes nothing when it refuses or fails part-way. Names YAML would read as another type (`123`, `true`, `2026-99-99`) are quoted.
- **Useless scaffolds stay visible:** the validator warns `[placeholder]` on every skill file holding `TODO(new-skill)`; `just eval` (and `--dry-run`) prints `UNWRITTEN <skill>/<case>` and exits 2 before reading a credential; `just validate-evals`, so `just check`, warns naming any distributed skill that still has placeholder cases.
- **Manifests:** the scaffold adds the marketplace entry. A hand-made skill fails `just check` with the exact entry (and, if missing, the `plugin.json`) to add, or the entry to remove. Beyond the plan: `plugin.json`'s description is now copied into the marketplace by `just format` and checked like the version, so the scaffold's TODO description cannot survive in the marketplace.
- **Tests in `just check`:** `tests/test_scaffold.py` (valid name passes the validator, eval loader, distribution check, Prettier and markdownlint; invalid and duplicate names; YAML-typed names; cleanup after a failure part-way; starter evals reported unwritten), placeholder cases in `tests/evals/test_cases.py`, distribution messages in `tests/test_distribution.py`, validator fixture `placeholder`. The install round trips now cover every shipped skill; checked with a second, scaffolded skill committed in a scratch clone (10 passed).
- **Docs:** `CONTRIBUTING.md` (RED/GREEN, cross-model review, versions, releases: a manual version bump merged to `main`, no recipe or tag; the update-on-version claim checked against Claude Code's plugin docs), `docs/tutorials/first-skill.md`, links from `README.md`, `docs/README.md`, `docs/how-to/README.md`, `docs/tutorials/README.md`; reference updates in `commands.md`, `evals.md`, `distribution.md`, `skill-validator.md`; glossary **Placeholder case**.
- **Nothing written outside the project:** the tutorial's install runs the pinned `skills` in a throwaway project under `.tools/tmp/`; checked that it writes nothing to the home directory.

### Tutorial walkthrough

Fresh-context subagents followed `docs/tutorials/first-skill.md` exactly in scratch clones under `ai_tmp/`, with a project-local Codex login (the user ran `codex login` there).

| Run | Commit | Result | Eval runs (Codex `gpt-5.6-terra`) |
| --- | --- | --- | --- |
| 1 (`ai_tmp/tutorial-walkthrough-1.md`) | 2914d79 | Succeeded with a workaround. Stuck points: `cat >` failed under zsh `noclobber`; the RED explanation was wrong (the stub already triggered; the gap was the behaviour case); the baseline arm's `VALID` and `scored 1/1` were unexplained; two output quotes were inexact. All fixed in 5d1dc36. | RED `20261105T044709Z-572f` exit 1; GREEN `20261105T044827Z-fbd8` exit 0, behaviour delta +1.00 |
| 2 (`ai_tmp/tutorial-walkthrough-2.md`) | 5d1dc36 | Succeeded end to end, no stuck points. Two wording nits fixed in f8bcc11. | RED `20261105T045205Z-8f6e` exit 1; GREEN `20261105T045317Z-ba3f` exit 0, behaviour delta +1.00 |

Both runs ended with `git status --short` empty; the scratch skill was never committed.

### Code review (`/code-review`)

| # | Finding | Verdict | Action |
| --- | --- | --- | --- |
| 1 | Rollback ran only on `OSError`, so an interrupt left a half-written scaffold | valid | Fixed in aebe926: rolls back on any exception |
| 2 | The rollback's own `read_text` could raise | valid | Fixed in aebe926 |
| 3 | `json.dumps` escaped non-ASCII descriptions in `marketplace.json` | valid | Fixed in aebe926: `ensure_ascii=False`; test added |
| 4 | Only an all-placeholder suite warned; a partly written one passed silently | valid | Fixed in aebe926: warns on any placeholder case, naming them; test added |
| 5 | A malformed `plugin.json` was reported as one to create | valid | Fixed in aebe926: says to fix it; test added |
| 6 | The staging directory sat at the repo root, outside `.gitignore` | valid | Fixed in aebe926: staged under `.tools/tmp/` |
| 7 | `just eval` loads the suite twice | valid, not changed | Kept: the early load refuses placeholders before any credential is read |
| 8 | Marketplace path defined three times | valid | Fixed in aebe926 |
| 9 | Manifest template duplicated in the distribution hint | valid, not changed | Sharing it would create an import cycle for a hint message |
| 10 | The placeholder check reads every skill file again | valid, not changed | Skills are small text trees |

### Cross-model review

- **Implementer:** Claude Code running `claude-opus-5-5`
- **Reviewer:** Codex `gpt-6-astra` (fallback: no). The first run (on f8bcc11) exited 4 because Codex's first start set up its home (`.tools/agent-homes/codex/skills/.system/`, `installation_id`, `memories_1.sqlite`); its output, `ai_tmp/rejected-20261105T045622Z-codex.md`, was not triaged, but its one partial finding (unquoted YAML-typed names) was reproduced independently and fixed in 736ef08 with tests before the rerun.
- **Reviewed:** 1e136bf...736ef08
- **Findings:** `ai_tmp/review-20261105T050945Z-codex.md` · **Triage:** `ai_tmp/triage-20261105T051232Z.md`

| # | Severity | Finding | Verdict | Action |
| --- | --- | --- | --- | --- |
| 1 | medium | A valid name shaped like an impossible date (`2026-99-99`) crashed `just new-skill` with a traceback | valid | Fixed in b562b98: a YAML construction error means the name is quoted; `2026-99-99` and `2026-02-30` added to the tests |

**Follow-ups:**

- Claude Code's docs advise against setting `version` in both `plugin.json` and the marketplace entry (the manifest wins silently). The repo sets both on purpose ([ADR 0010](../../../docs/adr/0010-distribution-boundaries.md)) and the gate keeps them equal; revisit if that ADR is reopened.
- The cross-model review runner's allowlist does not cover Codex's first-run home setup, so the first review in a fresh worktree always exits 4 and needs a rerun.
