# The first shipped skill is `cowsay`, with a bundled zero-dependency script

The example skill that proves the pipeline end to end is `cowsay`, and its output comes from a script bundled with the skill that has no dependencies. Its output is deterministic, so an eval can compare it exactly against an expected output computed by the harness. A skill built around open-ended prose could only be checked by an LLM grader, which would leave the deterministic tiers with nothing to prove.
