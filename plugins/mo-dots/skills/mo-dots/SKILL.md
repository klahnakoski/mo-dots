---
name: mo-dots
description: How to write Python with mo-dots so it reads simply - navigate instead of guarding, merge with `|`, test absence with `x == None`, and avoid the Null comparison traps. Use whenever code imports mo_dots or uses to_data, from_data, Data, Null, FlatList, leaves_to_data, literal_field or coalesce, and whenever you write or review dict navigation (`.get()` chains, `or {}` guards, `.update()` merges, `json.dumps`) in a repo that depends on mo-dots, mo-json, mo-kwargs or any other mo-* package - even if the user does not mention mo-dots.
---

# mo-dots - consumer rules

`Data` wraps JSON-like structures for dot access, and `Null` stands in for None at every
miss. These rules restate ordinary Python in the shape mo-dots makes short.

## Navigate

- Navigate, don't guard: `to_data(payload).tool_input.command`, never
  `(payload.get("tool_input") or {}).get("command")`. A missing key is `Null`, which
  chains, so no step of the path needs `or {}` and no read needs `or None`.
- `Null` survives operations: `Null[:8]` is `Null`, `Null.strip()` is `Null`,
  `list(Null)` is `[]`, `len(Null)` is `0`, `str(Null)` is `""`, and calling it answers
  `Null`. Write the operation as if the value were there; absence flows through and stays
  falsy. Guard only at the point a real value is required, not at every step on the way.
- Convert where the value is born, once. `to_data` belongs to the producer - the handler
  that read the request body, the function that built the dict - never to the callee: a
  `payload = to_data(payload)` at the top of a function is scrubbing what its callers
  hand it, repeated at every call. Hand `Data` across your own call chain and let the
  callee trust what it receives.
- Boundaries convert: `to_data` on the way in, `from_data` on the way out. Where the
  serializer is not yours to call (flask building a response), convert each field with
  `from_data`.
- A key that shares a name with a method is reached by index: `to_data({"items": 1}).items`
  is the bound method, `["items"]` is `1`. The same holds for `DataObject(obj)`.

## Absence and comparison

- The absence test is `x == None` - not `is None`, not `== Null`. `Null == None` is True
  and `Null is None` is False, so `is None` takes the wrong arm whenever a value came
  through mo-dots: `getattr(record, "a", [None])[0]` on a `Data` record answers `Null`.
- Against a real value, `Null == x` and `Null != x` are *both* falsy. `if a.b != "x"`
  silently takes the false branch when `b` is missing; write the positive form,
  `not (a.b == "x")`.
- `is_missing` is the one rule: `None`, `Null`, `""`, `b""`, `[]`, empty `FlatList` and
  `NaN` are missing; `{}`, `0` and `False` are real. `Null == x` and an empty `FlatList`
  `== x` hold exactly when `is_missing(x)`: `to_data([]) == None` and `Null == ""` are
  True, `Null == {}` is False. A non-empty `FlatList` equals only a list, tuple or
  `FlatList` of equal elements. For other absence questions ask by name:
  `is_missing(x)` / `exists(x)`, `is_data(x)`, `is_many(x)`, and `is_text(x)` from mo-future.
- Tuple membership answers a real bool: `x not in ("default", None)` is False for `Null`,
  where `x != "default"` would be `Null`.
- `"a" in data` is `exists(data.a)`: True for `0` and `False`, False for `""` and `[]`.
  `Data` equality and hash ignore missing-valued keys.
- `coalesce(a, b, c)` for the first non-missing of several: `coalesce("", 2)` is `2`.
- `NaN` is missing: `data.a` reads `Null`, and `from_data` drops it from dicts and makes it
  `None` in lists.

## Merge

- Merge with `|`, not `.update()`. When a `Data` or `Null` is an operand, `a | b` is
  *recursive coalesce*: the left side wins and the right only fills its gaps (`config |
  defaults` reads "config, defaulted by") - the opposite of stdlib dict `|`, where the
  right side wins; two plain dicts keep Python's meaning. A missing value on either side,
  at any depth, is a gap (`{"a": ""} | {"a": 2}` is `{"a": 2}`); nested data meeting a
  scalar keeps the left. `x | Null` and `Null | x` are both `x`, so a maybe-absent piece merges without a guard:
  `line = {...} | timing | failure`, with `failure=Null` in the signature, replaces two
  `.update()` calls and an `if`. `Data | <non-data real value>` is an error.
- Use `|` to avoid copying properties: name only the fields you reshape and let the
  record ride in whole - `{"cmd": payload.tool_input.command[:300]} | payload` - instead
  of hand-copying `"cwd": payload.cwd, "tool_name": payload.tool_name, ...` one per line.
  What rides through keeps its born name.
