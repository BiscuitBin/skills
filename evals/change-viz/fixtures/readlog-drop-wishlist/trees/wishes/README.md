# readlog

Keeps a log of the books you finish, and a wishlist of books to read.

```sh
python3 readlog.py add "The Left Hand of Darkness"
python3 readlog.py list
```

The log is a SQLite file, `~/.readlog.db`, or the path in `READLOG_DB`. Each run first brings the log up to date with the files in `migrations/`.

Keep a wishlist of the books you want to read next:

```sh
python3 readlog.py wish "Piranesi"
python3 readlog.py wishes
```
