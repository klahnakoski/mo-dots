# encoding: utf-8
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at https://www.mozilla.org/en-US/MPL/2.0/.
#
# Contact: Kyle Lahnakoski (kyle@lahnakoski.com)
#
# REFERENCE LEAKS IN THE HOT PATHS: EACH OPERATION MUST LEAVE THE REFCOUNTS
# OF THE OBJECTS IT TOUCHED, AND THE NUMBER OF GC-TRACKED OBJECTS, UNCHANGED.
# SEMANTICS PASS THE REST OF THE SUITE; A MISSED Py_DECREF ONLY SHOWS HERE.
import gc
import sys
import unittest

from mo_dots import Null, from_data, to_data

REPS = 5000
GROWTH_REPS = 2000
GROWTH_JITTER = 50  # INTERPRETER NOISE; A REAL LEAK GROWS BY ~GROWTH_REPS


class TestLeaks(unittest.TestCase):
    def setUp(self):
        self.inner = {"c": 42}
        self.value = ["payload"]
        self.d = {"a": {"b": self.inner}, "s": "text", "v": self.value, "n": None}
        self.w = to_data(self.d)
        self.rows = [{"name": "x", "value": 1}, None, {"name": "y", "value": 2}]
        self.fl = to_data(self.rows)
        self.tup = to_data(({"n": 1}, {"n": 2}))

    def assertNoLeak(self, op):
        watched = [self.d, self.inner, self.value, self.rows, Null, self.w, self.fl]
        for _ in range(100):  # WARMUP: CACHES, INTERNED KEYS
            op()
        before = [sys.getrefcount(o) for o in watched]
        for _ in range(REPS):
            op()
        after = [sys.getrefcount(o) for o in watched]
        deltas = [a - b for a, b in zip(after, before)]
        self.assertEqual(
            deltas, [0] * len(watched),
            f"refcount deltas {deltas} for (d, inner, value, rows, Null, w, fl)",
        )

        gc.collect()
        count = len(gc.get_objects())
        for _ in range(GROWTH_REPS):
            op()
        gc.collect()
        growth = len(gc.get_objects()) - count
        self.assertLess(growth, GROWTH_JITTER, f"{growth} tracked objects leaked")

    def test_harness_detects_growth(self):
        # THE HARNESS ITSELF MUST FAIL ON A REAL LEAK; A LIST IS ALWAYS
        # GC-TRACKED (AN EMPTY dict IS NOT, AND WOULD HIDE)
        sink = []
        with self.assertRaises(AssertionError):
            self.assertNoLeak(lambda: sink.append([]))

    def test_harness_detects_refcount(self):
        sink = []
        with self.assertRaises(AssertionError):
            self.assertNoLeak(lambda: sink.append(self.value))

    def test_attribute_reads(self):
        self.assertNoLeak(lambda: self.w.a)
        self.assertNoLeak(lambda: self.w.s)
        self.assertNoLeak(lambda: self.w.a.b.c)
        self.assertNoLeak(lambda: self.w.x.y.z)  # DEAD CHAIN OF NullType

    def test_getitem(self):
        self.assertNoLeak(lambda: self.w["a"])
        self.assertNoLeak(lambda: self.w["a.b.c"])
        self.assertNoLeak(lambda: self.w["a.q.r"])  # MISS MID-WALK
        self.assertNoLeak(lambda: self.w["a.3.x"])  # NUMERIC SEGMENT: BAIL TO PURE
        self.assertNoLeak(lambda: self.w[0])  # NON-str KEY: PURE

    def test_writes(self):
        def set_del():
            self.w["tmp"] = 1
            del self.w["tmp"]

        def set_none():  # ASSIGNING None IS DELETE
            self.w["tmp"] = 1
            self.w["tmp"] = None

        def set_attr():
            self.w.tmp = self.value
            self.w.tmp = None

        def set_dotted():
            self.w["deep.path"] = 1
            self.w["deep"] = None

        self.assertNoLeak(set_del)
        self.assertNoLeak(set_none)
        self.assertNoLeak(set_attr)
        self.assertNoLeak(set_dotted)

    def test_get_items_keys(self):
        self.assertNoLeak(lambda: self.w.get("a"))
        self.assertNoLeak(lambda: self.w.get("q"))
        self.assertNoLeak(lambda: self.w.get("q", 5))
        self.assertNoLeak(lambda: self.w.items())
        self.assertNoLeak(lambda: self.w.keys())

    def test_iteration_contains_len(self):
        self.assertNoLeak(lambda: list(self.w))
        self.assertNoLeak(lambda: "a" in self.w)
        self.assertNoLeak(lambda: "q" in self.w)
        self.assertNoLeak(lambda: len(self.w))
        self.assertNoLeak(lambda: bool(self.w))

    def test_null_operations(self):
        self.assertNoLeak(lambda: Null.a.b.c)
        self.assertNoLeak(lambda: Null[3])
        self.assertNoLeak(lambda: Null[1:2])
        self.assertNoLeak(lambda: Null == 5)
        self.assertNoLeak(lambda: Null != 5)
        self.assertNoLeak(lambda: Null | self.value)
        self.assertNoLeak(lambda: Null + [])
        self.assertNoLeak(lambda: Null - 1)
        self.assertNoLeak(lambda: -Null)
        self.assertNoLeak(lambda: str(Null))
        self.assertNoLeak(lambda: repr(Null))
        self.assertNoLeak(lambda: float(Null))
        self.assertNoLeak(lambda: len(Null))
        self.assertNoLeak(lambda: list(Null))
        self.assertNoLeak(lambda: Null())
        self.assertNoLeak(lambda: hash(Null))
        # LIVE CHAIN: NullType HOLDING THE PARENT dict, THEN COLLECTED
        self.assertNoLeak(lambda: self.w.missing.deeper)

    def test_conversions(self):
        self.assertNoLeak(lambda: to_data(self.d))
        self.assertNoLeak(lambda: to_data(self.rows))
        self.assertNoLeak(lambda: to_data(None))
        self.assertNoLeak(lambda: from_data(self.w))
        self.assertNoLeak(lambda: from_data(self.fl))
        self.assertNoLeak(lambda: from_data(Null))

    def test_flatlist_operations(self):
        self.assertNoLeak(lambda: self.fl.name)  # C COLUMN EXTRACT
        self.assertNoLeak(lambda: self.fl.get("name"))
        self.assertNoLeak(lambda: self.fl.get("q"))
        self.assertNoLeak(lambda: list(self.fl))
        self.assertNoLeak(lambda: len(self.fl))
        self.assertNoLeak(lambda: 5 in self.fl)
        self.assertNoLeak(lambda: self.rows[0] in self.fl)
        self.assertNoLeak(lambda: list(self.tup))
        self.assertNoLeak(lambda: len(self.tup))

    def test_error_paths(self):
        def tuple_contains():  # list.__contains__ ON A tuple SLOT RAISES
            try:
                1 in self.tup
            except TypeError:
                pass

        def missing_attr():  # FlatList SHADOWED NAME RAISES
            try:
                self.fl.__json__
            except AttributeError:
                pass

        self.assertNoLeak(tuple_contains)
        self.assertNoLeak(missing_attr)


if __name__ == "__main__":
    unittest.main()
