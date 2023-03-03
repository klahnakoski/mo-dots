# encoding: utf-8
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.
#
# Contact: Kyle Lahnakoski (kyle@lahnakoski.com)
#

import cProfile
import pstats

from mo_future import text, Mapping
from mo_math import randoms
from mo_testing.fuzzytestcase import FuzzyTestCase
from mo_threads import profiles
from mo_times import Timer

from mo_dots import Data, to_data, Null


class SpeedTestDot(FuzzyTestCase):
    def test_simple_access(self):
        """
        THIS WILL WRITE A STATS FILE TO THE PROJECT DIRECTORY
        """
        x = to_data({"a": {"b": 42}})

        cprofiler = cProfile.Profile()
        cprofiler.enable()
        for i in range(1000 * 1000):
            y = x.a
        cprofiler.disable()

        profiles.write_profiles(pstats.Stats(cprofiler))

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
        data = [options[randoms.int(len(options))]() for _ in range(num)]

        with Timer("isinstance check") as i_time:
            i_result = [isinstance(d, text) for d in data]

        with Timer("set check") as s_time:
            s_result = [d.__class__ in (text,) for d in data]

        with Timer("eq check") as e_time:
            e_result = [d.__class__ is text for d in data]

        with Timer("name check") as n_time:
            n_result = [is_instance(d, text) for d in data]

        with Timer("check w method") as m_time:
            m_result = [is_text(d) for d in data]

        self.assertEqual(s_result, i_result)
        self.assertEqual(m_result, i_result)
        self.assertEqual(e_result, i_result)
        self.assertEqual(n_result, i_result)

        self.assertGreater(i_time.duration, s_time.duration)
        self.assertGreater(m_time.duration, s_time.duration)


MAPPING_TYPES = (Data, dict)


def is_text(t):
    return t.__class__ is text


def is_mapping(d):
    return d.__class__ in MAPPING_TYPES


def is_instance(d, type_):
    return d.__class__.__name__ == type_.__name__
