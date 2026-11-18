"""Read a lending desk's event log and replay it, copy by copy."""

from datetime import date


def parse(line):
    """One event line: its date, its action and the fields after them."""
    day, action, *fields = line.split()
    return date.fromisoformat(day), action, fields


def replay(lines):
    """Each copy's state after every event in the log, by copy id."""
    copies = {}
    for line in lines:
        if not line.strip() or line.startswith("#"):
            continue
        day, action, fields = parse(line)
        copy = copies.setdefault(fields[0], {"state": "available", "member": None, "due": None})
        if action == "lend":
            if copy["state"] != "available":
                raise ValueError(f"{day}: {fields[0]} is {copy['state']}")
            copy.update(state="on_loan", member=fields[1], due=date.fromisoformat(fields[2]))
        elif action == "return":
            copy.update(state="available", member=None, due=None)
        else:
            raise ValueError(f"{day}: unknown action {action!r}")
    return copies
