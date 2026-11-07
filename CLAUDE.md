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
- `TODO.md` - campaign doc: the performance work queue, measured.
- `docs/` - the full feature documentation, changelog, and session log.
- `tests/`, `packaging/` - the suite and the release scaffolding.
