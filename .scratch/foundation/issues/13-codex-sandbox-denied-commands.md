# 13: Codex sandbox-denied commands

**What to build:** the Codex adapter reports a command its sandbox denied, and a trigger rests only on evidence that the skill was read. Ticket 06's first Linux CI run (actions run [40614691505](https://github.com/BiscuitBin/skills/actions/runs/40614691505), with the temporary debug prints of commit `8fe4d12`) showed two gaps. Ubuntu 24.04's AppArmor restriction made bubblewrap fail, so Codex denied every sandboxed command:

```text
INFO codex_otel.log_only: event.name="codex.sandbox_outcome" tool_name=exec_command call_id=exec-… outcome=denied initial_duration_ms=45 …
bwrap: loopback: Failed RTM_NEWADDR: Operation not permitted
WARN codex_sandboxing::violation: recorded sandbox violation: resource=filesystem backend=linux_sandbox reason=operation_not_permitted path=unknown
```

- The denied commands never reached the trace. `trace.commands` was empty, yet `trace.status` stayed `ok`, so the run looked like one where the agent ran nothing.
- `assert trace.skills_triggered == ["cowsay"]` passed in the trigger-command test even though no `SKILL.md` read ran. The next assertion, on `trace.commands[1]`, failed with `IndexError`.

CI now lifts the restriction (`sysctl -w kernel.apparmor_restrict_unprivileged_userns=0`), so these gaps no longer show there, but a user on a stock Ubuntu 23.10+ machine meets them.

**Blocked by:** 06 (Codex adapter).

**Status:** done

**Agent requirements:** Any implementing agent (Claude Code, Codex or Pi). Recording the transcript needs the pinned Codex on a Linux machine (or VM) with the AppArmor restriction on; the tests themselves must not. Cross-model review is also required.

## Acceptance criteria

- [x] A command the sandbox denies (`codex.sandbox_outcome … outcome=denied`) shows up in the trace as a failed command, or marks the trial, rather than disappearing while the status stays `ok`. Record which, and why, in `docs/reference/evals.md`.
- [x] Find out why `skills_triggered == ["cowsay"]` held on Linux when no `SKILL.md` read ran (a `codex.skill_invocation` event, a parser path, or something else), and record the answer here.
- [x] A trigger requires a read that succeeded or Codex's own event for one. A denied read does not count, and a test asserts this.
- [x] Regression tests drive the parser from a recorded denied-sandbox transcript in `tests/fixtures/evals/codex/`, with its stderr reduced to the kept lines. They run in `just check` on any OS.

## Review checkpoints

Use the repo's cross-model adversarial review skill from ticket 01, or the protocol written out there:

- Pick the reviewer by the cross-model rule.
- A reviewer subagent saves its findings to the scratch folder.
- A separate triage subagent checks each finding against the code.
- Apply the valid fixes, rerun `just check`, and record every finding and how it was handled under **Completion notes**.

- **Implementation checkpoint:** before marking done, review the full diff against these acceptance criteria. Pay particular attention to how a denied command is told apart from one that ran and failed, and to triggers that rest on stderr events alone.

## Completion notes

### What was built

