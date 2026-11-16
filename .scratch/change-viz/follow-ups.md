# change-viz follow-ups

What `change-viz` leaves for later. None of these blocks the release.

- **`script_ran`'s command parser lags `python_not_run`'s.** It still misreads `/usr/bin/env python3 scripts/x.py`, `PATH=/usr/bin:/bin python3 scripts/x.py` and `if python3 scripts/x.py; then …`, so it can falsely fail a correct run of a shipped script. Sharing `python_not_run`'s parser would fix it but changes cowsay's scoring (ticket 25, **What is known**; ticket 21, **/code-review at the end of Stage 3**, finding 4).
- **Richer output formats,** such as HTML or artifacts, as an option of this skill or as a separate skill that composes with it (ticket 25, the follow-ups criterion).
- **A skill that creates or updates a pull request description,** built on this one (ticket 25, the follow-ups criterion; ticket 23, **Out of scope**).
- **The maintainer's follow-up tickets** (D5, `ai_tmp/stage3/decisions.md`, **Stage 4 decisions (2026-11-16)**):
  - [26](issues/26-pull-requests-read-live-with-a-read-only-token.md): the four pull requests read live, with a read-only token;
  - [27](issues/27-gh-without-a-login-on-a-linux-host.md): `gh` without a login, on a Linux host;
  - [28](issues/28-render-proof-in-a-github-post.md): the render proof in a GitHub post;
  - [29](issues/29-codex-says-which-way-a-count-moves.md): Codex says which way a changed count moves (E7).

## Residuals from tickets 18 to 24

To be filled in at ticket 25.
