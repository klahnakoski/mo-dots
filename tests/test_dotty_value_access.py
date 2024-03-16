# encoding: utf-8

# SNAGED FROM https://github.com/pawelzny/dotty_dict/blob/98984911a61ae9f1aa4da3f6c4808da991b89847/tests/test_dotty_value_access.py
# UNDER THe MIT LICENSE
from unittest import skip

from mo_testing.fuzzytestcase import FuzzyTestCase

from mo_dots import *


class TestDottyValueAccess(FuzzyTestCase):
    def setUp(self):
        self.dot = to_data({
            "flat_key": "flat value",
            "deep": {"nested": 12, "deeper": {"secret": "abcd", "ridiculous": {"hell": "is here",},},},
        })

    def test_access_flat_value(self):
        self.assertEqual(self.dot["flat_key"], "flat value")

    def test_raise_key_error_if_key_does_not_exist(self):
        result = self.dot["not_existing"]
        self.assertTrue(result == None)

    def test_access_deep_nested_value(self):
        self.assertEqual(self.dot["deep.nested"], 12)

    def test_access_middle_nested_value(self):
        self.assertEqual(self.dot["deep.deeper.ridiculous"], {"hell": "is here"})

    def test_set_flat_value(self):
        self.dot["new_flat"] = "super flat"
        self.assertIn("new_flat", self.dot)

    def test_set_deep_nested_value(self):
        self.dot["deep.new_key"] = "new value"
        self.assertIn("new_key", self.dot["deep"])

    def test_set_new_deeply_nested_value(self):
        self.dot["other.chain.of.keys"] = True
        self.assertEqual(
            self.dot,
            {
                "flat_key": "flat value",
                "deep": {"nested": 12, "deeper": {"secret": "abcd", "ridiculous": {"hell": "is here",},},},
                "other": {"chain": {"of": {"keys": True,},},},
            },
        )

    def test_dotty_has_flat_key(self):
        self.assertIn("flat_key", self.dot)

    def test_dotty_has_deeply_nested_key(self):
        self.assertIn("deep.nested", self.dot)

    def test_dotty_has_not_flat_key(self):
        self.assertNotIn("some_key", self.dot)

    def test_dotty_has_not_deeply_nested_key(self):
        self.assertNotIn("deep.other.chain", self.dot)

    def test_has_in(self):
        result = "deep.deeper.secret" in self.dot
        self.assertTrue(result)

    def test_has_not_in(self):
        result = "deep.other" in self.dot
        self.assertFalse(result)

    def test_delete_flat_key(self):
        del self.dot["flat_key"]
        self.assertEqual(
            self.dot, {"deep": {"nested": 12, "deeper": {"secret": "abcd", "ridiculous": {"hell": "is here",},},},},
        )

    def test_delete_nested_key(self):
        del self.dot["deep.deeper.secret"]
        self.assertEqual(
            self.dot,
            {"flat_key": "flat value", "deep": {"nested": 12, "deeper": {"ridiculous": {"hell": "is here",},},},},
        )

    def test_raise_key_error_on_delete_not_existing_key(self):
        del self.dot["deep.deeper.key"]

    def test_set_value_with_escaped_separator(self):
        self.dot[r"deep.deeper.escaped..dot_key"] = "it works!"
        self.assertEqual(
            self.dot,
            {
                "flat_key": "flat value",
                "deep": {
                    "nested": 12,
                    "deeper": {"escaped.dot_key": "it works!", "secret": "abcd", "ridiculous": {"hell": "is here",},},
                },
            },
        )

    def test_get_value_with_escaped_separator(self):
        dot = to_data({
            "flat_key": "flat value",
            "deep": {
                "nested": 12,
                "deeper": {"escaped.dot_key": "it works!", "secret": "abcd", "ridiculous": {"hell": "is here",},},
            },
        })
        result = dot[r"deep.deeper.escaped..dot_key"]
        self.assertEqual(result, "it works!")

    def test_get_value_with_escaped_escape_separator1(self):
        dot = to_data({
            "flat_key": "flat value",
            "deep": {
                "nested": 12,
                "deeper": {
                    "escaped\\": {"dot_key": "it works!",},
                    "secret": "abcd",
                    "ridiculous": {"hell": "is here",},
                },
            },
        })
        result = dot["deep.deeper.escaped\\.dot_key"]
        self.assertEqual(result, "it works!")

    def test_get_value_with_escaped_escape_separator2(self):
        dot = to_data({"deep": {"deeper": {"escaped.": {"dot_key": "it works!"}},},})
        result = dot["deep.deeper.escaped\b.dot_key"]
        self.assertEqual(result, "it works!")

    def test_string_digit_key(self):
        dot = to_data({"field": {"1": "one", "5": "five"}})

        dict_one = dot["field.1"]
        dict_five = dot["field.5"]

        self.assertEqual(dict_one, "one")
        self.assertEqual(dict_five, "five")

    def test_integer_keys(self):
        dot = to_data({"field": {1: "one", 5: "five"}})

        dict_one = dot["field.1"]
        dict_five = dot["field.5"]

        self.assertEqual(dict_one, "one")
        self.assertEqual(dict_five, "five")

    def test_data_gathering_with_int(self):
        dot = to_data({
            "2": "string_value",
            2: "int_value",
            "nested": {"2": "nested_string_value", 3: "nested_int_value"},
        })

        dict_string = dot["2"]
        dict_int = dot[2]  # KEYS MUST BE STRINGS. THEY WILL BE CAST
        nested_dict_string = dot["nested.2"]
        nested_dict_int = dot["nested.3"]

        self.assertEqual(dict_string, "string_value")
        self.assertEqual(dict_int, "string_value")
        self.assertEqual(nested_dict_string, "nested_string_value")
        self.assertEqual(nested_dict_int, "nested_int_value")

    @skip("mo-dots only deals with string keys")
    def test_non_standard_key_types(self):
        dot = Data({3.3: "float", True: "bool", None: "None", "nested": {4.4: "nested_float"}}, separator=",",)

        dict_float = dot[3.3]
        dict_bool = dot[True]
        dict_none = dot[None]
        nested_dict_float = dot["nested,4.4"]
        self.assertEqual(dict_float, "float")
        self.assertEqual(dict_bool, "bool")
        self.assertEqual(dict_none, "None")
        self.assertEqual(nested_dict_float, "nested_float")
