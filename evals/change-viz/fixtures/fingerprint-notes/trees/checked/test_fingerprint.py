#!/usr/bin/env python3
import hashlib
import unittest

from fingerprint import fingerprint


class FingerprintTest(unittest.TestCase):
    def test_is_twelve_hex_digits(self):
        self.assertRegex(fingerprint("hello\n"), r"\A[0-9a-f]{12}\Z")

    def test_is_the_start_of_the_sha256_of_the_text(self):
        expected = hashlib.sha256(b"hello\n").hexdigest()[:12]
        self.assertEqual(fingerprint("hello\n"), expected)


if __name__ == "__main__":
    unittest.main()
