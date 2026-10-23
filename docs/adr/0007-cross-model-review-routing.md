# Adversarial review always comes from a different model family

Before a ticket is done, its work is reviewed by a reviewer from a different model family to the implementer's. A Claude implementer asks Codex, and an OpenAI implementer asks Claude Code. A separate triage pass checks each finding against the code before anything is applied. A model reviewing its own work tends to share the blind spots that produced it. When no reviewer from a different family is available, the work is reported as unreviewed and is not reviewed by the same family.

Ticket 01 (`.scratch/foundation/issues/01-cross-model-review-dev-skill.md`) holds the full protocol, and the repo-internal review skill encodes it.
