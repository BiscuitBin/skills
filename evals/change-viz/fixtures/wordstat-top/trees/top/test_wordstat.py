#!/usr/bin/env python3
import unittest

from wordstat import most_common, words


class WordsTest(unittest.TestCase):
    def test_splits_on_whitespace(self):
        self.assertEqual(words("one two\nthree"), ["one", "two", "three"])

    def test_empty_text_has_no_words(self):
        self.assertEqual(words(""), [])

    def test_ignores_case_and_punctuation(self):
        self.assertEqual(words("The cat, the CAT."), ["the", "cat", "the", "cat"])

    def test_drops_tokens_that_are_only_punctuation(self):
        self.assertEqual(words("one - two"), ["one", "two"])


class MostCommonTest(unittest.TestCase):
    def test_most_frequent_first(self):
        found = words("b a b c b a")
        self.assertEqual(most_common(found, 2), [("b", 3), ("a", 2)])


if __name__ == "__main__":
    unittest.main()
