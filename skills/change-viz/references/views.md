# Views for the change outline

Each view shows one kind of structure. You may use one of these or several, and you will rarely use them all.

| View | Fence | Shows |
| --- | --- | --- |
| Pseudocode | `text` | Logic or an algorithm, in the order it runs. |
| Call tree | `text` | Runtime control flow: what calls what. |
| Component tree | `text`, or the UI code's language | UI structure, with the state and module boundaries that matter. |
| File tree | `text` | Where responsibilities live, or a broad move of files. |
| Mermaid flowchart, sequence or state diagram | `mermaid` | How parts interact, how control or data flows, or states and their transitions. |
| Diff sketch | `diff` | What changes in a shape that already exists: any tree above, or pseudocode. |
| Whole block | the code's language | A shape that is mostly new, or one where cutting context would hide who owns what or what runs in which order. |

## Diff sketch or whole block

Use a diff sketch when the point is what changes and the surrounding shape already exists. Match its shape to the topic: a file tree for moved files, a call tree for a new call, pseudocode for changed logic. Mark added lines with `+` and removed lines with `-`, and start every other line with a space, as a real diff does, so a reader who knows the notation reads it at a glance.

Show the whole block instead when most of it is new, or when diff notation would hide ownership or order. A reader then sees the shape they will find in the code.

## Keep each view small

Keep only the calls, files, states and boundaries the point needs. Name things as the code names them, so a reader can find them, and leave out what does not bear on the point. A sketch that tries to show everything shows nothing in particular.
