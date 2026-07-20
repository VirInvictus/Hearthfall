# Patch notes

## v0.0.1 (2026-07-19)

Repository scaffolded. No game yet.

- **The design contract lands** (`spec.md`): the spine, the anti-goals, the engine/skin
  separation, the content strategy, the build phases, and the invariants.
- **Named Hearthfall.** The working title was Cairn, which collides with Yochai Gal's OSR
  ruleset (already cited as the combat chassis in a sibling project). Hearthfall carries the
  same arc without the collision: the thing you gather around, and what happens to most of
  them.
- **Phase 0 re-scoped as a foundation test.** It has no scouts, no intel, and no enemy, so
  it cannot test the spine. Its question is now "is the allocate-and-survive loop tolerable
  for thirty minutes", and the project's kill switch moved to Phase 2, where a scout report
  first changes what the player does next.
- **Event effects are structured TOML tables, not expression strings.** `food = -5` needs no
  parser; `"stores.food -= 5"` needs one, and a parser is the event DSL the spec spends a
  section warning against.
- **The engine takes no dependencies.** Textual stops at the `tui/` boundary. This is the
  mechanical proof that the separation is real, and a test will enforce it.
- `engine/rng.py`: the one seeded, injectable random source, with determinism tests.
