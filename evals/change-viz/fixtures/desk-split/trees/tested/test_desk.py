#!/usr/bin/env python3
import unittest
from datetime import date

from desk import is_overdue, replay, report

LOG = [
    "2026-05-01 lend c1 ana 2026-05-03",
    "2026-05-02 return c1",
    "2026-05-02 lend c2 ben 2026-05-04",
]


class ReplayTest(unittest.TestCase):
    def test_a_returned_copy_is_available(self):
        self.assertEqual(replay(LOG)["c1"]["state"], "available")

    def test_a_copy_on_loan_cannot_be_lent_again(self):
        with self.assertRaises(ValueError):
            replay([*LOG, "2026-05-03 lend c2 cal 2026-05-09"])


class OverdueTest(unittest.TestCase):
    def test_late_after_the_due_date(self):
        self.assertTrue(is_overdue(replay(LOG)["c2"], date(2026, 5, 5)))

    def test_not_late_before_the_due_date(self):
        self.assertFalse(is_overdue(replay(LOG)["c2"], date(2026, 5, 3)))


class ReportTest(unittest.TestCase):
    def test_one_line_per_copy_in_id_order(self):
        self.assertEqual(
            report(replay(LOG), date(2026, 5, 5)),
            ["c1 available", "c2 on_loan ben due 2026-05-04 OVERDUE"],
        )


if __name__ == "__main__":
    unittest.main()
