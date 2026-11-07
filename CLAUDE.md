# CLAUDE.md

## What this is

Null-safe data navigation: `Data` wraps JSON-like structures for dot access, and `Null`
stands in for None at every miss. The foundation of the mo-* stack.
[mo_dots/CLAUDE.md](mo_dots/CLAUDE.md) covers working inside the library - Null identity
semantics and the field-path algebra.

## Using it properly

The consumer rules are the `mo-dots` skill:
[plugins/mo-dots/skills/mo-dots/SKILL.md](plugins/mo-dots/skills/mo-dots/SKILL.md).

## Layout

- `mo_dots/` - the library: `datas.py` (Data), `nones.py` (Null), `lists.py`
  (FlatList), `fields.py` (the field-path algebra), `objects.py`, `utils.py`,
  `_speedups.c` (optional C accelerator - traps in mo_dots/CLAUDE.md).
- `plugins/mo-dots/` - the Claude Code plugin carrying the consumer skill;
  `.claude-plugin/marketplace.json` lists it.
- `docs/` - the full feature documentation, changelog, `TODO.md` (the owed list), and
  `CODE_SWEEP.md` (the /fix-code ledger: path @ content hash).
- `todo.md` - svn-sync's own note of major version bumps owed.
- `tests/`, `packaging/` - the suite and the release scaffolding.
