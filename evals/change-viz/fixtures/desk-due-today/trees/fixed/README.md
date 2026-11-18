# desk

Replays a lending desk's event log and prints the state of each copy on a given day, marking the loans that are overdue.

```sh
python3 desk.py events.txt 2026-05-03
```

Each line of the log is a date, an action and the action's fields:

- `lend COPY MEMBER DUE`: the copy goes out to the member until the due date.
- `return COPY`: the copy comes back and is available again.
