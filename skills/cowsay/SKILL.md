---
name: cowsay
description: Render an ASCII cow saying the user's text in a speech bubble. Use when asked for a talking cow, a cow saying something, or cowsay output. Excludes animal facts and unrelated ASCII art requests.
license: MIT
compatibility: Requires Python 3 on macOS or Linux.
---

# Cowsay

Run the bundled [cowsay script](scripts/cowsay.py) with the user's text as
one quoted argument, using `--` before the text so leading hyphens are safe:

```sh
python3 <skill-directory>/scripts/cowsay.py -- 'Hello there'
```

Resolve `<skill-directory>` to this skill's installed directory. For text with
complex quoting or multiple lines, pass the exact UTF-8 text through stdin
with no positional argument. Use `printf '%s' 'the text'` rather than `echo`
or a heredoc to avoid adding a newline; preserve any newline the user requested.
Empty text is valid; pass `-- ''`.

Show the script's stdout verbatim in a fenced text block, preserving spaces,
line breaks and backslashes. Use the printed cow rather than drawing one
freehand. The script wraps at 40 Unicode code points; wide glyphs may occupy
more than one terminal column.
