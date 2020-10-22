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

from mo_future import PY3

from mo_dots import to_data, Null, listwrap, is_missing, is_null
from mo_testing.fuzzytestcase import FuzzyTestCase

from mo_dots.lists import last, is_many, FlatList

values = [1, 2, 3]


class TestList(FuzzyTestCase):
    def test_generator(self):
        self.assertEqual(last(reversed(values)), 1)

    def test_empty_generator(self):
        self.assertEqual(last(reversed([])), None)

    def test_empty_list(self):
        self.assertEqual(last([]), None)

    def test_empty_set(self):
        self.assertEqual(last(set()), None)

    def test_set(self):
        self.assertEqual(last(set(values)).__class__, int)

    def test_list(self):
        self.assertEqual(last(values), 3)

    def test_flat_list(self):
        v = to_data(values)
        self.assertEqual(last(v), 3)

    def test_string(self):
        v = "test"
        self.assertEqual(last(v), "test")

    def test_bytes(self):
        v = b"test"
        self.assertEqual(last(v), b"test")

    def test_number(self):
        v = 42
        self.assertEqual(last(v), 42)

    def test_object(self):
        v = {}
        self.assertEqual(last(v), to_data({}))

    def test_none(self):
        v = None
        self.assertEqual(last(v), None)

    def test_null(self):
        v = Null
        self.assertEqual(last(v), None)

    def test_is_not_many(self):
        if PY3:
            self.assertEqual(hasattr("", "__iter__"), True)
        self.assertEqual(is_many(""), False)

    def test_index(self):
        v = to_data([{"index": v} for v in values])
        self.assertEqual(v.index, values)

    def test_json(self):
        self.assertEqual(hasattr(to_data(values), "__json__"), False)

    def test_call(self):
        self.assertEqual(hasattr(to_data(values), "__call__"), False)

    def test_listwrap_FlatList(self):
        a = listwrap(values)
        self.assertIsInstance(a, FlatList)
        b = listwrap(a)
        self.assertIs(b, a)

    def test_flatten(self):
        v = listwrap(
            [
                {"a": [{"b": 1}, {"b": 2}, {"b": 3}]},
                {"a": [{"b": 4}, {"b": 5}, {"b": 6}]},
                {"a": [{"b": 7}, {"b": 8}, {"b": 9}]},
            ]
        )

        level1 = v.a
        self.assertEqual(level1, [
            [{"b": 1}, {"b": 2}, {"b": 3}],
            [{"b": 4}, {"b": 5}, {"b": 6}],
            [{"b": 7}, {"b": 8}, {"b": 9}]
        ])
        self.assertEqual(level1.b, [1, 2, 3, 4, 5, 6, 7, 8, 9])
        self.assertEqual(v.a.b, [1, 2, 3, 4, 5, 6, 7, 8, 9])

        v["a.b"] = 3
        self.assertEqual(v.a.b, [3, 3, 3, 3, 3, 3, 3, 3, 3])

        self.assertEqual(
            v,
            [
                {"a": [{"b": 3}, {"b": 3}, {"b": 3}]},
                {"a": [{"b": 3}, {"b": 3}, {"b": 3}]},
                {"a": [{"b": 3}, {"b": 3}, {"b": 3}]},
            ],
        )

        v.a["b"] = 4
        self.assertEqual(v.a.b, [4, 4, 4, 4, 4, 4, 4, 4, 4])

        v.a.b = 5
        self.assertEqual(v.a.b, [5, 5, 5, 5, 5, 5, 5, 5, 5])

    def test_nulls(self):
        self.assertEqual(is_null(None), True)
        self.assertEqual(is_null(Null), True)
        self.assertEqual(is_null({}), False)
        self.assertEqual(is_null([]), False)
        self.assertEqual(is_null(FlatList()), True)
        self.assertEqual(is_null(to_data([0])), False)
        self.assertEqual(is_null(set()), False)
        self.assertEqual(is_null(tuple()), False)

    def test_missing(self):
        self.assertEqual(is_missing(None), True)
        self.assertEqual(is_missing(Null), True)
        self.assertEqual(is_missing({}), False)
        self.assertEqual(is_missing([]), True)
        self.assertEqual(is_missing(FlatList()), True)
        self.assertEqual(is_missing(to_data([0])), False)
        self.assertEqual(is_missing(set()), True)
        self.assertEqual(is_missing(tuple()), True)


