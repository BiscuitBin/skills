# Merge risk

The risk call under the why sentence, the risk line and its two bullets, tells the reader how closely to review before they look at anything else: whether a mistake in the change could be undone, and who it would reach. It is a report for the reader, not a gate: it says what merging risks, and whether to merge stays their decision.

## The shape

- **The risk line:** `**Risk: <level>** · **Door: <door>** · **Blast radius: <radius>**`, all on one line from the left margin. The level is `🟢 Low`, `🟡 Medium` or `🔴 High`, with the emoji written as characters. The door is `one-way` or `two-way`. The radius is at most eight plain words, with no emphasis inside its bold field.
- **A blank line above it.** Without one, the line joins the why sentence's paragraph, and a reader who stops at the sentence reads the call as part of it.
- **Nothing after the line's closing `**`.** Anything more belongs in a bullet.
- **Then exactly two bullets,** each on one line, with a plain label: `- Why <level>:`, with the level in lower case, then `- Walk it back:`. Neither carries a sub-list.
- **Once, under the why, with no heading of its own.** A second call, or a risk section at the end, gives the reader two places to look and two answers to reconcile.
- **Only in a description.** An answer that is not a description, such as a one-line question about the base or the scope line alone when there is nothing to describe, carries no call.

## What the call rates

Rate what the scope line includes, as if it alone were merged: that is what the description puts in front of the reader. Work the line leaves out, such as uncommitted edits beside the commits it covers, is not part of the call: neither bullet weighs it or names its files.

A change framed as a gain, such as a speed-up or a fix, still gets its call. What merging risks does not depend on how the change is told.

## The door

You can walk back through a two-way door, but not through a one-way door. The door is two-way when reverting the merge undoes everything the merge set off, and one-way when something outlives the revert. A change that is cheap to walk back is lower risk, whatever it touches.

First find out what merging into the base sets off. The files that decide it are often untouched by the branch, so the diff does not show them, and many sit under hidden paths, which most file searches skip unless told otherwise. So list the project's files from git itself: `git --no-optional-locks ls-tree -r --name-only HEAD` prints every tracked path, hidden ones included. Then read every file that defines what runs when the base changes: CI that runs on a push to the base, release or deploy scripts, install instructions, and anything else that reads the base. A version number the branch changes is a strong sign that merging publishes something, so find what reads that version. Read with the same read-only commands as the rest of the branch; nothing is fetched, built or run. Say that nothing ships from the base only after a search that could have found it, and keep the call to what you read.

| What merging sets off | Why a revert does not undo it |
| --- | --- |
| Stored data deleted or rewritten, such as by a migration that runs on data people already have | A revert restores the code, not the data, and the old code may not even read what the new code wrote. |
| A format or interface published that others store or build on | Others have already written files or calls in the new form, so a revert breaks them a second time. |
| Something that reaches people outside the repository and stays with them: a version they install, a build others deploy, a message sent | A revert changes what goes out next, not what was already delivered. |

For a case the table does not name, ask the same question: after a revert, is anything still different from before the merge? A project people run from a checkout of the base is not installed: a revert reaches them on their next pull, so that alone leaves the door two-way.

When merging ships something, the blast radius names who receives it, and the `Why` bullet says what ships and names what ships it, as the two bullets below say.

## The blast radius

The radius is who or what is affected if the change is wrong, meaning that what it does, as written, turns out to be a mistake. It is not whatever a bug could hit, since any edit could hide one. Name the people or the things whose results change, never the files that changed: the reader already has the file list, and it does not say who to warn.

## The level

Answer two questions, then read the level from the table.

1. **The door:** one-way or two-way, as above.
2. **The reach:** does something that exists before the merge behave differently after it, as the change is written?
   - **Wide** when a default, the main output, stored data, an interface others call, or a step every run goes through behaves differently.
   - **Contained** when everything that exists behaves as before, except the single edge case the change exists to fix: what changes is reached only by new or opt-in input, or lives in docs and tests. The reach stays contained even when the change rewrites code every run passes through, as long as only new input reaches the new behaviour. A new option or command that shows up in help or usage text is new input, not a change to what exists.

