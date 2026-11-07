# encoding: utf-8
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at https://www.mozilla.org/en-US/MPL/2.0/.
#
# Contact: Kyle Lahnakoski (kyle@lahnakoski.com)
#
from copy import copy, deepcopy
from decimal import Decimal

from mo_future import generator_types, MutableMapping, first
from mo_imports import expect, export

from mo_dots import utils
from mo_dots.fields import split_field, literal_field, concat_field
from mo_dots.nones import Null, NullType
from mo_dots.utils import *

_getdefault, coalesce, listwrap, from_data, to_data, list_to_data, FlatList, DataObject, get_keys, object_to_data = (
    expect(
        "_getdefault",
        "coalesce",
        "listwrap",
        "from_data",
        "to_data",
        "list_to_data",
        "FlatList",
        "DataObject",
        "get_keys",
        "object_to_data",
    )
)


_get = object.__getattribute__
_set = object.__setattr__

if utils._speedups:
    # object.__setattr__ ON A C-BACKED Data TRIPS CPython's hackcheck ON
    # 3.8-3.12 (_DataBase IS A STATIC TYPE WITH ITS OWN tp_setattro); THE
    # SLOT MEMBER AND __class__ DESCRIPTORS CARRY NO SUCH CHECK
    _slot_set = utils._speedups._StoreBase._internal_value.__set__
    _class_set = vars(object)["__class__"].__set__

    def _set(obj, key, value):
        if key == SLOT:
            _slot_set(obj, value)
        elif key == CLASS:
            _class_set(obj, value)
        else:
            object.__setattr__(obj, key, value)


DEBUG = False


