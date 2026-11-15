# readlog

Keeps a log of the books you finish.

```sh
python3 readlog.py add "The Left Hand of Darkness"
python3 readlog.py list
```

The log is a SQLite file, `~/.readlog.db`, or the path in `READLOG_DB`. Each run first brings the log up to date with the files in `migrations/`.
