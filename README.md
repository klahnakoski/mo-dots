
# More Dots!

[![PyPI Latest Release](https://img.shields.io/pypi/v/mo-dots.svg)](https://pypi.org/project/mo-dots/)
[![Build Status](https://github.com/klahnakoski/mo-dots/actions/workflows/build.yml/badge.svg?branch=master)](https://github.com/klahnakoski/mo-dots/actions/workflows/build.yml)
[![Coverage Status](https://coveralls.io/repos/github/klahnakoski/mo-dots/badge.svg?branch=dev)](https://coveralls.io/github/klahnakoski/mo-dots?branch=dev)
[![Downloads](https://static.pepy.tech/badge/mo-dots/month)](https://pepy.tech/project/mo-dots)

## Overview

Box your JSON-like data in a `Data` object to get null-safe dot access.  This library is a replacement for `dict` that is more consistent and easier to use.

> See [full documentation](https://github.com/klahnakoski/mo-dots/tree/dev/docs) for all the features of `mo-dots`

> See [change log](https://github.com/klahnakoski/mo-dots/tree/dev/docs/CHANGELOG.md) to read about major changes

### Create instances

Define `Data` using named parameters, just like you would a `dict`

    >>> from mo_dots import Data
    >>> Data(b=42, c="hello world")
    Data({'b': 42, 'c': 'hello world'})

You can also box an existing `dict`s so they can be used like `Data`

    >>> from mo_dots import to_data
    >>> to_data({'b': 42, 'c': 'hello world'})
    Data({'b': 42, 'c': 'hello world'})

### Dot Access

Access properties with attribute dots: `a.b == a["b"]`. You have probably seen this before.

### Path Access

Access properties by dot-delimited path.

	>>> a = to_data({"b": {"c": 42}})
	>>> a["b.c"] == 42
	True

### Null-Safe Access

If a property does not exist then return `Null` rather than raising an error.

	>>> a = Data()
	>>> a.b == Null
	True
	>>> a.b.c == Null
	True
	>>> a[None] == Null
	True

### Path assignment

No need to make intermediate `dicts`

    >>> a = Data()
    >>> a["b.c"] = 42   # same as a.b.c = 42
    a == {"b": {"c": 42}}

### Path accumulation

Use `+=` to add to a property; default zero (`0`)

    >>> a = Data()
    a == {}
    >>> a.b.c += 1
    a == {"b": {"c": 1}}
    >>> a.b.c += 42
    a == {"b": {"c": 43}}

Use `+=` with a list (`[]`) to append to a list; default empty list (`[]`)

    >>> a = Data()
    a == {}
    >>> a.b.c += [1]
    a == {"b": {"c": [1]}}
    >>> a.b.c += [42]
    a == {"b": {"c": [1, 42]}}

## Serializing to JSON

Use [mo-json](https://pypi.org/project/mo-json/): `value2json` converts `Data`, `FlatList` and many more structures to JSON, and `json2value` answers `Data`.

    from mo_dots import to_data
    from mo_json import value2json
    
    result = value2json(to_data({"a": ["b", 1]}))

Where mo-json is not a dependency, the standard library works with `default=from_data`, which converts the data structures in this module into Python primitives of the same:

    result = json.dumps(s, default=from_data)


## Using with Claude Code

This repo is a Claude Code plugin marketplace. Its `mo-dots` skill teaches an agent to write code with this library:

    /plugin marketplace add klahnakoski/mo-dots
    /plugin install mo-dots@mo-dots

Without the plugin, add this line to your project's `CLAUDE.md`:

    Code using mo-dots follows https://github.com/klahnakoski/mo-dots/blob/dev/plugins/mo-dots/skills/mo-dots/SKILL.md


## Summary

This library is the basis for a data transformation algebra: We want a succinct way of transforming data in Python. We want operations on data to result in yet more data. We do not want data operations to raise exceptions. This library also solves Python's lack of consistency (lack of closure) under the dot (`.`) and slice `[::]` operators when operating on data objects. 

[Full documentation](https://github.com/klahnakoski/mo-dots/tree/dev/docs)
