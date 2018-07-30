# encoding: utf-8
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.
#
# Author: Kyle Lahnakoski (kyle@lahnakoski.com)
#

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from collections import Mapping
from copy import deepcopy

from mo_future import UserDict
from mo_logs import Log
from mo_math import MAX
from mo_testing.fuzzytestcase import FuzzyTestCase

from mo_dots import wrap, Null, set_default, unwrap, Data, literal_field, NullType
from mo_dots.objects import datawrap


class TestDot(FuzzyTestCase):

    def test_set_union_w_null(self):
        s = set('a')
        s |= Null
        self.assertAlmostEqual(s, set('a'))

    def test_null_class(self):
        self.assertFalse(isinstance(Null, Mapping))

    def test_userdict_1(self):
        def show_kwargs(**kwargs):
            return kwargs

        a = UserDict(a=1, b=2)
        d = show_kwargs(**a)
        self.assertAlmostEqual(d, {"a": 1, "b": 2})

    def test_userdict_2(self):
        def show_kwargs(**kwargs):
            return kwargs

        a = UserDict()
        a.data["a"] = 1
        a.data["b"] = 2
        d = show_kwargs(**a)
        self.assertAlmostEqual(d, {"a": 1, "b": 2})

    def test_dict_args(self):
        def show_kwargs(**kwargs):
            return kwargs

        a = Data()
        a["a"] = 1
        a["b"] = 2
        d = show_kwargs(**a)
        self.assertAlmostEqual(d, {"a": 1, "b": 2})

    def test_is_mapping(self):
        self.assertTrue(isinstance(Data(), Mapping), "All Data must be Mappings")

    def test_none(self):
        a = 0
        b = 0
        c = None
        d = None

        if a == b:
            pass
        else:
            Log.error("error")

        if c == d:
            pass
        else:
            Log.error("error")

        if a == c:
            Log.error("error")

        if d == b:
            Log.error("error")

        if not c:
            pass
        else:
            Log.error("error")

    def test_null_access(self):
        a = Data()
        c = a.b[b'test']
        self.assertTrue(c == None, "Expecting Null to accept str() for item access")

    def test_null(self):
        a = 0
        b = 0
        c = Null
        d = Null
        e = Data()
        f = Data()

        if a == b:
            pass
        else:
            Log.error("error")

        if c == d:
            pass
        else:
            Log.error("error")

        if a == c:
            Log.error("error")

        if d == b:
            Log.error("error")

        if c == None:
            pass
        else:
            Log.error("error")

        if not c:
            pass
        else:
            Log.error("error")

        if Null != Null:
            Log.error("error")

        if Null != None:
            Log.error("error")

        if None != Null:
            Log.error("error")

        if e.test != f.test:
            Log.error("error")

    def test_get_value(self):
        a = wrap({"a": 1, "b": {}})

        if a.a != 1:
            Log.error("error")
        if not isinstance(a.b, Mapping):
            Log.error("error")

    def test_get_class(self):
        a = wrap({})
        _type = a.__class__

        if _type is not Data:
            Log.error("error")

    def test_int_null(self):
        a = Data()
        value = a.b * 1000
        assert value == Null

    def test_dot_self(self):
        a = Data(b=42)
        assert a["."] == a
        assert a["."].b == 42

        a["."] = {"c": 42}
        assert a.c == 42
        assert a.b == None

    def test_list(self):
        if not []:
            pass
        else:
            Log.error("error")

        if []:
            Log.error("error")

        if not [0]:
            Log.error("error")

    def test_assign1(self):
        a = {}

        b = wrap(a)
        b.c = "test1"
        b.d.e = "test2"
        b.f.g.h = "test3"
        b.f.i = "test4"
        b.k["l.m.n"] = "test5"

        expected = {
            "c": "test1",
            "d": {
                "e": "test2"
            },
            "f": {
                "g": {
                    "h": "test3"
                },
                "i": "test4"
            },
            "k": {
                "l": {"m": {"n": "test5"}}
            }
        }
        self.assertEqual(a, expected)

    def test_assign2(self):
        a = {}

        b = wrap(a)
        b_c = b.c
        b.c.d = "test1"

        b_c.e = "test2"

        expected = {
            "c": {
                "d": "test1",
                "e": "test2"
            }
        }
        self.assertEqual(a, expected)

    def test_assign3(self):
        # IMPOTENT ASSIGNMENTS DO NOTHING
        a = {}
        b = wrap(a)

        b.c = None
        expected = {}
        self.assertEqual(a, expected)

        b.c.d = None
        expected = {}
        self.assertEqual(a, expected)

        b["c.d"] = None
        expected = {}
        self.assertEqual(a, expected)

        b.c.d.e = None
        expected = {}
        self.assertEqual(a, expected)

        b.c["d.e"] = None
        expected = {}
        self.assertEqual(a, expected)

    def test_assign4(self):
        # IMPOTENT ASSIGNMENTS DO NOTHING
        a = {"c": {"d": {}}}
        b = wrap(a)
        b.c.d = None
        expected = {"c": {}}
        self.assertEqual(a, expected)

        a = {"c": {"d": {}}}
        b = wrap(a)
        b.c = None
        expected = {}
        self.assertEqual(a, expected)

    def test_assign5(self):
        a = {}
        b = wrap(a)

        b.c["d\.e"].f = 2
        expected = {"c": {"d.e": {"f": 2}}}
        self.assertEqual(a, expected)

    def test_assign6(self):
        a = {}
        b = wrap(a)

        b["c.d.e\.f"] = 1
        b["c.d.e\.g"] = 2

        expected = {"c": {"d": {"e.f": 1, "e.g": 2}}}
        self.assertEqual(a, expected)

    def test_assign7(self):
        a = {}
        b = wrap(a)

        b["c.d.e\.f"] = 1
        b["c.d.g\.h"] = 2

        expected = {"c": {"d": {"e.f": 1, "g.h": 2}}}
        self.assertEqual(a, expected)

    def test_assign8(self):
        a = {}
        b = wrap(a)

        b["a"][literal_field(literal_field("b.html"))]["z"] = 3

        expected = {"a": {
            "b\\.html": {"z": 3}
        }}
        self.assertEqual(a, expected)

    def test_assign9(self):
        a = {}
        b = wrap(a)

        b["a"]["."] = 1

        expected = {"a": 1}
        self.assertEqual(a, expected)

    def test_setitem_and_deep(self):
        a = {}
        b = wrap(a)

        b.c["d"].e.f = 3
        expected = {"c": {"d": {"e": {"f": 3}}}}
        self.assertEqual(a, expected)

    def test_assign_and_use1(self):
        a = wrap({})
        agg = a.b
        agg.c = []
        agg.c.append("test value")

        self.assertEqual(a, {"b": {"c": ["test value"]}})
        self.assertEqual(a.b, {"c": ["test value"]})
        self.assertEqual(a.b.c, ["test value"])

    def test_assign_and_use2(self):
        a = wrap({})
        agg = a.b.c
        agg += []
        agg.append("test value")

        self.assertEqual(a, {"b": {"c": ["test value"]}})
        self.assertEqual(a.b, {"c": ["test value"]})
        self.assertEqual(a.b.c, ["test value"])

    def test_assign_none(self):
        a = {}
        A = wrap(a)

        A[None] = "test"
        self.assertEqual(a, {})

    def test_increment(self):
        a = {}
        b = wrap(a)
        b.c1.d += 1
        b.c2.e += "e"
        b.c3.f += ["f"]
        b["c\\.a"].d += 1

        self.assertEqual(a, {"c1": {"d": 1}, "c2": {"e": "e"}, "c3": {"f": ["f"]}, "c.a": {"d": 1}})

        b.c1.d += 2
        b.c2.e += "f"
        b.c3.f += ["g"]
        b["c\\.a"].d += 3
        self.assertEqual(a, {"c1": {"d": 3}, "c2": {"e": "ef"}, "c3": {"f": ["f", "g"]}, "c.a": {"d": 4}})

    def test_slicing(self):

        def diff(record, index, records):
            """
            WINDOW FUNCTIONS TAKE THE CURRENT record, THE index THAT RECORD HAS
            IN THE WINDOW, AND THE (SORTED) LIST OF ALL records
            """
            # COMPARE CURRENT VALUE TO MAX OF PAST 5, BUT NOT THE VERY LAST ONE
            try:
                return record - MAX(records[index - 6:index - 1:])
            except Exception as e:
                return None

        data1_list = [1, 2, 3, 4, 5, 6, 7, 8, 9]
        result1 = [diff(r, i, data1_list) for i, r in enumerate(data1_list)]
        assert result1 == [-7, None, None, None, None, None, 2, 2, 2]  # WHAT IS EXPECTED, BUT NOT WHAT WE WANT

        data2_list = wrap(data1_list)
        result2 = [diff(r, i, data2_list) for i, r in enumerate(data2_list)]
        assert result2 == [None, None, 2, 2, 2, 2, 2, 2, 2]

    def test_delete1(self):
        a = wrap({"b": {"c": 1}})

        del a.b.c
        self.assertEqual({"b": {}}, a)
        self.assertEqual(a, {"b": {}})

        a = wrap({"b": {"c": 1}})

        a.b.c = None
        self.assertEqual({"b": {}}, a)
        self.assertEqual(a, {"b": {}})

    def test_delete2(self):
        a = wrap({"b": {"c": 1, "d": 2}})

        del a.b.c
        self.assertEqual({"b": {"d": 2}}, a)
        self.assertEqual(a, {"b": {"d": 2}})
        a = wrap({"b": {"c": 1, "d": 2}})

        a.b.c = None
        self.assertEqual({"b": {"d": 2}}, a)
        self.assertEqual(a, {"b": {"d": 2}})

    def test_wrap(self):
        d = {}
        dd = wrap(d)
        self.assertIs(unwrap(dd), d)

    def test_object_wrap(self):
        d = SampleData()
        dd = datawrap(d)

        self.assertEqual(dd["a"], 20)
        self.assertEqual(dd, {"a": 20, "b": 30})
        self.assertIs(unwrap(dd), dd)

    def test_object_wrap_w_deep_path(self):
        d = SampleData()
        d.a = Data(c=3)
        dd = datawrap(d)

        self.assertEqual(dd["a.c"], 3)
        self.assertEqual(dd, {"a": {"c": 3}, "b": 30})

    def test_deep_select(self):
        d = wrap([{"a": {"b": 1}}, {"a": {"b": 2}}])

        test = d.a.b
        self.assertEqual(test, [1, 2])

    def test_deep_select_list(self):
        d = wrap({"a": {"b": [{"c": 1}, {"c": 2}]}})

        test = d["a.b.c"]
        self.assertEqual(test, [1, 2])

    def test_set_default(self):
        a = {"x": {"y": 1}}
        b = {"x": {"z": 2}}
        c = {}
        d = set_default(c, a, b)

        self.assertTrue(unwrap(d) is c, "expecting first parameter to be returned")
        self.assertEqual(d.x.y, 1, "expecting d to have attributes of a")
        self.assertEqual(d.x.z, 2, "expecting d to have attributes of b")

        self.assertEqual(wrap(a).x.z, None, "a should not have been altered")

    def test_Dict_of_Dict(self):
        value = {"a": 1}
        wrapped = Data(Data(value))
        self.assertTrue(value is unwrap(wrapped), "expecting identical object")

    def test_leaves_of_mappings(self):
        a = wrap({"a": _TestMapping()})
        a.a.a = {"a": 1}
        a.a.b = {"b": 2}

        leaves = wrap(dict(a.leaves()))
        self.assertEqual(a.a.a['a'], leaves["a\.a\.a"], "expecting 1")
        self.assertEqual(a.a.b['b'], leaves["a\.b\.b"], "expecting 2")

    def test_null_set_index(self):
        temp = Null
        # expecting no crash
        temp[0] = 1
        temp[1] = None

    def test_deep_null_assignment(self):
        temp = wrap({"a": 0})
        e = temp.e
        e.s.t = 1
        e.s.s = 2
        self.assertEqual(temp, {"a": 0, "e": {"s": {"s": 2, "t": 1}}}, "expecting identical")

    def test_null_inequalities(self):
        self.assertEqual(Null < 1, None)
        self.assertEqual(Null <= 1, None)
        self.assertEqual(Null != 1, None)
        self.assertEqual(Null == 1, None)
        self.assertEqual(Null >= 1, None)
        self.assertEqual(Null > 1, None)

        self.assertEqual(1 < Null, None)
        self.assertEqual(1 <= Null, None)
        self.assertEqual(1 != Null, None)
        self.assertEqual(1 == Null, None)
        self.assertEqual(1 >= Null, None)
        self.assertEqual(1 > Null, None)

        self.assertEqual(Null < Null, None)
        self.assertEqual(Null <= Null, None)
        self.assertEqual(Null != Null, False)
        self.assertEqual(Null == Null, True)
        self.assertEqual(Null >= Null, None)
        self.assertEqual(Null > Null, None)

        self.assertEqual(Null < None, None)
        self.assertEqual(Null <= None, None)
        self.assertEqual(Null != None, False)
        self.assertEqual(Null == None, True)
        self.assertEqual(Null >= None, None)
        self.assertEqual(Null > None, None)

        self.assertEqual(None < Null, None)
        self.assertEqual(None <= Null, None)
        self.assertEqual(None != Null, False)
        self.assertEqual(None == Null, True)
        self.assertEqual(None >= Null, None)
        self.assertEqual(None > Null, None)

    def test_escape_dot(self):
        self.assertAlmostEqual(literal_field("."), "\\.")
        self.assertAlmostEqual(literal_field("\\."), "\\\\.")
        self.assertAlmostEqual(literal_field("\\\\."), "\\\\\\.")
        self.assertAlmostEqual(literal_field("a.b"), "a\.b")
        self.assertAlmostEqual(literal_field("a\\.html"), "a\\\\.html")

    def test_set_default_unicode_and_list(self):
        a = {"a": "test"}
        b = {"a": [1, 2]}
        self.assertAlmostEqual(set_default(a, b), {"a": ["test", 1, 2]}, "expecting string, not list, nor some hybrid")

    def test_deepcopy(self):
        self.assertIs(deepcopy(Null), Null)
        self.assertEqual(deepcopy(Data()), {})
        self.assertEqual(deepcopy(Data(a=Null)), {})

    def test_null_type(self):
        self.assertIs(Null.__class__, NullType)
        self.assertTrue(isinstance(Null, NullType))

    def test_null_assign(self):
        output = Null
        output.changeset.files = None

    def test_string_assign(self):
        def test():
            a = wrap({"a": "world"})
            a["a.html"] = "value"

        self.assertRaises(Exception, test, "expecting error")

    def test_string_assign_null(self):
        a = wrap({"a": "world"})
        a["a.html"] = None

    def test_empty_object_is_not_null(self):
        self.assertFalse(wrap({}) == None, "expect empty objects to not compare well with None")

    def test_add_null_to_list(self):
        expected = wrap(["test", "list"])
        test = expected + None
        self.assertEqual(test, expected, "expecting adding None to list does not change list")

    def test_pop(self):
        l = wrap([1, 2, 3, 4])

        self.assertEquals(l.pop(3), 4)
        self.assertEquals(l.pop(0), 1)
        self.assertEquals(l.pop(1), 3)
        self.assertEquals(l.pop(), 2)

    def test_values(self):
        a = wrap({"a": 1, "b": 2})
        result = []
        for v in a.values():
            result.append(v)

        expected = {1, 2}
        self.assertAlmostEqual(result, expected)

    def test_wrap_wrap(self):
        a = wrap({"a": 1, "b": 2})
        b = wrap(a)

        self.assertIs(a, b, "expecting same object")

    def test_key_in_data(self):
        a = wrap({"key": {}})
        self.assertIn("key", a)


class _TestMapping(object):
    def __init__(self):
        self.a = None
        self.b = None


class SampleData(object):

    def __init__(self):
        self.a = 20
        self.b = 30

    def __str__(self):
        return str(self.a) + str(self.b)
