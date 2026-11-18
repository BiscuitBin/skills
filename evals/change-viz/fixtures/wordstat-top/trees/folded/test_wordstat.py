#!/usr/bin/env python3
import unittest

from wordstat import words


class WordsTest(unittest.TestCase):
    def test_splits_on_whitespace(self):
        self.assertEqual(words("one two\nthree"), ["one", "two", "three"])

    def test_empty_text_has_no_words(self):
        self.assertEqual(words(""), [])

    def test_ignores_case_and_punctuation(self):
        self.assertEqual(words("The cat, the CAT."), ["the", "cat", "the", "cat"])

    def test_drops_tokens_that_are_only_punctuation(self):
        self.assertEqual(words("one - two"), ["one", "two"])


if __name__ == "__main__":
    unittest.main()
