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
- Boundaries convert: `to_data` on the way in, `from_data` on the way out. For JSON,
  `json.dumps(line, default=from_data)` serializes `Null` as `null` and `Data` as an
  object - no `or None` per field at the dump site.
- The comparison trap: against a real value, `Null == x` and `Null != x` are *both*
  falsy. `if a.b != "x"` silently takes the false branch when `b` is missing; write the
  positive form, `not (a.b == "x")`. And `x == None` is deliberate wherever mo-dots is in
  play - `Null is None` is False, so an `is None` "fix" breaks it.
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