- A conditional merge needs no `if`. Coalesce the maybe-absent record itself over the
  base - `{"prompt": answer.prompt[:4000]} | answer | base` - with a small dict up front
  for any field reshaped on the way in. Coalesce skips missing values and `answer=Null`
  contributes nothing, so `if answer: line |= {...}` disappears. The record should carry
  only fields the merge may take whole: a field that collides with the base's under
  another meaning is a field to rename or drop at its producer.
- `FlatList |` coalesces (non-empty left wins, empty left takes the right) and `+`
  concatenates. `Null` is the identity for `+` too: `Null + 1` is `1`, and `data + Null`,
  `data + ""`, `data + []` answer an equal `Data`.
- `Data + Data` is a different operator: it adds the leaves -
  `to_data({"a": 1, "l": [1]}) + to_data({"a": 2, "l": [2]})` gives `{"a": 3, "l": [1, 2]}`.

## Defaults

- Defaults live in the signature or the config file, not re-bound in the body. With
  mo-kwargs, `@override` fills parameters from a `kwargs` dict, and
  `@override(kwargs="payload")` takes a dict's worth of parameters as `Data`:
  `def send(timeout=12.0, payload=None)`. `config.timeout or 12.0` in the body is wrong
  when the config can carry `12.0` itself.
- `or` binds a real default only where neither the signature nor the config can carry
  it: `port or DEFAULT_PORT`. What mo-dots deletes is the null-guard noise - `or None`,
  `or ""`, `or {}`, `or []` written so a later read would not raise.

## Assignment

- Path assignment creates the intermediates: `d = Data(); d.p.q.r = 1` gives
  `{"p": {"q": {"r": 1}}}`. Reading never mutates: `d.m.n` on an empty `Data` leaves it
  empty.
- Assigning `None` deletes the key: `d.p.q.r = None` leaves `{"p": {"q": {}}}`.
- `+=` on a missing slot starts from `0` or `[]`: `d.count += 1` gives `1`, and
  `d[k] += [x]` assembles a list in append order - no pre-allocation.
- A read binds a value, not a slot: `x = a.b.c; x = 42` does not write into `a`.

## Paths

- A dotted string is a path: `a["b.c"] == a.b.c`.
- `to_data` of a dict keeps dotted keys literal; reach them with a doubled dot:
  `to_data({"b.c": 5})["b..c"]` is `5`, while `["b.c"]` is `Null`. The same doubling
  escapes a literal dot in a `Data`-backed settings key: `"3..15"` reaches key `"3.15"`.
- `literal_field(key)` escapes an untrusted or dotted key (URLs, file names) before using
  it as a path: `literal_field("x.com")` is `"x..com"`.
- Never `.split(".")` a field: use `split_field`, `join_field`, `concat_field`,
  `relative_field`. `split_field("a.b..c")` is `["a", "b.c"]`.
- `leaves_to_data(config)` once, where leaf-form config enters:
  `{"a.b": 1, "a.c": 2}` becomes `{"a": {"b": 1, "c": 2}}`. The inverse, `a.leaves()`,
  yields `(path, value)` pairs.

## FlatList

- `flist.name` is a column projection - one call, in C when the accelerator is built -
  and it skips rows where `name` is missing: `[{"name": "a"}, {"name": "b"}, {}]` projects
  to `["a", "b"]`.
- Indexing never raises: an out-of-range or negative index is `Null`, and a slice past
  the end is an empty `FlatList`. Count from the end with `.right(n)` / `.not_right(n)`,
  from the start with `.left(n)` / `.not_left(n)`.

## Foreign types

- `register_data(T)` makes `to_data` put a `Data` over a mapping mo-dots did not build,
  and nested ones wrap as you navigate.
- `register_view(T)` is for a type that answers navigation itself; `to_data` hands it
  back as-is.
- `DataObject(obj)` boxes a plain object for dot access; its attributes compete with
  `DataObject`'s own methods (`keys`, `items`, ...), which win.

## JSON

- Use mo-json: `value2json(x)` replaces `json.dumps(x, default=from_data)` and drops
  null-valued keys, which mean the same thing under mo-dots:
  `value2json(to_data({"a": 1, "b": None}))` is `'{"a":1}'`. Fall back to
  `json.dumps(x, default=from_data)` only where mo-json is not a dependency.
- `json2value(text)` answers `Data`, so its call site needs no `to_data`. It takes `str`
  only: `.decode()` bytes first.

## When to leave plain dicts

- A fixed-key hot path, where every key is known and the wrapper costs more than it
  saves.
- A module deliberately kept stdlib-only.
