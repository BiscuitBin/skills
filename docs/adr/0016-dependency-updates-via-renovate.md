# Renovate proposes every pin bump; a person merges each one

Every version in this repository is pinned exactly ([ADR 0003](0003-project-local-toolchain.md)), so nothing moves unless someone bumps it. Renovate proposes those bumps as pull requests. `renovate.json` holds the configuration.

- **Cadence.** Renovate runs before 6am on Mondays and proposes only releases that are at least 7 days old (`minimumReleaseAge`, with `internalChecksFilter: strict`), so a release pulled in its first week never reaches a PR. Lockfile maintenance refreshes the transitive dependencies in `uv.lock` and `package-lock.json` on the first day of each month.
- **Never automerged.** Every PR waits for a person. CI on both operating systems is the floor, not the review. `tests/test_renovate.py` fails if `automerge` is turned on anywhere in the config.
- **Coupled pins.** Several pins have copies that Renovate's built-in managers do not read: uv in `required-version`, the workflows' `setup-uv` step and the README; just in the Justfile's `just-version` recipe, the workflows and the README; Node and npm in the README; and Claude Code in the `allowScripts` key. A regex custom manager tracks each copy under the same dependency name as the original, so a bump changes every copy in one PR. A missed copy would fail the gate (`required-version`, `just-version`, `engine-strict`) or `npm ci` (`strict-allow-scripts`). `tests/test_renovate.py` asserts that each custom manager still matches in every file it targets and that the copies agree, so a reworded README row or workflow step fails `just check` instead of silently dropping out of Renovate's view.
- **Groups.** uv and `uv_build` (matched as `uv-build`, the normalized name Renovate compares), Node, npm and just each get one PR across their copies. GitHub Actions updates, the Python dev tools and the Node dev tools are grouped by minor and patch. Majors stay separate PRs.
- **Agent CLIs.** Claude Code and Codex each get their own PR, labelled `agent-cli`, with a checklist in the PR body: read Claude Code's new postinstall, which `allowScripts` approves by version; re-check eval isolation ([eval isolation](../explanation/eval-isolation.md)), including the skill locations Codex scans; and remember that the report labels benchmarks across a CLI bump not like-for-like ([ADR 0014](0014-benchmark-history.md)).
- **Python.** Renovate proposes only patch releases of the interpreter in `.python-version`. A minor or major upgrade also moves `requires-python`, ruff's `target-version` and mypy's `python_version`, so it stays a manual change.

## Considered options

- **Dependabot.** Rejected: it has no regex managers, so the README, Justfile, workflow and `allowScripts` copies would need a hand-written script, and it cannot group a pin's copies across ecosystems.
- **Automerge for patch releases and digests.** Rejected: an agent CLI or a dev tool can change eval behaviour or the gate's verdicts in a patch release, and CI does not run the live evals ([ADR 0004](0004-eval-tiers-and-ci.md)).
- **No minimum release age.** Rejected: an exact pin to a release that is later yanked or compromised lands in every contributor's install.

## Limits

Renovate's own config validator is not pinned here, so `renovate.json` is checked against Renovate's published JSON schema by hand, and proven only by the onboarding PR's preview and the Dependency Dashboard. The `github-actions` manager also reads `setup-uv`'s `version` and `setup-just`'s `just-version` (dep type `uses-with`), which would bump the CI copies on their own, so those deps are disabled and left to the regex managers. Whether `engines` or `required-version` is also detected natively, and proposed twice, is confirmed on the onboarding PR.
