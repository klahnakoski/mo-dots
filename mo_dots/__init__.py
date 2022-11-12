# encoding: utf-8
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.
#
# Contact: Kyle Lahnakoski (kyle@lahnakoski.com)
#

from __future__ import absolute_import, division, unicode_literals

import re
import sys

from mo_dots.datas import Data, data_types, is_data
from mo_dots.lists import (
    FlatList,
    is_list,
    is_sequence,
    is_container,
    is_many,
    list_types,
    container_types,
    finite_types,
    last
)
from mo_dots.nones import Null, NullType
from mo_dots.objects import DataObject
from mo_dots.utils import CLASS, SLOT, get_logger, get_module
from mo_future import (
    binary_type,
    generator_types,
    text,
    OrderedDict,
    none_type, flatten,
    first,
)
from mo_imports import export

_module_type = type(sys.modules[__name__])
_builtin_zip = zip
_get = object.__getattribute__
_set = object.__setattr__
_new = object.__new__
_dict_zip = zip


def inverse(d):
    """
    reverse the k:v pairs
    """
    output = {}
    for k, v in from_data(d).items():
        output[v] = output.get(v, [])
        output[v].append(k)
    return output


def coalesce(*args):
    # pick the first not null value
    # http://en.wikipedia.org/wiki/Null_coalescing_operator
    for a in args:
        if a != None:
            return to_data(a)
    return Null


def zip(keys, values):
    """
    CONVERT LIST OF KEY/VALUE PAIRS TO Data
    PLEASE `import mo_dots`, AND CALL `mo_dots.zip()`
    """
    output = Data()
    for k, v in _dict_zip(keys, values):
        output[k] = v
    return output


def missing(value):
    raise NotImplementedError("use is_missing")


def is_missing(t):
    # RETURN True IF EFFECTIVELY NOTHING
    class_ = t.__class__
    if class_ in null_types:
        return True
    elif class_ in data_types:
        return False
    elif class_ in finite_types and not t:
        return True
    elif class_ is text and not t:
        return True
    else:
        return t == None


def exists(value):
    return not is_missing(value)


ESCAPE_DOTS1 = re.compile(r"(^\.|\.$)")  # DOTS AT START/END
ESCAPE_DOTS2 = re.compile(r"(?<!^)\.(?!$)")  # INTERNAL DOTS
ILLEGAL_DOTS = re.compile(r"[^.]\.(?:\.\.)+")  # ODD DOTS ARE NOT ALLOWED
SPLIT_DOTS = re.compile(r"(?<!\.)\.(?!\.)")  # SINGLE DOTS
UNESCAPE_DOTS = re.compile(r"\x08|(?:\.\.)")  # ENCODED DOTS


def literal_field(field):
    """
    RETURN SAME WITH DOTS (`.`) ESCAPED
    """
    try:
        return ESCAPE_DOTS2.sub("..", ESCAPE_DOTS1.sub("\b", field))
    except Exception as e:
        get_logger().error("bad literal", e)


def unliteral_field(field):
    """
    DUE TO PATHOLOGY IN MY CODE WE HAVE A path WITH ESCAPED DOTS BUT WE WANT OT USE IT ON A dict, NOT A Data
    a = dict()
    b = Data(a)
    a[unliteral_field(k)]==b[k] (for all k)

    :param field: THE STRING TO DE-literal IZE
    :return: SIMPLER STRING
    """
    return UNESCAPE_DOTS.sub(".", field)


def tail_field(field):
    """
    RETURN THE FIRST STEP IN PATH, ALONG WITH THE REMAINING TAILf
    IN (first, rest) PAIR
    """
    if field == "." or field == None or field == "":
        return ".", "."
    elif "." in field:
        path = split_field(field)
        return path[0], join_field(path[1:])
    else:
        return field, "."


