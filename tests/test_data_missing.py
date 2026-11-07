# encoding: utf-8
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at https://www.mozilla.org/en-US/MPL/2.0/.
#
# Contact: Kyle Lahnakoski (kyle@lahnakoski.com)
#
# is_missing is the one rule: a key whose value is missing is absent.
import pytest

from mo_dots import Data, Null, from_data, to_data


@pytest.mark.parametrize(
    "value, expected",
    [(0, True), (False, True), (1, True), ({}, True), ("", False), ([], False), (None, False)],
    ids=["zero", "false", "one", "empty_dict", "empty_str", "empty_list", "none"],
)
def test_contains_is_exists(value, expected):
    assert ("a" in to_data({"a": value})) is expected


def test_contains_absent_key():
    assert "a" not in to_data({"b": 1})


@pytest.mark.parametrize("missing", [None, "", [], Null], ids=["none", "empty_str", "empty_list", "null"])
def test_eq_ignores_missing_valued_keys(missing):
    assert to_data({"a": missing, "b": 1}) == {"b": 1}
    assert {"b": 1} == to_data({"a": missing, "b": 1})
    assert to_data({"a": missing, "b": 1}) == to_data({"b": 1})
    assert to_data({"b": 1}) == to_data({"a": missing, "b": 1})


def test_eq_still_tells_values_apart():
    assert not (to_data({"a": 1}) == to_data({"a": 2}))
    assert not (to_data({"a": 0}) == to_data({"b": 0}))


def test_hash_ignores_key_order():
    assert hash(to_data({"a": 1, "b": 2})) == hash(to_data({"b": 2, "a": 1}))


@pytest.mark.parametrize("missing", [None, "", []], ids=["none", "empty_str", "empty_list"])
def test_hash_ignores_missing_valued_keys(missing):
    assert hash(to_data({"a": missing, "b": 1})) == hash(to_data({"b": 1}))


def test_or_left_wins_over_non_data_right():
    assert from_data(to_data({"a": {"b": 1}}) | {"a": 5}) == {"a": {"b": 1}}


def test_or_empty_left_dict_wins_over_non_data_right():
    assert from_data(to_data({"a": {}}) | {"a": 2}) == {"a": {}}


@pytest.mark.parametrize("identity", [Null, None], ids=["null", "none"])
def test_add_null_is_identity(identity):
    result = to_data({"a": 1}) + identity
    assert isinstance(result, Data)
    assert from_data(result) == {"a": 1}


def test_add_dict_answers_data():
    result = to_data({"a": 1}) + {"b": 2}
    assert isinstance(result, Data)
    assert from_data(result) == {"a": 1, "b": 2}
