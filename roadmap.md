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

## Sub-project 1: the fact ledger (complete, 2026-08-09). HELD THE KILL SWITCH

*Question: does paying to look pull the player forward?* **Yes, measured, and defended by the
suite.** All six slices are in. What the sub-project leaves behind: fog is a property of a fact
rather than of a tile, scouting is a slope rather than a threshold, the party's account is
rendered from what it learned, the ground moves under a picture nobody refreshes, and the
corpus that reads all of it is 82 entries rather than 34.

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

- [x] **Slice 3: scouts as a gradient (2026-08-09).** Two scouts walk a tile and learn what the
      ground is; the clan can then work it thinly (`WALKED_CAPACITY`, one hand at the tile's
      full yield). Three also survey: the party stops somewhere and works out what the place
      will feed, writing the `FORAGE` fact that lifts a tile to its whole terrain capacity.
      A forest is worth one hand walked and three surveyed.

      **Which tile is surveyed is the engine's call, not a new order.** The party looks at the
      best ground the clan knows of but has never worked out, which is usually the tile it just
      walked into and need not be. Orders stay scalar and the engine places the work, exactly
      as it places foragers (§9.9). A survey that would raise nothing is not made: marsh and
      water gain nothing, and the report says the hands were wasted rather than logging a
      survey that moved no number. Because `FACT_HALFLIFE[FORAGE]` is eight seasons, slice 5
      will make surveys expire, which is what turns scouting into a standing cost.

      **The third scout was worth less than nothing before this, and now pays.** Over 200
      seeds a policy that only walks ends with 3.1 people and one that surveys with 4.9; under
      the old rules the same third hand measured 5.8 against 6.2. `WALKED_CAPACITY` was chosen
      by sweeping it: at 0 a walking party is useless (14 runs in 200 endure) and the cliff has
      only moved to three scouts; at 2 nothing but a forest gains from a survey and the gap
      collapses to 5.2 against 5.6.

      **It does not fix the plateau, and was not expected to.** Parties still stop going out
      once ground is ahead of hands, in the same 5.9 seasons of 20 as before.

      **Gate verdict: ships.** Read across two full runs.
      1. *A real decision every season?* **Better early, still no late.** The choice between
         widening and deepening is now priced on screen before it is made (year 1 autumn, seed
         3: forage +16, walk +10, survey +5), where previously the third hand bought nothing
         and there was no trade to weigh. From about year 4 capacity exceeds the adults again
         and every scouting option is pure loss, which is the plateau and not this slice.
      2. *Slack to decide with?* **Unchanged.** A competent policy's worst year-one headcount
         is 6.7 of 8 against 7.0 before the slice. Harsher by a fraction of a person, which is
         not the disheartening kind.
      3. *Worth telling someone about?* **A little more.** "They worked out what the forest to
         the west will feed: 3 can work it now" is a beat, and a wasted third scout now says so
         out loud. The corpus itself is untouched; that is still slice 6.

      Settled here as well: `Orders.explore` became `Orders.scout` throughout, since the code
      was already open and slice 4 writes reports in the scouts' voice. Suite 238 → 255.

      *The presence rung is deliberately not built.* Two scouts walk and three survey; a fourth
      learning what lives on a tile waits for sub-project 4, because nothing lives on the map
      yet and a tier that costs four adults to write a fact nobody reads is a trap.
- [x] **Slice 4: reports (2026-08-09).** `engine/reports.py`: the party's account of the season,
      rendered from the facts it brought home, said once and in one voice. The steps that move
      the state are silent now, because prose written from inside three separate steps arrives
      in whatever order the steps run in, and a season could tell the player it found nothing
      before telling them what it found.

      The walk names where and what ("The scouts walked north into marsh") and, when it is
      worth saying, what the ground is worth: the best the clan has found, poorer than
      anything it holds, or water that will feed nobody. **A middling tile gets no verdict at
      all.** Measured over sixty runs that is 6.4 walks and 2.2 verdicts a run, which is the
      rate a line has to fire at to still be read. The survey reads as one visit or two
      depending on whether the party stopped where it walked, which fixes a sentence that read
      as a non sequitur whenever it surveyed ground the clan already knew.

      **A whole family of lines was written, measured, and deleted.** "Two ways still lead into
      the dark" and its variants fired zero times in sixty runs, because a clan walks six to
      ten tiles of twenty-five and the frontier never narrows. What survives is the one case
      that can happen: a party sent to a closed frontier says so rather than costing hands and
      reporting silence. Prose that cannot fire is worse than no prose, because it reads as
      covered.

      `TurnReport.learned` carries the typed facts beside the sentences, which is what
      sub-project 3's chronicle will read instead of re-parsing strings.

      **Gate verdict: ships, and the gate is not the right instrument for it.** No mechanic
      changed and the numbers prove it: the same 200 seeds end with the same survivors
      (3.1 / 4.8 / 7.6 for walking, surveying and season-aware policies). So questions 1 and 2
      are answered "unchanged" by construction, and only question 3 is live: *is anything worth
      telling someone about?* Reading a year, yes, and for the first time in the fog: a party
      that walks into marsh, finds it poorer than anything the clan holds, and comes home with
      nothing else worth a closer look is a season that happened, where before it was two
      sentences of bookkeeping. Suite 255 → 278.
