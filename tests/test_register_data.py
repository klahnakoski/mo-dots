# encoding: utf-8
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at https://www.mozilla.org/en-US/MPL/2.0/.
#
# Contact: Kyle Lahnakoski (kyle@lahnakoski.com)
#
import unittest

from mo_dots import Data, DataObject, Null, from_data, is_data, register_data, to_data


class Bag:
    """
    A MAPPING mo-dots DID NOT BUILD - WHAT AN OUTSIDE LIBRARY REGISTERS
    """

    def __init__(self, **kwargs):
        self.store = kwargs

    def get(self, key, default=None):
        return self.store.get(key, default)

    def pop(self, key, default=None):
        return self.store.pop(key, default)

    def keys(self):
        return self.store.keys()

    def items(self):
        return self.store.items()

    def __getitem__(self, key):
        return self.store[key]

    def __setitem__(self, key, value):
        self.store[key] = value

    def __iter__(self):
        return iter(self.store)

    def __len__(self):
        return len(self.store)


register_data(Bag)


class TestRegisterData(unittest.TestCase):
    def test_is_data(self):
        self.assertTrue(is_data(Bag(a=1)))

    def test_to_data_wraps_it(self):
        bag = Bag(a=1)
        found = to_data(bag)
        self.assertIs(found.__class__, Data)
        self.assertEqual(found.a, 1)
        self.assertIs(from_data(found), bag)

    def test_a_nested_one_wraps_too(self):
        found = to_data(Bag(a=Bag(b=Bag(c=3))))
        self.assertEqual(found.a.b.c, 3)
        self.assertEqual(found["a.b.c"], 3)

    def test_a_missing_key_is_null(self):
        found = to_data(Bag(a=1))
        self.assertEqual(found.zzz, Null)
        self.assertEqual(found.zzz.deeper, Null)

    def test_writes_reach_the_mapping(self):
        bag = Bag(a=Bag(b=1))
        found = to_data(bag)
        found.a.b = 2
        found.c = 3
        self.assertEqual(bag["a"]["b"], 2)
        self.assertEqual(bag["c"], 3)

    def test_a_view_is_handed_back(self):
        # Data AND DataObject ANSWER NAVIGATION THEMSELVES; WRAPPING THEM AGAIN IS WRONG
        data = to_data({"a": 1})
        self.assertIs(to_data(data), data)
        self.assertTrue(is_data(data))
        obj = DataObject(Bag(a=1))
        self.assertIs(to_data(obj), obj)
        self.assertTrue(is_data(obj))

    def test_a_dict_still_wraps(self):
        found = to_data({"a": {"b": 1}})
        self.assertIs(found.__class__, Data)
        self.assertEqual(found.a.b, 1)


if __name__ == "__main__":
    unittest.main()
