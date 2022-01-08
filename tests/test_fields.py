# encoding: utf-8
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.
#
# Contact: Kyle Lahnakoski (kyle@lahnakoski.com)
#

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from mo_testing.fuzzytestcase import FuzzyTestCase

from mo_dots import relative_field, tail_field, split_field, join_field, concat_field, startswith_field


class TestFields(FuzzyTestCase):
    def test_relative(self):
        self.assertEqual(relative_field("testing", "testing"), ".")

    def test_tail_field(self):
        value, tail = tail_field("meta..stats")
        expected = "meta.stats"

        self.assertEqual(value, expected, "expecting identical")

    def test_split_w_slashes(self):
        self.assertEqual(split_field("a..b"), ["a.b"])
        self.assertEqual(split_field("a\\..b"), ["a\\.b"])
        self.assertEqual(split_field("a\\\\..b"), ["a\\\\.b"])
        self.assertEqual(split_field("a.\bb"), ["a", ".b"])
        self.assertEqual(split_field("a\b.b"), ["a.", "b"])
        self.assertEqual(split_field("a\\.\bb"), ["a\\", ".b"])
        self.assertEqual(split_field("a\\\\.\bb"), ["a\\\\", ".b"])
        self.assertEqual(split_field("a.b"), ["a", "b"])
        self.assertEqual(split_field("a\\.b"), ["a\\", "b"])
        self.assertEqual(split_field("a\\\\.b"), ["a\\\\", "b"])

    def test_join_with_slashes(self):
        self.assertEqual("a.b", join_field(["a", "b"]))
        self.assertEqual("a..b", join_field(["a.b"]))
        self.assertEqual("a\\..b", join_field(["a\\.b"]))
        self.assertEqual("a\\\\..b", join_field(["a\\\\.b"]))
        self.assertEqual("a.\bb", join_field(["a", ".b"]))
        self.assertEqual("a\b.b", join_field(["a.", "b"]))
        self.assertEqual("a\\.\bb", join_field(["a\\", ".b"]))
        self.assertEqual("a\\\\.\bb", join_field(["a\\\\", ".b"]))
        self.assertEqual("a.b", join_field(["a", "b"]))
        self.assertEqual("a\\.b", join_field(["a\\", "b"]))
        self.assertEqual("a\\\\.b", join_field(["a\\\\", "b"]))

    def test_concat_field(self):
        self.assertEqual(concat_field("a.b.c", "d"), "a.b.c.d")
        self.assertEqual(concat_field("a.b.c", ".d"), "a.b.c.d")
        self.assertEqual(concat_field("a.b.c", "..d"), "a.b.d")
        self.assertEqual(concat_field("a.b.c", "...d"), "a.d")

    def test_startswith(self):
        self.assertEqual(startswith_field("a.b.c", None), False)
        self.assertEqual(startswith_field("a.b.c", "."), True)
        self.assertEqual(startswith_field("a.b.c", "a"), True)
        self.assertEqual(startswith_field("a.b.c", "b"), False)
        self.assertEqual(startswith_field("a.b.c", "a.b"), True)

    def test_illegal(self):
        with self.assertRaises(Exception):
            split_field('\\...a\bb.')

        with self.assertRaises(Exception):
            split_field('a\\a...\\b')