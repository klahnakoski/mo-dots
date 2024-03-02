# encoding: utf-8
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.
#
# Contact: Kyle Lahnakoski (kyle@lahnakoski.com)
#

from __future__ import absolute_import, division, unicode_literals

import os
import sys
from collections import deque
from unittest import skipIf

from mo_future import text, Mapping
from mo_logs import Log
from mo_math import randoms
from mo_testing.fuzzytestcase import FuzzyTestCase
from mo_times import Timer

from mo_dots import (
    Data,
    Null,
    FlatList,
    data_types,
    is_data,
    to_data,
    from_data,
    split_field,
    is_null,
)

IS_TRAVIS = bool(os.environ.get("TRAVIS"))
IS_COVERAGE = bool(os.environ.get("COVERAGE"))

PY37 = sys.version_info[0] == 3 and sys.version_info[1] == 7
PY39 = sys.version_info[0] == 3 and sys.version_info[1] == 9


@skipIf(IS_TRAVIS or IS_COVERAGE, "no need to test speed on Travis")
class TestDotSpeed(FuzzyTestCase):
    def test_simple_access(self):
        times = range(1000 * 1000)
        x = to_data({"a": {"b": 42}})
        y = Dummy({"b": 42})

        with Timer("slot access") as slot:
            for i in times:
                k = y.a

        with Timer("attribute access") as att:
            for i in times:
                k = x.a

        with Timer("property access access") as prop:
            for i in times:
                k = x["a"]

        Log.info(
            "attribute access is {{t|round(places=2)}}x faster",
            t=(att.duration.seconds + prop.duration.seconds) / 2 / slot.duration.seconds,
        )

    def test_compare_isinstance_to_class_checks(self):
        num = 1 * 1000 * 1000
        options = {
            0: lambda: {},
            1: lambda: Data(),
            2: lambda: Null,
            3: lambda: 6,
            4: lambda: "string",
        }
        data = [options[randoms.int(len(options))]() for _ in range(num)]

        with Timer("Data: isinstance of Mapping check") as i_time:
            i_result = [isinstance(d, Mapping) for d in data]

        with Timer("Data: in data_types check") as s_time:
            s_result = [d.__class__ in data_types for d in data]

        with Timer("Data: is checks") as e_time:
            e_result = [d.__class__ is Data or d.__class__ is dict for d in data]

        with Timer("Data: is_instance checks") as n_time:
            n_result = [is_instance(d, Data) or is_instance(d, dict) for d in data]

        with Timer("Data: check w is_data()") as m_time:
            m_result = [is_data(d) for d in data]

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
            1: lambda: "string",
            2: lambda: {},
            3: lambda: Data(),
            4: lambda: Null,
        }
        data = [options[randoms.int(len(options))]() for _ in range(num)]
        text_types = (text,)

        with Timer("String: isinstance text_types check") as i_time:
            i_result = [isinstance(d, text_types) for d in data]

        with Timer("String: in text_types check") as s_time:
            s_result = [d.__class__ in text_types for d in data]

        with Timer("String: is check") as e_time:
            e_result = [d.__class__ is text for d in data]

        with Timer("String: is_instance of text check") as n_time:
            n_result = [is_instance(d, text) for d in data]

        with Timer("String: check w is_text method") as m_time:
            m_result = [is_text(d) for d in data]

        # TRY AGAIN
        with Timer("String: isinstance text_types check") as i_time:
            i_result = [isinstance(d, text_types) for d in data]

        with Timer("String: in text_types check") as s_time:
            s_result = [d.__class__ in text_types for d in data]

        with Timer("String: is check") as e_time:
            e_result = [d.__class__ is text for d in data]

        with Timer("String: is_instance of text check") as n_time:
            n_result = [is_instance(d, text) for d in data]

        with Timer("String: check w is_text method") as m_time:
            m_result = [is_text(d) for d in data]

        self.assertEqual(s_result, i_result)
        self.assertEqual(m_result, i_result)
        self.assertEqual(e_result, i_result)
        self.assertEqual(n_result, i_result)

        self.assertGreater(
            i_time.duration.total_seconds() * 1.2,
            s_time.duration.total_seconds(),
            msg="isinstance should be slower than __class__ in set",
        )

        self.assertGreater(
            m_time.duration.total_seconds() * 1.2,
            s_time.duration.total_seconds(),
            "is_text should be slower than isinstance check",
        )

        Log.info(
            "is_text check is {{t|round(places=2)}}x slower than isinstance",
            t=m_time.duration.total_seconds() / i_time.duration.total_seconds(),
        )

    def test_null_compare(self):
        values = randoms.sample([None, Null, {}, Data(), Data(a="b"), [], FlatList()], 1000 * 1000)

        with Timer("is compare") as is_time:
            for v in values:
                v is None

        with Timer("equal compare") as eq_time:
            eq_result = [v == None for v in values]

        with Timer("method compare") as me_time:
            me_result = [is_null(v) for v in values]

        self.assertAlmostEqual(me_result, eq_result, "expecting compare to be the same")

        Log.info(
            "is_null compare is {{t|round(places=2)}}x slower than `== None`",
            t=me_time.duration.seconds / eq_time.duration.seconds,
        )
        Log.info(
            "is_null compare is {{t|round(places=2)}}x slower than `is None`",
            t=me_time.duration.seconds / is_time.duration.seconds,
        )

    def test_from_data(self):
        num = 100 * 1000
        options = {0: Data(), 1: {}, 2: "string", 3: None, 4: Null}
        data = [options[randoms.int(len(options))] for _ in range(num)]

        with Timer("unwrap") as i_time:
            i_result = [from_data(d) for d in data]

    def test_compare_split_replace_vs_lists(self):
        data = []
        for i in range(1_000_000):
            d = "".join(randoms.sample("ab.\b\\", 8))

            try:
                s_result = split_field(d)
                data.append(d)
            except Exception:
                continue

            r_result = split_field_using_replace(d)
            d_result = split_using_double_replace(d)

            self.assertEqual(s_result, r_result, msg=f"problem with {d}")
            self.assertEqual(s_result, d_result, msg=f"problem with {d}")

        with Timer("using standard") as s_time:
            s_result = [split_field(d) for d in data]

        with Timer("using replace") as r_time:
            r_result = [split_field_using_replace(d) for d in data]

        with Timer("using double replace") as d_time:
            d_result = [split_using_double_replace(d) for d in data]

        with Timer("using iterator") as i_time:
            i_result = [split_using_double_replace(d) for d in data]

        # SECOND TIME TO VERIFY SPEED
        with Timer("using standard") as s_time:
            s_result = [split_field(d) for d in data]

        with Timer("using replace") as r_time:
            r_result = [split_field_using_replace(d) for d in data]

        with Timer("using double replace") as d_time:
            d_result = [split_using_double_replace(d) for d in data]

        with Timer("using iterator") as i_time:
            i_result = [split_using_double_replace(d) for d in data]

        self.assertEqual(r_result, s_result)
        self.assertEqual(d_result, s_result)
        self.assertEqual(i_result, s_result)


