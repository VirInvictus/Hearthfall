# Hearthfall roadmap

Phases are slices, not milestones. Each one is playable and answers a question. If a slice's
question comes back *no*, the answer is to stop, not to push into the next phase hoping it
fixes things. See `spec.md` §7 for the reasoning behind the order.

**Rewritten 2026-08-08.** Phase 0 is unchanged and shipped. Everything after it was replaced
when the spine was generalised (`spec.md` §1). The old Phases 1 to 5 are in git history; the
work they described is not lost, it is redistributed across sub-projects 2, 5, 6, 7, and 8,
and reordered so the kill switch is asked first.

## The standing gate: play a year before calling a slice done

**Added 2026-08-09, and it applies between every slice and every sub-project from here on.**

No slice is finished when its tests are green. It is finished when a year of play has been
read start to finish and judged **fun, interesting, and survivable**. This is a TUI game;
gameplay is the product, and a green suite says only that the arithmetic agrees with itself.

The gate, run at the end of every slice:

- Print an annotated year: season by season, the allocation offered, the forecast, what
  actually happened, and every event that fired with the choice taken.
- Read it as a player would, not as an author. Three questions, answered out loud in the
  slice's roadmap entry:
  1. **Was there a real decision every season**, or did the allocation write itself?
  2. **Was there slack to decide with?** A store pinned at zero for three seasons is not
     difficulty, it is a run with the choices removed.
  3. **Did anything happen worth telling someone about?**
- A slice that fails this does not ship, and the answer is not to lower the difficulty
  reflexively. It is to find which of the three questions failed and fix that one.

**Why this exists.** Slice 2's first measurement passed every automated guard while year one
killed half the clan under good play and left the store at zero for the rest of the run. The
guards are shaped to catch a broken loop, not a joyless one, and nothing in the suite can tell
the difference between hard and disheartening.

---

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

## Sub-project 1: the fact ledger (in progress). HOLDS THE KILL SWITCH

*Question: does paying to look pull the player forward?*

Built in slices, each green before the next starts.

- [x] **Slice 1: the ledger (2026-08-08).** `engine/intel.py` with `Fact`, `FactKind`,
      `Staleness`, and `Ledger`. Fog migrated off `Tile.revealed` entirely; `World` is pure
      geography and a test asserts its knowledge API stays gone, so a second source of truth
      cannot quietly return. Half-lives are injected rather than imported, because `balance`
      imports `state` and `state` owns a `Ledger`. Fact keys namespace places apart from
      names (`terrain@1,2` vs `presence#stonefold`) so sub-project 4 can add neighbours
      without reshaping keys. No gameplay change. 169 tests.
- [x] **Slice 2: known ground is workable ground (2026-08-09).** Each known tile carries a
      per-terrain yield and a forager capacity; hands beyond the capacity of revealed ground
      bring back nothing. Terrain multiplies the season base in tenths, so winter's zero stays
      zero with no special case. The engine places foragers greedily, best ground first, so
      orders stay scalar and the map stays a knowledge surface (§9.9). `forage_take` reads
      terrain from the ledger and takes no world argument at all: the clan forages the ground
      it *believes* is there. Water is dead ground, so a reveal is a gamble. Suite 169 → 189.

      **The kill switch answers yes, decisively.** Measured over 200 seeds, a policy that
      never scouts ends with 1.4 people; one that scouts while the map is the binding
      constraint ends with 6.5; one that also reads winter ends with 7.8. Paying to look pays.
      `TestPayingToLookPullsYouForward` now asserts it, so the premise is defended by the
      suite rather than by a note.

      **Binary endurance died as a metric here.** Explorer 198/200 against season-aware
      199/200 is noise, while a clan that never scouts still "endures" 152 times by shrinking
      to two people on one tile, which the win condition counts as survival. The policy
      comparisons moved to total survivors, which separates the same three policies
      1.4 / 6.5 / 7.8.

      **The standing gate failed this slice on two of its three questions**, and the failures
      are recorded rather than tuned away:
      1. *A real decision every season?* **No.** From year 2 onward the allocation is
         identical every single season (`forage 5, scout 0, tend 0`) across every seed
         examined. Capacity plateaus around 7, the clan settles at 5, and the last eight
         seasons of a twenty-season run are one turn repeated. **Exploration switches itself
         off**: once capacity exceeds the adults available, there is no reason to scout again,
         so the mechanic this slice exists for stops mattering halfway through the run.
      2. *Slack to decide with?* **Marginal.** The store reaches zero in year 2 on the seeds
         read. The death spiral is self-correcting rather than threatening (people die, demand
         falls, the survivors are comfortable), which removes tension instead of adding it.
      3. *Anything worth telling someone about?* **Weakly.** Events repeat inside a single run
         and are uniformly small nudges to food or morale. Nothing is game-altering and
         nothing remembers anything.

      `STARTING_FOOD` was the obvious lever and it does not work; see the note on it in
      `balance.py`. The game is too harsh in year one and too safe from year two, and one
      scalar cannot move those in opposite directions.
