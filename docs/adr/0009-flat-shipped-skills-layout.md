# Shipped skills use a flat skills directory

Shipped skills live at `skills/<name>/`; dev skills remain at
`dev-skills/<name>/`. The first shipped skill is `skills/cowsay/`.
Distribution manifests can group skills without adding buckets to their
source paths. A flat layout makes discovery explicit and keeps source paths
stable as the catalogue grows. Supporting files, including templates named
SKILL.md, are resources of their containing skill rather than more skills.

The validator checks direct child directories of both roots. It also checks
empty child directories for a missing SKILL.md, so deleting an entrypoint
cannot silently remove a skill from the gate. Discovery symlinks under agent
directories are not separate sources.
