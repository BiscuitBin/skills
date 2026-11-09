# 15: Renovate configuration

**What to build:** finish Renovate's onboarding branch (`renovate/configure`), which held only a bare `config:recommended` `renovate.json`. That config missed most of the repo's pins, including every copy Renovate's built-in managers cannot read, and failed `just check` on Prettier formatting. The decision is recorded in [ADR 0016](../../../docs/adr/0016-dependency-updates-via-renovate.md).

**Blocked by:** none.

**Status:** in review

**Agent requirements:** Any implementing agent (Claude Code or Codex). Pushing to `renovate/configure` updates Renovate's onboarding PR and needs the user's OK. Cross-model review is also required.

## Acceptance criteria

- [x] `renovate.json` runs weekly (before 6am Monday), proposes only releases at least 7 days old, never automerges, and refreshes both lockfiles monthly.
- [x] Every coupled copy of a pin is tracked under the same dependency name as its original, so one PR bumps every copy: uv (`required-version`, both workflows, README), just (Justfile, both workflows, README), Node and npm (README), and Claude Code's `allowScripts` key.
- [x] uv with `uv_build`, Node, npm and just are each grouped across their copies. GitHub Actions, the Python dev tools and the Node dev tools are grouped by minor and patch; majors stay separate.
- [x] Claude Code and Codex each get their own PR, labelled `agent-cli`, with a checklist covering the postinstall review, eval isolation and benchmark comparability.
- [x] Python minor and major upgrades are disabled; patches are proposed.
- [x] `tests/test_renovate.py` fails when a custom manager stops matching in a file it targets, when coupled copies disagree, or when automerge is turned on.
- [x] ADR 0016 and a "Dependency updates" section in `CONTRIBUTING.md`.
- [x] `just check` passes.
- [ ] After the push (user's OK): the onboarding PR's preview and the Dependency Dashboard show no config errors and detect uv, just, node, npm, both agent CLIs and the actions.

## Review checkpoints

Use the `cross-model-review` dev skill. Pay particular attention to regexes that RE2 or Renovate's template handling would read differently from Python's `re`, and to group rules that could pull an agent CLI into a shared PR.

## Completion notes
