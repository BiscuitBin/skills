"""The desk's report: one line per copy."""

from lending.rules import is_overdue


def report(copies, today):
    """One line per copy, in id order, with late loans marked."""
    lines = []
    for copy_id in sorted(copies):
        copy = copies[copy_id]
        line = f"{copy_id} {copy['state']}"
        if copy["state"] == "on_loan":
            line += f" {copy['member']} due {copy['due']}"
            if is_overdue(copy, today):
                line += " OVERDUE"
        lines.append(line)
    return lines
