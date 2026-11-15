# desk

Replays a lending desk's event log and prints the state of each copy on a given day, marking the loans that are overdue.

```sh
python3 desk.py events.txt 2026-05-03
```

Each line of the log is a date, an action and the action's fields:

- `lend COPY MEMBER DUE`: the copy goes out to the member until the due date. A copy kept for a member goes out to that member only.
- `hold COPY MEMBER`: the member asks for a copy that is out. Only a copy on loan takes a hold, and only one.
- `return COPY`: the copy comes back. It is kept for the member who holds it, if anyone does, and is available again otherwise.
