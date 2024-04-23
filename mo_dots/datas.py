# encoding: utf-8
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.
#
# Contact: Kyle Lahnakoski (kyle@lahnakoski.com)
#


from copy import copy, deepcopy
from datetime import datetime, date, timedelta, time
from decimal import Decimal

from mo_future import (
    generator_types,
    iteritems,
    long,
    text,
    MutableMapping,
    OrderedDict,
    first,
)
from mo_imports import expect

from mo_dots.fields import split_field, literal_field, concat_field
from mo_dots.nones import Null, NullType, null_types, is_null
from mo_dots.utils import CLASS, SLOT
from mo_dots.utils import get_logger

(
    _getdefault,
    coalesce,
    listwrap,
    from_data,
    to_data,
    list_to_data,
    finite_types,
    is_list,
    FlatList,
    is_sequence,
    is_many,
    DataObject,
    get_keys,
    object_to_data,
) = expect(
    "_getdefault",
    "coalesce",
    "listwrap",
    "from_data",
    "to_data",
    "list_to_data",
    "finite_types",
    "is_list",
    "FlatList",
    "is_sequence",
    "is_many",
    "DataObject",
    "get_keys",
    "object_to_data",
)


_get = object.__getattribute__
_set = object.__setattr__
_new = object.__new__

DEBUG = False