def split_field(field):
    """
    RETURN field AS ARRAY OF DOT-SEPARATED FIELDS
    """
    if ILLEGAL_DOTS.search(field):
        get_logger().error("Odd number of dots is not allowed")
    if field.startswith(".."):
        remainder = field.lstrip(".")
        back = len(field) - len(remainder) - 1
        return [".."] * back + [
            UNESCAPE_DOTS.sub(".", k) for k in SPLIT_DOTS.split(remainder) if k
        ]
    else:
        return [UNESCAPE_DOTS.sub(".", k) for k in SPLIT_DOTS.split(field) if k]


def join_field(path):
    """
    RETURN field SEQUENCE AS STRING
    """
    if path.__class__ in generator_types:
        path = list(path)

    if not path:
        return "."

    prefix = ""
    while True:
        try:
            i = path.index("..")
            if i == 0:
                prefix += "."
                path = path[1:]
            else:
                path = path[: i - 1] + path[i + 1 :]
        except ValueError:
            return (
                ("." if prefix else "")
                + prefix
                + ".".join(literal_field(f) for f in path)
            )


def concat_field(*fields):
    return join_field(flatten(split_field(f) for f in fields))


def startswith_field(field, prefix):
    """
    RETURN True IF field PATH STRING STARTS WITH prefix PATH STRING
    """
    if prefix == None:
        return False
    if prefix.startswith("."):
        return True
        # f_back = len(field) - len(field.strip("."))
        # p_back = len(prefix) - len(prefix.strip("."))
        # if f_back > p_back:
        #     return False
        # else:
        #     return True

    if field.startswith(prefix):
        lp = len(prefix)
        if len(field) == len(prefix) or field[lp] in (".", "\b") and field[lp+1] not in (".", "\b"):
            return True
    return False


def endswith_field(field, suffix):
    """
    RETURN True IF field PATH STRING ENDS WITH suffix PATH STRING
    """
    if suffix == None:
        return False
    if suffix == ".":
        return True

    if field.endswith(suffix):
        ls = len(suffix)
        if len(field) == ls or field[-ls - 1] in (".", "\b") and field[-ls - 2] not in (".", "\b"):
            return True
    return False


def relative_field(field, parent):
    """
    RETURN field PATH WITH RESPECT TO parent
    """
    if parent == ".":
        return field

    field_path = split_field(field)
    parent_path = split_field(parent)
    common = 0
    for f, p in _builtin_zip(field_path, parent_path):
        if f != p:
            break
        common += 1

    tail = join_field(field_path[common:])
    if len(parent_path) <= common:
        return join_field(field_path[common:])

    dots = "." * (len(parent_path) - common)
    if tail == ".":
        return "." + dots
    else:
        return "." + dots + tail


def hash_value(v):
    if is_many(v):
        return hash_value(first(v))
    elif _get(v, CLASS) in data_types:
        return hash_value(first(v.values()))
    else:
        return hash(v)


def fromkeys(keys, value=None):
    if value == None:
        return Data()
    return dict_to_data(dict.fromkeys(keys, value))


def set_default(d, *dicts):
    """
    RECURSIVE MERGE OF MULTIPLE dicts MOST IMPORTANT FIRST

    UPDATES d WITH THE MERGE RESULT, WHERE MERGE RESULT IS DEFINED AS:
    FOR EACH LEAF, RETURN THE FIRST NOT-NULL LEAF VALUE

    :param dicts: dicts IN PRIORITY ORDER, HIGHEST TO LOWEST
    :return: d
    """
    agg = d if d or _get(d, CLASS) in data_types else {}
    for p in dicts:
        _set_default(agg, p, seen={})
    return to_data(agg)


