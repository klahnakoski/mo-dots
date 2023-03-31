# encoding: utf-8
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.
#
# Contact: Kyle Lahnakoski (kyle@lahnakoski.com)
#

from mo_testing.fuzzytestcase import FuzzyTestCase

import tests
from mo_dots import (
    inverse,
    coalesce,
    Null,
    missing,
    exists,
    hash_value,
    set_default,
    to_data,
    get_attr,
    tuplewrap,
    utils,
    Data,
)
from mo_dots.utils import PoorLogger


class TestUtils(FuzzyTestCase):
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

        x = set_default({"a": 1}, to_data({"b": 1}))
        self.assertEqual(x, {"a": 1, "b": 1})

    def test_set_default_w_None(self):
        x = set_default({}, {"a": None})
        self.assertEqual(x, {})

        y = {"d": 2}
        x = set_default(to_data({"b": 1}), {"a": {"b": y, "c": y}})
        self.assertEqual(x, {"b": 1, "a": {"b": {"d": 2}, "c": {"d": 2}}})

    def test_get_unknown_module_attr(self):
        m = get_attr(tests, "get_attr")
        self.assertIsInstance(m, type(tests))
        v = get_attr(tests, "get_attr.D")
        self.assertEqual(v, {"unique": 1234})

    def test_tuplewrap(self):
        self.assertEqual(tuplewrap(None), tuple())
        self.assertEqual(tuplewrap("hi"), ("hi",))
        self.assertEqual(tuplewrap(["a", "b"]), ("a", "b"))

        self.assertIsInstance(tuplewrap(None), tuple)
        self.assertIsInstance(tuplewrap("hi"), tuple)
        self.assertIsInstance(tuplewrap(["a", "b"]), tuple)

    def test_poor_logger(self):
        logger = PoorLogger()
        lines = []
        utils.STDOUT, old = Data(write=lambda t: lines.append(t)), utils.STDOUT

        logger.info("test1")
        logger.warning("test2")
        with self.assertRaises("test3"):
            logger.error("test3")

        with self.assertRaises("test4"):
            logger.error("test3", cause=Exception("test4"))
