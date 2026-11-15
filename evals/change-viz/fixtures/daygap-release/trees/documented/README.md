# daygap

Prints how many days lie between two dates.

```sh
pip install daygap
daygap 2026-03-02 2026-03-16
```

This prints `14 days`. The count is negative when the second date comes first.

Add `--weekdays` to print, on a second line, how many of those days fall on Monday to Friday:

```sh
daygap 2026-03-02 2026-03-16 --weekdays
```
