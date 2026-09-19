# Session Log

## 2026-09-19
- tests/test_register_data.py added: 7 pass in both modes (C extension built in
  place, and MO_DOTS_PURE=1).  4 of the 7 fail against the pre-change code.
- suite 29 ran / 11 err on py3.12: the 11 are import errors, unchanged by this
  work - this venv's installed mo_collections does `from mo_dots.objects import
  datawrap`, and objects.py has no datawrap any more.  Everything that imports
  mo_testing is out, which is most of the suite.
- `register_data` now promises what its callers assumed: `to_data()` puts a Data
  over a registered mapping, and `Data.__getattr__` wraps a nested one, so an
  outside mapping navigates like a dict.  Registering used to feed `is_data`
  alone, so `to_data` handed the object straight back and `w.b.c` raised.
- the types mo-dots itself registers are views - they answer navigation already -
  so `Data` and `DataObject` go through the new `register_view`, and wrapping
  them again is what `test_a_view_is_handed_back` pins.
- three places learn a registration now: `_data_types` (is_data),
  `_wrapped_data_types` (to_data), and the `__getattr__` dispatch, through a new
  `on_data_type_change` hook beside the null-type one.  `_sync` carries the
  second tuple to C, and `c_to_data` wraps there too - the C `Data.__getattr__`
  already falls back to python for a non-dict slot, so that half needed nothing.
- asked for by mo-json, whose `LazyObject` is a mapping over JSON text.  It reads
  and writes through the `Data` now; mo-json's 261 tests pass against this tree.
- next: nothing pending here.  A release would let mo-json drop `dict_to_data`.

## 2026-09-13
- suite 329 ran / 1 err / 2 skip on py3.13, pure mode (local .pyds removed by
  request; the 1 err is test_leaves_w_bs4 - bs4 absent locally, pre-existing)
- 10.689.26256 released to pypi by the mo-deploy session: first release with
  binary wheels
- phase 5a C slots (tp_iter/sq_contains/mp_length), hackcheck-safe `_set`
  (descriptor-based, fixed 3.8-3.12 deploy blocker), tests/test_leaks.py
  (refcount + gc-count harness, no leaks found)
- release pipeline verified end to end, full suite against every installed
  wheel: windows 18 wheels x 329 tests (local MSVC), linux x86_64 9 x 329
  (docker), macos arm64+x86_64 18 (GitHub run 34772924041); aarch64 smoke only
- found+fixed: CIBW_TEST_REQUIRES is unusable on windows - cibuildwheel shells
  through cmd, `>` in version floors becomes a redirect, pip installed 2020-era
  mo-testing (c193add: `pip install -r tests/requirements.txt` in test command)
- packaging simplifications: --required dropped, smoke is the enforcement
  (3918e23); install_speedups.py deleted (abaf6ff); ext_modules as data in
  setuptools.json (039042f); committed packaging/setup.py deleted - mo-deploy
  translator renders it (b2d53d0; mo-deploy 667beb7/97856b3/c8965ff)
- DISCOVERED AT SESSION END: mo-deploy is not on pypi (404) - the
  `pip install mo-deploy` wired into build_wheels.py and wheels.yml can never
  resolve; the 11.1.26256 deploy running at session end fails at pypi() and
  rolls back. Decision needed: publish mo-deploy, install from git, or another
  route to the translator
- next: pick the translator-distribution route, fix build_wheels/wheels.yml,
  re-deploy

## 2026-09-12
- suite 318 ran / 0 err / 6 skip, measured in both modes (C accelerator and MO_DOTS_PURE=1)
- python quick wins (b60d610): dispatch-dict `__getattr__`, frozenset `is_null`,
  precomputed `is_missing` types, Null singleton for dead chains; `test_assign2b` and
  `test_assign_through_dead_chain` pin the path-tracking semantics
- C accelerator `_speedups.c` phases 1-4 (0e93f68, 196e9c0, 86c7a51, 67c333a): hot
  functions, then C base types for Data/NullType/FlatList, dotted-path walk +
  get/items/setitem, FlatList column extract. Measured py3.13: attr hit 1669->230ns,
  `w['a.b.c']` 2747->107ns, miss chain 4435->239ns, `flist.name` 4514->16ns/element (287x)
- repo `.venv` is stale (2022-era deps); the suite ran in a fresh venv built from
  `tests/requirements-3.13.lock`, from repo root with CI=true
- mo-json gained `TODO.md` (a739cde in that repo): plan for C-based mo-json-lazy
  string-backed JSON
