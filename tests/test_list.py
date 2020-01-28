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

from mo_dots import wrap, Null
from mo_testing.fuzzytestcase import FuzzyTestCase

from mo_dots.lists import last

values = [1, 2, 3]


class TestList(FuzzyTestCase):
    def test_generator(self):
        self.assertEqual(last(reversed(values)), 1)

    def test_empty_generator(self):
        self.assertEqual(last(reversed([])), None)

    def test_empty_list(self):
        self.assertEqual(last([]), None)

    def test_empty_set(self):
        self.assertEqual(last(set()), None)

    def test_set(self):
        self.assertEqual(last(set(values)).__class__, int)

    def test_list(self):
        self.assertEqual(last(values), 3)

    def test_flat_list(self):
        v = wrap(values)
        self.assertEqual(last(v), 3)

    def test_string(self):
        v = "test"
        self.assertEqual(last(v), "test")

    def test_bytes(self):
        v = b"test"
        self.assertEqual(last(v), b"test")

    def test_number(self):
        v = 42
        self.assertEqual(last(v), 42)

    def test_object(self):
        v = {}
        self.assertEqual(last(v), wrap({}))

    def test_none(self):
        v = None
        self.assertEqual(last(v), None)

    def test_null(self):
        v = Null
        self.assertEqual(last(v), None)