def _set_default(d, default, seen=None):
    """
    ANY VALUE NOT SET WILL BE SET BY THE default
    THIS IS RECURSIVE
    """
    if default is None:
        return

    for k, default_value in default.items():
        raw_value = from_data(default_value)  # TWO DIFFERENT Dicts CAN SHARE id() BECAUSE THEY ARE SHORT LIVED
        if is_data(d):
            existing_value = d.get(k)
        else:
            existing_value = _get_attr(d, [k])

        if existing_value == None:
            if default_value != None:
                if _get(default_value, CLASS) in data_types:
                    df = seen.get(id(raw_value))
                    if df is not None:
                        _set_attr(d, [k], df)
                    else:
                        copy_dict = {}
                        seen[id(raw_value)] = copy_dict
                        _set_attr(d, [k], copy_dict)
                        _set_default(copy_dict, default_value, seen)
                else:
                    # ASSUME PRIMITIVE (OR LIST, WHICH WE DO NOT COPY)
                    try:
                        _set_attr(d, [k], default_value)
                    except Exception as e:
                        if PATH_NOT_FOUND not in e:
                            get_logger().error(
                                "Can not set attribute {{name}}", name=k, cause=e
                            )
        elif is_list(existing_value) or is_list(default_value):
            _set_attr(d, [k], None)
            _set_attr(d, [k], listwrap(existing_value) + listwrap(default_value))
        elif (
            hasattr(existing_value, "__setattr__")
            or _get(existing_value, CLASS) in data_types
        ) and _get(default_value, CLASS) in data_types:
            df = seen.get(id(raw_value))
            if df is not None:
                _set_attr(d, [k], df)
            else:
                seen[id(raw_value)] = existing_value
                _set_default(existing_value, default_value, seen)


def _getdefault(obj, key):
    """
    obj ANY OBJECT
    key IS EXPECTED TO BE LITERAL (NO ESCAPING)
    TRY BOTH ATTRIBUTE AND ITEM ACCESS, OR RETURN Null
    """
    try:
        return obj[key]
    except Exception as f:
        pass

    if is_sequence(obj):
        return [_getdefault(o, key) for o in obj]

    try:
        if obj.__class__ is not dict:
            return getattr(obj, key)
    except Exception as f:
        pass

    try:
        if float(key) == round(float(key), 0):
            return obj[int(key)]
    except Exception as f:
        pass

    # TODO: FIGURE OUT WHY THIS WAS EVER HERE (AND MAKE A TEST)
    # try:
    #     return eval("obj."+text(key))
    # except Exception as f:
    #     pass
    return NullType(obj, key)


PATH_NOT_FOUND = "Path not found"
AMBIGUOUS_PATH_FOUND = "Path is ambiguous"


def set_attr(obj, path, value):
    """
    SAME AS object.__setattr__(), BUT USES DOT-DELIMITED path
    RETURN OLD VALUE
    """
    try:
        return _set_attr(obj, split_field(path), value)
    except Exception as cause:
        Log = get_logger()
        if PATH_NOT_FOUND in cause:
            Log.warning(PATH_NOT_FOUND + ": {{path}}", path=path, cause=cause)
        else:
            Log.error("Problem setting value", cause=cause)


def get_attr(obj, path):
    """
    SAME AS object.__getattr__(), BUT USES DOT-DELIMITED path
    """
    try:
        return _get_attr(obj, split_field(path))
    except Exception as cause:
        Log = get_logger()
        if PATH_NOT_FOUND in e:
            Log.error(PATH_NOT_FOUND + ": {{path}}", path=path, cause=cause)
        else:
            Log.error("Problem setting value", cause=cause)


