# Major Changes


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
  