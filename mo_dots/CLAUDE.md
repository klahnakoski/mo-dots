# mo_dots — null-safe data structures and the field-path algebra

Foundation for everything above it. Two things matter when working in this repo:

## Null semantics

- `Null` (NullType) is a null-safe None: attribute/index access on it returns `Null`, so
  chained access never raises. `Null == None` is **True** — code all over this repo tests
  `x == None` deliberately (do NOT "fix" it to `is None`; that breaks NullType/Data slots).
- **Against any other value, `Null == x` and `Null != x` are BOTH falsy** (each returns `Null`).
  So `if query.format != "cube"` is False when no format was set — a negated comparison on a
  possibly-missing field silently takes the wrong branch (this shipped as a bug in
  `jx_sqlite/query.py`). Test the positive form: `not (query.format == "cube")`.
- `Data` is a dict with dot-path access; missing paths yield `Null`, and assigning to a deep
  path auto-creates intermediates. `to_data`/`from_data` convert at API boundaries.
- Empty containers and `Null` are falsey; `is_missing(x)` is the sanctioned test.
- **List assembly via `+= [x]`:** `slot += [x]` builds a list without pre-allocating.
  When the slot is `Null`, `NullType.__iadd__` (nones.py) writes the list back through
  its deferred parent/key; on a `FlatList` it extends in place (lists.py). So
  `data[k] += [x]` for a missing `k` creates `[x]`, and repeating appends — no
  `[None]*n` + index bookkeeping. Order is append order, so only use it where the
  values arrive in the order you want them stored.

## Field paths (`fields.py`)

Property names may contain literal dots (escaped). Never `s.split(".")` on a field name —
use `split_field`/`join_field`/`concat_field`/`relative_field`/`startswith_field`/
`endswith_field`. `"."` names the root/fact table; `".."` walks toward the parent
(`relative_field("a", "a.b.c")` → `"..."`-style relative names). The entire snowflake naming
scheme (tables and columns) is built on these functions.