def _get_attr(obj, path):
    if not path:
        return obj

    attr_name = path[0]

    if isinstance(obj, _module_type):
        if attr_name in obj.__dict__:
            return _get_attr(obj.__dict__[attr_name], path[1:])
        elif attr_name in dir(obj):
            return _get_attr(obj[attr_name], path[1:])

        # TRY FILESYSTEM
        File = get_module("mo_files").File
        possible_error = None
        python_file = (File(obj.__file__).parent / attr_name).set_extension("py")
        python_module = File(obj.__file__).parent / attr_name / "__init__.py"
        if python_file.exists or python_module.exists:
            try:
                # THIS CASE IS WHEN THE __init__.py DOES NOT IMPORT THE SUBDIR FILE
                # WE CAN STILL PUT THE PATH TO THE FILE IN THE from CLAUSE
                if len(path) == 1:
                    # GET MODULE OBJECT
                    output = __import__(
                        obj.__name__ + str(".") + str(attr_name),
                        globals(),
                        locals(),
                        [str(attr_name)],
                        0,
                    )
                    return output
                else:
                    # GET VARIABLE IN MODULE
                    output = __import__(
                        obj.__name__ + str(".") + str(attr_name),
                        globals(),
                        locals(),
                        [str(path[1])],
                        0,
                    )
                    return _get_attr(output, path[1:])
            except Exception as e:
                Except = get_module("mo_logs.exceptions.Except")
                possible_error = Except.wrap(e)

        # TRY A CASE-INSENSITIVE MATCH
        matched_attr_name = lower_match(attr_name, dir(obj))
        if not matched_attr_name:
            get_logger().warning(
                PATH_NOT_FOUND + "({{name|quote}}) Returning None.",
                name=attr_name,
                cause=possible_error,
            )
        elif len(matched_attr_name) > 1:
            get_logger().error(AMBIGUOUS_PATH_FOUND + " {{paths}}", paths=attr_name)
        else:
            return _get_attr(obj, matched_attr_name + path[1:])

    try:
        obj = obj[int(attr_name)]
        return _get_attr(obj, path[1:])
    except Exception:
        pass

    try:
        obj = getattr(obj, attr_name)
        return _get_attr(obj, path[1:])
    except Exception:
        pass

    try:
        obj = obj[attr_name]
        return _get_attr(obj, path[1:])
    except Exception as f:
        return NullType(obj, attr_name)


def _set_attr(obj_, path, value):
    obj = _get_attr(obj_, path[:-1])
    if obj is None:
        # DELIBERATE USE OF `is`: WE DO NOT WHAT TO CATCH Null HERE (THEY CAN BE SET)
        get_logger().error(PATH_NOT_FOUND + " tried to get attribute of None")

    attr_name = path[-1]

    # ACTUAL SETTING OF VALUE
    try:
        old_value = _get_attr(obj, [attr_name])
        old_type = _get(old_value, CLASS)
        if old_value == None or old_type in (bool, int, float, text, binary_type):
            old_value = None
            new_value = value
        elif value == None:
            new_value = None
        else:
            new_value = _get(
                old_value, CLASS
            )(value)  # TRY TO MAKE INSTANCE OF SAME CLASS
    except Exception:
        old_value = None
        new_value = value

    try:
        setattr(obj, attr_name, new_value)
        return old_value
    except Exception as e:
        try:
            obj[attr_name] = new_value
            return old_value
        except Exception as f:
            get_logger().error(PATH_NOT_FOUND, cause=[f, e])


def lower_match(value, candidates):
    return [v for v in candidates if v.lower() == value.lower()]


def dict_to_data(d):
    """
    FASTEST WAY TO MAKE Data, DO NOT CHECK TYPE
    :param d: dict
    :return: Data
    """
    m = _new(Data)
    _set(m, SLOT, d)
    return m


def list_to_data(v):
    """
    to_data, BUT WITHOUT CHECKS
    """
    output = _new(FlatList)
    _set(output, SLOT, v)
    return output


def to_data(v=None) -> object:
    """
    WRAP AS Data OBJECT FOR DATA PROCESSING: https://github.com/klahnakoski/mo-dots/tree/dev/docs
    :param v:  THE VALUE TO WRAP
    :return:  Data INSTANCE
    """

    type_ = _get(v, CLASS)

    if type_ in (dict, OrderedDict):
        m = _new(Data)
        _set(m, SLOT, v)
        return m
    elif type_ is none_type:
        return Null
    elif type_ is tuple:
        return list_to_data(v)
    elif type_ is list:
        return list_to_data(v)
    elif type_ in generator_types:
        return list_to_data(list(from_data(vv) for vv in v))
    else:
        return v


wrap = to_data


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

    class_ = _get(value, CLASS)
    if class_ in (text, binary_type, int, float):
        return value

    if class_ in data_types:
        if class_ is Data:
            value = from_data(value)

        output = {}
        for key, value in value.items():
            value = _leaves_to_data(value)

            if key == "":
                get_logger().error("key is empty string.  Probably a bad idea")

            d = output
            seq = split_field(key)
            for k in seq[:-1]:
                e = d.get(k, None)
                if e is None:
                    d[k] = {}
                    e = d[k]
                d = e

            if value == None:
                d.pop(seq[-1], None)
            else:
                d[seq[-1]] = value
        return output

    if hasattr(value, "__iter__"):
        return [_leaves_to_data(v) for v in value]

    return value


