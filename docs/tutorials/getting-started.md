# Getting started

This tutorial takes you from a fresh clone to a green gate. It takes a few minutes, most of it downloading the pinned tools.

## Before you start

Install the host prerequisites listed in the [README](../../README.md#host-prerequisites): just, uv and the exact Node version in `.node-version`, plus Git.

## 1. Clone the repository

```sh
git clone https://github.com/BiscuitBin/skills.git
cd skills
```

## 2. Set it up

```sh
just initialize
```

This downloads the pinned Python into `.tools/python`, installs the Python tools into `.venv/` and the Node tools and agent CLIs into `node_modules/`, and installs the pre-commit hooks. Everything it writes is inside the project directory and ignored by Git. It ends with:

```text
Ready. Next: just check.
Nothing has been staged, committed, tagged, or pushed.
```

## 3. Run the gate

```sh
just check
```

This checks the lockfiles, runs every lint and format check, then mypy, pytest, and prints the version of each pinned agent CLI. When every step passes, your setup matches CI's.

## Next

Run `just` on its own to list every recipe, or read the [commands reference](../reference/commands.md).