- [x] **Slice 5: staleness that bites (2026-08-09).** The ground stopped holding still. A tile
      the clan leans on thins out and one it rests comes back; a survey records how rich a
      place was *the season it was made*; and the number does not follow the ground afterwards.
      So the fact ledger can now be wrong rather than merely old, which is what slice 2 shaped
      `forage_take` around and what the whole spine promised.

      `forage_take` is the clan's expectation and `work_ground` is the season that happened.
      The season ledger became a forecast rather than a guarantee, and the gap is prose: *the
      forest to the west gave 3 less than it should have. It is not the ground the clan
      remembers.* `stale_surveys` is the first staleness key in `snapshot()`.

      **A party out looks over the clan's own ground as well as the dark, and that one rule is
      the slice.** Without it a clan scouting every season was disappointed 6.7 times a run and
      one that never scouted 7.0: a party can look at one tile while the clan works five, so
      intel could never keep up whatever the player did, and the mechanic punished everyone
      equally and taught nobody anything. With it, keeping a party out in winter costs 161 food
      to stale numbers across thirty seeds against 403 for letting the picture rot.

      **Two designs were built, measured, and thrown away first, and both failures are worth
      keeping.** (1) Wear took a tile's *capacity*. It does nothing, because this clan is
      hands-limited: a tile losing a forager it never had the people to send is free, and a
      clan that stopped scouting entirely ended a run half a person behind one that never
      stopped. Anything that lowers a ceiling nobody reaches is invisible here, and that rules
      out a whole family of future ideas. (2) Wear healed only tiles nobody touched, which has
      no equilibrium at all: anything worked every season accrues forever, and the clan's best
      forest fell to the floor inside a year. The healing allowance also has to scale with the
      tile, or depletion is a tax on surveying alone: a flat one-hand allowance is exactly what
      a clan that only walks ground puts on a tile, and it flattened slice 3's gradient from
      4.8-against-3.1 survivors to 2.5-against-2.4.

      **`PRESENCE` staleness is not in this slice.** The roadmap's original line named it, but
      nothing lives on the map until sub-project 4, so it has no client to bite. It moves there
      with the presence scouting rung deferred out of slice 3.

      **Gate verdict: ships, with the cost named.** Read across two runs, one watchful and one
      that settles down.
      1. *A real decision every season?* **Improved, and in the half of the run that needed
         it.** Keeping a party out is now worth something after the map is walked, which is the
         first time late-game scouting has had a reason at all. The allocation still writes
         itself when capacity outruns hands; that is the plateau and still sub-projects 6 to 8.
      2. *Slack to decide with?* **Tighter, deliberately.** A season-reading policy ends with
         7.1 people against 7.6 and endures 110 runs in 120 against 116. Ground that can be
         spent is worth less than ground that cannot, and that is the trade this slice makes.
      3. *Anything worth telling someone about?* **Yes, and it is the best line in the game so
         far**, because it is the only one that tells the player something they got wrong.
