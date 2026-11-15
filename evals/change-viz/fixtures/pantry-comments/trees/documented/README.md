# pantry

Prints the total count of each item in a pantry list.

Each line of the list is one record: an item's name and a count, separated by `|`.

```text
rice|2
```

Blank lines are skipped, and so is any line that starts with `#`, so a list can hold comments.

```sh
python3 pantry.py pantry.txt
```

A line that is not in the `name|count` form stops the count with an error that gives its line number, counting from 1:

```text
pantry.py: line 4: expected "name|count", got 'rice'
```
