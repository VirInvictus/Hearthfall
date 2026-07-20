# Patch notes

## v0.1.0 (2026-07-20)

Phase 0 ships. The game is playable start to finish: allocate a finite clan across
foraging, scouting, and tending, resolve the season, answer what the world asks, and reach
a verdict twenty seasons later or die before you get there.

**The loop.** A turn produces, feeds, starves, rots, explores, fires an event, ages the
young, and judges the run, in that fixed order. Producing before feeding means this
season's foraging can cover this season's mouths; rotting after feeding means food someone
just ate is never lost to spoilage first. Children starve before adults, furthest from
maturity first, both deterministic.

**The content.** Thirty events across winter, the growing seasons, the clan itself, and
what the scouts walk into. Conditions are `key op value`, AND-ed, and nothing more.
Effects are TOML tables rather than expression strings, because a string needs a parser and
a parser is the event DSL the spec spends a section warning against.

**Strict loading.** An unknown effect key, an unknown condition key, an ordered season, or
a duplicate id fails when the corpus loads. The failure this prevents is the quiet one:
`moral = -1` parses cleanly and changes nothing, and content that looks authored but does
nothing is indistinguishable from content that needs rewriting.

**Determinism.** One seeded, injectable RNG. A seed replays a run exactly, terrain and
event order included, which is what makes any of the balance work below possible.

**The balance pass, and what it found.** Two guards did real work here. The first caught
that all fifty sampled seeds survived a naive policy, which meant the allocation was not a
decision at all. Winter now yields nothing to foraging and costs every mouth extra, which
turns it from a lean season into the one that decides the run, and hands it a different
puzzle: with foraging worthless, the free hands go to tending or into the fog. A policy
that has noticed this endures 190 runs in 200; one that ignores it endures 126, with a
third of the survivors. That gap is Phase 0's question answered.

The second guard caught dead content. Six events were authored, shipped, and unreachable,
including the flagship one from the spec: `winter.granary_rats` required more food in the
store than a winter clan ever has, so it was eligible in 14 of 2148 draws. Thresholds were
re-set from measured draw-time distributions rather than from intuition, and every shipped
event now fires.

**The skin.** A Textual front end that computes nothing: it holds a state, hands the engine
an orders object, and renders the report that comes back. Keyboard-first allocation,
Kanagawa Dragon throughout, ASCII map glyphs so nothing depends on an installed font.

148 tests. `hearthfall --seed N` replays any run exactly.

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
