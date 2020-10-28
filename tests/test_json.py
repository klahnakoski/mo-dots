# encoding: utf-8
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.
#
# Contact: Kyle Lahnakoski (kyle@lahnakoski.com)
#

from __future__ import absolute_import, division, unicode_literals

import json

from mo_testing.fuzzytestcase import FuzzyTestCase

from mo_dots import to_data, from_data


class TestJson(FuzzyTestCase):
    def test_use_standard_json_encode(self):
        a = to_data({"a": ["b", 1]})
        result = json.dumps(a, default=from_data)
        expected = '{"a": ["b", 1]}'
        self.assertEqual(result, expected)

    def test_flatlist(self):
        a = to_data(["b", 1])
        result = json.dumps(a, default=from_data)
        expected = '["b", 1]'
        self.assertEqual(result, expected)
