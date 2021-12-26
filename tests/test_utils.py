# encoding: utf-8
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.
#
# Contact: Kyle Lahnakoski (kyle@lahnakoski.com)
#
from unittest import TestCase

from mo_dots import inverse, coalesce, Null, missing, exists


class TestUtils(TestCase):

    def test_inverse(self):
        result = inverse({"a": "b", "b": "b"})
        self.assertEqual(result, {"b": ["a", "b"]})

    def test_coalesce(self):
        self.assertEqual(None, coalesce())
        self.assertEqual(None, coalesce(None))
        self.assertEqual(None, coalesce(Null))

    def test_missing(self):
        with self.assertRaises(Exception):
            missing(None)

    def test_exists(self):
        self.assertEqual(exists(None), False)