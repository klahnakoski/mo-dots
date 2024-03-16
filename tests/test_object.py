# encoding: utf-8
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.
#
# Contact: Kyle Lahnakoski (kyle@lahnakoski.com)
#
import sys
from dataclasses import dataclass
from typing import List

from mo_testing.fuzzytestcase import FuzzyTestCase

from mo_dots import *

values = [1, 2, 3]


class TestObject(FuzzyTestCase):
    def test_funcs(self):
        x = MyObject(42)
        d = DataObject(x)
        self.assertEqual(d.my_attr, 42)
        d.my_attr = 43
        self.assertEqual(d["my_attr"], 43)
        self.assertEqual(d.get("my_attr"), 43)
        self.assertEqual(d.keys(), {"my_attr"})
        self.assertEqual(list(d.items()), [("my_attr", 43)])
        self.assertEqual(d.__data__(), {"my_attr": 43})
        self.assertEqual(list(d), {"my_attr"})
        self.assertEqual(str(d), "testing")
        self.assertEqual(len(d), 1)
        self.assertEqual(d(42), 42)

    def test_wrap(self):
        self.assertEqual(datawrap((1, 2)), (1, 2))
        self.assertEqual(to_data([1, 2]), (1, 2))
        self.assertEqual(to_data(gen()), (1, 2))

    def test_datawrap(self):
        self.assertEqual(datawrap(None), Null)
        self.assertEqual(datawrap(Null), Null)
        self.assertEqual(list(datawrap(gen())), [1, 2])
        self.assertEqual(to_data({"a": 3}), {"a": 3})

    def test_dict_class(self):
        BetterObject = DataClass(MyObject)
        x = BetterObject(42)
        self.assertEqual(x.my_attr, 42)

    def test_apply1(self):
        @dataclass
        class Example2:
            c: int

        @dataclass
        class ExampleA:
            a: List[str]
            b: Example2

        obj = ExampleA(["a", "x"], Example2(42))
        d = object_to_data(obj)

        c = to_data({"a": ["z"], "b": {"c": 99}})

        result = c | d

        self.assertEqual(result.b.c, 99)
        self.assertFalse(result == d)

    def test_apply2(self):
        @dataclass
        class Example2:
            c: int

        @dataclass
        class ExampleA:
            a: List[str]
            b: Example2

        obj = ExampleA(["a", "x"], Example2(42))
        d = object_to_data(obj)

        c = to_data({"b": {"c": 42}})

        result = d | c

        self.assertEqual(result.b.c, 42)
        self.assertTrue(result == d)
        self.assertTrue(d == result)

    def test_apply3(self):
        @dataclass
        class Example2:
            c: int

        @dataclass
        class ExampleA:
            a: List[str]
            b: Example2

        obj = ExampleA(["a", "x"], Example2(42))
        d = object_to_data(obj)

        c = to_data({"a": ["z"], "b": {"c": 99}})

        result = d + c
        expected = to_data({"a": ["a", "x", "z"], "b": {"c": 42 + 99}})
        self.assertTrue(result == expected)
        self.assertTrue(expected == result)

    def test_radd(self):
        @dataclass
        class Example2:
            c: int

        @dataclass
        class ExampleA:
            a: List[str]
            b: Example2

        obj = ExampleA(["a", "x"], Example2(42))
        d = object_to_data(obj)

        c = {"a": ["z"], "b": {"c": 99}}

        result = c + d
        expected = to_data({"a": ["z", "a", "x"], "b": {"c": 99 + 42}})
        self.assertTrue(result == expected)
        self.assertTrue(expected == result)

    def test_ror(self):
        @dataclass
        class Example2:
            c: int

        @dataclass
        class ExampleA:
            a: List[str]
            b: Example2

        obj = ExampleA(["a", "x"], Example2(42))
        d = object_to_data(obj)

        c = {"a": ["z"], "b": {"c": 99}}

        result = c | d
        expected = to_data({"a": ["z"], "b": {"c": 99}})
        self.assertTrue(result == expected)
        self.assertTrue(expected == result)

    def test_class_properties_are_ignored(self):
        class Unknown:
            parent = None

            __slots__ = ["a"]
            def __init__(self, a):
                self.a = a

        Unknown.parent = Unknown(4)

        obj = DataObject(Unknown(3))

        self.assertEqual(list(obj.items()), [('a', 3)])

    def test_dataclass_properties_are_ignored(self):
        @dataclass
        class Unknown:
            a: int

        obj = DataObject(Unknown(3))

        self.assertEqual(list(obj.items()), [('a', 3)])
        self.assertEqual([('a', 3)], list(obj.items()))

    def test_w_traceback(self):
        try:
            return 1 / 0
        except Exception:
            exc_type, exc_value, exc_traceback = sys.exc_info()

        obj = DataObject(exc_traceback)
        self.assertEqual(obj.keys(), {"tb_frame", "tb_lasti", "tb_lineno", "tb_next"})
        self.assertEqual(obj.tb_frame.f_code.co_name, "test_w_traceback")


def gen():
    yield 1
    yield 2


class MyObject(object):
    def __init__(self, v):
        self.my_attr = v

    def __getattr__(self, item):
        return self.__dict__[item]

    def __setattr__(self, item, value):
        self.__dict__[item] = value

    def __call__(self, value):
        return value

    def __len__(self):
        return 1

    def __str__(self):
        return "testing"
