# encoding: utf-8
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.
#
# Contact: Kyle Lahnakoski (kyle@lahnakoski.com)
#

import os
import sys
from collections import deque
from unittest import skipIf

from mo_dots import datas
from mo_future import text, Mapping
from mo_logs import Log
from mo_math import randoms
from mo_testing.fuzzytestcase import FuzzyTestCase
from mo_times import Timer

from mo_dots import *

IS_CI = bool(os.environ.get("TRAVIS") or os.environ.get("CI"))
IS_COVERAGE = bool(os.environ.get("COVERAGE"))

PY37 = sys.version_info[0] == 3 and sys.version_info[1] == 7
PY39 = sys.version_info[0] == 3 and sys.version_info[1] == 9


@skipIf(IS_CI or IS_COVERAGE, "no need to test speed on Travis")
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

    def test_null_compare(self):
        values = randoms.sample([None, Null, {}, Data(), Data(a="b"), [], FlatList()], 1000 * 1000)

        with Timer("is compare") as is_time:
            for v in values:
                v is None

        with Timer("equal compare") as eq_time:
            eq_result = [v == None for v in values]

        with Timer("method compare") as me_time:
            me_result = [is_null(v) for v in values]

        self.assertAlmostEqual(me_result, eq_result, "expecting compare to be the same", places=1.5)

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