class Data(object):
    """
    Please see https://github.com/klahnakoski/mo-dots/tree/dev/docs#data-replaces-pythons-dict
    """

    __slots__ = [SLOT]

    def __init__(self, *args, **kwargs):
        """
        CONSTRUCT DATA WITH GIVEN PROPERTY VALUES
        """
        if args:
            raise Exception("only keywords are allowed, not " + args[0].__class__.__name__)
        _set(self, SLOT, kwargs)

    def __bool__(self):
        d = _get(self, SLOT)
        if _get(d, CLASS) is dict:
            return True
        else:
            return d != None

    __nonzero__ = __bool__

    def __contains__(self, item):
        value = Data.__getitem__(self, item)
        if _get(value, CLASS) in _data_types or value:
            return True
        return False

    def __iter__(self):
        d = _get(self, SLOT)
        if _get(d, CLASS) is dict:
            yield from d.items()
        else:
            yield from d.__iter__()

    def __getitem__(self, key):
        if key == None:
            return Null
        if key == ".":
            output = _get(self, SLOT)
            if _get(output, CLASS) in _data_types:
                return self
            else:
                return output

        key = str(key)
        d = _get(self, SLOT)

        if key.find(".") >= 0:
            seq = _split_field(key)
            for n in seq:
                if _get(d, CLASS) is NullType:
                    d = NullType(d, n)  # OH DEAR, Null TREATS n AS PATH, NOT LITERAL
                elif is_list(d):
                    d = [_getdefault(dd, n) for dd in d]
                else:
                    d = _getdefault(d, n)  # EVERYTHING ELSE TREATS n AS LITERAL

            return to_data(d)
        else:
            o = d.get(key)

        if is_null(o):
            return NullType(d, key)
        return to_data(o)

    def __setitem__(self, key, value):
        if key == "":
            get_logger().error("key is empty string.  Probably a bad idea")
        if key == None:
            return Null
        if key == ".":
            # SOMETHING TERRIBLE HAPPENS WHEN value IS NOT A Mapping;
            # HOPEFULLY THE ONLY OTHER METHOD RUN ON self IS from_data()
            v = from_data(value)
            if is_many(v):
                _set(self, CLASS, FlatList)
            _set(self, SLOT, v)
            return self
        try:
            d = _get(self, SLOT)
            value = from_data(value)
            if "." not in key:
                if value is None:
                    d.pop(key, None)
                else:
                    d[key] = value
                return self

            seq = _split_field(key)
            for k in seq[:-1]:
                d = _getdefault(d, k)
            if value == None:
                try:
                    d.pop(seq[-1], None)
                except Exception as _:
                    pass
            elif d == None:
                d[literal_field(seq[-1])] = value
            elif is_sequence(d):
                for dd in d:
                    from_data(dd)[seq[-1]] = value
            else:
                d[seq[-1]] = value
            return self
        except Exception as e:
            from mo_logs import Log

            Log.error("can not set key={{key}}", key=key, cause=e)

    def __getattr__(self, key):
        d = _get(self, SLOT)
        v = d.get(key)
        t = _get(v, CLASS)

        # OPTIMIZED to_data()
        if t is dict:
            return dict_to_data(v)
        elif t in null_types:
            return NullType(d, key)
        elif t is list:
            return list_to_data(v)
        elif t in generator_types:
            return FlatList(list(from_data(vv) for vv in v))
        else:
            return v

    def __setattr__(self, key, value):
        d = _get(self, SLOT)
        value = from_data(value)
        if value is None:
            d = _get(self, SLOT)
            d.pop(key, None)
        else:
            d[key] = value
        return self

    def __add__(self, other):
        return _iadd(_iadd({}, self), other)

    def __radd__(self, other):
        return _iadd(_iadd({}, other), self)

    def __iadd__(self, other):
        return _iadd(self, other)

    def __or__(self, other):
        """
        RECURSIVE COALESCE OF DATA PROPERTIES
        """
        if not _get(other, CLASS) in _data_types:
            get_logger().error("Expecting Data")

        d = _get(self, SLOT)
        output = Data(**d)  # COPY
        output.__ior__(other)
        return output

    def __ror__(self, other):
        """
        RECURSIVE COALESCE OF DATA PROPERTIES
        """
        if not _get(other, CLASS) in _data_types:
            get_logger().error("Expecting Data")

        return to_data(other).__or__(self)

    def __ior__(self, other):
        """
        RECURSIVE COALESCE OF DATA PROPERTIES
        """
        d = _get(self, SLOT)
        if not _get(other, CLASS) in _data_types:
            if is_missing(d) or (isinstance(d, dict) and not d):
                _set(self, SLOT, other)
            return self

        for ok, ov in other.items():
            if ov == None:
                continue

            sv = to_data(d.get(ok))
            if sv == None:
                d[ok] = ov
            elif is_data(sv):
                d[ok] = sv | ov
        return self

    def __hash__(self):
        d = _get(self, SLOT)
        return hash_value(d)

    def __eq__(self, other):
        if self is other:
            return True

        d = _get(self, SLOT)
        if _get(d, CLASS) is not dict:
            return d == other

        if not d and other == None:
            return False

        if _get(other, CLASS) not in _data_types:
            return False
        e = other
        for k, v in d.items():
            if e.get(k) != v:
                return False
        for k, v in e.items():
            if d.get(k) != v:
                return False
        return True

    def __ne__(self, other):
        return not self.__eq__(other)

    def get(self, key, default=Null):
        v = self[key]
        if _get(v, CLASS) == NullType:
            if default is Null:
                return NullType(self, key)
            return default
        return v

    def items(self):
        d = _get(self, SLOT)
        return [(k, to_data(v)) for k, v in d.items() if v != None or _get(v, CLASS) in _data_types]

    def leaves(self, prefix=None):
        """
        LIKE items() BUT RECURSIVE, AND ONLY FOR THE LEAVES (non dict) VALUES
        """
        return leaves(self, prefix)

    def iteritems(self):
        # LOW LEVEL ITERATION, NO WRAPPING
        d = _get(self, SLOT)
        return ((k, to_data(v)) for k, v in iteritems(d))

    def pop(self, key, default=Null):
        if key == None:
            return Null
        if key == ".":
            raise NotImplemented()

        key = str(key)
        d = _get(self, SLOT)

        if key.find(".") >= 0:
            seq = _split_field(key)
            for n in seq[:-1]:
                if _get(d, CLASS) is NullType:
                    d = NullType(d, n)  # OH DEAR, Null TREATS n AS PATH, NOT LITERAL
                elif is_list(d):
                    d = [_getdefault(dd, n) for dd in d]
                else:
                    d = _getdefault(d, n)  # EVERYTHING ELSE TREATS n AS LITERAL
            key = seq[-1]

        o = d.get(key)
        if o == None:
            if default is Null:
                return NullType(d, key)
            return default

        d[key] = None
        return to_data(o)

    def keys(self):
        d = _get(self, SLOT)
        return set(d.keys())

    def values(self):
        d = _get(self, SLOT)
        return listwrap(list(d.values()))

    def clear(self):
        get_logger().error("clear() not supported")

    def __len__(self):
        d = _get(self, SLOT)
        return dict.__len__(d)

    def copy(self):
        d = _get(self, SLOT)
        if _get(d, CLASS) is dict:
            return Data(**d)
        else:
            return copy(d)

    def __copy__(self):
        d = _get(self, SLOT)
        if _get(d, CLASS) is dict:
            return Data(**self)
        else:
            return copy(d)

    def __deepcopy__(self, memo):
        d = _get(self, SLOT)
        return to_data(deepcopy(d, memo))

    def __delitem__(self, key):
        if "." not in key:
            d = _get(self, SLOT)
            d.pop(key, None)
            return

        d = _get(self, SLOT)
        seq = _split_field(key)
        for k in seq[:-1]:
            d = d[k]
        d.pop(seq[-1], None)

    def __delattr__(self, key):
        key = str(key)
        d = _get(self, SLOT)
        d.pop(key, None)

    def setdefault(self, k, d=None):
        v = self[k]
        if v == None:
            self[k] = d
            return d
        return v

    def __str__(self):
        return str(_get(self, SLOT))

    def __dir__(self):
        d = _get(self, SLOT)
        return d.keys()

    def __repr__(self):
        try:
            return f"to_data({repr(_get(self, SLOT))})"
        except Exception as e:
            return "Data(?)"


