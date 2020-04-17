
# Classes for Processing Data

There are two major families of objects in Object Oriented programming. The
first, are ***Actors***: characterized by a number of useful instance methods
and some state bundled together to form a unit. The second are ***Data***: Primarily
a set of properties, with only (de)serialization functions, or algebraic
operators defined. 

*Data* objects in Python have minimal attributes, if any. Therefore, we can use attributes to access properties: `a.x == a["x"]`. Static property access is clearest done with dot notation `a.x`, and parametric property access is best done with item access `a[v]`. Property access is only the beginning. 

Focusing on just *data* objects; We want a succinct way of transforming data. We want operations on data to result in yet more data. We do not want data operations to raise exceptions. This library is solves Python's lack of consistency (lack of closure) under the dot (`.`) and slice `[::]` operators when operating on data objects. This library provides the consistent base for a high level data manipulation algebra. 


## `Data` replaces Python's `dict`

`Data` is used to declare an instance of an anonymous type, and intended for manipulating JSON. Anonymous types are necessary when writing sophisticated list comprehensions, or queries, while at the same time keeping them succinct. In many ways, `dict` can act as an anonymous type, but it is missing the features listed here.

 1. `a.b == a["b"]`
 2. missing property names are handled gracefully, which is beneficial when being used in
    set operations (database operations) without raising exceptions <pre>
&gt;&gt;&gt; a = wrap({})
a == {}
&gt;&gt;&gt; a.b == None
True
&gt;&gt;&gt; a.b.c == None
True
&gt;&gt;&gt; a[None] == None
True</pre>
    missing property names are common when dealing with JSON, which is often almost anything.
    Unfortunately, you do loose the ability to perform <code>a is None</code>
    checks: **You must always use <code>a == None</code> instead**.
 3. Accessing missing properties does not change the data; unlike `defaultdict`
 4. Remove an attribute by assigning `None` (eg `a.b = None`)
 5. Access paths as a variable: `a["b.c"] == a.b.c`. Of course,
 this creates a need to refer to literal dot (`.`), which can be done by
 escaping with backslash: `a["b\\.c"] == a["b\.c"]`
 6. you can set paths to values, missing dicts along the path are created:<pre>
&gt;&gt;&gt; a = wrap({})
a == {}
&gt;&gt;&gt; a["b.c"] = 42   # same as a.b.c = 42
a == {"b": {"c": 42}}</pre>
 7. path assignment also works for the `+=` operator <pre>
&gt;&gt;&gt; a = wrap({})
a == {}
&gt;&gt;&gt; a.b.c += 1
a == {"b": {"c": 1}}
&gt;&gt;&gt; a.b.c += 42
a == {"b": {"c": 43}}</pre>
 8. `+=` with a list (`[]`) will `append()`<pre>
&gt;&gt;&gt; a = wrap({})
a == {}
&gt;&gt;&gt; a.b.c += [1]
a == {"b": {"c": [1]}}
&gt;&gt;&gt; a.b.c += [42]
a == {"b": {"c": [1, 42]}}</pre>
 9. If the leaves of your datastructure are numbers or lists, you can add `Data` to other `Data`:<pre>
&gt;&gt;&gt; a = wrap({"a":42, "b":["hello"]})
&gt;&gt;&gt; b = {"a":24, "b":["world"]}
&gt;&gt;&gt; c = a + b
c == {"a":66, "b":["hello", "world"]}
</pre>
 10. property names are coerced to unicode - it appears Python2.7
 `object.getattribute()` is called with `str()` even when using `from __future__
 import unicode_literals`

## Mapping Leaves

The implications of allowing `a["b.c"] == a.b.c` opens up two different Data
forms: *standard form* and *leaf form*

### Standard Form

The `[]` operator in `Data` has been overridden to assume dots (`.`) represent
paths rather than literal string values; but, the internal representation of
`Data` is the same as `dict`; the property names are treated as black box
strings. `[]` just provides convenience.

