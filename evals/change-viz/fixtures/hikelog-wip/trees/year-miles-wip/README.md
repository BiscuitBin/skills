# hikes

Prints how many hikes a log holds and how far they went in all.

Each row of the log is one hike: its `date` as YYYY-MM-DD, the `trail`, and the distance in `km`.

```sh
python3 hikes.py hikes.csv
```

Add `--longest` to also name the longest hike, with its distance and date:

```sh
python3 hikes.py hikes.csv --longest
```

Add `--year` to count only the hikes from one year:

```sh
python3 hikes.py hikes.csv --year 2025
```

Add `--miles` to print distances in miles instead of km.

Tracks recorded on a GPS watch go in `tracks/`.