- [x] **Slice 6: corpus toward 80 (2026-08-09).** 34 events to 82, in five new files written
      against vocabulary that did not exist when the old ones were: terrain plus season and
      survey depth (`ground.toml`), the intel layer itself (`fog.toml`), households outside the
      rationing prompt (`hearths.toml`), hunger the clan remembers (`hunger.toml`), and three
      tally chains for generosity, caution and the dead (`debts.toml`, `dead.toml`). Two new
      tallies, `strangers_taken_in` and `graves`.

      **`EVENT_COOLDOWN` stays at 16, against this slice's own instruction to lower it.**
      Tripling the corpus did help at a fixed cooldown: runs replaying an event verbatim fell
      from 9 in 60 to 3 in 60. But lowering the cooldown is *worse* at 82 events than 16 was at
      34 (8 seasons: 35 runs in 60). Repetition is governed by how many entries are eligible at
      once, not by how many exist, and tight gating means a season offers about a dozen
      candidates however big the corpus gets. Writing more raises the ceiling; it does not
      retire the cooldown.

      **Three entries were cut rather than shipped, and the finding is worth more than they
      were.** All three were gated on `households_resentful`, which is not reachable content:
      across sixty runs of the harshest rationing available, 142 seasons ran short and 138
      household-seasons were wronged, and the highest resentment any hearth reached was exactly
      the threshold, at the very end of runs. Lowering the threshold to two bought a window so
      narrow that the three traded places at random, and removing one made another stop firing.
      `RESENTFUL_AT` was put back to 3 and the events wait for sub-project 2 slice 4.

      **The reachability guard earned its keep twice.** It caught a condition on
      `terrain_home == hills`, which can never be true because the hearth is always placed on
      plain; and it caught that the guard's own policy ladder predated slice 3, so nothing in
      it ever sent a third scout or rationed unevenly and a whole file was unreachable by
      construction of the harness. The ladder now runs nine policies including surveying,
      watchful and unequal-rationing.

      **Gate verdict: ships, with one regression named.**
      1. *A real decision every season?* Unchanged. This slice is content, not mechanics.
      2. *Slack?* Unchanged.
      3. *Anything worth telling someone about?* **Yes, and this is the slice that was supposed
         to deliver it.** Reading a run, no entry repeats and the seasons are about different
         things: a marriage arranged between two hearths, a camp that has outgrown one fire,
         the wind off the hills charging for the high ground, ground that gave less than it
         should have.

      **What it made worse:** every season now carries an event, where it used to be about nine
      in ten. A quiet season no longer exists, and with something always eligible the draw
      always fires. That is a pacing problem and the fix belongs to the director (sub-project
      4), not to a constant here. Recorded rather than patched.

**A larger map: deferred, and the reason has changed.** It was parked as a balance change on
top of a balance change, to be revisited once slice 2's numbers settled. They have settled, and
the answer is now *no* rather than *not yet*: measured, the clan already stops needing new
ground around four tiles, so a bigger map adds ground nobody walks to. Revisit only after
sub-projects 6 to 8 give hands a second thing to do. See `spec.md` §7.

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

**Settled in slice 3:** `Orders.explore` versus `Orders.scout`. It is `scout`, everywhere, and
the key binding moved from `e` to `s` with it.

## Sub-project 2: households (in progress)

*Question: does a famine that creates a rival hurt more than a famine that creates a number?*

- [x] **Slice 1: the famine lands on somebody (2026-08-09).** `engine/people.py` with
      `Household`, `Rationing`, and `share_out`. The pool moved rather than gained a
      neighbour: `Population` still answers `adults`, `child_count`, `total`, and `morale`,
      but derives all four from households, so there is one source of truth and the corpus
      and frontend needed no changes at all. Morale is the average of the *living* households,
      which is what kept roughly thirty shipped events working unchanged.

      **Rationing is the new decision.** When the store cannot cover demand you choose how to
      divide it, and there is no dominant answer. Measured over 120 seeds: an even split is
      *worse* for survival (a clan that never scouts endures 51 against 67) because spreading
      a shortfall pushes every hearth into the starvation threshold at once, but it breeds
      exactly zero resentment. Concentrating food saves people and makes a household that
      remembers being fed last. Being wronged is deliberately not the same as being hungry.

      Households also made the game less safe, which the plateau needed: a scouting policy
      fell from 99% to 93%. Famine now concentrates instead of averaging.

      **Gate verdict: mechanically sound, dormant in good play.** Reading a run: the store
      swings 30 → 2 → 36 across a year, which is a real rhythm, and the elder chain gives the
      seasons something to be about. But the rationing prompt never appeared in eight seasons
      of competent play, because a competent player is rarely short, and the three households
      stayed identical (`m6 m6 m6`) for the same reason. **Both the new decision and the new
      structure are invisible unless things are already going wrong.** That is the honest
      result and it is what slices 2 to 4 are for: households need reasons to diverge that are
      not famine.

      Also measured: `WORKERS` and `CHILDREN` produce nearly identical outcomes, because the
      clan is capacity-bound rather than labour-bound, so protecting the workers buys nothing.
      Same root cause as the plateau. Suite 205 → 231.