When wrapping `dict`, the property names are **NOT** interpreted as paths;
property names can include dots (`.`).

```python
>>> from mo_dots import wrap
>>> a = wrap({"b.c": 42})
>>> a.keys()
set(['b.c'])

>>> a["b.c"]
Null    # because b.c path does not exist

>>> a["b\.c"]
42      # escaping the dot (`.`) makes it literal
```

### Leaf form

Leaf form is used in some JSON, or YAML, configuration files. Here is an
example from my ElasticSearch configuration:

**YAML**

```javascript
discovery.zen.ping.multicast.enabled: true
```

**JSON**

```javascript
{"discovery.zen.ping.multicast.enabled": true}
```

Both are intended to represent the deeply nested JSON

```javascript
{"discovery": {"zen": {"ping": {"multicast": {"enabled": true}}}}}
```

Upon importing such files, it is good practice to convert it to standard form
immediately:

```python
config = wrap_leaves(config)
```

`wrap_leaves()` assumes any dots found in JSON names are referring to paths
into objects, not a literal dots.

When accepting input from other automations and users, your property names
can potentially contain dots; which must be properly escaped to produce the
JSON you are expecting. Specifically, this happens with URLs:

**BAD** - dots in url are interpreted as paths

```python
>>> from mo_dots import wrap, literal_field, Data
>>>
>>> def update(summary, url, count):
...     summary[url] += count
...
>>> s = Data()
>>> update(s, "example.html", 3)
>>> print s

Data({u'example': {'html': 3}})
```

**GOOD** - Notice the added `literal_field()` wrapping

```python
>>> def update(summary, url, count):
...     summary[literal_field(url)] += count
...
>>> s = Data()
>>> update(s, "example.html", 3)
>>> print s

Data({u'example.html': 3})
```

You can produce leaf form by iterating over all leaves. This is good for
simplifying iteration over deep inner object structures.

```python
>>> from mo_dots import wrap
>>> a = wrap({"b": {"c": 42}})
>>> for k, v in a.leaves():
...     print k + ": " + unicode(v)

b.c: 42
```



## Towards a better `None`

