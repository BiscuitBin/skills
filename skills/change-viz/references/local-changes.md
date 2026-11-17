# Local changes

The scope is what a description covers: the branch's commits, its uncommitted work, or both. This page gives what the scope line says, how the request chooses the scope, and how to read uncommitted work without writing. Every git command here only reads, and each starts `git --no-optional-locks`, as the main instructions say. `<base>` is the base you found, and `<fork>` the commit the branch forked from.

The examples are invented: a URL shortener whose branch lets people pick their own short links.

## The scope line

The first line of every description, and the whole answer when there is nothing to describe:

```text
**Scope:** `<branch>` against `<base>` · commits: <N> included · staged: included · unstaged: left out · untracked: none
```

- **One fixed form.** `**Scope:**`, the source, then four fields in this order, each after ` · `: `commits:`, `staged:`, `unstaged:` and `untracked:`. The reader finds each field in the same place every time, and a field that is missing leaves them guessing.
- **Three words.** Each field reads `included`, `left out` or `none`. The commits field puts its count first, as `3 included` or `3 left out`, from `git --no-optional-locks rev-list --count <base>..HEAD`; a count of 0 reads `none`.
- **Its own line.** Write it from the left margin, and put a blank line under it in a description, so that it stays a paragraph of its own. It names kinds, never files, so it stays short: about 250 characters at most.
- **Further fields,** such as one a pull request needs, go after `untracked:`, each as `<name>: <value>` after its own ` · `, so the four keep their places.
- **The source** is `` `<branch>` against `<base>` ``. A detached `HEAD` has no branch name, so it is `` detached `HEAD` at `<short commit>` against `<base>` ``. With no base, it is `` `<branch>` at `<short commit>` `` and the commits field reads `none`, since no commits are counted against a base. `git --no-optional-locks rev-parse --short HEAD` prints the short commit.
- **Not on an ask.** A one-line question, such as which base to use, and a report of a source you were unable to read, have no scope line: nothing was described, so there is no scope to report.

Filled in, for a branch four commits ahead of `main`, with a staged fix on top and unfinished edits beside it, when the request asks for the branch and the staged fix:

```text
**Scope:** `custom-aliases` against `main` · commits: 4 included · staged: included · unstaged: left out · untracked: none
```

The reader learns that the four commits and the staged fix are described, that there are unstaged edits this description does not cover, and that there are no new files.

## Which word each field takes

Each field keeps one meaning, whatever the request asked for:

- A kind that does not exist reads `none`.
- A kind the request chose reads `included`, or `none` when it turns out empty.
- A kind that exists but was not chosen reads `left out`, or `<N> left out` for the commits.

So every field reads `none` only when nothing exists at all. A request for one kind that is empty, beside other work, still shows that work as `left out`, and the reader learns there is something else to ask about.

## Choosing what to describe

The request's own words choose, and they may choose several kinds:

- **The commits:** the branch, its commits, what it adds.
- **The staged edits:** staged, the index, what is about to be committed.
- **All the uncommitted work, staged, unstaged and untracked:** uncommitted, not committed, local changes, the working tree, work in progress.
- **One other kind,** when the request names it: unstaged edits, or new files.

Words that name only uncommitted work leave the commits out, even when the branch has some: the person asked about the work on top of them. A request that names both, such as the branch together with its uncommitted work, takes both.

When the request names none, describe the commits since the base if there are any, otherwise all the uncommitted work. With commits, that is what a pull request from here would carry, and work in progress is not part of it; with none, the work in progress is the change. A wrong guess shows in the first line, and costs one more request.

## What the scope leaves out

Name work the scope leaves out in the scope line, by kind, and nowhere else: describe none of it and name none of its files, in the why, the risk call, the notes or the outline. The line has told the reader it is not covered, so a word about it reads as if it were. The risk call rates only what the line includes, as if that alone were merged. The one exception is the sentence that reports a run the request asked for: it names, by kind only, any left-out work on disk that the run used, as the rules on evidence say.

Do not read left-out work at all, not even a summary of it such as `diff --stat`, and do not check or open a new file the scope leaves out. `status` already says which kinds exist, and that is all the scope line needs. What you have read tends to reach the description, and nothing about this work belongs there.

Read every file you open in the state the scope covers, so that left-out work cannot slip in through the code you read for context:

- **The commits without uncommitted work:** as committed, with `git --no-optional-locks show HEAD:path/to/file`. Search with `git --no-optional-locks grep -n -e <pattern> HEAD`, because a search of the files on disk finds uncommitted lines and misses committed ones that an edit removed.
- **Staged edits without the unstaged ones:** the staged version, with `git --no-optional-locks show :path/to/file`.
- **Unstaged edits included:** the files on disk, with the file reader.

