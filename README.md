
# More Dots!


|Branch      |Status   |
|------------|---------|
|master      | [![Build Status](https://travis-ci.org/klahnakoski/mo-dots.svg?branch=master)](https://travis-ci.org/klahnakoski/mo-dots) |
|dev         | [![Build Status](https://travis-ci.org/klahnakoski/mo-dots.svg?branch=dev)](https://travis-ci.org/klahnakoski/mo-dots)  [![Coverage Status](https://coveralls.io/repos/github/klahnakoski/mo-dots/badge.svg?branch=dev)](https://coveralls.io/github/klahnakoski/mo-dots?branch=dev)  |



## Overview

This library defines a `Data` class that can serve as a replacement for `dict`, with additional features. 

    >>> from mo_dots import wrap, Data

*See the [full documentation](https://github.com/klahnakoski/mo-dots/tree/dev/docs) for all the features of `mo-dots`*

### Easy Definition

Define `Data` using named parameters, just like you would a `dict`

    >>> Data(b=42, c="hello world")
    Data({'b': 42, 'c': 'hello world'})

You can also wrap existing `dict`s so they can be used like `Data`

    >>> wrap({'b': 42, 'c': 'hello world'})
    Data({'b': 42, 'c': 'hello world'})

### Dot Access

Access properties with attribute dots: `a.b == a["b"]`. You have probably seen this before.

### Path Access

Access properties by dot-delimited path.

	>>> a = wrap({"b": {"c": 42}})
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


## Transforming JSON Data in Python

This library is the basis for a data transformation algebra: We want a succinct way of transforming data in Python. We want operations on data to result in yet more data. We do not want data operations to raise exceptions. This library is solves Python's lack of consistency (lack of closure) under the dot (`.`) and slice `[::]` operators when operating on data objects. 

[Full documentation](https://github.com/klahnakoski/mo-dots/tree/dev/docs)