The reach asks what behaves differently, not what code is touched or what a bug could hit: either of those makes nearly every change wide, and the level then stops telling changes apart. How many people a change reaches does not make it wide either; what changes for them does. A change every user receives is still contained when what they already use behaves as before.

|             | Contained | Wide      |
| ----------- | --------- | --------- |
| **Two-way** | 🟢 Low    | 🟡 Medium |
| **One-way** | 🟡 Medium | 🔴 High   |

- **Low** tells the reader they can skim: a revert fixes any mistake, and only new input meets the change. So a one-way door is never Low, since its mistake outlives the revert.
- **Medium, two-way and wide:** something people rely on behaves differently, but a revert brings it back for everyone.
- **Medium, one-way and contained:** a mistake outlives the revert, but it reaches only what is new.
- **High** tells the reader to read slowly: what people already rely on changes, and a revert does not bring it back. So a two-way door is never High, since a revert reaches everyone it broke.

Each question has a yes-or-no answer in the diff and the project's files, so answer both rather than settling on Medium when unsure.

A worked example: a shipping tool rewrites its `postage()` function to add an optional express rate. A parcel sent without the option costs what it did, so the reach is contained, though every parcel now passes through the rewritten function. Had the rewrite also changed how weight is rounded, the parcels people already send would cost differently, and the reach would be wide.

## The two bullets

- **`Why <level>:`** gives the reason for the level from the two answers. It names the part of the change that decides them, such as the function, migration or job that makes the door one-way or the reach wide, or the new input that alone reaches the change, so the reader can find it in the diff: the call is read first, and often alone. When the door or the reach rests on something the diff does not show, such as a job that runs when the base changes, it names that too, by what it is and the file that defines it, such as "the deploy job in `ci/deploy.yml` runs on every push to the base": the reader cannot check a claim whose source they cannot open. It also says what behaves differently and for whom, and, when the door is one-way, the step that cannot be undone.
- **`Walk it back:`** says what undoing the merge takes. Before writing it, separate what the branch adds from what was already on the base: a revert undoes only what the branch adds, so anything that was there before it, such as a job that runs on every push, keeps running. Say what a revert leaves in place when that matters to the reader.
  - For a two-way door, say that a revert is enough, and why, such as that nothing stored, published or sent outlives it.
  - For a one-way door, say plainly what a revert leaves in place, then the nearest recovery the project itself offers, as its files show it. If nothing recovers it, say so. The bullet never reads as if a revert were enough.
  - A recovery that the still-merged change would undo on its next run is no recovery. Say what has to be reverted or removed first, then the recovery.

## Two invented calls

Both are for the shipping tool above, and each is the risk call alone; in a description it sits under the why sentence. First, a change that adds a `track` command printing where a parcel was last scanned:

```markdown
**Risk: 🟢 Low** · **Door: two-way** · **Blast radius: people who run the new track command**

- Why low: only the new `track` command reaches the new code, and every existing command behaves as before.
- Walk it back: a revert is enough, because the command only reads the scan log and nothing ships when the base changes.
```

Second, a change to the nightly job, which runs whatever is on the base, so that it emails every customer with a parcel in transit, not only those whose parcel is late:

```markdown
**Risk: 🔴 High** · **Door: one-way** · **Blast radius: every customer with a parcel in transit**

- Why high: the nightly job in `jobs/schedule.toml` runs `notify_delays()` from the base, and the change makes that function pick every parcel in transit, so the job's first run after the merge emails customers who were never emailed before, and a sent email cannot be recalled.
- Walk it back: a revert returns the nightly job to emailing only customers whose parcel is late, from its next run on, but cannot recall the emails already sent; nothing in the project recalls them, so the nearest recovery is a correction sent to the same customers.
```
