# mo_dots — known defects

## `literal_field` did not round-trip through `split_field` (FIXED — no test yet)

`ILLEGAL_DOTS` was unanchored (`[^.]\.(?:\.\.)+`), so it matched the first three dots of any
longer run and rejected even runs. A name that already contains an escaped dot escapes to four
dots — `literal_field("a..html") == "a....html"` — and `split_field` refused it with "Odd number
of dots is not allowed". A trailing `(?!\.)` makes it reject only genuinely odd runs.

## `Data.__eq__` read a literal dot in a key as a path (FIXED)

`__eq__` compared `d.items()` — raw keys, dots and all — against `other.get(k)`. When `other`
is a `Data`, `get` splits on the dot and walks the path, so a key holding a literal dot
answered `Null` and two equal objects compared unequal while their hashes matched:

    k = literal_field("g.a")            # 'g..a'
    a = Data(); a[k] = "b"
    b = Data(); b[k] = "b"
    hash(a) == hash(b)  # True
    a == b              # False

Fix: `e = from_data(other)`, keeping `other` when the unwrap is not a `dict` — `from_data`
of a `DataObject` is the wrapped object, which has no `.get`/`.items`.
Coverage: `tests/test_mo_dots.py` (this repo, not upstream).
