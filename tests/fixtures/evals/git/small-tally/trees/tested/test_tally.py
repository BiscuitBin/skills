import unittest

from tally import total


class TotalTest(unittest.TestCase):
    def test_adds_every_line(self):
        self.assertEqual(total(["3\n", "4.5\n", "12\n"]), 19.5)

    def test_no_lines_total_zero(self):
        self.assertEqual(total([]), 0)


if __name__ == "__main__":
    unittest.main()
