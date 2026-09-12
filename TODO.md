# TODO

## Performance (measured: `w.a.b.c` ~1,700ns vs 83ns plain dict; cost is interpreter frames per dunder)

- Pure-Python quick wins (~1.5-2x): dispatch `Data.__getattr__` type branches via dict
  keyed by class instead of tuple scans; make `is_null` a set lookup; skip allocating
  `NullType` on misses chained off an existing `NullType` — only the first miss needs
  (obj, key) for late assignment, the rest can be the `Null` singleton.
- C extension for the hot primitives — `Data`, `NullType`, `to_data`, `_getdefault`,
  `split_field` — pure-Python kept as fallback (simplejson `_speedups` pattern).
  C dunders run through type slots with no frame creation; expect near-dict speed.
  Existing test suite is the conformance test.
- JSON-as-string backend for pipeline workloads (doc arrives as text, read a few
  fields, patch a few, emit text — NDJSON ETL shape). Measured on an 819-byte line,
  2 changes + 1 append: naive pure-Python splice 1,175ns vs stdlib
  loads/mutate/dumps 15,438ns (13x); win is skipping materialization AND
  re-serialization of untouched bytes. Scanning must be C-based and escape-aware:
  a search pattern can occur inside a string value, addressing is nesting-aware
  (`response.status`, not first `"status"` anywhere), appends need comma/brace
  logic, duplicate-key semantics decided. At ~1K docs no rope/piece-table — output
  is slices + patches joined once; rescanning after a splice is sub-microsecond.
  Untouched bytes pass through byte-identical (preserves key order, number
  formatting; stable diffs). Loses when the doc lives as Python data between
  operations — for that, materialize.
