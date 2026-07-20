<p align="center">
  <img src="logo.svg" width="128" height="128" alt="Hearthfall logo">
</p>

# Hearthfall

A grimdark clan-survival game for the terminal. Start with a handful of villagers and a
fog-black map. Send people out; the world reveals itself tile by tile through scarcity,
story, and violence. Grow a hearth into a war-band into a people, or bury them.

Think *A Dark Room* that grows a spine into *King of Dragon Pass*, rendered in glyphs.

> **Status: pre-alpha, unbuilt.** This repository currently holds the design contract and a
> scaffold. Phase 0 has not been built. See [`roadmap.md`](roadmap.md) for what "done"
> means at each slice.

## The spine

Scouts reveal the map *and* reveal enemy composition. That intel lets you assemble a
counter-force before you commit.

Exploration and combat are the same loop. You do not fight blind; you fight prepared, and
the fun lives in the preparation rather than the swing. A scout that comes back with *"forty
of them, mostly spears, no archers, holding the high ground"* is worth more than a sword.

## The turn

Time is seasonal, four turns to a year, and winter never negotiates. Each turn you read the
state, allocate finite people to work or exploration or war, watch the engine resolve it,
and live with what comes back. The tension is always the same shape: not enough hands, not
enough food, and the dark is full of things you haven't scouted yet.

## Architecture

The engine is a pure Python library with no I/O, no rendering, and no dependencies. The TUI
is a thin, shed-able skin over it.

```
src/hearthfall/engine/   pure logic, stdlib only, fully tested
src/hearthfall/tui/      Textual skin; the engine does not know it exists
src/hearthfall/data/     TOML content: events, terrain, units, peoples
tests/                   the engine is tested; the skin is not
```

You can drive a full game from a Python REPL with zero terminal. Every random draw goes
through one seeded, injectable RNG, so a seed reproduces a run exactly. Both properties are
enforced by tests, not by good intentions.

## Requirements

- Python 3.14+
- Textual (frontend only; the engine needs nothing)

## Running the tests

```sh
./run_tests.sh
```

## Documentation

- [`spec.md`](spec.md): the contract. Read it before changing semantics.
- [`roadmap.md`](roadmap.md): build phases and their kill gates.
- [`patchnotes.md`](patchnotes.md): release notes.

## License

MIT. See [`LICENSE`](LICENSE).
