# The LLM grader runs on the pinned Claude Code, and failures it can be blamed for count against the trial

Rubric expectations are graded by Claude through the pinned Claude Code CLI, with no tools, the run's `CLAUDE_CODE_OAUTH_TOKEN` and a configurable model (default `claude-opus-5-5`), whatever agent ran the trial. That adds no dependency and no new credential, and the local fake API tests it end to end in `just check`. The grader sees the final message and output files with trial paths and skill-install prefixes removed, and the harness records, rather than rewrites, any prose that names the arm.

Graded material is untrusted, so the rules lean against the trial. The harness slips a known-false canary expectation in among the real ones. A pass must quote the material verbatim. A grading whose canary passed, or whose reply fails validation, counts as failed. Only a grader call that returned no reply at all is excluded from the denominators, because the material cannot cause that through the reply. An empty reply is a reply, and counts as failed. Material that drives the grader into its timeout or budget cap is a residual risk: such a trial is excluded, but counted for each arm. The benchmark reports n beside every mean, leaves stddev null below two trials, counts every exclusion, and claims no significance. With the handful of trials a live run can afford, a test would overstate certainty.

## Considered options

- **The Anthropic SDK directly.** It would add a dependency and a second way to hold the credential, for no gain over the pinned CLI.
- **Excluding invalid replies like transport failures.** Rejected after the design review: material that breaks the reply format would remove its own failing trial from the benchmark.
- **Rewriting arm-revealing prose before grading.** Rejected: it changes the outcome being judged and breaks the verbatim-quote rule. Such trials are flagged and counted per arm instead.
