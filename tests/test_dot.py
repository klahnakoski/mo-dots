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

from copy import deepcopy, copy
from math import isnan

from mo_future import UserDict, first, Mapping
from mo_logs import Log
from mo_logs.strings import expand_template
from mo_math import MAX
from mo_testing.fuzzytestcase import FuzzyTestCase

from mo_dots import (
    to_data,
    Null,
    set_default,
    Data,
    literal_field,
    NullType,
    leaves_to_data,
    from_data,
    FlatList,
    get_attr,
    relative_field,
    unliteral_field,
    tail_field,
    join_field,
    set_attr,
    PATH_NOT_FOUND,
)
from mo_dots.datas import leaves
from mo_dots.objects import datawrap
from tests import ambiguous_test


class TestDot(FuzzyTestCase):
    def test_set_union_w_null(self):
        s = set("a")
        s |= Null
        self.assertAlmostEqual(s, set("a"))

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

    def test_kwargs(self):
        d = Data(a=1, b=2)

        def func(a, b):
            return a == 1, b == 2

        self.assertTrue(func(**d))

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
        c = a.b["test"]
        self.assertTrue(c == None)

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
        a = to_data({"a": 1, "b": {}})

        if a.a != 1:
            Log.error("error")
        if not isinstance(a.b, Mapping):
            Log.error("error")

    def test_get_class(self):
        a = to_data({})
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

        b = to_data(a)
        b.c = "test1"
        b.d.e = "test2"
        b.f.g.h = "test3"
        b.f.i = "test4"
        b.k["l.m.n"] = "test5"

        expected = {
            "c": "test1",
            "d": {"e": "test2"},
            "f": {"g": {"h": "test3"}, "i": "test4"},
            "k": {"l": {"m": {"n": "test5"}}},
        }
        self.assertEqual(a, expected)

    def test_assign2(self):
        a = {}

        b = to_data(a)
        b_c = b.c
        b.c.d = "test1"

        b_c.e = "test2"

        expected = {"c": {"d": "test1", "e": "test2"}}
        self.assertEqual(a, expected)

    def test_assign3(self):
        # IMPOTENT ASSIGNMENTS DO NOTHING
        a = {}
        b = to_data(a)

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
        b = to_data(a)
        b.c.d = None
        expected = {"c": {}}
        self.assertEqual(a, expected)

        a = {"c": {"d": {}}}
        b = to_data(a)
        b.c = None
        expected = {}
        self.assertEqual(a, expected)

    def test_assign5(self):
        a = {}
        b = to_data(a)

        b.c["d..e"].f = 2
        expected = {"c": {"d.e": {"f": 2}}}
        self.assertEqual(a, expected)

    def test_assign6(self):
        a = {}
        b = to_data(a)

        b["c.d.e..f"] = 1
        b["c.d.e..g"] = 2

        expected = {"c": {"d": {"e.f": 1, "e.g": 2}}}
        self.assertEqual(a, expected)

    def test_assign7(self):
        a = {}
        b = to_data(a)

        b["c.d.e..f"] = 1
        b["c.d.g..h"] = 2

        expected = {"c": {"d": {"e.f": 1, "g.h": 2}}}
        self.assertEqual(a, expected)

    def test_assign8(self):
        a = {}
        b = to_data(a)

        b["a"][literal_field(literal_field("b.html"))]["z"] = 3

        expected = {"a": {"b..html": {"z": 3}}}
        self.assertEqual(a, expected)

    def test_assign9(self):
        a = {}
        b = to_data(a)

        b["a"]["."] = 1

        expected = {"a": 1}
        self.assertEqual(a, expected)

    def test_setitem_and_deep(self):
        a = {}
        b = to_data(a)

        b.c["d"].e.f = 3
        expected = {"c": {"d": {"e": {"f": 3}}}}
        self.assertEqual(a, expected)

    def test_assign_and_use1(self):
        a = to_data({})
        agg = a.b
        agg.c = []

        v = agg.c
        agg.c.append("test value")

        self.assertEqual(a, {"b": {"c": ["test value"]}})
        self.assertEqual(a.b, {"c": ["test value"]})
        self.assertEqual(a.b.c, ["test value"])

    def test_assign_and_use2(self):
        a = to_data({})
        agg = a.b.c
        agg += []
        agg.append("test value")

        self.assertEqual(a, {"b": {"c": ["test value"]}})
        self.assertEqual(a.b, {"c": ["test value"]})
        self.assertEqual(a.b.c, ["test value"])

    def test_assign_and_use3(self):
        a = to_data({})
        agg = a.b
        agg.c += ["test value"]

        self.assertEqual(a, {"b": {"c": ["test value"]}})
        self.assertEqual(a.b, {"c": ["test value"]})
        self.assertEqual(a.b.c, ["test value"])

    def test_assign_none(self):
        a = {}
        A = to_data(a)

        A[None] = "test"
        self.assertEqual(a, {})

    def test_increment(self):
        a = {}
        b = to_data(a)
        b.c1.d += 1
        b.c2.e += "e"
        b.c3.f += ["f"]
        b["c..a"].d += 1

        self.assertEqual(a, {"c1": {"d": 1}, "c2": {"e": "e"}, "c3": {"f": ["f"]}, "c.a": {"d": 1}})

        b.c1.d += 2
        b.c2.e += "f"
        b.c3.f += ["g"]
        b["c..a"].d += 3
        self.assertEqual(
            a, {"c1": {"d": 3}, "c2": {"e": "ef"}, "c3": {"f": ["f", "g"]}, "c.a": {"d": 4},},
        )

    def test_slicing(self):
        def diff(record, index, records):
            """
            WINDOW FUNCTIONS TAKE THE CURRENT record, THE index THAT RECORD HAS
            IN THE WINDOW, AND THE (SORTED) LIST OF ALL records
            """
            # COMPARE CURRENT VALUE TO MAX OF PAST 5, BUT NOT THE VERY LAST ONE
            try:
                return record - MAX(records[index - 6 : index - 1 :])
            except Exception as e:
                return None

        data1_list = [1, 2, 3, 4, 5, 6, 7, 8, 9]
        result1 = [diff(r, i, data1_list) for i, r in enumerate(data1_list)]
        assert result1 == [
            -7,
            None,
            None,
            None,
            None,
            None,
            2,
            2,
            2,
        ]  # WHAT IS EXPECTED, BUT NOT WHAT WE WANT

        data2_list = to_data(data1_list)
        result2 = [diff(r, i, data2_list) for i, r in enumerate(data2_list)]
        assert result2 == [None, None, 2, 2, 2, 2, 2, 2, 2]

    def test_delete1(self):
        a = to_data({"b": {"c": 1}})

        del a.b.c
        self.assertEqual({"b": {}}, a)
        self.assertEqual(a, {"b": {}})

        a = to_data({"b": {"c": 1}})

        a.b.c = None
        self.assertEqual({"b": {}}, a)
        self.assertEqual(a, {"b": {}})

    def test_delete2(self):
        a = to_data({"b": {"c": 1, "d": 2}})

        del a.b.c
        self.assertEqual({"b": {"d": 2}}, a)
        self.assertEqual(a, {"b": {"d": 2}})
        a = to_data({"b": {"c": 1, "d": 2}})

        a.b.c = None
        self.assertEqual({"b": {"d": 2}}, a)
        self.assertEqual(a, {"b": {"d": 2}})

    def test_wrap(self):
        d = {}
        dd = to_data(d)
        self.assertIs(from_data(dd), d)

    def test_object_wrap(self):
        d = SampleData()
        dd = datawrap(d)

        self.assertEqual(dd["a"], 20)
        self.assertEqual(dd, {"a": 20, "b": 30})
        self.assertIs(from_data(dd), d)

    def test_object_wrap_w_deep_path(self):
        d = SampleData()
        d.a = Data(c=3)
        dd = datawrap(d)

        self.assertEqual(dd["a.c"], 3)
        self.assertEqual(dd, {"a": {"c": 3}, "b": 30})

    def test_deep_select(self):
        d = to_data([{"a": {"b": 1}}, {"a": {"b": 2}}])

        test = d.a.b
        self.assertEqual(test, [1, 2])

    def test_deep_select_list(self):
        d = to_data({"a": {"b": [{"c": 1}, {"c": 2}]}})

        test = d["a.b.c"]
        self.assertEqual(test, [1, 2])

    def test_set_default1(self):
        a = {"x": {"y": 1}}
        b = {"x": {"z": 2, "y": None}}
        c = {}
        d = set_default(c, a, b)

        self.assertIs(from_data(d), c)
        self.assertEqual(d.x.y, 1, "expecting d to have attributes of a")
        self.assertEqual(d.x.z, 2, "expecting d to have attributes of b")

        self.assertEqual(to_data(a).x.z, None, "a should not have been altered")

    def test_set_default2(self):
        a = {"x": {"y": 1}}
        b = {"x": {"z": 2}}
        c = {}
        d = set_default(c, None, a, b)

        self.assertIs(from_data(d), c)
        self.assertEqual(d.x.y, 1, "expecting d to have attributes of a")
        self.assertEqual(d.x.z, 2, "expecting d to have attributes of b")

        self.assertEqual(to_data(a).x.z, None, "a should not have been altered")

    def test_set_default3(self):
        a = {"x": {"y": 1}}
        b = {"x": {"z": 2}}
        c = {}
        d = set_default(None, c, a, b)

        self.assertIsNot(from_data(d), c)
        self.assertEqual(d.x.y, 1, "expecting d to have attributes of a")
        self.assertEqual(d.x.z, 2, "expecting d to have attributes of b")

        self.assertEqual(to_data(a).x.z, None, "a should not have been altered")

    def test_or(self):
        a = {"x": {"y": 1}}
        b = {"x": {"z": 2}}
        c = Data()
        d = c | a | b

        self.assertEqual(d.x.y, 1, "expecting d to have attributes of a")
        self.assertEqual(d.x.z, 2, "expecting d to have attributes of b")

        self.assertEqual(to_data(a).x.z, None, "a should not have been altered")

    def test_Data_of_Data(self):
        value = {"a": 1}
        wrapped = to_data(to_data(value))
        self.assertTrue(value is from_data(wrapped), "expecting identical object")

    def test_leaves_of_mappings(self):
        a = to_data({"a": _TestMapping()})
        a.a.a = {"a": 1}
        a.a.b = {"b": 2}

        leaves = to_data(dict(a.leaves()))
        self.assertEqual(a.a.a["a"], leaves["a..a..a"], "expecting 1")
        self.assertEqual(a.a.b["b"], leaves["a..b..b"], "expecting 2")

    def test_null_set_index(self):
        temp = Null
        # expecting no crash
        temp[0] = 1
        temp[1] = None

    def test_deep_null_assignment(self):
        temp = to_data({"a": 0})
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
        self.assertAlmostEqual(literal_field("."), "\b")
        self.assertAlmostEqual(literal_field(".."), "\b\b")
        self.assertAlmostEqual(literal_field("..."), "\b..\b")
        self.assertAlmostEqual(literal_field("a.b"), "a..b")
        self.assertAlmostEqual(literal_field("a..html"), "a....html")

    def test_set_default_unicode_and_list(self):
        a = {"a": "test"}
        b = {"a": [1, 2]}
        self.assertAlmostEqual(
            set_default(a, b), {"a": ["test", 1, 2]}, "expecting string, not list, nor some hybrid",
        )

    def test_unicode_or_list(self):
        a = to_data({"a": "test"})
        b = {"a": [1, 2]}
        self.assertAlmostEqual(a | b, {"a": "test"}, "expecting string, not list, nor some hybrid")
        self.assertAlmostEqual(b | a, {"a": [1, 2]}, "expecting list")

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
            a = to_data({"a": "world"})
            a["a.html"] = "value"

        self.assertRaises(Exception, test, "expecting error")

    def test_string_assign_null(self):
        a = to_data({"a": "world"})
        a["a.html"] = None

    def test_empty_object_is_not_null1(self):
        self.assertFalse(to_data({}) == None, "expect empty objects to not equal None")

    def test_empty_object_is_not_null2(self):
        self.assertTrue(to_data({}) != None, "expect empty objects to not equal None")

    def test_add_null_to_list(self):
        expected = to_data(["test", "list"])
        test = expected + None
        self.assertEqual(test, expected, "expecting adding None to list does not change list")

    def test_pop_list(self):
        l = to_data([1, 2, 3, 4])

        self.assertEqual(l.pop(3), 4)
        self.assertEqual(l.pop(0), 1)
        self.assertEqual(l.pop(1), 3)
        self.assertEqual(l.pop(), 2)

    def test_pop_dict(self):
        d = to_data({"a": 1, "b": 2, "c": 3})

        self.assertAlmostEqual(d.pop("a"), 1)
        self.assertAlmostEqual({"b": 2, "c": 3}, d)
        self.assertAlmostEqual(d.pop("c"), 3)
        self.assertAlmostEqual({"b": 2}, d)
        self.assertAlmostEqual(d.pop("b"), 2)
        self.assertAlmostEqual({}, d)

    def test_values(self):
        a = to_data({"a": 1, "b": 2})
        result = []
        for v in a.values():
            result.append(v)

        expected = {1, 2}
        self.assertAlmostEqual(result, expected)

    def test_wrap_wrap(self):
        a = to_data({"a": 1, "b": 2})
        b = to_data(a)

        self.assertIs(a, b, "expecting same object")

    def test_key_in_data(self):
        a = to_data({"key": {}})
        self.assertIn("key", a)

    def test_list_eq(self):
        a = to_data([{"a": 1}])
        b = to_data([])
        c = to_data([])

        self.assertFalse(a == b)
        self.assertTrue(a == a)
        self.assertTrue(b == b)
        self.assertTrue(b == c)
        self.assertTrue(b == None)
        self.assertTrue(b == Null)
        self.assertTrue(None == b)
        self.assertTrue(Null == b)

    def test_add_1(self):
        a = to_data({"a": 1, "y": {"b": 4, "c": [5]}})
        b = to_data({"a": 1, "x": 5, "y": {"b": 6, "c": [12]}})

        expected_ab = {"a": 2, "x": 5, "y": {"b": 10, "c": [5, 12]}}
        expected_ba = {"a": 2, "x": 5, "y": {"b": 10, "c": [12, 5]}}
        self.assertEqual(a + b, expected_ab)
        self.assertEqual(b + a, expected_ba)

        a += b
        self.assertEqual(a, expected_ab)

    def test_add_2(self):
        a = to_data({"a": 1, "y": {"b": 4, "c": [5]}})
        b = to_data({"a": 1, "x": 5, "y": {"b": 6, "c": 12}})

        expected_ab = {"a": 2, "x": 5, "y": {"b": 10, "c": [5, 12]}}
        expected_ba = {"a": 2, "x": 5, "y": {"b": 10, "c": [12, 5]}}
        self.assertEqual(a + b, expected_ab)
        self.assertEqual(b + a, expected_ba)

        a += b
        self.assertEqual(a, expected_ab)

    def test_list_get(self):
        flat_list = to_data([{"a": 1}, {"a": None}])
        # THIS IS NOT AN OPTION BECAUSE [] IS RESERVED FOR INDEXING AND SLICING
        self.assertEqual(flat_list["a"], None)

    def test_copy1(self):
        a = Data(b="c")
        aa = a.copy()
        self.assertEqual(aa, a, "expecting to be the same")
        self.assertEqual(a, aa, "expecting to be the same")

        a.b = "d"
        self.assertNotEqual(a, aa, "expecting to be different now")
        self.assertNotEqual(aa, a, "expecting to be different now")

    def test_copy2(self):
        a = Data(b="c")
        aa = copy(a)
        self.assertEqual(aa, a, "expecting to be the same")
        self.assertEqual(a, aa, "expecting to be the same")

        a.b = "d"
        self.assertNotEqual(a, aa, "expecting to be different now")
        self.assertNotEqual(aa, a, "expecting to be different now")

    def test_copy_value(self):
        a = to_data({})
        a["."] = "test"

        aa = a.copy()
        self.assertEqual(aa, a, "expecting to be the same")
        self.assertEqual(a, aa, "expecting to be the same")

    def test_in(self):
        a = {"_id": "yes"}
        b = {"id": "no"}
        aa = to_data(a)
        bb = to_data(b)

        self.assertEqual("_id" in aa, "_id" in a)
        self.assertEqual("_id" in bb, "_id" in b)

    def test_in_null(self):
        self.assertIn(Null, [None])

    def test_in_none(self):
        self.assertIn(None, [Null])

    def test_none_and_null_in_dict(self):
        d = {None: None, Null: None}
        self.assertEqual(len(d), 1)

    def test_none_and_null_compare_with_list(self):
        empty = to_data([])

        self.assertTrue([] == Null)
        self.assertTrue(empty == Null)
        self.assertTrue(empty == None)

    def test_none_and_magic(self):
        # self.assertIs(int(Null), Null)
        # self.assertIs(float(Null), Null)
        self.assertEqual(list(Null), Null)

    def test_keys(self):
        a = to_data({"a.b": "c"})
        self.assertEqual(a.keys(), {"a.b"})

    def test_items(self):
        a = to_data({"a.b": "c"})
        self.assertEqual(a.items(), [("a.b", "c")])

    def test_iteritems(self):
        a = to_data({"a.b": "c"})
        self.assertEqual(list(a.iteritems()), [("a.b", "c")])

    def test_update_complex(self):
        a = Data(a=1, b={"c": 0})
        b = Data(b={"d": 3})
        result = a | b
        self.assertEqual(result, {"a": 1, "b": {"c": 0, "d": 3}})

    def test_string_using_leaves(self):
        result = leaves_to_data("test")
        self.assertNotIsInstance(result, Data)
        self.assertEqual(result, "test")

    def test_leaves_returns_flat_list(self):
        x = to_data({"a": [1, 2, 3]})
        self.assertIsInstance(first(x.leaves())[1], FlatList)

    def test_leaves_returns_flat_list(self):
        x = to_data([{"a": [1, 2, 3]}])
        self.assertIsInstance(x, FlatList)

    def test_leaves_returns_inner(self):
        x = leaves_to_data({"a.b.c": 3, "\b": 42, "d": None})
        self.assertEqual(x, {"a": {"b": {"c": 3}}, ".": 42})

    def test_empty_string_is_bad(self):
        with self.assertRaises(Exception):
            leaves_to_data({"": 4})

    def test_leaves_w_Data(self):
        x = leaves_to_data({"a": to_data({"b.c": 42})})
        self.assertEqual(x, {"a": {"b": {"c": 42}}})

    def test_leaves_w_simple(self):
        x = leaves_to_data(42)
        self.assertEqual(x, 42)

        x = leaves_to_data([42, 0])
        self.assertEqual(x, [42, 0])

    def test_leaves_on_dict(self):
        x = list(leaves({"a": to_data({"b.c": 42})}))
        self.assertEqual(x, [("a.b..c", 42)])

    def test_leaves_on_dict_w_prefix(self):
        x = leaves({"a": to_data({"b.c": 42})}, prefix="::")
        self.assertEqual(x, [("::a.b..c", 42)])

    def test_to_generator(self):
        def gen():
            yield 1
            yield 2

        x = to_data(gen())
        self.assertIsInstance(x, FlatList)
        self.assertEqual(len(x), 2)

    def test_get_module_attr(self):
        x = get_attr(ambiguous_test, "d")
        self.assertEqual(x, {"a": 44})

    def test_get_module_attr_ambiguous(self):
        with self.assertRaises(Exception):
            x = get_attr(ambiguous_test, "DE")

    def test_get_module_attr_lowercase(self):
        x = get_attr(ambiguous_test, "d")
        y = get_attr(ambiguous_test, "D")
        self.assertIs(x, y)

    def test_set_module_attr(self):
        old, Log.main_log = Log.main_log, StructuredLogger_usingList()
        set_attr(ambiguous_test, "d1", "test")
        new, Log.main_log = Log.main_log, old
        self.assertIn(PATH_NOT_FOUND, new.lines[0])
        self.assertEqual(ambiguous_test.d1, "test")

    def test_relative(self):
        self.assertEqual(relative_field("a.b.c", "."), "a.b.c")
        self.assertEqual(relative_field("a.b.c", "a"), "b.c")
        self.assertEqual(relative_field("a.b.c", "a.b"), "c")
        self.assertEqual(relative_field("a.b.c", "a.b.c"), ".")
        self.assertEqual(relative_field("a.b.c", "a.b.c.d"), "..")
        self.assertEqual(relative_field("a.b.c", "a.b.c.d.e"), "...")

        self.assertEqual(relative_field("a.b.c.k", "a.b.c"), "k")
        self.assertEqual(relative_field("a.b.c.k", "a.b.c.d"), "..k")
        self.assertEqual(relative_field("a.b.c.k", "a.b.c.d.e"), "...k")

    def test_unliteral(self):
        for f in (".", "..", "a", "a.b", "..a.b", "", "a.."):
            self.assertEqual(unliteral_field(literal_field(f)), f)

    def test_tail_field(self):
        self.assertEqual(tail_field(None), (".", "."))
        self.assertEqual(tail_field(""), (".", "."))
        self.assertEqual(tail_field("."), (".", "."))
        self.assertEqual(tail_field(".."), ("..", "."))
        self.assertEqual(tail_field("..."), ("..", ".."))
        self.assertEqual(tail_field("...."), ("..", "..."))
        self.assertEqual(tail_field("a"), ("a", "."))
        self.assertEqual(tail_field("a.b"), ("a", "b"))
        self.assertEqual(tail_field("a.b.c."), ("a", "b.c"))

    def test_join_field_generator(self):
        def gen():
            yield "a"
            yield "b"

        self.assertEqual(join_field(gen()), "a.b")

    def test_hash(self):
        k1 = to_data({"a": 1, "b": 2})
        k2 = to_data({"a": 1, "b": 2})
        x = {k1: "42"}

        self.assertEqual(x[k1], x[k2])

        k1 = to_data([{"a": 1}, {"b": 2}])
        k2 = to_data([{"a": 1}, {"b": 2}])
        x = {k1: "42"}

        self.assertEqual(x[k1], x[k2])

    def test_bool(self):
        a = to_data({})
        b = to_data([])
        c = to_data("")
        d = Data()
        d["."] = None
        e = Data()
        e["."] = 0

        self.assertEqual(bool(a), True)
        self.assertEqual(bool(b), False)
        self.assertEqual(bool(c), False)
        self.assertEqual(bool(d), False)
        self.assertEqual(bool(e), True)

    def test_iter(self):
        a = to_data({})
        self.assertEqual(list(a), [])

        b = to_data({"a": 42})
        self.assertEqual(list(iter(b)), [("a", 42)])

    def test_null(self):
        with self.assertRaises(Exception):
            int(Null)

        result = float(Null)
        self.assertTrue(isnan(result))

        self.assertFalse(bool(Null))
        self.assertFalse(len(Null))

        self.assertEqual([1] + Null, [1])
        self.assertEqual(Null + [1], [1])

        self.assertTrue(1 + Null == None)
        self.assertTrue(Null + 1 == None)
        self.assertTrue(Null + Null == None)
        self.assertTrue(Null() == None)
        self.assertTrue(Null - 1 == None)
        self.assertTrue(1 - Null == None)
        self.assertTrue(Null * 1 == None)
        self.assertTrue(1 * Null == None)
        self.assertTrue(Null / 1 == None)
        self.assertTrue(1 / Null == None)
        self.assertTrue(Null / 1.2 == None)
        self.assertTrue(1.2 / Null == None)
        self.assertTrue(Null // 1 == None)
        self.assertTrue(1 // Null == None)
        self.assertTrue(Null | 1 == 1)
        self.assertTrue(1 | Null == 1)
        self.assertTrue(Null ^ 1 == None)
        self.assertTrue(1 ^ Null == None)
        self.assertTrue(Null & 1 == None)
        self.assertTrue(1 & Null == None)
        self.assertFalse(Null & False)
        self.assertFalse(False & Null)
        self.assertTrue((1 > Null) == None)
        self.assertTrue((1 >= Null) == None)
        self.assertTrue((1 <= Null) == None)
        self.assertTrue((1 < Null) == None)
        self.assertTrue(-Null == None)
        self.assertTrue(copy(Null) == Null)
        self.assertTrue(Null[1:3] == Null)
        self.assertTrue(Null[1] == Null)
        self.assertTrue(Null.__div__(0) == None)
        self.assertTrue(Null.__rdiv__(0) == None)
        self.assertTrue(Null.__itruediv__(0) == None)

        x = Null
        x += Null
        self.assertTrue(x == None)

        x = to_data({}).a.b.c
        x += 3
        self.assertTrue(x == 3)

    def test_get_zero(self):
        self.assertEqual(get_attr({"a": [{"b": 2}, 2]}, "a.0.b"), 2)

    def test_set_attr1(self):
        d = {"a": [{"b": 3}, 2]}
        set_attr(d, "a.0.b", 2)
        self.assertEqual(to_data(d).a[0].b, 2)

    def test_set_attr2(self):
        old, Log.main_log = Log.main_log, StructuredLogger_usingList()
        set_attr(None, "a", 2)
        new, Log.main_log = Log.main_log, old
        self.assertIn(PATH_NOT_FOUND, new.lines[0])

    def test_set_attr3(self):
        x = SampleData()
        x.a = SampleData()
        set_attr(x, "a.a", "q")
        self.assertEqual(x.a.a, "q")

        set_attr(x, "a.a", None)
        self.assertEqual(x.a.a, None)

        set_attr(x, "a", 42)
        self.assertEqual(x.a.a, 42)

        x.b = {}
        set_attr(x, "b", None)
        self.assertTrue(x.b == None)

    def test_none_item(self):
        self.assertIsInstance(to_data({"a": 1})[None], NullType)

    def test_assign_to_dot(self):
        x = to_data({"a": 1})
        x["."] = 42
        self.assertEqual(x["."], 42)

    def test_assign_list_to_dot(self):
        x = to_data({"a": 1})
        x["."] = ["a", "b"]
        self.assertEqual(x["."], ["a", "b"])

    def test_repr(self):
        self.assertEqual(repr(to_data({"a": 1})), "to_data({'a': 1})")

    def test_repr2(self):
        d = {}
        for i in range(3):
            d = {"a": d}
        d = to_data(d)
        self.assertEqual(eval(repr(d)), d)

    def test_repr3(self):
        d = Data()
        for i in range(3):
            d = Data(a=d)
        self.assertEqual(repr(d), "to_data({'a': to_data({'a': to_data({'a': to_data({})})})})")

    def test_add_one_to_dict(self):
        x = to_data({"a": {"b": 42}})
        with self.assertRaises(Exception):
            x += {"a": 1}

    def test_add_dict_to_one(self):
        x = to_data({"a": 1})
        with self.assertRaises(Exception):
            x += {"a": {"b": 42}}

    def test_add_dict_to_list(self):
        x = to_data({"a": [1]})
        x += {"a": {"b": 42}}
        self.assertEqual(x, {"a": [1, {"b": 42}]})

    def test_add_str_to_dict(self):
        x = to_data({"a": {"b": 42}})
        with self.assertRaises(Exception):
            x += {"a": "test"}

    def test_add_dict_to_str(self):
        x = to_data({"a": "test"})
        with self.assertRaises(Exception):
            x += {"a": {"b": 42}}

    def test_add_str_to_str(self):
        x = to_data({"a": "test"})
        with self.assertRaises("has no attribute 'append'"):
            x += {"a": "world"}

    def test_iadd(self):
        x = Data()
        x["."]["."] += [42]
        self.assertEqual(x, [42])

    def test_leaves1(self):
        result = leaves_to_data({"a": "hi", "a.b": "test"})
        self.assertEqual(result, {"a": {"b": "test"}})

    def test_leaves2(self):
        result = leaves_to_data({".": "hi"})
        self.assertEqual(result, "hi")

    def test_leaves3(self):
        result = leaves_to_data({".": "hi", "a": 42})
        self.assertEqual(result, {"a": 42})

    def test_leaves4(self):
        result = leaves_to_data({"a": 42, ".": "hi"})
        self.assertEqual(result, {"a": 42})

    def test_leaves5(self):
        data = Data()
        data["."] = "hi"
        b = Data(a=data)

        result = list(b.leaves())
        self.assertEqual(result, [("a", "hi")])

    def test_float(self):
        data = Data()
        data.a = float(data.a)
        self.assertTrue(data.a == None)


class _TestMapping(object):
    def __init__(self):
        self.a = None
        self.b = None


class SampleData(object):
    def __init__(self, a=None):
        self.a = a or 20
        self.b = 30

    def __str__(self):
        return str(self.a) + str(self.b)


class StructuredLogger_usingList(object):
    def __init__(self):
        self.lines = []

    def write(self, template, params):
        self.lines.append(expand_template(template, params))

    def stop(self):
        pass
