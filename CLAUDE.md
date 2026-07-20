# CLAUDE.md (Hearthfall)

Per-project guidance. Overrides the global file where they conflict.

## What this is

A grimdark clan-survival game in the terminal: turn-based, season-timed, fog-black map.
Read `spec.md` before changing anything semantic. It is written as a knife, not a wishlist,
and its warnings are aimed at real failure modes rather than hypothetical ones.

## Hard constraints

- **The engine imports nothing from the frontend, and nothing from PyPI.** `engine/` is
  stdlib-only pure logic: no I/O, no rendering, no terminal. Textual lives in `tui/` and
  nowhere else. A test enforces this. If a task seems to need a dependency inside the
  engine, stop and ask.
- **One seeded RNG.** Every random draw goes through `engine/rng.py`. Never call
  `random.*` or `secrets.*` directly anywhere else in the engine. A seed must reproduce a
  run exactly; determinism is what makes balancing and bug-fixing possible at all.
- **Event effects are structured TOML tables, never expression strings.** `food = -5`, not
  `"stores.food -= 5"`. The second one requires a parser, and the parser is the event DSL
  that `spec.md` §6 spends a warning block telling us not to build.
- **The condition evaluator stays small.** A list of `key op value` clauses, AND-ed, over a
  state dict. It does not grow OR, parentheses, functions, or arithmetic without a hundred
  real events proving the need.
- **Phase order is load-bearing.** Do not pull work forward from a later phase because it
  is more interesting. See `roadmap.md`.

## Layout

- `src/hearthfall/engine/`: pure logic (state, turn, world, pops, combat, events, rng).
- `src/hearthfall/tui/`: the Textual skin. Throwaway-able by design.
- `src/hearthfall/data/`: TOML content. Events, terrain, units, peoples. No logic.
- `tests/`: engine tests. The skin is not tested.

## Conventions

- Type hints, `from __future__ import annotations`, ruff for lint and format.
- Python 3.14+. TOML is read with stdlib `tomllib`.
- `VERSION` lives in `src/hearthfall/__init__.py` and is mirrored in `pyproject.toml`.
  Bumping the version means updating both.
- Run tests with `./run_tests.sh` (or
  `PYTHONPATH=src python3 -m unittest discover -s tests`).
- Tests are stdlib `unittest`, matching the rest of the author's Python projects.

## Content

The event corpus is the actual project; the engine that reads it is a weekend. When a task
is "improve events", the answer is almost always "write more events", not "improve the
event system". Treat requests to enrich the event format with suspicion and point at
`spec.md` §6.

## Comments

Sparingly. Explain the non-obvious where it lives: why the RNG is injected, why a modifier
is tuned the way it is, why an invariant test exists. Game balance constants deserve a note
saying what they were tuned against; mechanics that read plainly do not need narration.