- **Denied commands mark the trial (AC1).** `kept_lines` keeps a fourth kind, `sandbox_outcome tool_name=… call_id=… outcome=…`, and `parse_stream` makes any `outcome=denied` an `infra_error` with the reason `Codex reported N command(s) as denied by its sandbox, which the event stream omits; see docs/reference/evals.md`. It is checked after a failed skill load and before `turn.failed`. Why the trial, not a failed `Command`: Codex writes no `command_execution` item for a denied command, and the command's text is only in the `codex.tool_result` record, which the adapter drops whole because it carries raw tool output and account fields. A trace missing commands cannot be scored, the same principle as a truncated stream. A failed `Command` would also still leave `skills_triggered` empty, so a `should_trigger: false` case would pass on a run whose read the sandbox blocked. Any denial counts, including a legitimate one in a working sandbox (a write outside the workspace, say). Codex's denial test is a heuristic (`is_likely_sandbox_denied`, `codex-rs/sandboxing/src/denial.rs` at `rust-v0.163.0`): a nonzero exit whose output contains a permission keyword such as `permission denied` or `sandbox`. Recorded under **Run status** in `docs/reference/evals.md`.
- **Why `skills_triggered == ["cowsay"]` held (AC2).** Codex's own `codex.skill_invocation … implicit` event, which `parse_stream` counted as a trigger on its own. In the pinned source (`openai/codex` tag `rust-v0.163.0`), `core/src/tools/handlers/unified_exec/exec_command.rs:250` calls `maybe_emit_implicit_skill_invocation` while it parses the tool call's arguments, before the command runs. Detection (`skills/src/invocation.rs`) is static on the command text plus a skill-catalog lookup, deduplicated per turn, and tries `detect_skill_script_run` first, so a script run alone (`python3 .agents/skills/cowsay/scripts/cowsay.py`) emits `implicit` too. In the CI log the event (01:23:31.620Z) precedes the `tool_decision` (31.634Z) and the `sandbox_outcome … denied` (31.679Z). The docs' claim that Codex logs it "when it sees a successful read" was wrong, and is corrected.
- **The trigger rule (AC3).** `implicit` counts for its skill only when the JSONL also has a completed command that passes the existing success test (`ok` and `outcome_is_the_read`) and either reads that skill's `SKILL.md` (which triggers on its own) or names a `SKILL.md` the text cannot place (`skills_read` now returns that flag too) and whose output opens with frontmatter whose YAML `name` is the skill (`frontmatter_name`, which reads the block as the validator does). That keeps a read such as `cat SKILL.md` run with the skill's directory as `workdir`, and drops a denied read (no item), a script run with no read, a read of another skill's placed `SKILL.md`, and an unplaced read that printed some other file. `explicit` still triggers alone: Codex injects the file, with no command or sandbox involved. `fake-sandbox-denied` asserts the denied read does not trigger.
- **Fixture (AC4).** `tests/fixtures/evals/codex/fake-sandbox-denied.jsonl` is the event stream of the debug CI run 40614691505 (commits `8fe4d12` and `97fc0ee`): the real pinned 0.163.0 on Ubuntu 24.04 with the AppArmor restriction on, driven by the fake API. `fake-sandbox-denied.log` is `kept_lines` over that run's raw stderr, checked equal once the new branch existed. No Linux machine was needed. `test_codex_parser.py` also holds a raw-stderr excerpt of the same run, showing the `sandbox_outcome` line is kept reduced and the multi-line `tool_result` records, with their `bwrap:` text, are dropped. The tests use no Codex binary and run on any OS.
- `test_codex_adapter.py`'s real-binary trigger test now also asserts that a working sandbox (macOS Seatbelt) logs no `sandbox_outcome` line at all.
- **Contamination: listed skills.** The plan kept `contamination.py` on `skills_triggered` alone, because widening it to `skills_invoked` would fail a trial on any guessed path. Code review (finding 2) showed that this lost evidence: before, every `skill_invocation` event reached `seen` as a trigger, and Codex logs that event only for a skill in its own list. `Trace` gained `listed_skills` (default empty, so Claude Code is unchanged), which Codex fills from every `skill_invocation` event, and step 1 unions it into `seen`. A never-appear skill Codex names, or the skill under test named in a baseline, fails, read or not. Reads alone still do not count.

### Residual risk

