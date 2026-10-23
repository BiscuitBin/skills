# Ticket-set review log

On 2026-10-22, Codex (`gpt-6-astra`, codex-cli 0.163.0) gave the ticket set a cross-model adversarial review. It was read-only and ephemeral. A separate subagent then triaged the findings against the ticket text and the research notes. The raw findings and triage are in `ai_tmp/`, which is not committed. Ticket 02 adds it to `.gitignore`.

The review raised 28 findings: 10 valid, 16 partly valid, 1 invalid and 1 out of scope. Every valid and partly valid finding was applied.

| ID | Verdict | What changed |
| --- | --- | --- |
| F1 | valid | 05: isolate the user home as well as the agent home. The contamination check allows the agent's built-in skills, plants canaries in every discovery location, and fails closed. 06, 07: canaries in the OS-home shared folder. research: corrected the `--bare` claim. |
| F2 | partly | 05: repo context files must not load. The workspace holds no expected outputs. "Discovery, not file access" is recorded as a known limit. research: same caveat. |
| F3 | partly | 05: credentials are minimal, kept out of results, and removed on exit. A fake-secret test proves it. |
| F4 | partly | 10: inputs are validated and passed as data, trial count has a cap, minimum permissions, secrets in a deployment environment. |
| F5 | partly | 01: a Pi or other implementer picks its reviewer by the model family it is actually running. |
| F6 | partly | 01: the reviewer subagent writes the findings, never the external reviewer. Read-only is enforced by CLI flags and checked by comparing content. |
| F7 | valid | 01, 04: dev-skill placement must stop the dev skill showing up in `npx skills` listings. 04 asserts this and records the choice in an ADR. research: installer scanning notes. |
| F8, F14 | valid | 05: exact-output assertion, with the expected output computed by the harness. 08: the baseline delta counts outcome assertions only, and a positive delta is no longer required. |
| F9 | valid | 06, 07: explicit invocation detected separately, because Pi's `/skill:` makes no read call. research: Pi expansion note. |
| F10 | valid | 05: crashed or timed-out runs are infrastructure errors and are never scored. 06, 07: only completed reads count. |
| F11 | partly | 03 is now blocked by 01, which gives 04, 05 and 12 a dependency path to 01. |
| F12 | invalid | No change. 06 and 07 already update every adapter, and 09 is the integration gate. |
| F13 | valid | 08: the grader is blinded (skill calls removed), treats graded material as data, and has a prompt-injection fixture. |
| F15 | valid | 08, 09: "trigger rate" replaced by trigger accuracy, with fixtures for should-trigger and should-not-trigger cases. |
| F16 | partly | 08: record the commit, dirty flag, and hashes of the skill and cases. 09: label comparisons that are not like-for-like. |
| F17 | partly | 10: changed-skill selection rules defined against the merge base. |
| F18 | valid | 10: check grader credentials, with deterministic-only fallback. |
| F19 | valid | 04: install from a clean committed copy as a cached install. |
| F20 | partly | 04: name the exact version fields. 11: the release process matches a real recipe or is stated as manual. |
| F21 | partly | 03: "one level deep" means reference chains, not directory depth. research: ASCII-only names are repo policy. |
| F22 | partly | 03: the allowlist records which agents accept each field. A field any agent rejects is an error in a shipped skill. |
| F23 | partly | 05: `just check` validates case files against the schema. 11: warn on shipped skills with only placeholder cases. Whether that warning should be an error is the user's call. |
| F24 | partly | 05: case input files are either staged or explicitly rejected. |
| F25 | partly | 02: the README lists host prerequisites. |
| F26 | partly | 01: reviewer and triage are told not to start their own reviews. Completion notes record the reviewer model and the commit reviewed. |
| F27 | out of scope | The 12-ticket breakdown is fixed. Ticket 05 is now the largest, at about 87 lines, and is the main size risk. |
| F28 | partly | 12: unmet mandatory criteria stay open until the user confirms them, instead of being moved to follow-ups. |
