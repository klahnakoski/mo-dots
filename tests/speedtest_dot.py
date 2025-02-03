# encoding: utf-8
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at https://www.mozilla.org/en-US/MPL/2.0/.
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

        with Timer("Data: isinstance of Mapping check") as i_time:
            i_result = [isinstance(d, Mapping) for d in data]

        with Timer("Data: in data_types check") as s_time:
            s_result = [d.__class__ in datas.data_types for d in data]

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
        self.assertGreater(m_time.duration * 1.2, s_time.duration)


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

        if sys.version_info[:2] >= (3, 10):
            self.assertGreater(
                s_time.duration.total_seconds() * 1.2,
                i_time.duration.total_seconds(),
                msg="isinstance should be slower than __class__ in set",
            )
        else:
            self.assertGreater(
                i_time.duration.total_seconds() * 1.2,
                s_time.duration.total_seconds(),
                msg="isinstance should be faster than __class__ in set",
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


MAPPING_TYPES = (Data, dict)


def is_text(t):
    return t.__class__ is text


def is_mapping(d):
    return d.__class__ in MAPPING_TYPES


def is_instance(d, type_):
    return d.__class__.__name__ == type_.__name__
