# 28: Render proof in a GitHub post

**What to build:** ticket 24's render proof. Recorded outputs of the released skill, at least one per diagram type it uses plus a table and the risk line, are posted in one GitHub comment or pull request description, and every block is shown rendering. The maintainer approves the place and the exact text first, or posts it.

Why: the repository checks Mermaid offline against a pinned Mermaid (D3), and GitHub does not publish the Mermaid version it runs. That check also reads only `mermaid` fences, not tables or the risk line. Only a real post shows what a reader of a pull request sees. The maintainer made it a follow-up, not a release blocker (D5, `ai_tmp/stage3/decisions.md`, **Stage 4 decisions (2026-11-16)**).

**Blocked by:** 24 (Output renders on GitHub) and 25 (Review with the maintainer, then ship). The outputs posted are the released skill's.

**Status:** needs-maintainer

**Agent requirements:** Any implementing agent (Claude Code or Codex). Posting to GitHub is outward-facing: the maintainer posts the comment, or approves the exact text and place before the agent posts it. Cross-model review is also required.

## What is known

As of 2026-11-16.

- **The offline check (D3, plan Phase 1):** a repository dev tool, `scripts/check-mermaid.mjs` behind `just check-mermaid`, renders each `mermaid` fence with the official Mermaid CLI, `@mermaid-js/mermaid-cli`.
  - It is pinned at Mermaid 12.2.0, the version GitHub's viewer bundle hard-coded in one snapshot, taken on 2026-11-10.
  - Its limit: GitHub's Mermaid version is unpublished, so the check is against the pinned version, not GitHub's.
- **No eval case produces a state diagram,** so the post needs one from another output (ticket 24, **Residual risk**, **At Stage 4**). Ticket 24's cases ask for a flowchart and a sequence diagram.
- **The risk line** uses 🟢, 🟡 and 🔴 (ticket 24, **What is known**).
- **Where to post** is not yet chosen. Ticket 24 allows one comment or one pull request description.

## Acceptance criteria

- [ ] The post holds recorded outputs of the skill: at least one per diagram type it uses, a table, and the risk line.
- [ ] The place and the exact text are approved by the maintainer before anything is posted, or the maintainer posts it.
- [ ] Every block renders on GitHub. The link is recorded here, with a note of anything that failed and was fixed.
- [ ] Each Mermaid block in the post is also run through `just check-mermaid`. Any block where GitHub and the pinned check disagree is recorded here, with both results.
- [ ] A break the post shows is fixed in the skill's rules by its general reason, or carried to a new ticket.

## Out of scope

Rendering anywhere but GitHub pull request descriptions and comments, HTML and image output, and a checker bundled with the skill (`ai_tmp/stage3/decisions.md`, row 7: "rules only").

## Review checkpoints

Use the `cross-model-review` dev skill.

- **Before posting:** review the draft post against these acceptance criteria. Pay particular attention to a proof that covers fewer constructs than the skill emits.