class Data:
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
        return not is_missing(Data.__getitem__(self, item))

    def __iter__(self):
        d = _get(self, SLOT)
        if _get(d, CLASS) is dict:
            yield from d.items()
        else:
            yield from d.__iter__()

    def __getitem__(self, key):
        if is_null(key):
            return Null
        key = str(key)
        d = _get(self, SLOT)

        if "." not in key and "\b" not in key:
            o = d.get(key)
            if is_null(o):
                return NullType(d, key)
            return to_data(o)

        path = split_field(key)
        if not path:
            return self if is_data(d) else d
        for n in path:
            if _get(d, CLASS) is NullType:
                d = NullType(d, n)
            elif is_many(d):
                d = [_getdefault(dd, n) for dd in d]
            else:
                d = _getdefault(d, n)
        return to_data(d)

    def __setitem__(self, key, value):
        if key == "":
            get_logger().error("key is empty string.  Probably a bad idea")
        if is_null(key):
            return Null
        try:
            d = _get(self, SLOT)
            value = from_data(value)
            if "." not in key and "\b" not in key:
                if value is None:
                    d.pop(key, None)
                else:
                    d[key] = value
                return self

            seq = split_field(key)
            if not seq:
                # SOMETHING TERRIBLE HAPPENS WHEN value IS NOT A Mapping;
                # HOPEFULLY THE ONLY OTHER METHOD RUN ON self IS from_data()
                if is_many(value):
                    _set(self, CLASS, FlatList)
                _set(self, SLOT, value)
                return self
            for k in seq[:-1]:
                d = _getdefault(d, k)
            if is_null(value):
                try:
                    d.pop(seq[-1], None)
                except Exception as _:
                    pass
            elif is_null(d):
                d[literal_field(seq[-1])] = value
            elif is_sequence(d):
                for dd in d:
                    from_data(dd)[seq[-1]] = value
            else:
                d[seq[-1]] = value
            return self
        except Exception as e:
            from mo_logs import logger

            logger.error("can not set key={key}", key=key, cause=e)

    def __getattr__(self, key):
        d = _get(self, SLOT)
        v = d.get(key)

        # OPTIMIZED to_data(): _getattr_dispatch MAPS VALUE CLASS TO WRAPPER
        handler = _getattr_dispatch.get(_get(v, CLASS))
        if handler is None:
            return v
        if handler is NullType:
            return NullType(d, key)
        return handler(v)

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
        return to_data(_iadd(deepcopy(from_data(self)), other))

    def __radd__(self, other):
        return to_data(_iadd(_iadd({}, other), self))

    def __iadd__(self, other):
        if is_missing(other) or is_data(other):
            return _iadd(self, other)
        # HAPPENS WHEN += WITH ['.'] SELF REFERENCE
        d = _get(self, SLOT)
        if isinstance(d, dict) and not len(d):
            # LOOKS LIKE A FRESH Data OBJECT (AN IDENTITY ELEMENT)
            # âˆ€ x, x += {} => x
            d = Data()
        else:
            d = dict_to_data({"$": self})
        d += dict_to_data({"$": other})
        d["."] = d["$"]
        return d

    def __or__(self, other):
        """
        RECURSIVE COALESCE OF DATA PROPERTIES
        """
        if not is_data(other) and not is_missing(other):
            get_logger().error("Expecting Data")

        d = _get(self, SLOT)
        output = Data(**d)  # COPY
        if is_missing(other):
            return output
        output.__ior__(other)
        return output

    def __ror__(self, other):
        """
        RECURSIVE COALESCE OF DATA PROPERTIES
        """
        if is_missing(other):
            return self | Null
        if not is_data(other):
            get_logger().error("Expecting Data")

        return to_data(other).__or__(self)

    def __ior__(self, other):
        """
        RECURSIVE COALESCE OF DATA PROPERTIES
        """
        d = _get(self, SLOT)
        if not is_data(other):
            if is_missing(d) or (isinstance(d, dict) and not d):
                _set(self, SLOT, other)
            return self

        for ok, ov in other.items():
            if is_missing(ov):
                continue

            sv = to_data(d.get(ok))
            if is_missing(sv):
                d[ok] = ov
            elif is_data(sv) and is_data(ov):
                d[ok] = sv | ov
        return self

    def __hash__(self):
        d = _get(self, SLOT)
        if _get(d, CLASS) is not dict:
            return hash_value(d)
        return hash(frozenset((k, hash_value(v)) for k, v in d.items() if not is_missing(v)))

    def __eq__(self, other):
        if self is other:
            return True

        d = _get(self, SLOT)
        if _get(d, CLASS) is not dict:
            return d == other

        if not d and is_null(other):
            return False

        if not is_data(other):
            return False
        # UNWRAP: d HOLDS RAW KEYS, AND Data.get WOULD READ A DOT AS A PATH
        e = from_data(other)
        if _get(e, CLASS) is not dict:
            e = other
        # ASK `==`, NOT `!=`: A MISSING KEY ANSWERS Null, AND `Null != value` IS Null - FALSY -
        # SO EVERY EXTRA KEY WAS READ AS A MATCH, AND {"a": 1, "b": 2} == {"a": 1}
        for k, v in d.items():
            if not (e.get(k) == v) and not is_missing(v):
                return False
        for k, v in e.items():
            if not (d.get(k) == v) and not is_missing(v):
                return False
        return True

    def __ne__(self, other):
        return not self.__eq__(other)

    def get(self, key, default=Null):
        v = self[key]
        return v if default is Null else coalesce(v, default)

    def items(self):
        d = _get(self, SLOT)
        return [(k, to_data(v)) for k, v in d.items() if v != None or is_data(v)]

    def leaves(self, prefix=None):
        """
        LIKE items() BUT RECURSIVE, AND ONLY FOR THE LEAVES (non dict) VALUES
        """
        return leaves(self, prefix)

    def pop(self, key, default=Null):
        if is_null(key):
            return Null
        seq = split_field(str(key))
        if not seq:
            return Null
        d = _get(self, SLOT)

        for n in seq[:-1]:
            if _get(d, CLASS) is NullType:
                d = NullType(d, n)
            elif is_many(d):
                d = [_getdefault(dd, n) for dd in d]
            else:
                d = _getdefault(d, n)
        key = seq[-1]

        o = d.get(key)
        if is_null(o):
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
        d = _get(self, SLOT)
        if "." not in key and "\b" not in key:
            d.pop(key, None)
            return

        seq = split_field(key)
        for k in seq[:-1]:
            d = d[k]
        d.pop(seq[-1], None)

    def __delattr__(self, key):
        key = str(key)
        d = _get(self, SLOT)
        d.pop(key, None)

    def setdefault(self, k, d=None):
        v = self[k]
        if is_null(v):
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


if utils._speedups:
    # REBUILD OVER THE C BASE: getattr/setattr/delattr/getitem/setitem/delitem/
    # bool/iter/contains/len/get/items BECOME C SLOTS AND METHODS; THE PURE
    # METHODS REMAIN AS THE SLOW PATH (DOTTED EDGE CASES, NON-dict SLOTS)
    _pure_Data = Data
    Data = utils._rebuild_class(
        _pure_Data,
        utils._speedups._DataBase,
        {
            "__getattr__",
            "__setattr__",
            "__delattr__",
            "__getitem__",
            "__setitem__",
            "__delitem__",
            "__bool__",
            "__iter__",
            "__contains__",
            "__len__",
            "get",
            "items",
        },
    )
    utils._speedups._init_data(
        Data,
        _pure_Data.__getattr__,
        _pure_Data.__getitem__,
        _pure_Data.__setitem__,
        _pure_Data.__delitem__,
        _pure_Data.items,
    )

