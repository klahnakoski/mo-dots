# encoding: utf-8
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at https://www.mozilla.org/en-US/MPL/2.0/.
#
# Contact: Kyle Lahnakoski (kyle@lahnakoski.com)
#
from mo_imports import expect, export

from mo_dots.fields import split_field
from mo_dots.utils import (
    CLASS,
    KEY,
    SLOT,
    is_null,
    is_missing,
    register_null_type,
    is_many,
    _speedups,
    _rebuild_class,
)

__all__ = ["Null", "NullType"]

to_data, _getdefault, Data = expect("to_data", "_getdefault", "Data")

_get = object.__getattribute__
_set = object.__setattr__
_zero_list = []
_null_hash = hash(None)


class NullType:
    """
    Structural Null provides closure under the dot (.) operator
        Null[x] == Null
        Null.x == Null

    Null INSTANCES WILL TRACK THEIR OWN DEREFERENCE PATH SO
    ASSIGNMENT CAN BE DONE
    """

    __slots__ = [SLOT, KEY]

    def __init__(self, obj=None, key=None):
        """
        obj - VALUE BEING DEREFERENCED
        key - LITERAL KEY INTO obj (DOT(.) IS NOT ESCAPED)
        """
        _set(self, SLOT, obj)
        _set(self, KEY, key)

    def __bool__(self):
        return False

    __nonzero__ = __bool__

    def __add__(self, other):
        return other

    def __radd__(self, other):
        return other

    def __call__(self, *args, **kwargs):
        return Null

    def __enter__(self):
        # `with Null:` OTHERWISE RAISES A BARE AttributeError: __enter__, NAMING
        # NOTHING; THIS NAMES THE MISSING CONTEXT MANAGER INSTEAD
        from mo_logs import logger

        logger.error("Expecting a context manager, not Null (`with` on a missing value)")

    def __exit__(self, exc_type, exc_val, exc_tb):
        return False

    def __iadd__(self, other):
        o = _get(self, SLOT)
        if o is None:
            return self
        key = _get(self, KEY)

        _assign_to_null(o, [key], other)
        return other

    def __sub__(self, other):
        return Null

    def __rsub__(self, other):
        return Null

    def __neg__(self):
        return Null

    def __mul__(self, other):
        return Null

    def __rmul__(self, other):
        return Null

    def __int__(self):
        return None

    def __float__(self):
        return float("nan")

    def __div__(self, other):
        return Null

    def __itruediv__(self, other):
        return Null

    def __rdiv__(self, other):
        return Null

    def __truediv__(self, other):
        return Null

    def __floordiv__(self, other):
        return Null

    def __rfloordiv__(self, other):
        return Null

    def __rtruediv__(self, other):
        return Null

    def __gt__(self, other):
        return Null

    def __ge__(self, other):
        return Null

    def __le__(self, other):
        return Null

    def __lt__(self, other):
        return Null

    def __eq__(self, other):
        if is_missing(other):
            return True
        return Null

    def __ne__(self, other):
        if is_missing(other):
            return False
        else:
            return Null

    def __or__(self, other):
        return other

    def __ror__(self, other):
        return other

    def __and__(self, other):
        if other is False:
            return False
        return Null

    def __rand__(self, other):
        if other is False:
            return False
        return Null

    def __xor__(self, other):
        return Null

    def __rxor__(self, other):
        return Null

    def __len__(self):
        return 0

    def __iter__(self):
        return _zero_list.__iter__()

    def __copy__(self):
        return Null

    def __deepcopy__(self, memo):
        return Null

    def __getitem__(self, key):
        if isinstance(key, slice):
            return Null
        o = _get(self, SLOT)
        if o is None or o is Null:
            # DEAD CHAIN: ASSIGNMENT THROUGH self IS ALREADY A NO-OP
            return Null
        if isinstance(key, int) or ("." not in key and "\b" not in key):
            return NullType(self, key)

        output = self
        for p in split_field(key):
            output = NullType(output, p)
        return output

    def __getattr__(self, key):
        key = str(key)

        o = _get(self, SLOT)
        if o is None or o is Null:
            # DEAD CHAIN: ASSIGNMENT THROUGH self IS ALREADY A NO-OP
            return Null
        v = _getdefault(o, _get(self, KEY))
        if is_null(v):
            return NullType(self, key)
        try:
            return to_data(v).get(key)
        except Exception as e:
            from mo_logs import logger

            logger.error("not expected", cause=e)

    def __setattr__(self, key, value):
        key = str(key)
        o = _get(self, SLOT)
        k = _get(self, KEY)
        seq = [k] + [key]
        _assign_to_null(o, seq, value)

    def __setitem__(self, key, value):
        o = _get(self, SLOT)
        if o is None:
            return
        k = _get(self, KEY)
        if isinstance(key, int) or ("." not in key and "\b" not in key):
            _assign_to_null(o, [k, key], value)
        else:
            _assign_to_null(o, [k] + split_field(key), value)

    def keys(self):
        return set()

    def items(self):
        return []

    def pop(self, key, default=None):
        return Null

    def __str__(self):
        return ""

    def __repr__(self):
        return "Null"

    def __hash__(self):
        return _null_hash


# DUNDERS THE C _NullBase IMPLEMENTS AS TYPE SLOTS
_NULL_HOT = {
    "__init__",
    "__bool__",
    "__getattr__",
    "__getitem__",
    "__hash__",
    "__str__",
    "__repr__",
    "__call__",
    "__iter__",
    "__len__",
    "__eq__",
    "__ne__",
    "__gt__",
    "__ge__",
    "__le__",
    "__lt__",
    "__add__",
    "__radd__",
    "__sub__",
    "__rsub__",
    "__neg__",
    "__mul__",
    "__rmul__",
    "__truediv__",
    "__rtruediv__",
    "__floordiv__",
    "__rfloordiv__",
    "__itruediv__",
    "__or__",
    "__ror__",
    "__and__",
    "__rand__",
    "__xor__",
    "__rxor__",
    "__int__",
    "__float__",
}

if _speedups:
    _pure_NullType = NullType
    NullType = _rebuild_class(_pure_NullType, _speedups._NullBase, _NULL_HOT)
    _speedups._init_null(NullType, _pure_NullType.__getattr__, _pure_NullType.__getitem__)

register_null_type(NullType)
Null = NullType()  # INSTEAD OF None!!!
_set(Null, SLOT, Null)
if _speedups:
    _speedups._set_null(Null)


def _assign_to_null(obj, path, value):
    """
    value IS ASSIGNED TO obj[self.path][key]
    path IS AN ARRAY OF PROPERTY NAMES
    """
    if obj is Null:
        return
    if _get(obj, CLASS) is NullType:
        o = _get(obj, SLOT)
        p = _get(obj, KEY)
        s = [p] + path
        return _assign_to_null(o, s, value)

    if _get(obj, CLASS) is Data:
        obj = _get(obj, SLOT)
    path0 = path[0]

    if len(path) == 1:
        obj[path0] = value
        return

    old_value = _getdefault(obj, path0)
    if is_null(old_value):
        if is_null(value):
            return
        else:
            obj[path0] = old_value = {}

    _assign_to_null(old_value, path[1:], value)
