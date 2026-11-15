#!/usr/bin/env python3
"""Keep a log of the books you finish."""

import argparse
import os
import shutil
import sqlite3
import sys
from datetime import date
from pathlib import Path

MIGRATIONS = Path(__file__).resolve().with_name("migrations")


def log_path():
    """Where the log lives: $READLOG_DB if it is set, else ~/.readlog.db."""
    return Path(os.environ.get("READLOG_DB") or Path.home() / ".readlog.db")


def pending(connection):
    """The migrations this log has not had yet, in the order they apply."""
    connection.execute("CREATE TABLE IF NOT EXISTS applied (name TEXT PRIMARY KEY)")
    done = {name for (name,) in connection.execute("SELECT name FROM applied")}
    return [path for path in sorted(MIGRATIONS.glob("*.sql")) if path.stem not in done]


def open_log(path):
    """Open the log, first applying every migration it has not had yet.

    Before any migration runs on an existing log, the log is copied to the
    same name with .bak added, replacing the copy the last migration left.
    """
    existed = path.exists()
    connection = sqlite3.connect(path)
    todo = pending(connection)
    if todo and existed:
        shutil.copyfile(path, path.with_name(path.name + ".bak"))
    for migration in todo:
        connection.executescript(migration.read_text(encoding="utf-8"))
        connection.execute("INSERT INTO applied (name) VALUES (?)", (migration.stem,))
        connection.commit()
    return connection


def add(connection, title):
    today = date.today().isoformat()
    connection.execute("INSERT INTO books (title, finished) VALUES (?, ?)", (title, today))
    connection.commit()
    print(f"logged: {title}")


def show(connection):
    rows = connection.execute("SELECT title, finished FROM books ORDER BY finished, rowid")
    for title, finished in rows:
        print(f"{finished}  {title}")


def main(argv=None):
    parser = argparse.ArgumentParser(prog="readlog", description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("add", help="log a book you finished today").add_argument("title")
    commands.add_parser("list", help="list the books you have finished")
    args = parser.parse_args(argv)
    connection = open_log(log_path())
    if args.command == "add":
        add(connection, args.title)
    else:
        show(connection)
    connection.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
