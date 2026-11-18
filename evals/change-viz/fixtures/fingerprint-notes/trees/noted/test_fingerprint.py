#!/usr/bin/env python3
import hashlib
import unittest

from fingerprint import fingerprint, normalise


class FingerprintTest(unittest.TestCase):
    def test_is_twelve_hex_digits(self):
        self.assertRegex(fingerprint("hello\n"), r"\A[0-9a-f]{12}\Z")

    def test_is_the_start_of_the_sha256_of_the_normalised_text(self):
        expected = hashlib.sha256(b"hello\n").hexdigest()[:12]
        self.assertEqual(fingerprint("hello  \n\n"), expected)


class NormaliseTest(unittest.TestCase):
    def test_drops_blank_lines_and_trailing_spaces(self):
        self.assertEqual(normalise("one  \n\n  two\n"), "one\n  two\n")

    def test_leaves_clean_text_alone(self):
        self.assertEqual(normalise("one\ntwo\n"), "one\ntwo\n")


if __name__ == "__main__":
    unittest.main()
