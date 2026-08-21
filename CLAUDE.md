# CLAUDE.md

## What this is

Null-safe data navigation: `Data` wraps JSON-like structures for dot access, and `Null`
stands in for None at every miss. The foundation of the mo-* stack.
[mo_dots/CLAUDE.md](mo_dots/CLAUDE.md) covers working inside the library - Null identity
semantics and the field-path algebra. This file is how a consumer uses it without being
surprised.

## Using it properly

- Navigate, don't guard: `to_data(payload).tool_input.command`, never
  `(payload.get("tool_input") or {}).get("command")`. A missing key is `Null`, which
  chains, so no step of the path needs `or {}` and no read needs `or None`.
- `Null` survives operations: `Null[:8]` is `Null`, `Null.strip()` is `Null`,
  `list(Null)` is `[]`, `len(Null)` is `0`, `str(Null)` is `""`, and calling it answers
  `Null`. Write the operation as if the value were there; absence flows through and stays
  falsy. Guard only at the point a real value is required, not at every step on the way.
- Boundaries convert: `to_data` on the way in, `from_data` on the way out. For JSON text
  prefer mo-json - `value2json(line)` scrubs whole structures and `json2value(text)`
  answers `Data` - and fall back to `json.dumps(line, default=from_data)` only where
  mo-json is not a dependency. Where the serializer is not yours to call (flask building
  a response), convert each field with `from_data`.
- The comparison trap: against a real value, `Null == x` and `Null != x` are *both*
  falsy. `if a.b != "x"` silently takes the false branch when `b` is missing; write the
  positive form, `not (a.b == "x")`. And `x == None` is deliberate wherever mo-dots is in
  play - `Null is None` is False, so an `is None` "fix" breaks it.
- Convert where the value is born, once. `to_data` belongs to the producer - the handler
  that read the request body, the function that built the dict - never to the callee: a
  `payload = to_data(payload)` at the top of a function is scrubbing what its callers
  hand it, repeated at every call. Hand `Data` across your own call chain and let the
  callee trust what it receives.
- Merge with `|`, not `.update()`. When a `Data` or `Null` is an operand, `a | b` is
  *recursive coalesce*: the left side wins and the right only fills its gaps (`config |
  defaults` reads "config, defaulted by") - the opposite of stdlib dict `|`, where the
  right side wins; two plain dicts keep Python's meaning. `x | Null` and `Null | x` are
  both `x`, so a maybe-absent piece merges without a guard: `line = {...} | timing |
  failure`, with `failure=Null` in the signature, replaces two `.update()` calls and an
  `if`. `Data | <non-data>` is an error.
- Use `|` to avoid copying properties: name only the fields you reshape and let the
  record ride in whole - `{"cmd": payload.tool_input.command[:300]} | payload` - instead
  of hand-copying `"cwd": payload.cwd, "tool_name": payload.tool_name, ...` one per line.
  What rides through keeps its born name, which is also what the same-name rule wants.
- A conditional merge needs no `if`. Coalesce the maybe-absent record itself over the
  base - `{"prompt": answer.prompt[:4000]} | answer | base` - with a small dict up front
  for any field reshaped on the way in. Coalesce skips `Null` values and `answer=Null`
  contributes nothing, so `if answer: line |= {...}` disappears. It also means the record
  should carry only fields the merge may take whole: a field that collides with the
  base's under another meaning is a field to rename or drop at its producer.
- A real default still uses `or`: `port or DEFAULT_PORT` binds a value the code needs.
  What mo-dots deletes is only the null-guard noise - `or None`, `or ""`, `or {}`,
  `or []` written so a later read would not raise.
- `is_missing(x)` / `exists(x)` when empty-string-is-missing is the question;
  `coalesce(a, b, c)` for the first non-null of several.

## Layout

- `mo_dots/` - the library: `datas.py` (Data), `nones.py` (Null), `lists.py`
  (FlatList), `fields.py` (the field-path algebra), `objects.py`, `utils.py`.
- `docs/` - the full feature documentation and changelog.
- `tests/`, `packaging/` - the suite and the release scaffolding.
