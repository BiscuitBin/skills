# 14: Claude Code workload identity federation in the live-eval job

**What to build:** the manual live-eval job (ticket 10, `.github/workflows/live-evals.yml`) authenticates Claude Code, for both the agent and the grader, through the Claude API's workload identity federation with GitHub Actions OIDC, instead of the long-lived `CLAUDE_CODE_OAUTH_TOKEN` environment secret. Once it works, that secret is removed from the `live-evals` environment.

Why: a setup token is long-lived and tied to the person who created it, and its spend bills that person's account. The Claude Code docs recommend Console credentials for anything shared. A federation rule scoped to this repository's `live-evals` environment lets only this job get a credential, and only for minutes.

**Blocked by:** foundation 10 (Manual live-eval CI job).

**Status:** ready-for-agent

**Agent requirements:** Any implementing agent (Claude Code or Codex). A Claude Console admin creates the federation rule, and a maintainer approves the dispatches, since the environment requires a reviewer. Cross-model review is also required.

## What is known

These facts come from the docs, as of 2026-11-05. None has been tried here.

- Docs:
  - [Workload identity federation](https://platform.claude.com/docs/en/manage-claude/workload-identity-federation.md)
  - [GitHub Actions provider](https://platform.claude.com/docs/en/manage-claude/wif-providers/github-actions.md)
  - Claude Code [authentication](https://code.claude.com/docs/en/authentication.md)
  - Claude Code [environment variables](https://code.claude.com/docs/en/env-vars.md)
- **Console setup** (admin role): Settings → Workload identity → Connect workload → GitHub Actions. This creates an issuer (`https://token.actions.githubusercontent.com`), a service account (`svac_…`) and a federation rule (`fdrl_…`). Scope the rule to the subject `repo:BiscuitBin/skills:environment:live-evals` and the audience `https://api.anthropic.com`. The docs warn that a rule with no ref or environment constraint also matches fork runs.
- **Variables Claude Code reads:**
  - `ANTHROPIC_FEDERATION_RULE_ID` and `ANTHROPIC_ORGANIZATION_ID`, both required
  - `ANTHROPIC_SERVICE_ACCOUNT_ID`
  - `ANTHROPIC_WORKSPACE_ID`, when the rule covers several workspaces
  - `ANTHROPIC_IDENTITY_TOKEN_FILE`, the path of GitHub's identity token
- **The job needs `id-token: write`.** It fetches the identity token from `$ACTIONS_ID_TOKEN_REQUEST_URL&audience=https://api.anthropic.com`, using the bearer token `$ACTIONS_ID_TOKEN_REQUEST_TOKEN`.
- **Precedence:** `ANTHROPIC_AUTH_TOKEN`, `ANTHROPIC_API_KEY` and `CLAUDE_CODE_OAUTH_TOKEN` all outrank federation. A leftover one silently wins.
- **Token lifetimes:** identity tokens are single-use by default (`jti`) and short-lived (about 5 minutes). A federated access token lasts the rule's `token_lifetime_seconds`.
- **`--bare`** ignores the federation variables.

## The hard part: one identity token per `claude` process

A run starts a separate `claude -p` for every trial and every grader call, dozens of them over up to 90 minutes. Each process exchanges its own identity token, so the harness must give each trial, and each grader call, a fresh token. Settle this with a short spike on a real runner before building:

- Does each `claude -p` exchange once at start, or again during a long trial?
- Can the rule allow reuse within a token's lifetime (no `jti` single use)? If so, at what security cost?
- Should the harness fetch tokens itself, which hands it `ACTIONS_ID_TOKEN_REQUEST_TOKEN`, a credential that can mint identity tokens? Or should a small helper outside the trial fetch them?

## Acceptance criteria

- [ ] The spike's answers to the three questions above are recorded here, with the run that showed them.
- [ ] The Claude Code adapter and the grader take either `CLAUDE_CODE_OAUTH_TOKEN` or the federation settings.
  - A trial's environment, still built from scratch, carries only the credential in use.
  - The identity token file sits inside the trial and is removed at teardown.
  - `results.json`'s `credential_env` names what was used, never a value.
- [ ] No outranking credential (`ANTHROPIC_API_KEY`, `ANTHROPIC_AUTH_TOKEN`, `CLAUDE_CODE_OAUTH_TOKEN`) reaches a federated trial, and a test shows it.
- [ ] The scrub, the trial sweep and `just eval-ci scan` also look for:
  - the identity tokens and the request token
  - any federated access token the run can observe
- [ ] The workflow:
  - The job asks for `id-token: write` and nothing else beyond `contents: read`, and `tests/test_live_evals_workflow.py` is updated to require exactly that.
  - Without the federation settings it falls back to the token secret, and with neither it skips Claude Code and grading as it does today.
  - The rule IDs are environment variables or secrets of `live-evals`, documented as not secret where they are not.
- [ ] `docs/how-to/live-evals-in-ci.md` explains the Console setup, the rule's scope, and which settings go in the environment. ADR 0004 or a new ADR records the decision.
- [ ] Shown working: a dispatch of cowsay on Claude Code with grading, using federation and with `CLAUDE_CODE_OAUTH_TOKEN` removed, produces the artifact. Record the run URL.
- [ ] Unit tests cover the adapter's federated credentials without network. They run in `just check`.

## Out of scope

Codex auth (`OPENAI_API_KEY`), and running Claude Code through Bedrock or Vertex, which change model IDs and billing.

## Review checkpoints

Use the repo's cross-model adversarial review skill from ticket 01, or the protocol written out there:

- Pick the reviewer by the cross-model rule.
- A reviewer subagent saves its findings to the scratch folder.
- A separate triage subagent checks each finding against the code.
- Apply the valid fixes, rerun `just check`, and record every finding and how it was handled under **Completion notes**.

- **Implementation checkpoint:** before marking done, review the full diff against these acceptance criteria. Pay particular attention to the federation rule's scope, credentials reaching a trial or an artifact, and the job's token permissions.
