# Reading the branch

The cases that finding the base leaves open, and how to read a large branch. Every command here only reads, and each starts `git --no-optional-locks`, as the main instructions say. `<base>` is the base you found.

## The candidates in full

- Local `main` and `master`, and `origin/main` and `origin/master`, when they exist.
- The branch that `git --no-optional-locks config --get init.defaultBranch` names, when a branch of that name exists here. It is the default this machine gives new repositories, which is often what a repository with no remote uses. `git --no-optional-locks rev-parse --verify --quiet <name>` prints a commit only when that branch exists, so it tells you whether the name is real here without an error message.
- For each remote that `git --no-optional-locks remote` lists, the branch its `HEAD` points at: `git --no-optional-locks symbolic-ref --quiet --short refs/remotes/origin/HEAD` prints `origin/main`, for example. A clone has one. A repository made with `git init` has none, and the command then prints nothing and exits 1.

## When there is no clear base

Each one-line answer here also says that uncommitted changes to the project's files exist, when `git status` listed any.

- **No candidate exists.** There is no default branch to compare with. Say so in one line, list the local branches (`git --no-optional-locks for-each-ref --format='%(refname:short)' refs/heads`), and ask which one is the base. A guessed base describes the wrong commits.
- **The current branch is the default branch.** It cannot be its own base. A remote's default branch, such as `origin/main`, is still a candidate, and the description then covers the commits not yet pushed. With no remote there is no base: say so in one line and ask for one.
- **`HEAD` is detached.** `rev-parse --abbrev-ref HEAD` prints `HEAD`. Find the base as usual, and say in a note that the description is of a detached `HEAD` at its short commit id, since there is no branch name to give.
- **Nothing is ahead.** The count is 0, so there are no commits to describe. Say so in one line that names the branch and the base, and stop. Three headings over an empty change send the reader looking for something that is not there.

## A large branch

Start from `git --no-optional-locks diff --stat <base>...HEAD` and the commit messages, which show where the weight of the change is. Read in full the files that carry the change. When the whole diff is too long to read at once, read it a path at a time with `git --no-optional-locks diff <base>...HEAD -- path/to/file`, rather than saving it to a file. Name generated files, lockfiles and vendored code in passing, if at all: they rarely change what a reader needs to know.
