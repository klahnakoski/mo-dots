# encoding: utf-8
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.
#
# Author: Kyle Lahnakoski (kyle@lahnakoski.com)
#

from __future__ import absolute_import, division, unicode_literals

from collections import Mapping

from mo_future import text_type, none_type
from mo_logs import Log
from mo_math.randoms import Random
from mo_testing.fuzzytestcase import FuzzyTestCase
from mo_times import Timer

from mo_dots import Data, Null, wrap, NullType, FlatList, data_types
from speedtest_dot import MAPPING_TYPES


class TestDotSpeed(FuzzyTestCase):

    def test_simple_access(self):
        times = range(1000*1000)
        x = wrap({"a": {"b": 42}})
        y = Dummy({"b": 42})

        with Timer("slot access") as slot:
            for i in times:
                k = y.a

        with Timer("attribute access") as att:
            for i in times:
                k = x.a

        with Timer("property access access") as prop:
            for i in times:
                k = x.a

        Log.note("attribute access is {{t|round(places=2)}}x faster", t=(att.duration.seconds+prop.duration.seconds)/2/slot.duration.seconds)

    def test_compare_isinstance_to_class_checks(self):
        num = 1 * 1000 * 1000
        options = {
            0: lambda: {},
            1: lambda: Data(),
            2: lambda: Null,
            3: lambda: 6,
            4: lambda: "string"

        }
        data = [options[Random.int(len(options))]() for _ in range(num)]

        with Timer("isinstance check") as i_time:
            i_result = [isinstance(d, Mapping) for d in data]

        with Timer("set check") as s_time:
            s_result = [d.__class__ in MAPPING_TYPES for d in data]

        with Timer("eq check") as e_time:
            e_result = [d.__class__ is Data or d.__class__ is dict for d in data]

        with Timer("name check") as n_time:
            n_result = [is_instance(d, Data) or is_instance(d, dict) for d in data]

        with Timer("check w method") as m_time:
            m_result = [is_mapping(d) for d in data]

        self.assertEqual(s_result, i_result)
        self.assertEqual(m_result, i_result)
        self.assertEqual(e_result, i_result)
        self.assertEqual(n_result, i_result)

        self.assertGreater(i_time.duration, s_time.duration)
        self.assertGreater(m_time.duration, s_time.duration)

    def test_compare_isinstance_to_text(self):
        num = 1 * 1000 * 1000
        options = {
            0: lambda: 6,
            1: lambda: "string"
            # 2: lambda: {},
            # 3: lambda: Data(),
            # 4: lambda: Null,

        }
        data = [options[Random.int(len(options))]() for _ in range(num)]

        with Timer("isinstance check") as i_time:
            i_result = [isinstance(d, text_type) for d in data]

        with Timer("set check") as s_time:
            s_result = [d.__class__ in (text_type,) for d in data]

        with Timer("eq check") as e_time:
            e_result = [d.__class__ is text_type for d in data]

        with Timer("name check") as n_time:
            n_result = [is_instance(d, text_type) for d in data]

        with Timer("check w method") as m_time:
            m_result = [is_text(d) for d in data]

        self.assertEqual(s_result, i_result)
        self.assertEqual(m_result, i_result)
        self.assertEqual(e_result, i_result)
        self.assertEqual(n_result, i_result)

        self.assertGreater(i_time.duration, s_time.duration)
        self.assertGreater(m_time.duration, s_time.duration)

        Log.note("is_text check is {{t|round(places=2)}}x faster than isinstance", t=i_time.duration.seconds/m_time.duration.seconds)

    def test_null_compare(self):
        values = Random.sample([None, Null, {}, Data(), Data(a="b"), [], FlatList()], 1000*1000)

        with Timer("is compare") as is_time:
            for v in values:
                v is None

        with Timer("equal compare") as eq_time:
            eq_result = [v == None for v in values]

        with Timer("method compare") as me_time:
            me_result = [is_null(v) for v in values]

        self.assertAlmostEqual(me_result, eq_result, "expecting compare to be the same")

        Log.note("is_null compare is {{t|round(places=2)}}x faster", t=me_time.duration.seconds/eq_time.duration.seconds)
        Log.note("is compare is {{t|round(places=2)}}x faster", t=me_time.duration.seconds/is_time.duration.seconds)


def is_null(t):
    class_ = t.__class__
    if class_ in (none_type, NullType):
        return True
    elif class_ in data_types:
        return False
    elif class_ in (FlatList,) and not t:
        return True
    elif class_ is list:
        return False
    else:
        return t == None


def is_text(t):
    return t.__class__ is text_type


def is_mapping(d):
    return d.__class__ in MAPPING_TYPES


def is_instance(d, type_):
    return d.__class__.__name__ == type_.__name__


class Dummy(object):

    __slots__ = ["a"]

    def __init__(self, a):
        self.a = a


