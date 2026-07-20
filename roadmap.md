# Hearthfall roadmap

Phases are slices, not milestones. Each one is playable and answers a question. If a
slice's question comes back *no*, the answer is to stop, not to push into the next phase
hoping it fixes things. See `spec.md` §7 for the reasoning behind the order.

## Phase 0: prove the foundation holds (not started)

*Question: is the allocate-and-survive loop tolerable to sit inside for thirty minutes?*

- [ ] `engine/rng.py`: one seeded, injectable source, with a determinism test
- [ ] `engine/state.py`: world, population pool, stores, season, turn counter
- [ ] `engine/turn.py`: resolve a turn (produce, consume, spoil, explore, fire event)
- [ ] `engine/world.py`: small fixed grid, fog, home tile, adjacent reveal
- [ ] `engine/events/`: TOML loader plus the condition evaluator (`key op value`, AND-ed)
- [ ] A ~20-entry event table in `data/events/`
- [ ] Survival win/lose conditions
- [ ] Textual skin: state readout, allocation controls, event modal
- [ ] Engine test suite: turn resolution, food math, condition evaluation, determinism
- [ ] Architecture guard test: nothing under `engine/` imports Textual or the frontend

**Phase 0 does not test the spine.** It has no scouts, no intel, and no enemy, so it cannot.
A yes means the floor is solid. It does not mean the game works.

## Phase 1: make it a game (planned)

*Question: does anyone want a second run?*

- [ ] Event corpus grown to 60 to 80 entries
- [ ] Council decisions with advisors who have agendas
- [ ] Seasons that bite: winter draw-down balanced survivable but never safe
- [ ] Spoilage tuned so stockpiling is a decision rather than a ratchet
- [ ] Morale as a real pressure, not a display number

## Phase 2: make the map matter (planned, holds the kill switch)

*Question: does the fog pull the player forward?*

- [ ] Larger generated map
- [ ] Terrain-gated resources and terrain-keyed event tables
- [ ] Scouts as a distinct role, better at reveal
- [ ] Exploration intel returned as readable reports
- [ ] Peoples placed on the map, discoverable

**This phase holds the kill switch.** It is the first slice where the spine is legible: a
scout goes out, a report comes back, and the report changes what you do next. If the fog
does not pull here, the central premise is wrong and combat depth will not retrofit a
reason to explore.

## Phase 3: introduce violence (planned)

*Question: is losing people to a fight you misread painful in the right way?*

- [ ] Abstract single-stack combat: your strength vs. theirs, one roll
- [ ] Terrain and morale modifiers
- [ ] Intel quality as a combat input
- [ ] Raiders that hit stores; the granary as a target
- [ ] Real stakes: dead people, lost stores, ground gained

## Phase 4: the reward (planned)

*Question: is assembling the right stack against a read enemy the best decision in the
game?*

- [ ] Unit types with strengths and weaknesses
- [ ] Groups assembled from types
- [ ] The counter-web that makes composition a puzzle
- [ ] Scout intel driving pre-battle assembly

## Phase 5: the long game (planned)

- [ ] Multiple peoples with distinct doctrines and group structures
- [ ] Resource variance across terrain
- [ ] The 4X arc: hearth to city to power
- [ ] Grimdark endgame: attrition, hard borders, a people that endures or is buried

## Deferred, deliberately

Parked so they stop asking. None of these ship before Phase 5.

- Named individual characters with needs (the pool abstraction comes first; names are a
  flavor layer over it, never the foundation)
- A GTK frontend (the architecture permits it; the prototype does not need it)
- Save/load beyond a seed and a turn log
- Any event authoring tool more elaborate than a text editor
- Multiplayer in any form
