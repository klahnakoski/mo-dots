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

from mo_testing.fuzzytestcase import FuzzyTestCase

from mo_dots import relative_field, tail_field


class TestFields(FuzzyTestCase):
    def test_relative(self):
        self.assertEqual(relative_field("testing", "testing"), ".")

    def test_tail_field(self):
        value, tail = tail_field("meta\\.stats")
        expected = "meta.stats"

        self.assertEqual(value, expected, "expecting identical")
