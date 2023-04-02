# encoding: utf-8

# SNAGED FROM https://github.com/pawelzny/dotty_dict/blob/98984911a61ae9f1aa4da3f6c4808da991b89847/tests/test_dotty_api.py
# UNDER THe MIT LICENSE
from __future__ import unicode_literals

import mo_dots
from mo_dots import split_field, to_data, Data, from_data
from mo_testing.fuzzytestcase import FuzzyTestCase


class TestDottyPrivateMembers(FuzzyTestCase):
    def test_split_separator(self):
        result = split_field("chain.of.keys")
        self.assertEqual(result, ["chain", "of", "keys"])


class TestDottyPublicMembers(FuzzyTestCase):
    def test_to_dict(self):
        plain_dict = {"very": {"deeply": {"nested": {"thing": "spam"}}}}
        dot = to_data(plain_dict)
        self.assertIsInstance(from_data(dot), dict)
        self.assertEqual(sorted(from_data(dot).items()), sorted(plain_dict.items()))
        self.assertEqual(sorted(dot.items()), sorted(plain_dict.items()))

    def test_nested_dotty_object_to_dict(self):
        expected_dict = {"hello": {"world": 1}, "nested": {"to_data": {"wazaa": 3}}}
        top_dot = to_data({"hello": {"world": 1}})
        nested_dot = to_data({"wazaa": 3})
        top_dot["nested.to_data"] = nested_dot
        self.assertEqual(from_data(top_dot), expected_dict)

    def test_nested_dotty_in_list_to_dict(self):
        expected_dict = {"testlist": [{"dot1": 1}, {"dot2": 2}]}
        dot_list = [to_data({"dot1": 1}), to_data({"dot2": 2})]
        top_dot = to_data({"testlist": dot_list})
        self.assertEqual(from_data(top_dot), expected_dict)


class TestDictSpecificMethods(FuzzyTestCase):
    def setUp(self):
        self.dot = to_data({
            "flat_key": "flat value",
            "deep": {"nested": 12, "deeper": {"secret": "abcd", "ridiculous": {"hell": "is here",},},},
        })

    def test_access_keys(self):
        keys = list(sorted(self.dot.keys()))
        self.assertEqual(keys, ["deep", "flat_key"])

    def test_access_keys_from_deeply_nested_structure(self):
        keys = list(sorted(self.dot["deep.deeper"].keys()))
        self.assertEqual(keys, ["ridiculous", "secret"])

    def test_get_value_without_default(self):
        result = self.dot.get("deep.nested")
        self.assertEqual(result, 12)

    def test_get_value_with_default(self):
        result = self.dot.get("deep.other", False)
        self.assertFalse(result)

    def test_return_dotty_length(self):
        self.assertEqual(len(self.dot), 2)

    def test_pop_from_dotty_flat(self):
        result = self.dot.pop("flat_key")
        self.assertEqual(result, "flat value")
        self.assertEqual(
            self.dot, {"deep": {"nested": 12, "deeper": {"secret": "abcd", "ridiculous": {"hell": "is here",},},},},
        )

    def test_pop_with_default_value(self):
        result = self.dot.pop("not_existing", "abcd")
        self.assertEqual(result, "abcd")
        self.assertEqual(
            self.dot,
            {
                "flat_key": "flat value",
                "deep": {"nested": 12, "deeper": {"secret": "abcd", "ridiculous": {"hell": "is here",},},},
            },
        )

    def test_pop_nested_key(self):
        result = self.dot.pop("deep.nested")
        self.assertEqual(result, 12)
        self.assertEqual(
            self.dot,
            {"flat_key": "flat value", "deep": {"deeper": {"secret": "abcd", "ridiculous": {"hell": "is here",},},},},
        )

    def test_pop_nested_key_with_default_value(self):
        result = self.dot.pop("deep.deeper.not_existing", "abcd")
        self.assertEqual(result, "abcd")
        self.assertEqual(
            self.dot,
            {
                "flat_key": "flat value",
                "deep": {"nested": 12, "deeper": {"secret": "abcd", "ridiculous": {"hell": "is here",},},},
            },
        )

    def test_setdefault_flat_not_existing(self):
        result = self.dot.setdefault("next_flat", "new default value")
        self.assertEqual(result, "new default value")
        self.assertEqual(
            self.dot,
            {
                "flat_key": "flat value",
                "next_flat": "new default value",
                "deep": {"nested": 12, "deeper": {"secret": "abcd", "ridiculous": {"hell": "is here",},},},
            },
        )

    def test_setdefault_flat_existing(self):
        self.dot["next_flat"] = "original value"
        result = self.dot.setdefault("next_flat", "new default value")
        self.assertEqual(result, "original value")
        self.assertEqual(
            self.dot,
            {
                "flat_key": "flat value",
                "next_flat": "original value",
                "deep": {"nested": 12, "deeper": {"secret": "abcd", "ridiculous": {"hell": "is here",},},},
            },
        )

    def test_setdefault_nested_key_not_existing(self):
        result = self.dot.setdefault("deep.deeper.next_key", "new default value")
        self.assertEqual(result, "new default value")
        self.assertEqual(
            self.dot,
            {
                "flat_key": "flat value",
                "deep": {
                    "nested": 12,
                    "deeper": {"next_key": "new default value", "secret": "abcd", "ridiculous": {"hell": "is here",},},
                },
            },
        )

    def test_setdefault_nested_key_existing(self):
        self.dot["deep.deeper.next_key"] = "original value"
        result = self.dot.setdefault("deep.deeper.next_key", "new default value")
        self.assertEqual(result, "original value")
        self.assertEqual(
            self.dot,
            {
                "flat_key": "flat value",
                "deep": {
                    "nested": 12,
                    "deeper": {"next_key": "original value", "secret": "abcd", "ridiculous": {"hell": "is here",},},
                },
            },
        )

    def test_copy(self):
        first = to_data({"a": 1, "b": 2})
        second = first.copy()

        self.assertIsInstance(second, Data)
        self.assertEqual(first, second)
        self.assertIsNot(first, second)
        self.assertIsNot(first._data, second._data)

    def test_fromkeys1(self):
        dot = mo_dots.fromkeys({"a", "b", "c"}, value=10)
        self.assertEqual(from_data(dot), {"a": 10, "b": 10, "c": 10})
        self.assertIsInstance(dot, Data)

    def test_fromkeys2(self):
        dot = mo_dots.fromkeys({"a", "b", "c"}, value=None)
        self.assertEqual(len(from_data(dot).keys()), 0)
