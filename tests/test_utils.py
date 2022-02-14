# encoding: utf-8
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.
#
# Contact: Kyle Lahnakoski (kyle@lahnakoski.com)
#
from unittest import TestCase

import tests
from mo_dots import inverse, coalesce, Null, missing, exists, hash_value, set_default, to_data, get_attr


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

    def test_hash_value(self):
        self.assertEqual(hash_value(["a"]), hash("a"))

    def test_set_default(self):
        x = set_default({"a": 1}, None)
        self.assertEqual(x, {"a": 1})

        x = set_default({"a": 1}, to_data({"b":1}))
        self.assertEqual(x, {"a": 1, "b": 1})

    def test_get_unknown_module_attr(self):
        m = get_attr(tests, "get_attr")
        self.assertIsInstance(m, type(tests))
        v = get_attr(tests, "get_attr.D")
        self.assertEqual(v, {"unique": 1234})