- [x] **Slice 2: growth (2026-08-09).** A household with two adults, a decent mood, and a fed
      season builds a silent `bond`; at `BOND_TO_BEAR` it bears a child and the meter resets. A
      hungry season knocks it back, so famine costs years of growth rather than a turn of it.
      Hearths that outgrow `HOUSEHOLD_SPLITS_AT` split, which is how three kin groups head
      toward the ten to forty `spec.md` §5 wants.

      **Deterministic, with no roll at all.** The old gate gave the clan forty food and decent
      morale and then rolled dice; it asked about the clan as a whole, which is a question
      about nobody, and it came back yes so rarely that the clan simply never grew. Making
      growth a schedule ties it to *how the player rationed*: the hearth you feed last is the
      hearth that stops growing. That connection is what a lottery would have severed.

      **It works, and it does not fix the plateau.** The clan can now grow (65 runs in 120
      rise above their starting eight, average peak 9.7), but tiles known moved only 3.8 → 4.0
      and exploration still switches off. Measured cause: about four tiles already yield ~9
      capacity, and a clan peaking near ten people has ~7 adults to staff it, so the ground
      stays ahead of the hands. A sweep confirms neither lever closes it. Faster growth
      (`BOND_TO_BEAR` 6 → 3) buys 0.4 tiles and pushes endurance to 98%, which is worse.
      Halving terrain capacity buys 1.4 tiles and collapses survival from 94% to 62%.

      **So the diagnosis moves.** Foraging is the clan's only sink for labour, and one sink
      saturates. The fix is another thing worth spending hands on, which is sub-projects 6 to
      8 (violence, composition, the long game), not more growth and not a bigger map. The
      deferred larger map should stay deferred: more ground nobody needs helps nothing.

      **A real bug fell out of the measurement.** `WORKERS` and `CHILDREN` had been producing
      identical outcomes (93/93, 142/142 across 150 seeds) because the founding clan gives
      every household the same number of adults, so `-adults` tied everywhere and fell back to
      index order, which is exactly what `-child_count` produced. They were one function with
      two names. Each now carries a dependent-count tiebreak, and they diverge properly under
      real scarcity (89 against 73). `test_the_three_policies_are_three_different_functions`
      guards it. Suite 231 → 233.
- [x] **Slice 4: resentment with teeth (2026-08-09).** Taken out of order, ahead of slice 3,
      because slice 6 measured `households_resentful` as unreachable and three finished events
      were cut over it. The meter now moves, does something, and ends somewhere.

      **The accrual first.** Burying somebody *while another fire ate* is its own grievance and
      a heavier one than being passed over. The old rule needed the store short and the
      rationing uneven, which is why the highest any hearth ever reached was the threshold
      itself. It is charged only to a hearth that was also passed over, which keeps the
      invariant the rationing decision rests on: an even split still wrongs nobody, however
      badly the season went. A first version charged it on any death, broke exactly that, and
      the suite caught it.

      **Then two rungs.** Past `HOARDS_AT` a hearth stops waiting to be dealt a share and takes
      what it thinks it is owed first, so the player's rationing applies only to the remainder.
      Past `WALKS_OUT_AT` it is gone, with its people and a proportional share of the store,
      checked against a grudge carried in from *last* season so the player gets one season to
      answer it. Measured over 120 runs of a policy that always feeds the workers first: a
      hoarding hearth in 35 runs and a walkout in 9. A policy that splits evenly produces
      neither, ever.

      **`[event.choice.effect.household]`** is a new structured effect table, landing on the
      hearth with the longest memory. It exists because effects were clan-wide, so nothing the
      corpus offered could repair a specific grievance and resentment was a ratchet the player
      could only watch. The target is the engine's call rather than the author's, for the same
      reason the survey plan picks its own tile: a selector in the TOML is the event DSL
      `spec.md` §6 refuses.

      **Gate verdict: ships.**
      1. *A real decision every season?* **Improved, in the seasons that were already hard.**
         Rationing was the layer's only decision and it only appeared when short; now a short
         season has a consequence that outlives it, and there is a second decision (mend it or
         let it run) in the seasons after.
      2. *Slack?* Unchanged for an even-splitting player. Deliberately worse for one who keeps
         favouring the same hearths, which is the point.
      3. *Worth telling someone about?* **Yes.** "A hearth did not come to the fire this
         morning, or any morning after. Three went with them. They took 7 food. Nobody stopped
         them."

      ⚠ **Measured and left alone:** losing a hearth slightly *improves* the odds of enduring,
      because it is fewer mouths. Total survivors do not improve, but driving them off is not
      currently punished. What should punish it is the walked-out hearth turning up on the map,
      which is sub-project 4.

