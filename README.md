
# More Dots!

[![PyPI Latest Release](https://img.shields.io/pypi/v/mo-dots.svg)](https://pypi.org/project/mo-dots/)
[![Build Status](https://app.travis-ci.com/klahnakoski/mo-dots.svg?branch=master)](https://travis-ci.com/github/klahnakoski/mo-dots)
 [![Coverage Status](https://coveralls.io/repos/github/klahnakoski/mo-dots/badge.svg?branch=dev)](https://coveralls.io/github/klahnakoski/mo-dots?branch=dev)
[![Downloads](https://pepy.tech/badge/mo-dots)](https://pepy.tech/project/mo-dots)

#### Changes in version 9.x.x

Escaping a literal dot (`.`) is no longer (`\\.`) rather double-dot (`..`). Escaping a literal dot can still be done with bell (`\b`) 

#### Changes in version 5.x.x

The `Data()` constructor only accepts keyword parameters. It no longer accepts a dict, nor does it attempt to clean the input.  Replace `Data(my_var)` with `to_data(my_var)`
  

## Overview

This library defines a `Data` class that can serve as a replacement for `dict`, with additional features. 

    >>> from mo_dots import to_data, Data

*See the [full documentation](https://github.com/klahnakoski/mo-dots/tree/dev/docs) for all the features of `mo-dots`*

### Create instances

Define `Data` using named parameters, just like you would a `dict`

    >>> Data(b=42, c="hello world")
    Data({'b': 42, 'c': 'hello world'})

You can also wrap existing `dict`s so they can be used like `Data`

    >>> to_data({'b': 42, 'c': 'hello world'})
    Data({'b': 42, 'c': 'hello world'})

### Dot Access

Access properties with attribute dots: `a.b == a["b"]`. You have probably seen this before.

### Path Access

Access properties by dot-delimited path.

	>>> a = to_data({"b": {"c": 42}})
	>>> a["b.c"] == 42
	True

### Safe Access

If a property does not exist then return `Null` rather than raising an error.

	>>> a = Data()
	a == {}
	>>> a.b == None
	True
	>>> a.b.c == None
	True
	>>> a[None] == None
	True

### Path assignment

No need to make intermediate `dicts`

    >>> a = Data()
    a == {}
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

Use `+=` with a list ([]) to append to a list; default empty list (`[]`)

    >>> a = Data()
    a == {}
    >>> a.b.c += [1]
    a == {"b": {"c": [1]}}
    >>> a.b.c += [42]
    a == {"b": {"c": [1, 42]}}

## Serializing to JSON

The standard Python JSON library does not recognize `Data` as serializable.  You may overcome this by providing `default=from_data`; which converts the data structures in this module into Python primitives of the same. 

    from mo_dots import from_data, to_data
    
    s = to_data({"a": ["b", 1]})
    result = json.dumps(s, default=from_data)  

Alternatively, you may consider [mo-json](https://pypi.org/project/mo-json/) which has a function `value2json` that converts a larger number of data structures into JSON.


## Summary

This library is the basis for a data transformation algebra: We want a succinct way of transforming data in Python. We want operations on data to result in yet more data. We do not want data operations to raise exceptions. This library is solves Python's lack of consistency (lack of closure) under the dot (`.`) and slice `[::]` operators when operating on data objects. 

[Full documentation](https://github.com/klahnakoski/mo-dots/tree/dev/docs)
