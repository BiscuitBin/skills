# Evals run in tiers, and PR CI runs only the free, deterministic ones

The eval harness has four tiers: structural checks of each skill, deterministic assertions over an agent's output, rubrics graded by an LLM, and benchmarks that compare a skill against a baseline over several trials. PR CI runs only the static and deterministic tiers, which need no secrets and give the same answer every time. Live evals call paid models and vary from run to run, so they run locally through `just eval` or from a manual `workflow_dispatch` job that holds the secrets.

Running live evals on every PR was rejected. It would put secrets within reach of pull requests from forks, cost money on every push, and make the required check flaky.
