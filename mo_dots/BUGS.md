# mo_dots — known defects

## `literal_field` did not round-trip through `split_field` (FIXED — no test yet)

`ILLEGAL_DOTS` was unanchored (`[^.]\.(?:\.\.)+`), so it matched the first three dots of any
longer run and rejected even runs. A name that already contains an escaped dot escapes to four
dots — `literal_field("a..html") == "a....html"` — and `split_field` refused it with "Odd number
of dots is not allowed". A trailing `(?!\.)` makes it reject only genuinely odd runs.