MutableMapping.register(Data)


def leaves(value, prefix=None):
    """
    LIKE items() BUT RECURSIVE, AND ONLY FOR THE LEAVES (non dict) VALUES
    SEE leaves_to_data FOR THE INVERSE

    :param value: THE Mapping TO TRAVERSE
    :param prefix:  OPTIONAL PREFIX GIVEN TO EACH KEY
    :return: Data, WHICH EACH KEY BEING A PATH INTO value TREE
    """
    if not prefix:
        yield from _leaves(".", value)
    else:
        for k, v in _leaves(".", value):
            yield prefix + k, v


def _leaves(parent, value):
    value = from_data(value)
    obj = object_to_data(value)
    if obj is value or is_many(value):
        yield parent, value
        return

    for k in get_keys(obj):
        try:
            v = obj[literal_field(k)]
            if is_missing(v):
                continue
            kk = concat_field(parent, literal_field(k))
            vv = object_to_data(v)
            yield from _leaves(kk, vv)
        except Exception as cause:
            get_logger().error("Do not know how to handle", cause=cause)


def _split_field(field):
    """
    SIMPLE SPLIT, NO CHECKS
    """
    return [k.replace("\b", ".") for k in field.replace("..", "\b").split(".")]


def _iadd(self, other):
    """
    RECURSIVE ADDITION OF DATA PROPERTIES
    * LISTS ARE CONCATENATED
    * SETS ARE UNIONED
    * NUMBERS ARE ADDED
    """

    if not _get(other, CLASS) in _data_types:
        # HAPPENS WHEN _iadd WITH ['.'] SELF REFERENCE
        d = _get(self, SLOT)
        if isinstance(d, dict) and not len(d):
            # LOOKS LIKE A FRESH Data OBJECT (AN IDENTITY ELEMENT)
            # ∀ x, x += {} => x
            d = Data()
        else:
            d = dict_to_data({"$": self})
        d += dict_to_data({"$": other})
        d["."] = d["$"]
        return d

    d = from_data(self)
    for ok, ov in other.items():
        sv = d.get(ok)
        if sv == None:
            d[ok] = from_data(deepcopy(ov))
        elif isinstance(ov, (Decimal, float, long, int)):
            if _get(sv, CLASS) in _data_types:
                get_logger().error(
                    "can not add {{stype}} with {{otype}",
                    stype=_get(sv, CLASS).__name__,
                    otype=_get(ov, CLASS).__name__,
                )
            elif is_list(sv):
                d[ok].append(ov)
            else:
                d[ok] = sv + ov
        elif is_list(ov):
            d[ok] = from_data(listwrap(sv) + ov)
        elif _get(ov, CLASS) in _data_types:
            if _get(sv, CLASS) in _data_types:
                _iadd(sv, ov)
            elif is_list(sv):
                d[ok].append(ov)
            else:
                get_logger().error(
                    "can not add {{stype}} with {{otype}",
                    stype=_get(sv, CLASS).__name__,
                    otype=_get(ov, CLASS).__name__,
                )
        else:
            if _get(sv, CLASS) in _data_types:
                get_logger().error(
                    "can not add {{stype}} with {{otype}",
                    stype=_get(sv, CLASS).__name__,
                    otype=_get(ov, CLASS).__name__,
                )
            else:
                d[ok].append(ov)
    return self