def is_text(t):
    return t.__class__ is text


def is_instance(d, type_):
    return d.__class__.__name__ == type_.__name__


class Dummy(object):

    __slots__ = ["a"]

    def __init__(self, a):
        self.a = a


def split_using_double_replace(field):
    """
    RETURN field AS ARRAY OF DOT-SEPARATED FIELDS
    """
    try:
        if field.startswith(".."):
            remainder = field.lstrip(".")
            back = len(field) - len(remainder) - 1
            return [".."] * back + [
                k.replace("\a\a", ".").replace("\b", ".") for k in remainder.replace("..", "\a\a").split(".") if k
            ]
        else:
            return [k.replace("\a\a", ".").replace("\b", ".") for k in field.replace("..", "\a\a").split(".") if k]
    except Exception as cause:
        return []


def split_field_using_replace(field):
    """
    RETURN field AS ARRAY OF DOT-SEPARATED FIELDS
    """
    try:
        if field.startswith(".."):
            remainder = field.lstrip(".")
            back = len(field) - len(remainder) - 1
            return [".."] * back + [k.replace("\b", ".") for k in remainder.replace("..", "\b").split(".") if k]
        else:
            return [k.replace("\b", ".") for k in field.replace("..", "\b").split(".") if k]
    except Exception as cause:
        return []


def split_field_using_iterator(field):
    output = deque()
    escape = False
    word = []
    for c in field:
        if escape:
            if c == ".":
                word.append(".")
            else:
                word.append("\\")
                word.append(c)
            escape = False
        else:
            if c == "\\":
                escape = True
            elif c == ".":
                output.append("".join(word))
                word = []
            else:
                word.append(c)
    output.append("".join(word))
    return output
