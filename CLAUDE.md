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
- **Run the tools through `uv run`.** `ruff` and `pyright` are pinned in the `dev` dependency
  group and resolved from the committed lockfile, so `uv run ruff check src tests` is exactly
  what CI runs. A bare `ruff` is whatever is on `PATH` and has disagreed with CI before.
- **Pyright is strict over `engine/` and gates the whole tree.** The four CI steps are
  `ruff check`, `ruff format --check`, `pyright src tests`, and the suite. Keep it at zero.
- Engine dataclasses carry `slots=True`, and `frozen=True` too when they are value types.
  This is deliberate (`spec.md` §8): it is a chunk of what a stricter language would have
  given, bought without leaving Python.
- Two idioms exist to keep strict mode honest rather than to satisfy it. `field(default_factory=list[str])`
  is parameterised because a bare `list` leaves the element type unknown and that unknown
  spreads to callers. `tests/support.py` holds `not_none` and `an_int` because
  `assertIsNotNone` does not narrow a type and `snapshot()` values are deliberately `int | str`.
- `hypothesis` is available for invariants that are genuinely properties (forecast parity,
  determinism) rather than examples. It does not replace the example tests.

## Content

The event corpus is the actual project; the engine that reads it is a weekend. When a task
is "improve events", the answer is almost always "write more events", not "improve the
event system". Treat requests to enrich the event format with suspicion and point at
`spec.md` §6.

**Tallies are how the corpus remembers.** A tally is one integer that persists for the run,
written by an effect (`[event.choice.effect.tally]`) and read by a condition as
`tally_<name>`. Because the write hangs off a *choice*, a later event can require that you
answered a particular way, not merely that something happened. Every tally is declared in
`data/tallies.toml`; declaring it is what makes it exist, and an undeclared name fails at
load. Reach for a tally before reaching for a new engine feature: chains, silent resentment
meters, and earned payoffs are all already expressible. `data/events/elder.toml` is the
worked example.

**Rarity comes from conditions, not from weight.** A powerful event should be rare because
it is hard to reach, not because a die came up short. Earned reads as consequence; rolled
reads as noise.

## Comments

Sparingly. Explain the non-obvious where it lives: why the RNG is injected, why a modifier
is tuned the way it is, why an invariant test exists. Game balance constants deserve a note
saying what they were tuned against; mechanics that read plainly do not need narration.
