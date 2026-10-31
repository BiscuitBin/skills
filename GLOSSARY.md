# Skills

The vocabulary for developing, evaluating and distributing agent skills for Claude Code, Codex and Pi.

## Skills

**Skill**:
A folder with a `SKILL.md` in the Agent Skills format, plus any bundled scripts, references or assets. It is shipped to users for an agent to load when its description matches the task.
_Avoid_: Plugin, prompt, command

**Dev skill**:
A skill used only by agents working on this repository, such as the cross-model review skill. It is never shipped, and it never appears in an eval workspace.
_Avoid_: Internal skill, private skill

**Trigger**:
An agent loading a skill on its own because the request matched the skill's description, as opposed to the user invoking it by name.
_Avoid_: Activation, firing

## Evals

**Eval case**:
One scenario a skill is tested against: a prompt, any input files, and the assertions or rubric that decide whether the outcome is right.
_Avoid_: Test case, scenario, example

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

**Contamination**:
Anything the agent could see during a trial other than the skill under test and the agent's built-in skills, such as this repo's dev skills, other shipped skills or the user's own skills.
_Avoid_: Leakage, pollution
