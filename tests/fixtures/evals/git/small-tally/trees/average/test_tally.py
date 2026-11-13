import unittest

from tally import average, total


class TotalTest(unittest.TestCase):
    def test_adds_every_line(self):
        self.assertEqual(total(["3\n", "4.5\n", "12\n"]), 19.5)

    def test_no_lines_total_zero(self):
        self.assertEqual(total([]), 0)


class AverageTest(unittest.TestCase):
    def test_divides_the_total_by_the_count(self):
        self.assertEqual(average(["3\n", "4.5\n", "12\n"]), 6.5)


if __name__ == "__main__":
    unittest.main()
