# Architecture decision records

Each record states one decision that is hard to reverse, would surprise a reader without context, and came from a real trade-off. Records are numbered in order and never renumbered. When a decision changes, add a new record that supersedes the old one.

| Record | Decision |
| --- | --- |
| [0001](0001-local-markdown-tracker.md) | Work is tracked in local Markdown, one ticket per file |
| [0002](0002-python-core-node-tooling-just-front-door.md) | Python is the core, Node carries the tooling, and Just is the front door |
| [0003](0003-project-local-toolchain.md) | Every tool is pinned and installed inside the project directory |
| [0004](0004-eval-tiers-and-ci.md) | Evals run in tiers, and PR CI runs only the free, deterministic ones |
| [0005](0005-distribution-channels.md) | Skills ship through a Claude Code plugin marketplace and `npx skills` |
| [0006](0006-cowsay-example-skill.md) | The first shipped skill is `cowsay`, with a bundled zero-dependency script |
| [0007](0007-cross-model-review-routing.md) | Adversarial review always comes from a different model family |
| [0008](0008-mit-licence.md) | The repository is MIT-licensed |
| [0009](0009-flat-shipped-skills-layout.md) | Shipped skills use a flat skills directory |
| [0010](0010-distribution-boundaries.md) | Each shipped skill is its own plugin; dev skills stay behind discovery symlinks |
