# mo_dots — null-safe data structures and the field-path algebra

Foundation for everything above it. Two things matter when working in this repo:

## Null semantics

- `Null` (NullType) is a null-safe None: attribute/index access on it returns `Null`, so
  chained access never raises. `Null == None` is **True** — code all over this repo tests
  `x == None` deliberately (do NOT "fix" it to `is None`; that breaks NullType/Data slots).
- Against a real (non-missing) value, `Null == x` and `Null != x` are both falsy; the consumer
  rules, this trap among them, are the skill in
  [plugins/mo-dots/skills/mo-dots/SKILL.md](../plugins/mo-dots/skills/mo-dots/SKILL.md).
- `Data` is a dict with dot-path access; missing paths yield `Null`, and assigning to a deep
  path auto-creates intermediates. `to_data`/`from_data` convert at API boundaries.
- `is_missing(x)` is the one test for missing (`None`, `Null`, `""`, `b""`, `[]`, NaN); an empty `Data` is a real value.
- **List assembly via `+= [x]`:** `slot += [x]` builds a list without pre-allocating.
  When the slot is `Null`, `NullType.__iadd__` (nones.py) writes the list back through
  its deferred parent/key; on a `FlatList` it extends in place (lists.py). So
  `data[k] += [x]` for a missing `k` creates `[x]`, and repeating appends — no
  `[None]*n` + index bookkeeping. Order is append order, so only use it where the
  values arrive in the order you want them stored.

## The C accelerator (`_speedups.c`)

- Optional C extension; `MO_DOTS_PURE=1` forces pure Python; no built `.pyd`/`.so`
  also means pure. Build in place: `python packaging/setup_speedups.py build_ext --inplace`.
- When active, `Data`/`FlatList`/`NullType` are rebuilt over C base types
  (`utils._rebuild_class`) and the hot dunders run as C slots. **Editing a hot dunder
  in the .py is not enough** — the pure method is only the slow path (dotted edge
  cases, non-dict slots/elements): change the C twin in `_speedups.c` too, rebuild,
  and run the suite in both modes.
- Type registries flow to C via `utils._sync` inside every `register_*`; class and
  helper wiring goes through `_init_null`/`_init_data`/`_init_list`/`_init`.
- Two ways to say "this type holds data", and they differ in what `to_data` owes it:
  `register_data(type_)` is a mapping mo-dots did not build, so `to_data` puts a `Data`
  over it and `Data.__getattr__` wraps a nested one; `register_view(type_)` is a type
  that answers navigation itself (`Data`, `DataObject`), so `to_data` hands it back.
  Both make `is_data` true. A registration reaches three places - `_data_types`,
  `_wrapped_data_types`, and (through `on_data_type_change`) the `__getattr__`
  dispatch - and the C twin of the first two arrives by `_sync`.

## Field paths (`fields.py`)

Property names may contain literal dots (escaped). Never `s.split(".")` on a field name —
use `split_field`/`join_field`/`concat_field`/`relative_field`/`startswith_field`/
`endswith_field`. `"."` names the root/fact table; `".."` walks toward the parent
(`relative_field("a", "a.b.c")` → `"..."`-style relative names). The entire snowflake naming
scheme (tables and columns) is built on these functions.
