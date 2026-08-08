# Hearthfall roadmap

Phases are slices, not milestones. Each one is playable and answers a question. If a slice's
question comes back *no*, the answer is to stop, not to push into the next phase hoping it
fixes things. See `spec.md` §7 for the reasoning behind the order.

**Rewritten 2026-08-08.** Phase 0 is unchanged and shipped. Everything after it was replaced
when the spine was generalised (`spec.md` §1). The old Phases 1 to 5 are in git history; the
work they described is not lost, it is redistributed across sub-projects 2, 5, 6, 7, and 8,
and reordered so the kill switch is asked first.

## Phase 0: prove the foundation holds (shipped, v0.1.0)

*Question: is the allocate-and-survive loop tolerable to sit inside for thirty minutes?*

- [x] `engine/rng.py`: one seeded, injectable source, with a determinism test
- [x] `engine/state.py`: world, population pool, stores, season, turn counter
- [x] `engine/turn.py`: resolve a turn (produce, consume, spoil, explore, fire event)
- [x] `engine/world.py`: small fixed grid, fog, home tile, adjacent reveal
- [x] `engine/events/`: TOML loader plus the condition evaluator (`key op value`, AND-ed)
- [x] A ~20-entry event table in `data/events/` (shipped with thirty)
- [x] Survival win/lose conditions
- [x] Textual skin: state readout, allocation controls, event modal
- [x] Engine test suite: turn resolution, food math, condition evaluation, determinism
- [x] Architecture guard test: nothing under `engine/` imports Textual or the frontend
- [x] Headless full-run playthrough test, and guards on the shape of a run
- [x] **The season ledger (v0.1.1).** `turn.forecast` projects the food ledger for a set of
      orders without mutating anything, and the skin renders it under the allocation so the
      arithmetic moves as you assign. Before this, allocation was a guess. Forecast stops at
      spoilage deliberately: everything later in the tick consumes the RNG, and a forecast
      that guessed at the event draw would be lying about the one thing a forecast is for. It
      duplicates the food math rather than sharing code with the mutating steps, and
      `TestForecast` asserts the two agree across every season, store level, and household
      shape, so drift is caught rather than designed out.

**Phase 0 did not test the spine.** It had no scouts, no intel, and no enemy, so it could not.
A yes means the floor is solid. It does not mean the game works.

**One measured defect carries forward as a design input:** a policy that reads the seasons
endures 190 runs in 200, one that ignores them endures 126. Once a player finds the winter
insight the run is nearly safe. That is a pacing problem, and sub-project 4 (the director) is
the answer to it. Do not try to fix it by making winter harsher.

---

## Sub-project 1: the fact ledger (planned). HOLDS THE KILL SWITCH

*Question: does paying to look pull the player forward?*

- [ ] `engine/intel.py`: facts with a value, a staleness, and a price to refresh
- [ ] Tile fog migrated to be intel's first client, not a parallel system
- [ ] Scouts as a distinct role, better at reveal, with a real opportunity cost
- [ ] Larger generated map, terrain-gated resources, terrain-keyed event tables
- [ ] Exploration returns readable reports rather than a single revealed tile
- [ ] Facts that visibly age in the UI, so "we are guessing" is legible before it bites
- [ ] Event corpus grown toward 80

**This slice holds the kill switch, and it is the cheapest place to hold it.** It is the first
time a scout goes out, a report comes back, and the report changes what you do next. If the
fog does not pull here, the central premise is wrong. Council drama, combat depth, and a
grand-strategy endgame will not retrofit a reason to explore. Stop.

## Sub-project 2: households (planned)

*Question: does a famine that creates a rival hurt more than a famine that creates a number?*

- [ ] `engine/people.py`: pool, households, and the kin arithmetic that binds them
- [ ] Famine and scarcity resolved against households, not against a flat count
- [ ] Household mood and resentment with real consequences
- [ ] Aggregate keys in `snapshot()` (`households_resentful`, `worst_household_mood`)
- [ ] Corpus entries keyed on household state
- [ ] Morale becomes a household-level pressure rather than one global display number

