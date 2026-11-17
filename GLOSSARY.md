# Skills

The vocabulary for developing, evaluating and distributing agent skills for Claude Code and Codex, and for the change descriptions the `change-viz` skill writes. Pi can install the skills but is not yet evaluated.

## Skills

**Skill**:
A folder with a `SKILL.md` in the Agent Skills format, plus any bundled scripts, references or assets. It is shipped to users for an agent to load when its description matches the task.
_Avoid_: Plugin, prompt, command

**Dev skill**:
A skill used only by agents working on this repository, such as the cross-model review skill. It is never shipped, and it never appears in an eval workspace.
_Avoid_: Internal skill, private skill

**By-name-only skill**:
A skill that loads only when the user invokes it by name, never because a request matched its description. `change-viz` is one.
_Avoid_: Manual skill, explicit-only skill

**Trigger**:
A trial's recorded evidence that the agent loaded a skill: on its own because the request matched the skill's description, by name because the prompt invoked it (`/<name>` in Claude Code, `$<plugin>:<name>` in Codex), or by a read of its `SKILL.md` that the trace confirms. Not every load leaves such evidence, and a confirmed read can count without printing the skill's text.
_Avoid_: Activation, firing

## Change descriptions

**Change source**:
One kind of change a `change-viz` description can cover: a branch's commits since its base, uncommitted work, or a pull request.
_Avoid_: Diff target, diff source

**Scope**:
The change sources one `change-viz` description covers, with uncommitted work told apart as staged, unstaged and untracked edits. The skill's own text says scope, never change source.
_Avoid_: Coverage, selection

**Scope line**:
The first line of a `change-viz` description: what it was read from, such as a branch against its base or a pull request, which the skill calls the line's source, then whether the commits and each kind of uncommitted work are included, left out or absent.
_Avoid_: Header line, summary line

**Risk call**:
The line under a `change-viz` description's why sentence that gives the merge a risk level, a door and a blast radius, with two bullets: why that level, and how to walk the merge back.
_Avoid_: Risk section, risk score

**Door**:
Whether reverting a merge undoes everything the merge set off: two-way when it does, one-way when something outlives the revert, such as rewritten data or a published release.
_Avoid_: Reversibility

**Blast radius**:
Who or what is affected if a change, as written, turns out to be a mistake: the people or things whose results change, never the files that changed.
_Avoid_: Impact

**Evidence label**:
The words straight after a runtime claim, a claim about what code does when it runs, that say where the claim comes from: read from the code, or observed in a run, a commit message or a CI check.
_Avoid_: Provenance tag, source note

**Change outline**:
The last section of a `change-viz` description, which shows the shape of the change in views, each under its own lead-in.
_Avoid_: Change list

**View**:
One kind of visual a change outline is built from, each drawing one kind of structure, such as a diff sketch, a file tree or a Mermaid flowchart.
_Avoid_: Chart, figure

**Lead-in**:
The one line above a visual in a change outline, which says what the whole visual draws and then what to notice in it.
_Avoid_: Caption, intro

**Ceiling**:
The most characters a `change-viz` description may use, set by the shape of its change: a limit, not a target.
_Avoid_: Length budget, target

## Evals

**Eval case**:
One scenario a skill is tested against: a prompt, the fixture its trials start in if it has one, and the assertions or rubric that decide whether the outcome is right.
_Avoid_: Test case, scenario, example

**By-name case**:
An eval case whose skill arm invokes the skill by name, in the agent's own syntax, while the baseline arm and the grader get only the bare request.
_Avoid_: Slash case, invocation case

**Quiet case**:
A should-not-trigger case for a by-name-only skill: a plain request that invokes nothing, whose trials must record no trigger.
_Avoid_: Silent case, unnamed case

**Fixture**:
A small project with Git history, a branch checked out and any uncommitted edits, that an eval case's trials start in, the same in both arms.
_Avoid_: Input files, seed repo, test repo

**Placeholder case**:
A starter eval case that a new skill begins with, standing in for a real case the author has not written yet. It is never run, so it can never pass.
_Avoid_: Stub case, sample case, unwritten test

**Trial**:
One attempt by one agent at one eval case, in its own fresh workspace.
_Avoid_: Attempt, sample, rollout

**Run**:
A batch of trials started together with one configuration: the agents, skills, cases, trial count and pinned versions.
_Avoid_: Session, job, sweep

**Adapter**:
The part of the harness that drives one agent CLI headlessly and translates its event stream into the harness's common trace.
_Avoid_: Driver, runner, connector

**Grader**:
Whatever scores a trial against its eval case: a deterministic assertion, or an LLM judging the trace against a rubric.
_Avoid_: Judge, scorer, evaluator

**Baseline**:
The same eval case run with no skill installed, so a skill's effect is measured as the difference.
_Avoid_: Control, without-skill run

**Arm**:
One side of the comparison a run makes: the skill arm, with the skill installed, or the baseline arm, with nothing installed.
_Avoid_: Configuration, condition, variant

**Expectation**:
One statement in an eval case's rubric that an LLM grader judges true or false from what the trial produced.
_Avoid_: Criterion, check, rubric item

**Canary expectation**:
A known-false expectation the harness slips in among the real ones, so a grader that passes it is shown to have been subverted.
_Avoid_: Control expectation, honeypot

**Benchmark**:
A report that aggregates the trials of one or more runs across agents, skills and baselines, with means and spread.
_Avoid_: Leaderboard, scoreboard

**Iteration**:
A named benchmark recorded into the skill's history, holding one run per agent, so the report can show how each metric changed from one iteration to the next.
_Avoid_: Version, snapshot, release

**Regression**:
A metric that fell by more than the report's threshold between an agent's last two benchmarks of the same skill.
_Avoid_: Failure, drop

**Changed skill**:
A skill with an eval suite whose skill or eval files changed since the merge base with main; a change to the shared eval code or the pinned agent CLIs changes every one.
_Avoid_: Affected skill, dirty skill

**Contamination**:
Anything the agent could see during a trial other than the skill under test and the agent's built-in skills, such as this repo's dev skills, other shipped skills or the user's own skills.
_Avoid_: Leakage, pollution
