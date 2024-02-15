# encoding: utf-8
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.
#
# Contact: Kyle Lahnakoski (kyle@lahnakoski.com)
#



from collections import OrderedDict
from copy import deepcopy
from datetime import date, datetime
from decimal import Decimal

from mo_future import (
    binary_type,
    generator_types,
    get_function_arguments,
    get_function_defaults,
    text,
    Mapping,
)
from mo_imports import export, expect

from mo_dots.datas import register_data, Data, _iadd
from mo_dots.lists import FlatList
from mo_dots.nones import NullType, Null
from mo_dots.utils import CLASS, SLOT

get_attr, set_attr, list_to_data, dict_to_data, to_data, from_data, set_default = expect(
    "get_attr", "set_attr", "list_to_data", "dict_to_data", "to_data", "from_data", "set_default"
)

_new = object.__new__
_get = object.__getattribute__
_set = object.__setattr__
WRAPPED_CLASSES = set()


class DataObject(Mapping):
    """
    TREAT AN OBJECT LIKE DATA
    """

    __slots__ = [SLOT]

    def __init__(self, obj):
        _set(self, SLOT, obj)

    def __getattr__(self, item):
        obj = _get(self, SLOT)
        output = get_attr(obj, item)
        return object_to_data(output)

    def __setattr__(self, key, value):
        obj = _get(self, SLOT)
        set_attr(obj, key, value)

    def __getitem__(self, item):
        obj = _get(self, SLOT)
        output = get_attr(obj, item)
        return object_to_data(output)

    def __or__(self, other):
        return set_default({}, self, other)

    def __ror__(self, other):
        return to_data(other) | self

    def __add__(self, other):
        return to_data(_iadd(_iadd({}, self), other))

    def __radd__(self, other):
        return to_data(_iadd(_iadd({}, other), self))

    def get(self, item):
        obj = _get(self, SLOT)
        output = get_attr(obj, item)
        return object_to_data(output)

    def keys(self):
        obj = _get(self, SLOT)
        try:
            return obj.__dict__.keys()
        except Exception as e:
            raise e

    def items(self):
        obj = _get(self, SLOT)
        try:
            for k, v in obj.__dict__.items():
                yield k, object_to_data(v)
        except Exception as e:
            for k in dir(obj):
                if k.startswith("__"):
                    continue
                yield k, object_to_data(getattr(obj, k, None))

    def __deepcopy__(self, memodict={}):
        output = {}
        for k, v in self.items():
            output[k] = from_data(deepcopy(v))
        return dict_to_data(output)

    def __data__(self):
        return self

    def __iter__(self):
        return (k for k in self.keys())

    def __str__(self):
        obj = _get(self, SLOT)
        return str(obj)

    def __len__(self):
        obj = _get(self, SLOT)
        return len(obj)

    def __call__(self, *args, **kwargs):
        obj = _get(self, SLOT)
        return obj(*args, **kwargs)


register_data(DataObject)


def object_to_data(v):
    try:
        if v == None:
            return Null
    except Exception:
        pass

    type_ = _get(v, CLASS)

    if type_ is (dict, OrderedDict):
        m = _new(Data)
        _set(m, SLOT, v)
        return m
    elif type_ is tuple:
        return list_to_data(v)
    elif type_ is list:
        return list_to_data(v)
    elif type_ in (Data, DataObject, FlatList, NullType):
        return v
    elif type_ in (text, binary_type, int, float, Decimal, datetime, date):
        return v
    elif type_ in generator_types:
        return (to_data(vv) for vv in v)

    return DataObject(v)


datawrap = object_to_data


class DataClass(object):
    """
    ALLOW INSTANCES OF class_ TO ACT LIKE dicts
    ALLOW CONSTRUCTOR TO ACCEPT @override
    """

    def __init__(self, class_):
        WRAPPED_CLASSES.add(class_)
        self.class_ = class_
        self.constructor = class_.__init__

    def __call__(self, *args, **kwargs):
        settings = to_data(kwargs).settings

        params = get_function_arguments(self.constructor)[1:]
        func_defaults = get_function_defaults(self.constructor)
        if not func_defaults:
            defaults = {}
        else:
            defaults = {k: v for k, v in zip(reversed(params), reversed(func_defaults))}

        ordered_params = dict(zip(params, args))

        output = self.class_(**params_pack(params, ordered_params, kwargs, settings, defaults))
        return DataObject(output)


def params_pack(params, *args):
    settings = {}
    for a in args:
        for k, v in a.items():
            k = str(k)
            if k in settings:
                continue
            settings[k] = v

    output = {str(k): from_data(settings[k]) for k in params if k in settings}
    return output


export("mo_dots.lists", "object_to_data", object_to_data)
export("mo_dots.lists", "datawrap", object_to_data)