- [x] **Slice 2.5: the corpus grows a memory (2026-08-09).** Inserted ahead of slice 3 after a
      real playtest: the allocation writes itself, so the decisions have to live in the events,
      and events that forget everything cannot carry them.

      A **tally** is one integer that persists for the run, written by event effects as a
      structured table and read by conditions as `tally_<name>`. That single addition buys
      silent progress meters, chains gated on *specific answers* rather than on an event
      having fired, chains needing several prior events, and payoffs earned across years. The
      condition evaluator does not grow by one line, which is decision 5 holding exactly:
      `snapshot()` grows, the evaluator never does.

      Every tally is declared in `data/tallies.toml`, and effects validate names against the
      same reference snapshot conditions already use, so there is exactly one definition of
      which tallies exist. `tally.elder_resentmnt = 1` fails at load instead of incrementing a
      counter no condition will ever read.

      `data/events/elder.toml` is the worked example: overrule him in year one and it runs
      toward a man who stops arguing and starts arranging; defer and it runs somewhere else.
      **Rarity comes from conditions, not a weight lottery.** The powerful entry is rare
      because reaching resentment above five takes a run's worth of choices. A payoff you
      earned reads as a consequence; a payoff you rolled reads as noise. Suite 190 → 205.

      *Still open, and the reason this is not the plateau fix:* the labour allocation itself is
      unchanged, so gate question 1 is answered by events rather than solved.

- [ ] **Slice 3: scouts as a gradient.** Replace the `EXPLORERS_PER_REVEAL` cliff. Two learn
      the terrain, three also learn what can be foraged there, four also learn what lives
      there. Turns a threshold into a slope.
- [ ] **Slice 4: reports.** Scouts return the facts they learned, rendered as prose.
- [ ] **Slice 5: staleness that bites.** `PRESENCE` facts age visibly and an old fact should
      be able to mislead. Adds the first staleness keys to `snapshot()`.
- [ ] **Slice 6: corpus toward 80**, terrain-keyed.

Deferred within this sub-project, deliberately: a larger map. It is a balance change on top
of a balance change, and slice 2 already moves every food constant. Do it once slice 2's
numbers have settled, not alongside them.

> **The finding that reframes this sub-project (2026-08-08).** Exploring is currently almost
> mechanically pointless. `FORAGE_YIELD` is keyed on season alone, so a known tile feeds
> nothing but the event table, and the kill-switch question can only answer *no* because
> looking does not pay. That is a missing mechanic, not a tuning problem.
>
> The fix is slice 2: **ground you have walked is ground you can work.** Each known tile
> carries a forage bonus by terrain and supports a number of foragers; foragers beyond the
> capacity the clan has revealed bring back nothing. Exploration then raises the economic
> ceiling, and the cost of scouting is repaid in what the clan can eat next year. That is
> `spec.md` §1 expressed in food, and it is the smallest change that makes the kill-switch
> question answerable at all.
>
> Expect this to break the balance hard, and expect to re-measure. The Phase 0 figure to beat
> is the 190-in-200 endurance of a season-reading policy; `tests/test_playthrough.py` already
> has the harness for measuring it.

**This sub-project holds the kill switch, and it is the cheapest place to hold it.** It is the
first time a scout goes out, a report comes back, and the report changes what you do next. If
the fog does not pull here, the central premise is wrong. Council drama, combat depth, and a
grand-strategy endgame will not retrofit a reason to explore. Stop.

**Open naming question, not yet decided:** `Orders.explore` versus `Orders.scout`. The spec
and every design conversation say "scout"; the code says "explore". Left alone during slice 1
to avoid churn in a commit that was already touching ten files. Worth settling before slice 4
writes reports in the scouts' voice.

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
