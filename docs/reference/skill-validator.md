# Skill validator

Reviewed rules for ticket 03. Run `just validate-skills` to validate every
source skill; `just check` and CI include this recipe. For a single skill, run
`just run uv run --frozen python -m skills_tooling.validator <directory>`.
Add `--dev` for a dev skill. The public boundaries are a
`validate_skill(path, shipped=...)` function returning diagnostics and a CLI
that discovers shipped skills in `skills/` and dev skills in `dev-skills/`.
Diagnostics include a file, stable rule ID, severity, explanation and fix hint.
The CLI exits nonzero if any error occurs; warnings alone pass.

## Rules

| Rule | Severity | Requirement and rationale |
| --- | --- | --- |
| frontmatter | error | UTF-8 SKILL.md with opening and closing YAML delimiters, a mapping, unique string keys and safe YAML values; malformed data cannot be consumed reliably. |
| discovery | error | Source skill directories cannot be listed; run from the repo root or supply explicit skill directories. CLI invocation fixture covers missing roots. |
| name-format | error | Required string, 1–64 ASCII lowercase letters, digits and hyphens, no edge or consecutive hyphens; portable repo policy. |
| name-directory | error | Name equals the containing directory basename. |
| description | error | Required nonblank string, at most 1024 characters. |
| compatibility | error | If present, nonblank string, at most 500 characters. |
| metadata | error | If present, mapping of strings to strings. |
| field-type | error | license is a string; allowed-tools is a string for shipped skills, a string or string-list for dev skills. |
| field-unknown | error | Only six spec fields or explicitly listed agent extensions. |
| extension-type | error | Extension values match the documented type. |
| extension-portability | error | Shipped skills cannot use an extension known to fail a target loader; unknown support produces a warning, not an invented rejection. |
| body-lines | error | Body under 500 lines, repo-enforced context budget. |
| body-tokens | warning | Approximate tokens = ceiling UTF-8 byte length / 4; warn above 5000, since this is not a tokenizer or spec validity constraint. |
| reference-missing | error | Relative Markdown links/images, HTML href/src attributes and reference-style links resolve to files. Entire concrete inline-code tokens starting scripts/, references/ or assets/ (optionally ./) are references; commands, patterns, placeholders and directory tokens are examples, not file references. Inline bundled paths are skill-root-relative; Markdown links are relative to the referring file. Plain prose is not parsed. |
| reference-escape | error | Referenced filenames must match exact case on every platform. Relative paths, including symlinks, remain inside the skill after resolution; URL decoding precedes checking. Ignore external URLs and fragment-only links. |
| reference-chain | warning | A referenced UTF-8 documentation file (.md, .markdown, .txt or extensionless) contains Markdown references or concrete inline paths to another file. Missing/escaping descendants remain errors at every hop; emit a chain warning and use cycle detection. Skip binary content and source-code formats; linked scripts are checked as files without interpreting code as Markdown. Directory depth itself is unlimited. |
| openai-shape | error | Optional agents/openai.yaml is a mapping: interface string fields, policy.allow_implicit_invocation boolean and products string-list, dependencies.tools list of mappings with type/value strings and optional description/transport/url/command strings plus oauth_callback_port integer 0–65535. Interface keys: display_name, short_description, icon_small, icon_large, brand_color, default_prompt. Reject wrong types and unknown keys (repo policy to catch typos); interface and all sections are optional. |
| claude-description | warning | description plus when_to_use above 1536 characters is truncated by Claude Code. |
| openai-description | warning | If provided, short_description should be 25–64 characters (UI guidance). |

## Agent extension allowlist

Supported means documented consumption; ignored means the pinned loader tolerates
an unknown key, not that the feature works. Shipped skills target Claude Code,
Codex and Pi. Dev skills may use documented extensions. No current evidence
establishes a hard loader rejection in these three CLI targets; do not confuse
Claude's upload/packaging validators with Claude Code's loader.

| Fields | Type | Claude Code | Codex | Pi |
| --- | --- | --- | --- | --- |
| disable-model-invocation | boolean | supported | ignored | supported |
| user-invocable | boolean | supported | ignored | ignored |
| when_to_use, argument-hint, model, agent, shell, effort | string | supported | ignored | ignored |
| context | string (fork) | supported | ignored | ignored |
| arguments, paths, disallowed-tools | string or list of strings | supported | ignored | ignored |
| hooks | mapping | supported | ignored | ignored |

Keep acceptance/rejection status in data separate from type checks. Unsupported or unknown
semantics for an extension on shipped skills warns and suggests spec fields or
agents/openai.yaml. New evidence of rejection upgrades this to an error.

## Discovery, fixtures and reference comparison

Choose flat `skills/<name>/` for shipped skills; grouping can be expressed in
future distribution manifests without nesting. Record this in a new layout ADR.
Discover direct child directories under both roots, requiring their SKILL.md.
Nested SKILL.md assets stay resources. Bucket directories fail with a frontmatter diagnostic naming the missing SKILL.md entrypoint and a creation hint; do not scan tool caches, fixtures or discovery symlinks elsewhere.

Use one broken-skill fixture per stable rule and assert its diagnostic via the
public function. CLI tests assert file/rule/hint output and nonzero status.
Compare shared-rule fixture verdicts to PyPI skills-ref==0.1.1, locked in uv.lock.
Document intentional differences: ASCII names (reference accepts Unicode/NFKC
and trims surrounding whitespace); nonempty compatibility (reference accepts
empty); strict string metadata and scalar types (reference does not enforce
all types); documented agent extensions and dev allowed-tools lists; safe flow YAML accepted here but rejected by strictyaml in skills-ref. Duplicate keys fail in both parsers. Reference validation
does not cover budgets, file references or openai.yaml.

## Sources checked 2026-10-23

- [Agent Skills specification](https://agentskills.io/specification)
- [skills-ref validator](https://github.com/agentskills/agentskills/blob/main/skills-ref/src/skills_ref/validator.py)
- [Claude Code frontmatter](https://code.claude.com/docs/en/skills#frontmatter-reference)
- Pi 1.4.0: node_modules/@earendil-works/pi-coding-agent/dist/core/skills.js;
  unknown keys ignored and disable-model-invocation read as a boolean.
- Pinned Codex [parser.rs](https://github.com/openai/codex/blob/rust-v0.163.0/codex-rs/skills/src/parser.rs) ignores unknown fields.
- Pinned Codex [model.rs](https://github.com/openai/codex/blob/rust-v0.163.0/codex-rs/skills/src/model.rs) and [interface.rs](https://github.com/openai/codex/blob/rust-v0.163.0/codex-rs/skills/src/interface.rs) define UI metadata.

YAML parsing and reference Markdown parsing should use pinned libraries rather
than a homegrown YAML parser. The cowsay script itself uses only Python's standard
library and accepts text from stdin or one argument, wraps at 40 code points,
preserves explicit line breaks and emits one deterministic trailing newline.

The byte/4 token heuristic is English-oriented and can over- or underestimate
multilingual content; it only warns. Current target CLI loaders have no known
rejected allowlisted extension. The conditional rejection policy is tested
with explicitly synthetic agent evidence, not a fictitious real agent claim.

Reference comparison fixtures live in tests/fixtures/validator/: cases.json
has one broken or warning fixture per diagnostic rule, and reference-cases.json
records exact verdicts for shared syntax and intentional parser differences.
The suite materializes each definition as a real skill directory.
