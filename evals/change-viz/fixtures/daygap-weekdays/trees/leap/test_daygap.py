#!/usr/bin/env python3
import io
import unittest
from contextlib import redirect_stdout
from datetime import date

from daygap import days_between, main


class DaysBetweenTest(unittest.TestCase):
    def test_counts_whole_days(self):
        self.assertEqual(days_between(date(2026, 3, 2), date(2026, 3, 16)), 14)

    def test_negative_when_end_comes_first(self):
        self.assertEqual(days_between(date(2026, 3, 16), date(2026, 3, 2)), -14)

    def test_spans_a_leap_day(self):
        self.assertEqual(days_between(date(2028, 2, 28), date(2028, 3, 1)), 2)


class MainTest(unittest.TestCase):
    def test_prints_the_days(self):
        out = io.StringIO()
        with redirect_stdout(out):
            self.assertEqual(main(["2026-03-02", "2026-03-16"]), 0)
        self.assertEqual(out.getvalue(), "14 days\n")


if __name__ == "__main__":
    unittest.main()
