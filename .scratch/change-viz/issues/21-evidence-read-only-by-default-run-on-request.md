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

## Acceptance criteria

- [ ] By default the skill runs nothing in the project: no tests, no builds, no installs, and not the command the change touches. Reading files and read-only `git` commands are not "running the project". The skill says why, so an agent can judge a command the list does not name.
- [ ] Every runtime claim carries a label in one fixed form, set at the design checkpoint. It tells observed from read in the code, and an observed claim names its source: CI, a commit or the session.
- [ ] A claim nobody observed is never written as if it ran. "Tests pass" with no source is the failure this ticket exists to prevent.
- [ ] When the request asks for it, the skill runs what was asked (the project's checks, or the changed command), quotes the real output, trimmed but not reworded, and labels it as observed in this run, with the command.
- [ ] A command that fails when run is reported as failed, with its output. The description is still written.
- [ ] On a change source that is not checked out, the skill stays read-only even when asked, and says so. This is the implementing agent's reading of the options the maintainer was shown; confirm it at the design checkpoint.
- [ ] Eval cases, one per mode:
  - **Read-only:** a fixture whose change alters a command's output. The case asserts the label by pattern, and the description marks the outcome as read from the code.
  - **On request:** the same kind of fixture, with a request that asks for the command to be run. The case asserts the fixture's real output, which is something a reader could not produce from the code alone, such as a computed digest.
- [ ] The completion notes record what the baseline arm did on each case. On the on-request case it may well pass: an agent without the skill, asked to run the command, will quote the digest too. The case is then a guard that the skill still runs what it is asked to, not a measured gap, and the notes say so. The measured gap is the label in the read-only case.
- [ ] How "nothing ran" is checked is settled at the design checkpoint and recorded. Either the ticket adds a "command did not run" assertion type to the harness, as explicit scope with its own tests and docs, or the completion notes say the read-only case shows the labels but not that nothing ran.

### Every `change-viz` ticket

These repeat in tickets 18 to 24 so that each can be read alone.

- [ ] Eval cases are written and baselined before the skill text changes (RED, then GREEN), and each rubric is frozen before its live run (`CONTRIBUTING.md` §2 and §3). The baseline and skill-arm run ids on Claude Code and Codex are recorded here.
- [ ] Live evals are handed to the maintainer as absolute-path `just eval` commands. The agent reads `eval-results/` and never holds the token.
- [ ] Fixtures are a neutral project: no `skill` or `skills` wording anywhere in them, and none of Codex's sandbox-denial keywords (`operation not permitted`, `permission denied`, `read-only file system`, `seccomp`, `sandbox`, `landlock`, `failed to write file`) in output a failing command could print.
- [ ] Every "does not" outcome names how it is checked. A blinded expectation cannot be negative, so the check is an `output_matches` pattern, a transcript read by hand, or a limit stated in the completion notes.
- [ ] The skill explains why, not just what, and `SKILL.md` stays well under the validator's 500-line limit, with detail in `references/`.
- [ ] The skill's `plugin.json` version is higher than the one on `main` (ticket 18 keeps the scaffold's `0.1.0`), `just format` has run, the changes are committed, and then `just check` passes.

## Out of scope

Reading CI status (ticket 23), screenshots, checking out a pull request to run it, and running anything by default.

## Review checkpoints

Use the `cross-model-review` dev skill.

- **Design checkpoint:** before the live run, write the label's form, what counts as running the project, the two fixtures, the frozen rubric, and the choice on a "command did not run" assertion, and get them reviewed. Can the on-request case pass without the command running? If the assertion type is added, can a trial that ran the command behind `sh -c` or a script still pass it?
- **Implementation checkpoint:** before marking done, review the full diff against these acceptance criteria. Pay particular attention to wording that lets an agent label a guess as observed, and to a request that merely mentions tests being read as a request to run them.
