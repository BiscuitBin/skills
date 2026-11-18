# fingerprint

Prints a short fingerprint of each text file: the first 12 hex digits of the SHA-256 of its text.

```sh
python3 fingerprint.py notes/plan.txt notes/todo.txt
```

`fingerprints.txt` records the fingerprints of the notes. To check that the notes still match it:

```sh
python3 fingerprint.py --check fingerprints.txt
```
