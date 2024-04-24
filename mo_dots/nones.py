# encoding: utf-8
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.
#
# Contact: Kyle Lahnakoski (kyle@lahnakoski.com)
#


from mo_future import none_type
from mo_imports import expect, export

from mo_dots.utils import CLASS, KEY, SLOT

to_data, get_attr, is_sequence, FlatList = expect("to_data", "get_attr", "is_sequence", "FlatList")

_get = object.__getattribute__
_set = object.__setattr__
_zero_list = []
_null_hash = hash(None)


class NullType(object):
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
        key - THE dict ITEM REFERENCE (DOT(.) IS NOT ESCAPED)
        """
        _set(self, SLOT, obj)
        _set(self, KEY, key)

    def __bool__(self):
        return False

    __nonzero__ = __bool__

    def __add__(self, other):
        if is_sequence(other):
            return other
        return Null

    def __radd__(self, other):
        if is_sequence(other):
            return other
        return Null

    def __call__(self, *args, **kwargs):
        return Null

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
        if is_sequence(other) and not other:
            return True

        _class = _get(other, CLASS)
        if _class in null_types:
            return True
        else:
            return Null

    def __ne__(self, other):
        class_ = _get(other, CLASS)
        if class_ in null_types:
            return False
        elif class_ is list and not other:
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
        elif isinstance(key, int):
            return NullType(self, key)

        path = _split_field(key)
        output = self
        for p in path:
            output = NullType(output, p)
        return output

    def __getattr__(self, key):
        key = str(key)

        o = to_data(_get(self, SLOT))
        k = _get(self, KEY)
        if is_null(o):
            return NullType(self, key)
        v = o.get(k)
        if is_null(v):
            return NullType(self, key)
        try:
            return v.get(key)
        except Exception as e:
            from mo_logs import Log

            Log.error("not expected", cause=e)

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

        if o is None:
            return
        elif isinstance(key, int):
            seq = [k] + [key]
            _assign_to_null(o, seq, value)
        else:
            seq = [k] + _split_field(key)
            _assign_to_null(o, seq, value)

    def keys(self):
        return set()

    def items(self):
        return []

    def pop(self, key, default=None):
        return Null

    def __str__(self):
        return "None"

    def __repr__(self):
        return "Null"

    def __hash__(self):
        return _null_hash


Null = NullType()  # INSTEAD OF None!!!
_set(Null, SLOT, Null)


def _assign_to_null(obj, path, value, force=True):
    """
    value IS ASSIGNED TO obj[self.path][key]
    path IS AN ARRAY OF PROPERTY NAMES
    force=False IF YOU PREFER TO use setDefault()
    """
    try:
        if obj is Null:
            return
        if _get(obj, CLASS) is NullType:
            o = _get(obj, SLOT)
            p = _get(obj, KEY)
            s = [p] + path
            return _assign_to_null(o, s, value)

        path0 = path[0]

        if len(path) == 1:
            if force:
                obj[path0] = value
            else:
                _setdefault(obj, path0, value)
            return

        old_value = get_attr(obj, path0)
        if is_null(old_value):
            if is_null(value):
                return
            else:
                obj[path0] = old_value = {}

        _assign_to_null(old_value, path[1:], value)
    except Exception as e:
        raise e


def is_null(value):
    # RETURN True IF EFFECTIVELY NOTHING
    _class = _get(value, CLASS)
    if _class in null_types:
        return True
    if _class is FlatList:
        return not value
    return False


def is_not_null(value):
    _class = _get(value, CLASS)
    if _class in null_types:
        return False
    if _class is FlatList:
        return bool(value)
    return True


def _split_field(field):
    """
    SIMPLE SPLIT, NO CHECKS
    """
    if field == ".":
        return []
    else:
        return [k.replace("\b", ".") for k in field.replace("..", "\b").split(".")]


def _setdefault(obj, key, value):
    """
    DO NOT USE __dict__.setdefault(obj, key, value), IT DOES NOT CHECK FOR obj[key] == None
    """
    v = obj.get(key)
    if is_null(v):
        obj[key] = value
        return value
    return v


null_types = (none_type, NullType)

export("mo_dots.fields", is_null)