- [ ] **Slice 3: traits and compatibility.** The quiet meter behind who pairs with whom. Still
      not designed; see the ask in "Raised, not yet designed".

Note the constraint from `spec.md` §5: the pool comes first and names are a layer over it.
This sub-project ships **no named people**. It ships the thing they will later be drawn from.

## Sub-project 3: the chronicle (planned)

*Question: can the game run three years unattended and still feel like yours?*

- [x] `engine/chronicle.py`: typed entries, engine-side
- [x] `engine/orders.py`: standing orders and per-season orders as one type
- [x] `turn.run_until_interrupted`, with the naive threshold-based interrupt
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

> **Sub-projects 6 to 8 are the plateau fix, not garnish on a working economy.**
>
> Measured after sub-project 2 shipped: the game stops having decisions partway through
> because exploration switches itself off, and the cause is that **foraging is the clan's only
> sink for labour**. Four tiles already support more foragers than a clan of ten can staff, so
> ground stays permanently ahead of hands and scouting has nothing left to buy.
>
> A war-band is a second thing worth spending people on, and that is what makes new ground
> worth taking again. Two things follow, both load-bearing: a **bigger map does not help**, and
> **more growth does not help either**. Both were tried and measured; see `spec.md` §7 and the
> note on `STARTING_FOOD` in `balance.py`. Do not reach for either lever again.

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

## Sub-project 9: Infrastructure and Upgrades (planned)

*Question: does investing a season's surplus into a permanent upgrade or building feel earned?*

- [ ] Building infrastructure to greatly increase output (a new use for labour and resources)
- [ ] Seasonal upgrades to make the civ more powerful over time

## Sub-project 10: Races and Factions (planned)

*Question: does playing a different race make you value the map differently?*

- [ ] Races with distinct benefits and weaknesses
- [ ] Variance and replayability through asymmetric starting conditions

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

- *A larger map.* Now refused on measurement rather than sequencing; see sub-project 1.

**No longer deferred, and why:**

- *Named individual characters.* Un-parked for sub-project 5. The condition that justified
  parking them still holds and is now written into `spec.md` §5: the pool comes first,
  households are the join, names are drawn from households and never the foundation.
- *Save/load beyond a seed and a turn log.* Un-parked for sub-project 3. Correct to defer for
  a 30-minute run; a campaign that reaches tier 4 outlives a sitting.

---

## Raised, not yet designed

Brandon's asks from 2026-08-09 that have a home but no plan. Recorded so they are not lost and
not quietly built either.

- **More than two decisions in a season.** The most direct answer to an allocation that writes
  itself, and the one proposal on the table that creates a second thing to *decide* rather than
  a second thing to compute. It reopens `spec.md` §4 and every slice so far sits on the
  one-order-per-season shape, so it needs a design conversation first. **Currently the most
  promising unbuilt idea.**
- **An attraction web: compatibility meters and characteristics deciding which households
  pair.** Lands in sub-project 2 slice 3. Belongs at the household layer rather than the named
  cast, because `spec.md` §5 says a household is what marries.
- **Events that are rare *and* game-altering.** Half-answered: rarity-by-condition is in and
  demonstrated by the elder chain. What is missing is an effect vocabulary big enough for
  "game-altering" (revealing ground, granting capacity, a modifier that lasts the run). That is
  a real engine question and should be designed against `spec.md` §6's warning, not around it.

**Settled without code, for the record:** everything already randomises per new game, including
the map, terrain, and event order. `main()` and the new-run action both draw a fresh seed.

**Settled 2026-08-09, in slice 3:** the order is `Orders.scout`, not `Orders.explore`.