MutableMapping.register(Data)
register_view(Data)


def leaves(value, prefix=None):
    """
    LIKE items() BUT RECURSIVE, AND ONLY FOR THE LEAVES (non dict) VALUES
    SEE leaves_to_data FOR THE INVERSE

    :param value: THE Mapping TO TRAVERSE
    :param prefix:  OPTIONAL PREFIX GIVEN TO EACH KEY
    :return: Data, WHICH EACH KEY BEING A PATH INTO value TREE
    """
    if not prefix:
        yield from _leaves(".", value, tuple())
    else:
        for k, v in _leaves(".", value, tuple()):
            yield prefix + k, v


def _leaves(parent, value, path):
    val = from_data(value)
    _id = id(val)
    if _id in path:
        yield parent, value
        return
    obj = object_to_data(val)
    if obj is val or is_many(val):
        yield parent, value
        return

    for k in get_keys(obj):
        try:
            v = obj[literal_field(k)]
            if is_missing(v):
                continue
            kk = concat_field(parent, literal_field(k))
            vv = object_to_data(v)
            yield from _leaves(kk, vv, path + (_id,))
        except Exception as cause:
            get_logger().error("Do not know how to handle", cause=cause)


def _iadd(self, other):
    """
    RECURSIVE ADDITION OF DATA PROPERTIES
    * LISTS ARE CONCATENATED
    * SETS ARE UNIONED
    * NUMBERS ARE ADDED
    """
    if is_missing(other):
        return self
    if not is_data(other):
        get_logger().error(
            "can not add {stype} with {otype}", stype=_get(self, CLASS).__name__, otype=_get(other, CLASS).__name__
        )

    d = from_data(self)
    for ok, ov in other.items():
        sv = d.get(ok)
        if is_null(sv):
            d[ok] = from_data(deepcopy(ov))
        elif is_many(ov):
            d[ok] = from_data(listwrap(sv) + ov)
        elif is_data(sv) and is_data(ov):
            _iadd(sv, ov)
        elif is_many(sv):
            d[ok].append(ov)
        elif is_data(sv) or is_data(ov):
            get_logger().error(
                "can not add {stype} with {otype}", stype=_get(sv, CLASS).__name__, otype=_get(ov, CLASS).__name__
            )
        elif isinstance(ov, (Decimal, float, int)):
            d[ok] = sv + ov
        else:
            d[ok].append(ov)
    return self


def hash_value(v):
    if is_many(v):
        return hash_value(first(v))
    elif is_data(v):
        return hash(to_data(v))
    else:
        return hash(v)


def dict_to_data(d):
    """
    FASTEST WAY TO MAKE Data, DO NOT CHECK TYPE
    :param d: dict
    :return: Data
    """
    m = Data.__new__(Data)
    _set(m, SLOT, d)
    return m


def _gen_to_data(v):
    return FlatList(list(from_data(vv) for vv in v))


_getattr_dispatch = {}


def _nan_to_null(v):
    return Null if v != v else v


def _rebuild_getattr_dispatch():
    # NullType IS A SENTINEL: __getattr__ CONSTRUCTS NullType(d, key) FOR NULL VALUES
    _getattr_dispatch.clear()
    for t in utils._null_types:
        _getattr_dispatch[t] = NullType
    _getattr_dispatch[dict] = dict_to_data
    _getattr_dispatch[OrderedDict] = dict_to_data
    _getattr_dispatch[list] = list_to_data
    _getattr_dispatch[float] = _nan_to_null
    for t in generator_types:
        _getattr_dispatch[t] = _gen_to_data
    for t in utils._wrapped_data_types:
        # A MAPPING mo-dots DID NOT BUILD NAVIGATES THE WAY A dict DOES
        _getattr_dispatch.setdefault(t, dict_to_data)


utils.on_null_type_change(_rebuild_getattr_dispatch)
utils.on_data_type_change(_rebuild_getattr_dispatch)
_rebuild_getattr_dispatch()


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
    if is_null(value):
        return None

    if is_primitive(value):
        return value

    _class = _get(value, CLASS)
    if _class in utils._data_types:
        if _class is Data:
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

            if is_null(value):
                d.pop(seq[-1], None)
            else:
                d[seq[-1]] = value
        return output

    if hasattr(value, "__iter__"):
        return [_leaves_to_data(v) for v in value]

    return value