def from_data(v):
    if v is None:
        return None
    _type = _get(v, CLASS)
    if _type is NullType:
        return None
    elif _type is Data:
        d = _get(v, SLOT)
        return d
    elif _type is FlatList:
        return _get(v, SLOT)
    elif _type is DataObject:
        return _get(v, SLOT)
    elif _type in generator_types:
        return (from_data(vv) for vv in v)
    else:
        return v


unwrap = from_data


def listwrap(value):
    """
    PERFORMS THE FOLLOWING TRANSLATION
    None -> []
    value -> [value]
    [...] -> [...]  (unchanged list)

    ## MOTIVATION ##
    OFTEN IT IS NICE TO ALLOW FUNCTION PARAMETERS TO BE ASSIGNED A VALUE,
    OR A list-OF-VALUES, OR NULL.  CHECKING FOR WHICH THE CALLER USED IS
    TEDIOUS.  INSTEAD WE CAST FROM THOSE THREE CASES TO THE SINGLE CASE
    OF A LIST

    # BEFORE
    def do_it(a):
        if a is None:
            return
        if not isinstance(a, list):
            a=[a]
        for x in a:
            # do something

    # AFTER
    def do_it(a):
        for x in listwrap(a):
            # do something

    """
    if value == None:
        return FlatList()
    elif is_list(value):
        if isinstance(value, list):
            return list_to_data(value)
        else:
            return value
    elif is_many(value):
        return list_to_data(list(value))
    else:
        return list_to_data([from_data(value)])


def unwraplist(v):
    """
    LISTS WITH ZERO AND ONE element MAP TO None AND element RESPECTIVELY
    """
    if is_list(v):
        if len(v) == 0:
            return None
        elif len(v) == 1:
            return from_data(v[0])
        else:
            return from_data(v)
    else:
        return from_data(v)


def tuplewrap(value):
    """
    INTENDED TO TURN lists INTO tuples FOR USE AS KEYS
    """
    if value == None:
        return tuple()
    elif is_many(value):
        return tuple(tuplewrap(v) if is_sequence(v) else v for v in value)
    else:
        return from_data(value),


def is_null(t):
    # RETURN True IF EFFECTIVELY NOTHING
    class_ = t.__class__
    if class_ in null_types:
        return True
    else:
        try:
            return t == None
        except Exception:
            return False


def is_not_null(t):
    # RETURN True IF EFFECTIVELY SOMETHING
    class_ = t.__class__
    if class_ in null_types:
        return False
    elif class_ in data_types:
        return True
    elif class_ in finite_types and t:
        return True
    else:
        return t != None


null_types = (none_type, NullType)

# EXPORT
export("mo_dots.nones", to_data)
export("mo_dots.nones", null_types)
export("mo_dots.nones", get_attr)

export("mo_dots.datas", list_to_data)
export("mo_dots.datas", dict_to_data)
export("mo_dots.datas", to_data)
export("mo_dots.datas", from_data)
export("mo_dots.datas", coalesce)
export("mo_dots.datas", _getdefault)
export("mo_dots.datas", hash_value)
export("mo_dots.datas", listwrap)
export("mo_dots.datas", literal_field)
export("mo_dots.datas", null_types)
export("mo_dots.datas", concat_field)

export("mo_dots.lists", list_to_data)
export("mo_dots.lists", to_data)
export("mo_dots.lists", coalesce)
export("mo_dots.lists", from_data)
export("mo_dots.lists", hash_value)

export("mo_dots.objects", list_to_data)
export("mo_dots.objects", dict_to_data)
export("mo_dots.objects", to_data)
export("mo_dots.objects", from_data)
export("mo_dots.objects", get_attr)
export("mo_dots.objects", set_attr)
export("mo_dots.objects", set_default)