Housekeeping files that the system or an editor drops, such as `.DS_Store` or a swap file, and a folder with nothing but an agent's own setup in it, are not the author's work. Do not count them as untracked work, and leave them out of the description. Anything else counts, generated output and data included, and so does a file you are unsure of: leaving out real work misleads the reader more than naming a stray file.

## Reading each kind

Start from `git --no-optional-locks status --porcelain --untracked-files=all`, the record of what changed. Each line gives two status columns, then the path. The first column compares the staged version with `HEAD`, the second compares the working tree with the staged version, and `??` marks a file Git does not track:

```text
M  staged edit
 M unstaged edit
MM both
A  new file, staged
?? new file, untracked
```

`--untracked-files=all` lists each file inside a new folder, where plain `--porcelain` shows only the folder.

Then read each kind the scope includes, and only those. Give every `diff` `-c diff.autoRefreshIndex=false` straight after `--no-optional-locks`: a diff that reads the working tree otherwise refreshes `.git/index`, which writes it, even with the flag. `-c` sets that value for this one command and writes no config. Keep `--no-ext-diff --no-textconv` after `diff`, as everywhere.

- Staged edits, against `HEAD`: `git --no-optional-locks -c diff.autoRefreshIndex=false diff --no-ext-diff --no-textconv --cached`.
- Unstaged edits, against the staged version: the same without `--cached`.
- Staged and unstaged edits together, against `HEAD`: the same without `--cached`, with `HEAD` at the end.
- The commits and the uncommitted edits as one diff: `<fork>` in place of `HEAD`, with `--cached` too when the unstaged edits are left out.

Add `--stat` for a summary first. Trust `status` for which files changed. `--name-only`, `--name-status` and `--raw` can list a file whose content is unchanged and only its timestamp moved, while `-p`, `--stat` and `--numstat` leave such a file out. A file a diff lists and `status` does not is unchanged.

The version before the change is the one the diff compares with: `HEAD`, or the staged version for unstaged edits alone. When the scope leaves the commits out, read the old version there wherever the main instructions say `<fork>`.

A read of the working tree, `status` among them, runs any clean filter the repository sets up for a file, such as Git LFS's. Let it run: Git needs it to see a file's real content.

`add -N` (`--intent-to-add`) and `update-index` are the usual ways to make new files show in `git diff`, and both are out of bounds: they write the index, and the index keeps the author's own choice of what to commit next.

## New files

An untracked file is a new file, and it is in no diff the reader can open, so they learn it is new, and which file it is, only from the description. Name each one as new, by its path, in the sentence that says what it does when someone uses it: what it runs, and what it prints, writes or changes. For example: "`bin/export-links` is a new script: it reads the link table and writes each short link and its target to `links.csv`." A label in another place, such as "a handy export helper" in the why, leaves the reader to guess which file it is and what it does.

`git diff` never shows a new file, so read each one the scope includes itself, after two checks:

1. Its size in bytes: `wc -c < path/to/file`.
2. Whether Git counts it as binary: `git --no-optional-locks ls-files --others --exclude-standard --eol` marks such a file `w/-text`.

Run both checks before any other command touches the file. A type sniffer such as `file`, a pager, `head`, `sed`, `cat` and a diff all print or describe its content, which is what the checks decide whether to read.

Read a text file under 256 KB (262,144 bytes) whole, with the file reader or `cat`. Never read one with `git diff --no-index`: it exits 1 for any file that is not empty, so its output reads as a failure.

Leave a binary file, or one of 256 KB or more, unread. A new file that large is nearly always data, a log or generated output, and reading it would crowd out the change. Give its name and its size in bytes on one line, as digits followed by `bytes`, and say in a note that it is listed by name and size only, so the reader does not take it for checked:

```text
- `docs/redirect-flow.png`, a new image of 48,213 bytes, is listed by name and size only: Git counts it as binary, so nothing here says what it shows.
```

## Nothing to describe

When what you chose is empty, the answer is the scope line alone, with each field as the rules above give it, and nothing else: no heading, no visual and no risk call, since there is no change to rate. If you add a short clause, keep it on the same line. For a request about the branch's commits when none are ahead of `main` and a staged edit exists:

```text
**Scope:** `alias-limits` against `main` · commits: none · staged: left out · unstaged: none · untracked: none
```

The line says what was looked at and that none of it differs, and `left out` shows where there is work to ask about instead.