_data_types = data_types = (Data, dict, OrderedDict)  # TYPES TO HOLD DATA


def register_data(type_):
    """
    :param type_:  ADD OTHER TYPE THAT HOLDS DATA
    :return:
    """
    global _data_types
    _data_types = tuple(set(_data_types + (type_,)))


def is_data(d):
    """
    :param d:
    :return: True IF d IS A TYPE THAT HOLDS DATA
    """
    return d.__class__ in _data_types


def is_missing(t) -> bool:
    # RETURN True IF EFFECTIVELY NOTHING
    class_ = t.__class__
    if class_ in null_types:
        return True
    elif class_ in _data_types:
        return False
    elif class_ in finite_types and not t:
        return True
    elif class_ is text and not t:
        return True
    else:
        return t == None


def exists(value) -> bool:
    return not is_missing(value)


def hash_value(v):
    if is_many(v):
        return hash_value(first(v))
    elif _get(v, CLASS) in _data_types:
        return hash_value(first(v.values()))
    else:
        return hash(v)


def dict_to_data(d):
    """
    FASTEST WAY TO MAKE Data, DO NOT CHECK TYPE
    :param d: dict
    :return: Data
    """
    m = _new(Data)
    _set(m, SLOT, d)
    return m


def leaves_to_data(value):
    """
    dict WITH DOTS IN KEYS IS INTERPRETED AS A PATH
    """
    return to_data(_leaves_to_data(value))


wrap_leaves = leaves_to_data


def _leaves_to_data(value):
    """
    RETURN UNWRAPPED STRUCTURES
    """
    if value == None:
        return None

    if is_primitive(value):
        return value

    class_ = _get(value, CLASS)
    if class_ in _data_types:
        if class_ is Data:
            value = from_data(value)

        output = {}
        for key, value in value.items():
            value = _leaves_to_data(value)

            if key == "":
                get_logger().error("key is empty string.  Probably a bad idea")

            seq = split_field(key)
            if not seq:
                if not output:
                    output = value
                continue
            if not is_data(output):
                output = {}
            d = output
            for k in seq[:-1]:
                e = d.get(k, None)
                if not is_data(e):
                    e = d[k] = {}
                d = e

            if value == None:
                d.pop(seq[-1], None)
            else:
                d[seq[-1]] = value
        return output

    if hasattr(value, "__iter__"):
        return [_leaves_to_data(v) for v in value]

    return value


_primitive_types = (str, bytes, int, float, bool, Decimal, datetime, date, time, timedelta)


def is_primitive(value):
    return isinstance(value, _primitive_types)


def register_primitive(_type):
    global _primitive_types
    _primitive_types = tuple(set(_primitive_types + (_type,)))