In many applications the meaning of `None` (or `null`) is always in the context of
a known type: Each type has a list of expected properties, and if an instance
is missing one of those properties we set it to `None`. Let us call it this the
"*Missing Value*" definition. Also known as ["my billion dollar mistake"](https://en.wikipedia.org/wiki/Tony_Hoare).

Another interpretation for `None` (or `null`), is that the instance simply does not
have that property: Asking for the physical height of poem is nonsense, and
we return `None`/`null` to indicate this. Databases use `NULL` in this way to
allow tables to hold records of multiple (sub)types and minimize query complexity. 
Call this version of None the "*Out of Context*" definition.

Python, and the *pythonic way*, and many of its libraries, assume `None` is a
*Missing Value*. This assumption results in an excess of exception handling
and decision code when processing a multitude of types with a single
method, or when dealing with unknown future polymorphic types, or working with
one of many ephemeral 'types' who's existence is limited to a few lines of a method.

Assuming None means *Out of Context* makes our code forgiving when encountering
changing type definitions, flexible in the face of polymorphism, makes code
more generic when dealing with sets and lists containing members of non-uniform type.

#### More reading on Null

* A clear demonstration of how converting a schema to be "null-free" tends toward a columnar datastore: [Missing-info-without-nulls.pdf](https://www.dcs.warwick.ac.uk/~hugh/TTM/Missing-info-without-nulls.pdf) 
* Programmers use variables in their programs; they are used to hold (or point to) values. Insisting that variables continue to exist even when they do not point to a legitimate value results in the need for `null` to represent that missing value: [The Logical Disaster of Null](https://rob.conery.io/2018/05/01/the-logical-disaster-of-null/)

### `Null` replaces Python's `None`

I would like to override `None` in order to change its behaviour.
Unfortunately, `None` is a primitive that can not be extended, so we create
a new type, `NullType` and instances, `Null` ([a null object](https://en.wikipedia.org/wiki/Null_Object_pattern)), which are closed under the dot(`.`), access (`[]`), and slice (`[::]`)
operators. `Null` acts as both an impotent list and an impotent dict:

 1. `a[Null] == Null`
 2. `Null.a == Null`
 3. `Null[a] == Null`
 4. `Null[a:b:c] == Null`
 5. `a[Null:b:c] == Null`
 6. `a[b:Null:c] == Null`
 7. `Null() == Null`

To minimize the use of `Null` in our code we let comparisons
with `None` succeed. The right-hand-side of the above comparisons can be
replaced with `None` in all cases.

### Identity and Absorbing (Zero) Elements

With `Null` defined, we have met the requirements for an [algebraic semigroup](https://en.wikipedia.org/wiki/Semigroup): The identity element is the dot string (`"."`) and the zero element is `Null`
(or `None`).

 1. `a[Null] == Null`
 2. `a["."] == a`

which are true for all `a`. I hope, dear reader, you do not see this a some peculiar pattern, but rather a clean basis that allows us to perform complex operations over heterogeneous data with less code.


### NullTypes are Lazy

NullTypes can also perform lazy assignment for increased expressibility.

```python
>>> a = wrap({})
>>> x = a.b.c
>>> x == None
True
>>> x = 42
>>> a.b.c == 42
True
```
in this case, specific `Nulls`, like `x`, keep track of the path
assignment so it can be used in later programming logic. This feature proves
useful when transforming hierarchical data; adding deep children to an
incomplete tree.

### Null Arithmetic

When `Null` is part of arithmetic operation (boolean or otherwise) it results
in `Null`:

 * `a ∘ Null == Null`
 * `Null ∘ a == Null`

where `∘` is standing in for most binary operators. Operators `and` and `or`
are exceptions, and behave as expected with [three-valued logic](https://en.wikipedia.org/wiki/Three-valued_logic):

 * `True or Null == True`
 * `False or Null == Null`
 * `False and Null == False`
 * `True and Null == Null`

## `FlatList` is "Flat"

`FlatList` uses a *flat-list* assumption to interpret slicing and indexing
operations. This assumes lists are defined over all integer (**ℤ**)
indices; defaulting to `Null` for indices not explicitly defined otherwise.
This is distinctly different from Python's *loop-around* assumption,
where negative indices are interpreted modulo-the-list-length.

### Indexing

We will compare the Python list behaviour (`loop_list`) to the FlatList (`flat_list`): 

    loop_list = ['A', 'B', 'C']
    flat_list = wrap(loop_list)

Here is table of indexing results

| <br>`index`|*loop-around*<br>`loop_list[index]`|*flat-list*<br>`flat_list[index]`|
| ------:|:------------------:|:------------------:|
|   -5   |     `<error>`      |       `Null`       |
|   -4   |     `<error>`      |       `Null`       |
|   -3   |        `A`         |       `Null`       |
|   -2   |        `B`         |       `Null`       |
|   -1   |        `C`         |       `Null`       |
|    0   |        `A`         |        `A`         |
|    1   |        `B`         |        `B`         |
|    2   |        `C`         |        `C`         |
|    3   |     `<error>`      |       `Null`       |
|    4   |     `<error>`      |       `Null`       |
|    5   |     `<error>`      |       `Null`       |


### Slicing

The *flat list* assumption reduces exception handling and simplifies code for
window functions. For example, `mo_math.min(flat_list[a:b:])` is valid for
all `a<=b`

  * Python 2.x binary slicing `[:]` throws a warning if used on a FlatList (see implementation issues below)
  * Trinary slicing `[::]` uses the flat list definition

When assuming a *flat-list*, we loose the *take-from-the-right* tricks gained
from modulo arithmetic on the indices. Therefore, we require extra methods
to perform right-based slicing:

  * **right()** - `flat_list.right(b)` same as `loop_list[-b:]` except when `b<=0`
  * **not_right()** - `flat_list.not_right(b)` same as `loop_list[:-b]` except
  when `b<=0` (read as "left, but for ...")

For the sake of completeness, we have two more convenience methods:

  * `flat_list.left(b)` same as `flat_list[:b:]`
  * `flat_list.not_left(b)` same as `flat_list[b::]`

### Dot (.) Operator

The dot operator on a `FlatList` performs a simple projection; it will return a list of property values

```python
    myList.name == [x["name"] for x in myList]
```

## DataObject for data

You can wrap any object to make it appear as `Data`.

```python
	d = DataObject(my_data_object)
```

This allows you to use the operators in this library on the object, or set of objects. Care is required though: Your object may not be a pure data object,
and there can be conflicts between the object methods and the properties it
is expected to have.



# Appendix

### Examples in the wild

`Data` is a common pattern in many frameworks even though it goes by
different names and slightly different variations, some examples are:

 * [PEP 0505] uses ["safe navigation"](https://www.python.org/dev/peps/pep-0505/), but still treats None as a *missing value*. This is good for interacting with Nones coming out of libraries that share this meaning, but does not improve the manipulation of the data coming from those libraries.  
 * `jinja2.environment.Environment.getattr()` to allow convenient dot notation
 * `argparse.Environment()` - code performs `setattr(e, name, value)` on
  instances of Environment to provide dot(`.`) accessors
 * `collections.namedtuple()` - gives attribute names to tuple indices
  effectively providing <code>a.b</code> rather than <code>a["b"]</code>
     offered by dicts
 * `collections.defaultdict()` - observing missing properties will mutate the instance, which is not desired behaviour
 * [configman's DotDict](https://github.com/mozilla/configman/blob/master/configman/dotdict.py)
  allows dot notation, and path setting
 * [Fabric's _AttributeDict](https://github.com/fabric/fabric/blob/19f5cffaada0f6f6132cd06742acd34e65cf1977/fabric/utils.py#L216) allows dot notation
 * C# Linq requires anonymous types to avoid large amounts of boilerplate code.
 * D3 uses `null` to indicate property deletion: ["The function's return value is
  then used to set each element's attribute. A null value will remove the
  specified attribute."](https://github.com/mbostock/d3/wiki/Selections#attr)
 * [Simplify your code by making the data consistent](https://blog.conjur.org/special-cases-are-a-code-smell/)

### Notes
 * More on missing values: [http://www.np.org/NA-overview.html](http://www.np.org/NA-overview.html)
it only considers the legitimate-field-with-missing-value (Statistical Null)
and does not look at field-does-not-exist-in-this-context (Database Null)
 * [Motivation for a 'mutable named tuple'](http://www.saltycrane.com/blog/2012/08/python-data-object-motivated-desire-mutable-namedtuple-default-values/)
(aka anonymous class)


## Motivation for FlatList (optional reading)

`FlatList` is the final type required to to provide closure under the
dot(.) and slice [::] operators. Not only must `FlatList` deal with
`Nulls` (and `Nones`) but also provide fixes to Python's inconsistent
slice operator.

### The slice operator in Python2.7 is inconsistent

At first glance, the python slice operator `[:]` is elegant and powerful.
Unfortunately it is inconsistent and forces the programmer to write extra code
to work around these inconsistencies.

```python
    my_list = ['a', 'b', 'c', 'd', 'e']
```

Let us iterate through some slices:

```python
    my_list[4:] == ['e']
    my_list[3:] == ['d', 'e']
    my_list[2:] == ['c', 'd', 'e']
    my_list[1:] == ['b', 'c', 'd', 'e']
    my_list[0:] == ['a', 'b', 'c', 'd', 'e']
```

Looks good, but this time let's use negative indices:

```python
    my_list[-4:] == ['b', 'c', 'd', 'e']
    my_list[-3:] == ['c', 'd', 'e']
    my_list[-2:] == ['d', 'e']
    my_list[-1:] == ['e']
    my_list[-0:] == ['a', 'b', 'c', 'd', 'e']  # [] is expected
```

Using negative indices `[-num:]` allows the programmer to slice relative to
the right rather than the left. When `num` is a constant this problem is
never revealed, but when `num` is a variable, then the inconsistency can
bite you.

```python
    def get_suffix(num):
        return my_list[-num:]   # wrong
```

So, clearly, `[-num:]` can not be understood as a suffix slice, rather
something more complicated; given `num` <= 0 is possible.

I advocate never using negative indices in the slice operator. Rather, use the
`right()` method instead which is consistent for `num` ∈ ℤ:

```python
    def right(_list, num):
        if num <= 0:
            return []
        if num >= len(_list):
            return _list
        return _list[-num:]
```

### Python 2.7 `__getslice__` is broken

It would be nice to have our own list-like class that implements slicing in a
way that is consistent. Specifically, we expect to solve the inconsistent
behaviour seen when dealing with negative indices.

As an example, I would like to ensure my over-sliced-to-the-right and over-
sliced-to-the-left behave the same. Let's look at over-slicing-to-the-right,
which behaves as expected on a regular list:

```python
    assert 3 == len(my_list[1:4])
    assert 4 == len(my_list[1:5])
    assert 4 == len(my_list[1:6])
    assert 4 == len(my_list[1:7])
    assert 4 == len(my_list[1:8])
    assert 4 == len(my_list[1:9])
```

Any slice that requests indices past the list's length is simply truncated.
I would like to implement the same for over-slicing-to-the-left:

```python
    assert 2 == len(my_list[ 1:3])
    assert 3 == len(my_list[ 0:3])
    assert 3 == len(my_list[-1:3])
    assert 3 == len(my_list[-2:3])
    assert 3 == len(my_list[-3:3])
    assert 3 == len(my_list[-4:3])
    assert 3 == len(my_list[-5:3])
```

Here is an attempt:

```python
    class MyList(list):
        def __init__(self, value):
            self.list = value

        def __getslice__(self, i, j):
            if i < 0:  # CLAMP i TO A REASONABLE RANGE
                i = 0
            elif i > len(self.list):
                i = len(self.list)

            if j < 0:  # CLAMP j TO A REASONABLE RANGE
                j = 0
            elif j > len(self.list):
                j = len(self.list)

            if i > j:  # DO NOT ALLOW THE IMPOSSIBLE
                i = j

            return [self.list[index] for index in range(i, j)]

        def __len__(self):
            return len(self.list)
```

Unfortunately this does not work. When the `__len__` method is defined
`__getslice__` defines `i = i % len(self)`: Which
makes it impossible to identify if a negative value is passed to the slice
operator.

The solution is to implement Python's extended slice operator `[::]`,
which can be implemented using `__getitem__`; it does not suffer from this
wrap-around problem.

```python
    class BetterList(list):
        def __init__(self, value):
            self.list = value

        def __getslice__(self, i, j):
            raise NotImplementedError

        def __len__(self):
            return len(self.list)

        def __getitem__(self, item):
            if not isinstance(item, slice):
                # ADD [] CODE HERE

            i = item.start
            j = item.stop
            k = item.step

            if i < 0:  # CLAMP i TO A REASONABLE RANGE
                i = 0
            elif i > len(self.list):
                i = len(self.list)

            if j < 0:  # CLAMP j TO A REASONABLE RANGE
                j = 0
            elif j > len(self.list):
                j = len(self.list)

            if i > j:  # DO NOT ALLOW THE IMPOSSIBLE
                i = j

            return [self.list[index] for index in range(i, j)]
```

