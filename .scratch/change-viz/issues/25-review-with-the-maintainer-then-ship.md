# 25: Review with the maintainer, then ship

**What to build:** the finished `change-viz` skill is run on real changes, the maintainer reads what it wrote and says what is wrong, and the skill is corrected, benchmarked, reviewed as a whole and released. This is the human review step that the repo's `just eval` loop does not have on its own, and the last gate before the skill is called done.

Why: every earlier ticket checks one behaviour against small fixtures. Whether the whole description gives the maintainer "confidence and understanding" on a real change is a judgement only they can make.

**Blocked by:** 19 (Merge risk), 20 (Choosing visuals), 21 (Evidence), 22 (Local changes), 23 (Pull requests as a source), 24 (Output renders on GitHub).

**Status:** ready-for-agent

**Agent requirements:** Any implementing agent (Claude Code or Codex). The maintainer reads the outputs and gives feedback, runs the live evals in their own terminal, with the token, and has the `gh` login the pull request runs need. Cross-model review of the whole skill is also required.

## What is known

As of 2026-11-10.

- **The four pull requests the maintainer likes**, all public, each written in a session with the `show-me` and `visual-pr` personal skills:
  - BiscuitBin/knarr#75, "README for chart users, with a How it works diagram" (15 files)
  - BiscuitBin/skills#1, "Add foundation tickets for the skills repo" (14 files)
  - BiscuitBin/skills#4, "Add cowsay skill and skill validation gate" (31 files)
  - BiscuitBin/rove#11, "PROTOTYPE, do not merge: crawl4AI in a Smol Machines microVM" (13 files)
- **Those descriptions had more to work with.** The agent that wrote each one had just done the work, and quotes command output and timings from its own session. A read-only run of `change-viz` on the same diff cannot reproduce that, so the comparison is of shape, choice of visuals and risk call, not of evidence.
- **This repository's own changes cannot be eval material**, because the grader flags the word `skill` as disclosing the arm. Reading the skill's output on skills#1 and skills#4 by hand involves no grader, so it is fine here.
- **The skill is by-name-only**, so skill-creator's description optimisation does not apply.
- **Benchmarks:** `just eval-record` writes one iteration from one run per agent, and both runs must share the same `skill_sha256` and `evals_sha256` (ADR 0014).

## Acceptance criteria

- [ ] The skill is run on the changes behind each of the four pull requests, and on each fixture the suite uses:
  - knarr and rove are cloned under `ai_tmp/`, and the two skills pull requests are read from a clone there too, so nothing here changes this checkout.
  - Each is run as a branch against its base and, where `gh` works, as a pull request.
  - The runs use the project's pinned agent CLIs through `just run`, with the skill installed into the clone as a user would install it. Nothing is written to the maintainer's own agent homes.
  - Each output is saved under `ai_tmp/`, beside the pull request's original description.
- [ ] The maintainer reads each output beside the original and gives feedback. Their words are recorded here, by output.
- [ ] Each piece of feedback is applied by finding the general reason behind it and changing what the skill explains. No rule is added that only makes sense for one of the four. The notes say, for each, what changed and why it generalises, or why it was not applied.
- [ ] After the changes, the outputs are regenerated and the maintainer confirms the result, or a second round is recorded.
- [ ] The full suite passes on Claude Code and Codex with `--baseline`, and the two runs are recorded as a benchmark iteration with `just eval-record`. The file it writes is committed, and `just eval-report change-viz` builds.
- [ ] A cross-model review covers the whole skill as a user would install it: `SKILL.md`, every reference, any script, the eval suite and the fixtures. It is not limited to this ticket's diff.
- [ ] The version is set for release, by semver, and agreed with the maintainer: whether this is `1.0.0` or stays below it.
- [ ] Docs are current: `README.md`, `docs/reference/distribution.md`, and anything the earlier tickets changed in `docs/reference/evals.md`, `GLOSSARY.md` and the ADRs. Each term the tickets added is used the same way everywhere.
- [ ] Follow-ups are written to `.scratch/change-viz/follow-ups.md`, including:
  - richer output formats (HTML, artifacts), as this skill's option or as a separate skill that composes with it
  - the skill that creates or updates a pull request description, built on this one
  - every residual the earlier tickets recorded, such as a "does not" outcome with no automated check
- [ ] `just format` has run, the changes are committed, and `just check` passes.

## Out of scope

Building either follow-up, new behaviours the maintainer's feedback asks for that are larger than a correction (each becomes a ticket), and merging the pull request, which the maintainer does.

## Review checkpoints

Use the `cross-model-review` dev skill.

- **Maintainer checkpoint:** the review of the outputs, above. Do not record the benchmark iteration or start the whole-skill review until the maintainer has confirmed the regenerated outputs.
- **Implementation checkpoint:** before marking done, review the whole skill against the acceptance criteria of tickets 18 to 24 as well as this one. Pay particular attention to instructions added for one of the four pull requests, to rules that contradict each other across references, and to anything the skill tells an agent to do without saying why.