Note the constraint from `spec.md` §5: the pool comes first and names are a layer over it.
This slice ships **no named people**. It ships the thing they will later be drawn from.

## Sub-project 3: the chronicle (planned)

*Question: can the game run three years unattended and still feel like yours?*

- [ ] `engine/chronicle.py`: typed entries, engine-side
- [ ] `engine/orders.py`: standing orders and per-season orders as one type
- [ ] `turn.run_until_interrupted`, with the naive threshold-based interrupt
- [ ] TUI rebuilt around the chronicle spine; `tui/app.py` is replaced, not edited
- [ ] Ctrl+P command palette as the navigation surface
- [ ] Glyph tiers (`ascii` / `unicode` / `nerd`), `unicode` default, palette-hosted picker,
      glyph test card, and font advisor
- [ ] Responsive layout: the rail yields to the chronicle on narrow terminals
- [ ] Save and load

Replacing the skin is not a regression; `spec.md` §3 promised it was throwaway-able and this
is the first time that promise is cashed. Keep the season ledger: it is the model for how a
commitment should show its arithmetic before you make it.

## Sub-project 4: neighbours and the director (planned)

*Question: is being raided by someone you could have scouted better than being raided?*

- [ ] `engine/agents.py`: neighbours, weather, and wildlife with state, needs, and intents
- [ ] Peoples placed on the map, discoverable, with grain stores and moods that go stale
- [ ] `engine/director.py`: pacing only, never invention
- [ ] The honesty guarantee enforced in code: an intent requires a learnable fact
- [ ] Interrupts that break standing orders, with the cause traceable in the chronicle
- [ ] The 190-in-200 defect re-measured; the target is pressure, not a harsher winter

## Sub-project 5: the ring (planned)

*Question: is losing an argument to your own council worse than losing to winter?*

- [ ] Named cast drawn from households: traits, ambitions, relationships, ageing, death
- [ ] Advisors with agendas that are wrong in characteristic ways
- [ ] `engine/tiers.py`: emergence conditions and the named moment
- [ ] Council decisions rendered inline in the chronicle
- [ ] Corpus entries gated on ring composition and household standing

## Sub-project 6: violence (planned)

*Question: is losing people to a fight you misread painful in the right way?*

- [ ] `engine/combat.py`: abstract single-stack resolution, your strength vs. theirs, one roll
- [ ] Terrain and morale modifiers
- [ ] Intel quality as a combat input; a stale fact should cost you
- [ ] Raiders that hit stores; the granary as a target
- [ ] Real stakes: dead people, lost stores, ground gained

## Sub-project 7: composition (planned)

*Question: is assembling the right stack against a read enemy the best decision in the game?*

- [ ] Unit types with strengths and weaknesses
- [ ] Groups assembled from types
- [ ] The counter-web that makes composition a puzzle
- [ ] Scout intel driving pre-battle assembly

## Sub-project 8: the long game (planned)

- [ ] Multiple peoples with distinct doctrines and group structures
- [ ] Resource variance across terrain
- [ ] The arc from hearth to city to power, with each tier retiring a chore
- [ ] Grimdark endgame: attrition, hard borders, a people that endures or is buried

---

## Deferred, deliberately

Parked so they stop asking.

- A GTK frontend (the architecture permits it; the prototype does not need it)
- Any event authoring tool more elaborate than a text editor
- Multiplayer in any form
- A maneuvering map with fronts and army movement (`spec.md` §9.8; this one is not deferred,
  it is refused)

**No longer deferred, and why:**

- *Named individual characters.* Un-parked for sub-project 5. The condition that justified
  parking them still holds and is now written into `spec.md` §5: the pool comes first,
  households are the join, names are drawn from households and never the foundation.
- *Save/load beyond a seed and a turn log.* Un-parked for sub-project 3. Correct to defer for
  a 30-minute run; a campaign that reaches tier 4 outlives a sitting.
