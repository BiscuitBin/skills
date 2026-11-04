# Benchmark history is committed under benchmarks/, one file per named iteration

`just eval-record <name> <run-id>...` writes `benchmarks/<skill>/<name>.json`, and the file is committed. It holds one run per agent: each run's `benchmark.json` and the case list from its `results.json`, nothing else. Transcripts and grading files stay in `eval-results/`, which Git ignores. `just eval-report` reads only `benchmarks/` (plus any `--run` named on the command line), so the report is rebuilt from the repository alone, with no network and no agent.

`eval-results/` cannot hold the history. It is ignored and lives in one worktree, and every ticket here runs in a fresh one: ticket 09 found the only current Claude Code benchmark in ticket 08's worktree. A committed iteration file travels with the branch, shows up in review next to the skill change it measured, and keeps the order and names of iterations in Git. It is small (about 20 KB for cowsay at ten trials) because it holds aggregates, and it holds nothing new: every byte was already scrubbed when the run wrote it.

An iteration is never overwritten, and its runs must test one skill, at one `skill_sha256` and `evals_sha256`, with one run per agent. Two runs that measured different skill versions or case files are two iterations, not one. Iterations are ordered by when their runs started, not when they were recorded, so a run backfilled from another worktree takes its true place.

Regression flags compare each agent's last two benchmarks for the same skill. A comparison across a different case file, agent model or agent CLI version is labelled not like-for-like, as is a graded or outcome metric across a different grader prompt, model or CLI version. A different skill or commit is the change being measured, so it carries no label. A labelled fall is still flagged, and `--fail-on-regression` still fails on it. Otherwise a model bump in the same change as a skill edit would hide the skill's regression.

## Considered options

- **Keep history in `eval-results/`, ignored.** Rejected: it is lost with the worktree, and two branches cannot compare their benchmarks.
- **Commit whole runs, transcripts included.** Rejected: transcripts are large, can hold the user's paths and the agent's output verbatim, and the report needs none of them.
- **One appended `history.json` per skill.** Rejected: two branches that each record an iteration would conflict on every merge. A file per iteration merges cleanly.
- **Exempt not-like-for-like falls from `--fail-on-regression`.** Rejected: it trades false positives for false negatives, and the label already tells a reader why the fall may not be the skill's.
