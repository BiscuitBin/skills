"""When a loan is late."""


def is_overdue(copy, today):
    """Whether a copy on loan is late back on the given day."""
    return copy["state"] == "on_loan" and today >= copy["due"]
