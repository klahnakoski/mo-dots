# Major Changes

#### Changes in version 11.x.x

* Ships with binary wheels for Windows, MacOS and Linux.  No C compiler needed.
* `is_missing` is the one rule for "missing": `None`, `Null`, `""`, `b""`, empty lists, and `NaN`.  `{}` and `0` are real values.
  * `FlatList() == None` works again (reverses the 10.x change), and an empty `FlatList` equals exactly what `is_missing` accepts.  `to_data(["a", "b"]) == "ab"` and `to_data([1]) == {1: 2}` are now `False`.
  * `Null == x` is `is_missing(x)`, so `Null == ""` is `True` and `Null == {}` is `False`.
  * `"a" in to_data({"a": 0})` is `True`; `in` tests `exists`, not truthiness.
  * `Data` equality and hashing ignore keys whose value is missing, and hashing no longer depends on key order.
  * `NaN` is missing at every depth: `coalesce`, `from_data`, and dot access treat it as `None`.
* `|` is coalesce (left side wins) everywhere:
  * `Data | Null` and `Data | None` answer the `Data`.
  * A nested `Data` meeting a scalar keeps the left side instead of raising.
  * `FlatList | x` coalesces instead of concatenating; use `+` to concatenate.
* `Data + Null` answers the `Data`, and `Null + Data` no longer drops it.
* A `FlatList` built from a tuple supports `in`, `append`, `extend` and `+=`.
* `listwrap("")` is `[]`.


#### Changes in version 10.x.x

* Data now navigates `@dataclass` and `namedtuple` instances. All other types must be registered to be treated as data, otherwise they are assumed to be atoms.
  ```
  class MyType:
      ...
    
  register_type(MyType)
  ```
* Removed `datawrap`.  It is now `object_to_data`
* Comparision with `None` no longer works in all cases.

  Instead of 

  ```
  FlatList() == None  
  ```

  you now use 

  ```
  FlatList() == Null
  ```

  or 

  ```
  is_missing(FlatList())
  ```


#### Changes in version 9.x.x

Escaping a literal dot (`.`) is no longer (`\\.`) rather double-dot (`..`). Escaping a literal dot can still be done with bell (`\b`) 

#### Changes in version 5.x.x

The `Data()` constructor only accepts keyword parameters. It no longer accepts a dict, nor does it attempt to clean the input.  Replace `Data(my_var)` with `to_data(my_var)`
  