- **Unplaced reads pair by printed name.** An unplaced read that starts past the frontmatter (`sed -n '20,60p' SKILL.md` in the skill's `workdir`) backs no event, and a file elsewhere that carries the skill's frontmatter would back it. This assumes Codex's `skill.name` is the frontmatter `name`, which the Agent Skills format requires to match the directory name.
- **Unplaced reads must open with the frontmatter.** Output that concatenates several files backs only the first file's skill, and decorated output never opens with `---`: an unplaced `nl SKILL.md` (`nl` is a reader), `cat -n SKILL.md` or `bat SKILL.md` with its default decorations backs no event. Placed reads are unaffected.
- **Heuristic denials.** Codex reports an ordinary failed command as denied when its output contains a permission keyword, so a skill whose normal flow prints `Permission denied` and exits nonzero is an `infra_error` on every Codex trial.
- **Narrower than before.** A read that Codex flags `implicit` but whose shape fails `outcome_is_the_read` (piped, after `||` or `;`, `2>/dev/null`, `awk`) used to trigger through the event and no longer does. Ticket 06 left those shapes to Codex's event. The recorded live runs used plain `sed -n` and `pwd && sed -n` reads, which still trigger without the event.
- **Toolchain in this session.** The machine's `uv` (0.13.6) and `just` (1.59.0) are newer than the pins, so `just initialize` and `just check` stop at their version gates. The pinned `uv 0.13.4` and `just 1.51.0` were fetched into the project's uv cache (`uvx`, `UV_CACHE_DIR` under `.tools/`) and copied to `.tools/pinned-bin/`, which was put first on `PATH`. Nothing was installed outside the project.

### Code review (`/code-review` high, Claude)

Reviewed `main...fab4667`.

| # | Finding | Verdict | Action |
| --- | --- | --- | --- |
| 1 | Any successful `SKILL.md` read backed every implicit event, including a placed read of another skill or one outside a skills directory | valid | fixed: only the same skill's read or an unplaceable `SKILL.md` backs the event; tests added |
| 2 | Implicit events no longer reached contamination's `seen`, though they show Codex listed the skill | valid | fixed: `Trace.listed_skills`, unioned into `seen`; never-appear and baseline tests added |
| 3 | Any `outcome=denied` makes the trial `infra_error`, and Codex's denial test may be a keyword heuristic | valid in fact, decision kept | confirmed the heuristic in the pinned source; reason, docs and residual risk now say so |
| 4 | Requiring `outcome_is_the_read` for the backing read drops piped and redirected reads | invalid as a defect | the plan's choice: a looser test would let `cat SKILL.md 2>/dev/null \|\| echo missing` back an event. Recorded under residual risk |
| 5 | Ticket marked done without a cross-model review record | valid | the cross-model review runs next and is recorded below |
| 6 | `READERS` comment said an awk read is left to Codex's event | valid | fixed |
| 7 | The real-binary test asserted no `sandbox_outcome` line at all, which a working Linux sandbox may log | valid | fixed: asserts no `outcome=denied` |
| 8 | `reads_a_skill_md` walked the command a third time | valid | fixed with 1: `skills_read` returns both results in one walk |
| 9 | `tool_name` and `call_id` are kept but unread | low, not changed | not account fields; kept for diagnosis, as the docs now say |

### Cross-model review

- **Implementer:** Claude Code running Claude Opus 5.5 (`claude-opus-5-5`)
- **Reviewer:** Codex `gpt-6-astra` (fallback: no)
- **Reviewed:** `main...fda831e`
- **Findings:** `ai_tmp/review-20261031T014909Z-codex.md` · **Triage:** `ai_tmp/triage-20261031T015450Z.md`
- **Runs that did not count:** the first exited 3 because this worktree's `CODEX_HOME` had no login. The second exited 4 because Codex's first start wrote its home setup (`skills/.system/`, `installation_id`, `memories_1.sqlite`) into the monitored `.tools/agent-homes/codex`. Its output (`ai_tmp/rejected-20261030T235820Z-codex.md`) raised the same finding and was not triaged.

| # | Severity | Finding | Verdict | Action |
| --- | --- | --- | --- | --- |
| 1 | high (triage: medium) | One successful unplaced `SKILL.md` read backed every implicit event in the trial, so a failed read of cowsay, or a script run, plus an unrelated `cat SKILL.md` triggered cowsay | valid: the plan accepted this pairing because the trace "cannot tell them apart", but the read's output prints the skill's frontmatter. Exposure today is limited to edge paths: the workspace holds only the skill under test | fixed: an unplaced read backs only the implicit event of the skill whose frontmatter `name:` it printed (`frontmatter_names`); five regression cases added |

**Follow-ups:** none.

#### Round 2

- **Reviewer:** Codex `gpt-6-astra` (fallback: no)
- **Reviewed:** `main...f50414d`
- **Findings:** `ai_tmp/review-20261031T020059Z-codex.md` · **Triage:** `ai_tmp/triage-20261031T021201Z.md`

| # | Severity | Finding | Verdict | Action |
| --- | --- | --- | --- | --- |
| 1 | medium (triage: low) | A YAML comment on the `name:` line (`name: cowsay # the skill`) stayed in the matched name, so a valid skill's unplaced read backed nothing | valid | fixed: the block is parsed with `yaml.safe_load`, as the validator does |
| 2 | medium (triage: low) | Toggling on every `---` line let a Markdown rule in a body misalign the blocks: a later file's frontmatter was skipped, or a body block counted | valid | fixed: only a block that opens the output, after any `pwd` lines, counts. Output that runs several files together counts its first file's frontmatter only; a trial holds one installed skill |

No third round: the skill asks for one re-review when fixes are substantial, and round 2's fixes were narrow.
