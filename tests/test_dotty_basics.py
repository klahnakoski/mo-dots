# encoding: utf-8

# SNAGED FROM https://github.com/pawelzny/dotty_dict/blob/98984911a61ae9f1aa4da3f6c4808da991b89847/tests/test_dotty_basics.py
# UNDER THe MIT LICENSE
from __future__ import unicode_literals

from unittest import skip

from mo_dots import to_data, Data
from mo_testing.fuzzytestcase import FuzzyTestCase


class TestDottyBasics(FuzzyTestCase):
    def test_create_empty_instance(self):
        dot = to_data({})
        self.assertEqual(dot, {})

    def test_create_non_empty_instance(self):
        plain_dict = {"not": "empty"}

        dot = to_data(plain_dict)
        self.assertEqual(dot, plain_dict)
        self.assertIsNot(dot, plain_dict)

    def test_raise_attr_error_if_input_is_not_dict(self):
        with self.assertRaises(Exception):
            Data(["not", "valid"])

    def test_two_dotty_with_the_same_input_should_be_equal(self):
        first = to_data({"is": "valid"})
        second = to_data({"is": "valid"})

        self.assertEqual(first, second)

    def test_two_dotty_with_different_input_should_not_be_equal(self):
        first = to_data({"counter": 1})
        second = to_data({"counter": 2})

        self.assertNotEqual(first, second)

    def test_plain_dict_and_dotty_wrapper_should_be_equal(self):
        plain = {"a": 1, "b": 2}
        dot = to_data(plain)
        self.assertEqual(dot, plain)

    def test_dotty_and_not_mapping_instance_should_not_be_equal(self):
        dot = to_data({"a": 1, "b": 2})
        self.assertNotEqual(dot, [("a", 1), ("b", 2)])
        self.assertNotEqual(dot, ("a", 1))
        self.assertNotEqual(dot, {1, 2, 3})
        self.assertNotEqual(dot, 123)
        self.assertNotEqual(dot, "a:1, b:2")

    def test_pop_with_default_value(self):
        dot = to_data({})
        self.assertEqual(dot.pop("does.not.exist", None), None)
        self.assertEqual(dot.pop("does.not.exist", 55), 55)
        self.assertEqual(dot.pop("does.not.exist", "my_value"), "my_value")
