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

### Cross-model review

- **Implementer:** Claude Code running Opus 5.5 (`claude-opus-5-5`)
- **Reviewer:** Codex `gpt-6-astra` (fallback: no). The first run exited 4 on the known first-run Codex home setup (every changed path under `.tools/agent-homes/codex/`); its output, `ai_tmp/rejected-20261110T003926Z-codex.md`, was not triaged. The rerun succeeded.
- **Reviewed:** `db6fec0...0ad7cf6`
- **Findings:** `ai_tmp/review-20261110T004036Z-codex.md` · **Triage:** `ai_tmp/triage-20261110-renovate.md`

| # | Severity | Finding | Verdict | Action |
| --- | --- | --- | --- | --- |
| 1 | high | The uv group lists `uv_build`, but Renovate matches `matchPackageNames` against the PEP 503-normalized `uv-build`, so the backend would get its own PR | valid | `matchPackageNames` is now `["uv", "uv-build"]`; regression test `test_uv_groups_with_its_build_backend_by_normalized_name` |
| 2 | high | The `github-actions` manager also extracts `setup-uv`'s `version` and `setup-just`'s `just-version` (`uses-with` deps), and the "GitHub Actions" group would bump those CI copies on their own | valid | A rule disables `github-actions` `uses-with` deps; the Actions group is limited to `matchDepTypes: ["action"]`; regression test `test_the_actions_manager_leaves_the_workflow_tool_versions_to_the_regex_managers` |

**Follow-ups:** none from the review. The post-push checks are the open acceptance criterion above.

### Residual risk

- Renovate's own validator has not run; `renovate.json` passes Renovate's published JSON schema (checked with a one-off `jsonschema`).
- To confirm on the onboarding PR: every expected dependency is detected; `engines` and `required-version` are not also proposed natively; Renovate relocks `uv.lock` when the uv group bumps `required-version`; on the Claude Code PR the `allowScripts` key changes before npm relocks under `strict-allow-scripts`; and updates whose datasource has no release timestamp do not wait forever under `minimumReleaseAge`.
