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


class HoldTest(unittest.TestCase):
    HELD = [*LOG, "2026-05-03 hold c2 cal", "2026-05-04 return c2"]

    def test_a_returned_copy_is_kept_for_the_member_who_holds_it(self):
        copy = replay(self.HELD)["c2"]
        self.assertEqual((copy["state"], copy["member"]), ("held", "cal"))

    def test_only_that_member_can_take_a_kept_copy(self):
        with self.assertRaises(ValueError):
            replay([*self.HELD, "2026-05-05 lend c2 dee 2026-05-12"])
        lent = replay([*self.HELD, "2026-05-05 lend c2 cal 2026-05-12"])["c2"]
        self.assertEqual((lent["state"], lent["member"]), ("on_loan", "cal"))

    def test_an_available_copy_takes_no_hold(self):
        with self.assertRaises(ValueError):
            replay([*LOG, "2026-05-03 hold c1 cal"])

    def test_the_report_names_the_member_a_copy_is_kept_for(self):
        self.assertEqual(report(replay(self.HELD), date(2026, 5, 5))[1], "c2 held for cal")


class ReportTest(unittest.TestCase):
    def test_one_line_per_copy_in_id_order(self):
        self.assertEqual(
            report(replay(LOG), date(2026, 5, 5)),
            ["c1 available", "c2 on_loan ben due 2026-05-04 OVERDUE"],
        )


if __name__ == "__main__":
    unittest.main()
