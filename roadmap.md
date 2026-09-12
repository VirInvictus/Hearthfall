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

**Verdict discipline (added 2026-09-04).** SP 1 and SP 2 recorded their gate verdicts in the
slice entries; SP 3, SP 4, and SP 5 shipped on green suites without a recorded year-read, and
`FUNMETER` stops at SP 4. That debt is called out rather than papered over: the SP 3-5
verdicts are owed a single combined year-read before SP 6's first player-visible slice
(the raiders) can claim the gate, and every SP 6 slice records its verdict here when it is
run.

- [x] **The owed combined year-read (SP 3 through SP 6).** One annotated year, printed from
      the `test_playthrough.py` harness and read start to finish: allocation, forecast,
      outcome, and every event with the choice taken. Judged fun, interesting, and
      survivable. (Preparing it on 2026-09-06 is what surfaced the raid-economy finding in
      sub-project 6 below.)

      **Verdict, recorded 2026-09-06, read against v0.23.0: interesting and survivable,
      fun not yet.** The input is `audit/Hearthfall/year-read-input-2026-09-06.md` (two
      annotated runs, one carrying the full raid arc); the reading below was proposed by
      the agent and accepted by Brandon the same day. *Interesting:* yes. The raid arc is
      the best story in the game, the massing line names what is coming, and 40 percent of
      resolved raids are fought on a read that has silently gone wrong. *Survivable:* yes,
      for a player who reads the seasons and fields a wall; the naive policy at 13 of 50
      endured is the floor of brutal rather than past it, and the raid layer's costs
      (8 grain, the margin's graves) sit at bad-season weight, not burial-season weight.
      *Fun:* not yet, and the two reasons are named rather than tuned away: the mid-run
      allocation still writes itself (the plateau, still SP 8's to fix), and raids visit
      only about a third of runs, so the best new decision is rarely on stage. The named
      fix was tried the same day and **refused on measurement** (see the sub-project 6
      note): every shape of the frequency raise drove the naive run past the brutal floor
      the verdict had just recorded, so the fun gap waits on the economy, not the bands.
        *(GUT-CHECK CONFIRMED 2026-09-12 (Brandon): the verdict stands as his own.)*

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

## Sub-project 2: households (shipped)

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

- [x] **Slice 3: traits and compatibility.** The quiet meter behind who pairs with whom. Households have traits (Hearth, Iron, Wolf, Owl) and build attraction over settled seasons. Hunger strains them. Marriages are gated on this meter.

Note the constraint from `spec.md` §5: the pool comes first and names are a layer over it.
This sub-project ships **no named people**. It ships the thing they will later be drawn from.

## Sub-project 3: the chronicle (shipped)

*Question: can the game run three years unattended and still feel like yours?*

- [x] `engine/chronicle.py`: typed entries, engine-side
- [x] `engine/orders.py`: standing orders and per-season orders as one type
- [x] `turn.run_until_interrupted`, with the naive threshold-based interrupt
- [x] TUI rebuilt around the chronicle spine; `tui/app.py` is replaced, not edited
- [x] Ctrl+P command palette as the navigation surface
- [x] Glyph tiers (`ascii` / `unicode` / `nerd`), `unicode` default, palette-hosted picker,
      glyph test card, and font advisor
- [x] Responsive layout: the rail yields to the chronicle on narrow terminals
- [x] Save and load

Replacing the skin is not a regression; `spec.md` §3 promised it was throwaway-able and this
is the first time that promise is cashed. Keep the season ledger: it is the model for how a
commitment should show its arithmetic before you make it.

## Sub-project 4: neighbours and the director (shipped)

*Question: is being raided by someone you could have scouted better than being raided?*

- [x] `engine/agents.py`: neighbours, weather, and wildlife with state, needs, and intents
- [x] Peoples placed on the map, discoverable, with grain stores and moods that go stale
- [x] `engine/director.py`: pacing only, never invention
- [x] The honesty guarantee enforced in code: an intent requires a learnable fact
- [x] Interrupts that break standing orders, with the cause traceable in the chronicle
- [x] The 190-in-200 defect re-measured; the target is pressure, not a harsher winter

## Sub-project 5: the ring (shipped)

*Question: is losing an argument to your own council worse than losing to winter?*

- [x] Named cast drawn from households: traits, ambitions, relationships, ageing, death
- [x] Advisors with agendas that are wrong in characteristic ways
- [x] `engine/tiers.py`: emergence conditions and the named moment
- [x] Council decisions rendered inline in the chronicle
- [x] Corpus entries gated on ring composition and household standing

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

## Sub-project 6: violence (slices 1-5 shipped)

*Question: is losing people to a fight you misread painful in the right way?*

- [x] `engine/combat.py`: abstract single-stack resolution, your strength vs. theirs, one roll
      *(Shipped v0.14.0: `resolve()` takes our strength, theirs, and the rng; the odds
      are our share of the field and one `Rng.fraction()` draw decides. `Outcome` records
      odds, roll, and the margin — how far the draw landed from the decision boundary —
      so slice 5 grades stakes by it. Exactly one draw per fight, test-pinned. Engine-only
      slice: the standing-gate verdict accrues when the raiders make it player-visible,
      alongside the owed SP 3-5 combined read.)*
- [x] Terrain and morale modifiers
      *(Shipped v0.15.0: each side's strength is scaled by the ground it stands on
      (`balance.TERRAIN_COMBAT_WEIGHT` — hills 1.25, forest 1.10, plain 1.00,
      marsh 0.90, water 0.50) and by clan morale on a linear 0.80-1.20 band with
      parity at five. Every modifier is an optional keyword, so slice 1's calls
      are unchanged and the dumb version stays reachable. Same single draw,
      test-pinned; measured against a year-read once raiders make it visible.)*
- [x] Intel quality as a combat input; a stale fact should cost you
      *(Shipped v0.16.0: `balance.INTEL_COMBAT_FACTOR` prices the read — fresh
      1.00, aging 0.90, stale 0.80, never-scouted 0.70 — and
      `resolve(intel_staleness=...)` scales our side by it. The truth still
      wins on the numbers; this is the price of not knowing them. Slice 4
      wires the ledger's staleness into the call at raid time.)*
- [x] Raiders that hit stores; the granary as a target
      *(Shipped v0.17.0: a miserable band masses — strength drawn seeded at
      formation, `FactKind.RAIDER_STRENGTH` learned the season it masses, and
      the director holds it for `RAID_MATURITY_TURNS` (2) — then the raid
      resolves at the season boundary: `combat.resolve(militia × spears-per-
      adult, band strength, home terrain, clan morale, staleness of the read)`.
      Won: the band breaks. Lost: the granary pays `RAID_STORE_LOSS` (15,
      clamped to the store) and the clan takes a morale hit. The player
      decision is the militia count in Orders, competing with foraging for the
      same hands — the pre-committed auto-resolution from the design brief.*
      *Decision taken 2026-09-04: auto-resolution, per the brief's
      recommendation and Brandon's keep-moving directive.)*
      *(Design brief, written 2026-09-04 from a survey of `agents.py`,
      `director.py`, and `turn.py`; the surfaces all exist. **Where it hooks:**
      `IntentKind.RAID` and `Intent(target_turn, target)` already exist in
      `agents.py`, and `Director.evaluate` surfaces a mature intent as a
      `DirectorInterrupt` with a slack heuristic (food per household minus
      worst resentment: doing well draws raids sooner). The raid fires at the
      season boundary in `turn.resolve` when the director raises the RAID
      interrupt. **The player decision:** a militia count in `Orders`,
      competing with foraging for the same adults — the standing scarcity trade,
      and the "real decision every season" the gate demands. **The read:** the
      raider band's strength surfaces as a ledger fact (new `FactKind` or reuse
      of `PRESENCE` keyed on the agent id); its `Staleness` prices the fight
      through `resolve(intel_staleness=...)`, so ignoring scouting is the cost
      slice 3 already built. **The fight:**
      `combat.resolve(militia_strength, raider_strength, rng, our_ground=home
      tile terrain, our_morale=clan morale, intel_staleness=...)`. **Slice 5
      stakes:** losses graded by `Outcome.margin` — a rout costs the losers
      less than a near-run thing — with dead people via
      `Population.take_a_person`, lost `stores.food` (the granary as the
      target), and ground: a lost fight exposes frontier tiles.
      **Open for Brandon:** the raid as a pre-committed auto-resolution driven
      by the militia order (recommended: keeps spec §"resolved not micro'd")
      versus an interrupt event with fight/avoid/tribute choices. The
      recommendation keeps the allocation as the decision and the fight as
      consequence.)*
- [x] Real stakes: dead people, lost stores, ground gained
      *(Shipped v0.18.0: losses grade by the margin — `combat.raid_deaths`
      buries 1-3 of the clan (round-robin over the living hearths, children
      first via `take_a_person`, each grave a morale hit on that hearth), and
      a rout (`combat.is_rout`, |margin| >= 0.25) scatters the band far
      enough to mark its camp on the map: `ledger.reveal` at the band's
      location. Lost stores landed with slice 4. The SP 6 question is now
      answerable in play; the year-read verdict is owed alongside SP 3-5's.)*
- [x] **The band economy must be able to reach a raid (found 2026-09-06
      while preparing the owed year-read; fixed v0.19.0).** Two dead spots,
      found together. No band could get miserable inside a twenty-season run:
      bands started with 20-50 food and net one less per season, and mood only
      fell once the store was empty, so the earliest possible raid intent was
      turn 23 against a run that ends at 20. And the director never checked an
      intent's `target_turn`, so a raid landed the same season the band
      massed, on orders committed before the band existed: the promised
      window, the read aging while the player reassigns hands, had never
      opened. The raiders of slices 4 and 5 were dead content in real play,
      and only hand-built test states ever fought one.
      *(Fixed v0.19.0: the band's economy moved to `balance.py` as
      `BAND_FORAGE`/`BAND_CONSUMPTION` (8 against 10), `BAND_STARTING_FOOD`
      (15-35), and `MORALE_AFTER_RAID` (6), which spaces a repeat raid two
      years out instead of the inline 3 that made one band a siege; the
      director holds a massing band until its intent matures, and the massing
      itself is announced with the read. The raid constants were retuned for
      a raid that can recur: band strength 4-14 to 3-8, granary loss 15 to 8,
      deaths slope 6 to 4. Measured over the harness's fifty seeds: fourteen
      runs meet a resolved raid, the naive no-militia policy endures 13 of 50
      against roughly 20 before, and arming by the read wins some fights and
      pays forage for them, which is the trade SP 7 now gets to price.
      Reachability is a suite guard (`TestRaidersReachARun`), not a note.)*
**The frequency ceiling is the clan's slack: measured and refused, 2026-09-06.** The
year-read verdict named raid rarity as one of the two fun gaps and a frequency pass as the
fix. The pass was measured and refused. Raising `BAND_COUNT_RANGE` to (2, 3) lifted
contact from 14 to 19 runs in 50 but dropped the naive policy's endurance from 13 to 8;
hungrier or earlier bands (starting food 10-25, or 8-20) reached 25-28 runs contacted and
collapsed endurance to 1-6, against a suite floor of 5. Softening the per-raid costs
alongside (granary 6, deaths capped at 2) did not rescue it: 3-8 of 50 endured. The naive
run has no slack to absorb a second blow, so the frequency ceiling is set by the mid-game
economy and not by the band constants; more bands is a siege of the same wall. The count
now lives at `balance.BAND_COUNT_RANGE = (1, 2)` unchanged in behavior, so the next
attempt, once the economy gives a run somewhere to absorb the blows, is one constant
rather than a hunt.

## Sub-project 7: composition (complete, 2026-09-06)

*Question: is assembling the right stack against a read enemy the best decision in the game?*

- [x] Unit types with strengths and weaknesses
      *(Shipped v0.20.0: `data/units.toml` declares the three types of the
      coming counter-triangle (spear 2/2, bow 3/1, axe 4/1: strength then
      guard), parsed by `engine/units.py` with the event loader's strictness,
      and a `Composition` is a frozen value of counts per type. `resolve`
      grows `our_units`/`their_units` with the game's grammar attached: the
      first side is the line that holds and is weighed by its guard, the
      second is the side that presses and is weighed by its strength. That is
      what makes both numbers real in a one-draw fight: a bow wall of five
      holds at guard 5 where a spear wall of five holds at 10, and an axe
      band of three presses at 12 where spears press at 6. The spear's two
      stats are both `MILITIA_STRENGTH_PER_ADULT`, so the scalar militia and
      a spear line of the same count are the same wall and every shipped
      call prices identically. Engine-only slice: no caller ships a
      composition yet, so the standing-gate verdict accrues to slice 2,
      when assembly becomes the player's decision. 24 new tests; suite at
      361; pyright strict zero.)*
- [x] Groups assembled from types
      *(Shipped v0.21.0: the untyped militia count is the spear line it
      always was, and `Orders.militia_lines` stands other declared lines
      beside it, every hand competing for the same adults as every other
      order. The wall is priced through slice 1's grammar; a declared spear
      line adds to the untyped one rather than replacing it; an undeclared
      type fails at the top of the tick with its name in the error; and the
      chronicle names what stood ("The line: 3 spear, 2 bow."). The unit
      registry rides on `GameState` (`unit_defs`), read from
      `data/units.toml` in `new_game` and injectable like the tallies. The
      band still presses as its scalar strength, and the fight is still one
      draw.*

      *Standing-gate verdict, read over annotated years: **ships, with the
      decision half-alive.** (1) The window makes a real seasonal decision,
      but only for a clan with hands to pull: the naive policy's years one
      and two often leave a clan too small to arm when the massing comes, so
      under weak play the blow lands on nobody who could answer it. (2)
      Slack is unchanged; the granary loss is a bad season, not a burial
      one. (3) Worth telling: the massing line with its read, then the blow
      two seasons later with the line named, is the best raid beat in the
      game. Measured over 40 seeds, a policy that reserves its wall from the
      forage line before filling it armed in 9 of 40 runs, endured 13 of 40
      against the naive policy's 10, survivors 38 against 23. The
      composition choice itself is dormant in favor of spears until the
      counter-web prices a bow line against what it counters; that is slice
      3's debt, named here so it does not pass silently.)*
- [x] The counter-web that makes composition a puzzle
      *(Shipped v0.22.0: `counters` on the unit table, one direction per
      pair, three in a cycle: spear closes on bow, bow breaks the axe rush,
      axe comes apart the wall. When my type counters what it faces, my
      side's number carries `COUNTER_BONUS` (1.5) scaled by the countered
      share of the enemy; the countered side gets nothing, which is what
      makes the mix worth reading. Bands muster a mix now too: bodies drawn
      by `band_weight` (spear 1, bow 2, axe 2: raiders travel with fighters),
      pressed as what the mix totals, announced in the massing line ("2 bow,
      1 axe. The read says 10 spears."), and resolved against the wall's
      composition. Hand-built scalar bands still fight the old way, and the
      fight stays one draw.*

      *Standing-gate verdict: **ships, with the payoff narrow and the lever
      named.** In the pure matchup the read is worth a lot: a bow wall
      against a pure-axe band holds at 0.38 odds where the spear wall,
      countered by those same axes, holds at 0.17. In mixed bands the bonus
      dilutes toward noise, and bands of one to three bodies are usually
      mixed, so measured over 150 seeds the crude counter-reading policy
      only edges the spear default in the engagements that matter (4
      repelled to 3, against axe-carrying bands, walls armed). That is the
      honest shape of a puzzle whose pieces are this small: real, legible,
      sharp at the edges, rare in the middle. The levers if Brandon wants it
      louder: `COUNTER_BONUS`, the band weights, and `BAND_SIZE_RANGE`. 12
      new tests; suite at 377; pyright strict zero.)*
- [x] Scout intel driving pre-battle assembly
      *(Shipped v0.23.0: the read became a proper fact loop. A massing band
      learns its strength and its mix into the ledger (`RAIDER_COMPOSITION`,
      halflife 2, faster than its size: bodies come and go behind the
      border); while it waits, `RAID_RESHUFFLE_CHANCE` (0.3 a season)
      reinforces it in silence, so the held read goes wrong without a
      word; and a scouting party that walks or surveys the camp refreshes
      both reads and says what it saw when the mix has changed ("The
      Ashen Clan's camp has changed: 2 axe now, where the read said 1 axe,
      1 bow."). The fight prices the strength read through the staleness
      bands as before; the mix read is priced by the web itself, the wall
      you aimed at what you believed. The raid note carries the read and
      the odds on a win as well as a loss.)*

      *Standing-gate verdict: **ships.** The loop closes end to end: the
      massing tells you once, the camp lies to you after that, and walking
      out to look is the only thing that un-lies it. Measured over 80 seeds
      of the naive policy: 30 raids resolved and 12 of them (40 percent)
      were fought on a mix read that had silently gone wrong, which is the
      exact shape of "you positioned for the enemy you read about, not the
      one across the field". The cost side is real too: re-reading a camp
      is a party out for a season, gated by geography (the camp must be
      reachable ground), so the informed wall is a paid wall. SP 7's
      question is now answerable in play, and the answer is waiting on
      Brandon's year-read alongside the others. 4 new tests; suite at 381;
      pyright strict zero.)*

*(SP 7 complete: the four boxes shipped as v0.20.0 through v0.23.0 on
2026-09-06. The sub-project's question, "is assembling the right stack
against a read enemy the best decision in the game?", is answerable in
play: the read exists, it ages, it lies, and the wall is yours to aim.)*

## Sub-project 8: the long game (slice 1 shipped)

*Doctrine, borders, attrition, the endgame. The campaign arc: runs long enough that the
thing being managed is a people rather than a household.*

> **Proposed shape, 2026-09-06: unsigned, riding the SP 9/10 triage conversation, and
> therefore not commitments.** Candidate boxes for whenever this front opens, in the order
> the research says they should come:
>
> 1. **Rivals: the walked-out hearth returns.** The oldest promise in the repo still
>    standing: sub-project 2 slice 4 measured that driving a hearth off is unpunished and
>    named the fix ("the walked-out hearth turning up on the map"), and `_leave`'s
>    docstring still promises the second half. Nothing was built; the neighbours on the
>    map are procedurally named strangers. Everything a rival needs now exists: agents
>    carry food, mood, location, and since sub-project 7 a unit mix and a readable
>    strength; the hearth leaves carrying its grudge; the raid and intel layers price the
>    reunion. This is the most grounded candidate in the repo: it closes a measured debt,
>    reuses three shipped systems, and invents no new fiction.
> 2. **Doctrine: the run's choices harden into a people's character.** Grounded in what
>    tallies already are: a persistent, choice-written memory that content reads. Doctrine
>    is named moments and epilogue prose gated on those tallies, corpus-first and
>    engine-light: what the clan was in year one is what its people are in year five.
> 3. **The arc: runs past twenty seasons.** Deliberately last, because the measurements
>    argue against it until something changes: the plateau means a long run auto-pilots
>    through its middle, and the frequency refusal showed the naive run cannot absorb more
>    pressure. The extra-decision brief (surplus into permanence) is the candidate that
>    gives a long run a middle; ENDURED and BURIED would need era milestones rather than a
>    longer clock.
>
> Riding along from the retired sub-project 9, as candidates for whichever front opens
> first: research progressed by processing scouted facts, and buildings as a spent,
> permanent sink (their warning stands: nothing passive, or scarcity dies).

- [x] The works: surplus raised into permanence
      *(Shipped v0.26.0, applying the extra-decision brief under the
      keep-moving directive. `Orders.work` is a labour line like any other;
      what the hands raise is the ladder's next entry, the engine's call
      (`balance.WORKS`: palisade, smokehouse, shrine), each spent once and
      modest forever - 6 grain the next raid does not carry off, half a
      tender's worth of rot trimmed every season, one point of standing
      cheer. Completions are announced; a finished ladder says so; and the
      works read into `snapshot()` as three flat keys. The spoil arithmetic
      moved into `_spoil_rate` so the forecast cannot drift from the rule.*

      *Standing-gate verdict: **ships.** Gate-read over 50 seeds: a builder
      policy (two hands on the works whenever the store is healthy) finishes
      two works a run, endures 14 of 50 against the naive 11, and cuts what
      raiders carry off - the decision is paid for in forage hands, in
      exactly the prosperous seasons where the allocation used to write
      itself. 9 new tests; suite at 403; pyright strict zero.)*

**The arc: measured and refused, 2026-09-06.** The signed order put the arc
last and conditional on the economy, and the precondition was tested rather
than assumed: with the works shipped, `TURNS_PER_RUN` was measured at 28
seasons against the shipped 20. Every activity signal got better and the
game got worse: raids rose from 16 to 27 per 50 runs under the naive
policy, works were built, doctrine forks fired - and endurance fell from 11
to 5 of 50, with the builder policy at 3 of 50, below the suite floor, and
survivors from 28 to 11. Twenty-eight seasons is not a longer game; it is a
longer death, because the clan economy cannot feed the extra winters at
current yields, and that is the shape problem the `STARTING_FOOD` note
records, not a magnitude a constant can move. The arc stays refused until a
dedicated economy campaign re-tunes yields, winters, and band pressure
together; the pieces it will need - the works, doctrine, the rivals - are
all shipped and waiting for it.
  *(OPENED 2026-09-12 (Brandon): the economy re-tune campaign is a go; the next Hearthfall lane files its boxes, runs the coordinated re-tune through the 50-seed gate-read harness, and brings targets back for approval before any ship verdict.)*

- [x] Doctrine: the run's choices harden into character
      *(Shipped v0.25.0. The corpus gains the doctrine fork
      (`data/events/doctrine.toml`): after the graves have started, the clan
      is asked once what it is - keep people, or keep ground - and the
      answer is the `doctrine` tally, which nothing shows and only the
      ending reads. The payoffs are years later, gated on the choice plus
      the thing the choice was about: kept people meets kin of the fed
      strangers at the crossings; kept ground finds the marked stones have
      held. And the run's last entry is assembled from the tallies
      (`reports.epilogue_lines`): doctrine first, then the burying ground,
      the fed strangers, the hungry winters, the inherited debts, the elder
      who no longer argues, and the walked-out hearths, each line earned.*

      *Standing-gate verdict: **ships.** Gate-read in real play: the fork
      lands mid-run and the ending reads differently clan to clan ("Five
      winters. The fire is still lit. / They were, by the end, the clan
      that kept ground. / There are steads that owe the clan grain, and the
      debt is inherited."). Prose and small payoffs only, so the economy is
      untouched. The liveness guard earned its keep again: the kept-ground
      payoff was unreachable by construction of the policy ladder - doctrine
      2 needs a choice-1 run, surveys happen on surveying policies, and the
      spread never combined the two - and the fix was extending the ladder
      (surveying runs now answer both ways) rather than loosening the
      content. 6 new tests; suite at 394; pyright strict zero.)*

- [x] Rivals: the walked-out hearth returns
      *(Shipped v0.24.0: both halves of the promise live in `_leave` now.
      The hearth that walks out camps in the dark as an ordinary band — id
      `rival_N`, named by its trait ("the Ironkin Clan"), holding the food
      it took and the mood it left in, camped on the nearest ground that is
      not the hearth and not water, and no random draw spent at creation.
      From there nothing is special-cased: the band economy starves it, the
      SP 7 muster gives it a mix, the massing is announced, and the fight is
      priced by the web and the read. The chronicle line lands with the
      walkout: "They are raising a fire of their own. The Ironkin Clan is
      camped in the dark, and it knows what it is owed."*

      *Standing-gate verdict: **ships, as a story weight rather than a
      balance weight.** Walkouts happen in 9 of 120 runs under the harshest
      rationing the game offers, and paired runs over those nine seeds count
      7 survivors with rivals against 6 without: the punishment is legible,
      not yet punishing, because a hearth that starved out of the clan
      leaves weak and the calibrated band costs cap what any one band can
      do. That is the correct shape for a slice whose job was closing the
      promise, and the lever if the grudge should weigh more is the rival's
      starting food and mood, not new rules. Read in real play: walkout at
      turn six, massing at eleven with a mixed band, the blow at fourteen;
      the clan that buried the hearth met it again across the granary. 6
      new tests; suite at 388; pyright strict zero.)*
>
> **Signed 2026-09-06, Brandon:** the order below is the plan. Rivals first, doctrine
> second, the arc last (and only when the economy can carry it). The candidates ride with
> the retired sub-project 9's survivors: research progressed by processing scouted facts,
> and buildings as a spent, permanent sink (their warning stands: nothing passive, or
> scarcity dies).

## Sub-projects 9 and 10: retired 2026-09-06, the ideas triaged

These two sections stood as planned boxes since August without ever entering `spec.md` §7's
list, and the ten-versus-eight drift has been resolved against them: the count is eight.
Where each idea went:

- **The grimdark endgame** (attrition, hard borders, a people that endures or is buried)
  folds into sub-project 8, where the same clause already lived.
- **Research Integration** (tech progression driven by the fact ledger, processed by
  educational buildings) and **buildings as a permanent sink for surplus** ride
  sub-project 8's design conversation as candidates. Research is the strongest idea either
  section had: it makes paying to look the prerequisite for progress, which is `spec.md` §1.
  Buildings carry a warning: *passive baseline resources* would delete scarcity, and
  scarcity is the game.
- **Seasonal upgrades** were too vague to keep as a commitment; folded into the buildings
  candidate.
- **The Calendar Flow** is sub-project 3, shipped: standing orders and
  `run_until_interrupted` are exactly the time compression it asked for.
- **Races, asymmetric starts, and the macro transition** move to "Raised, not yet designed"
  below: real ideas for the game after sub-project 8's game, parked so they stop asking.

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

  **Design brief, drafted 2026-09-06: a proposal to be designed, not a decision.** The
  strongest shape merges this ask with the retired sub-project 9's best idea: **spending
  surplus into permanence.** A labour order (hands, or hands and goods, committed for the
  season) that works toward a permanent, modest improvement: a palisade that prices the
  next raid's granary loss down, a smokehouse that trims spoilage, a shrine that steadies
  morale. What it buys: prosperous seasons get a real allocation choice, which is exactly
  when the game currently stops asking, and the effect is *spent* rather than passive, so
  scarcity is not deleted. The invariants a design must keep: a full store never makes the
  choice irrelevant, because there is always a next thing worth building; the condition
  evaluator does not grow (an improvement is one `snapshot()` key, the way
  `forage_capacity` is); the TUI gains no new screen, because a work order is a labour
  line (`spec.md` §9.9); and the band economy is tuned against whatever the palisade
  multiplies, or raids stop mattering. Open questions for the conversation: which three
  improvements earn their place, what they cost in hands against the forage trade, whether
  a raid can burn what was built (the grimdark answer is probably yes, and it makes the
  decision seasonal instead of ratcheting), and whether improvements belong to the clan or
  to a hearth (household ownership would feed the resentment layer).
- **An attraction web: compatibility meters and characteristics deciding which households
  pair.** Lands in sub-project 2 slice 3. Belongs at the household layer rather than the named
  cast, because `spec.md` §5 says a household is what marries. *(Landed there: traits,
  `TRAIT_COMPATIBILITY`, and the attraction meters shipped with sub-project 2 slice 3,
  v0.11.0.)*
- **Events that are rare *and* game-altering.** Half-answered: rarity-by-condition is in and
  demonstrated by the elder chain. What is missing is an effect vocabulary big enough for
  "game-altering" (revealing ground, granting capacity, a modifier that lasts the run). That is
  a real engine question and should be designed against `spec.md` §6's warning, not around it.

  **Design brief, drafted 2026-09-06: a proposal to be designed, not a decision.** The
  finding from walking the engine: every "game-altering" shape already has an in-engine
  precedent, so the vocabulary costs one structured effect table each and the evaluator
  never grows. Three shapes, in the order they should be built:

  1. **Revealing ground.** Precedent: a rout's flight already marks the band's camp on the
     map (`ledger.reveal` in `turn._raid`). Effect: `[event.effect.reveal]` with a count
     (`tiles = 2`); the engine picks which frontier tiles, ranked the way `survey_plan`
     ranks ground, because a target named in the TOML is the selector the spec refuses.
     The corpus story writes itself: floods cut paths, refugees describe vales, a dying
     man trades what he saw.
  2. **Granting capacity.** Precedent: `forage_capacity` is already cached on the state
     and already a snapshot key; the grant is one state counter that `_refresh_ground`
     adds in, written by `[event.effect.improvement]` as a named pair (`clearings = 1`).
     Readable back by content through that one key. Improvements are named in code and
     never selected in TOML, which is the same rule the household effect already lives by.
  3. **A modifier that lasts the run.** The honest home for "the granary wall held" is a
     *charge*: a state counter that a rule reads and spends. The raid path would halve its
     granary take once and decrement; what remains is visible in the snapshot. Effects
     write charges as structured pairs. What is deliberately out: timed modifiers ("for
     the next four seasons"), because a timer is a hidden state machine the corpus cannot
     see and the chronicle cannot render; a charge is spent or it endures, and both are
     legible.

  Rarity stays condition-based, per the elder chain. A worked sketch to prove the corpus
  is ready: "the mason of the fallen stead", gated on `hearths_walked_out > 0` and
  `tally_graves > 2` (both keys exist today), offers the granary wall at a cost in food;
  the refusal branches through a tally, and somewhere years later a band finds the
  granary unguarded. Nothing in the sketch needs a new grammar.
- **Peoples with distinct doctrines and asymmetric starts.** From the retired sub-project 10.
  A different people should make the map worth reading differently. It needs the long game
  first: doctrine without a campaign to express it is a menu.
- **The macro transition: retiring manual allocation for population-wide assignment at
  scale.** `spec.md` §9.9 done right, and only reachable once there is a scale to abstract.
- **Research driven by processed facts, and buildings as a spent, permanent sink.** The
  surviving candidates from the retired sub-project 9. They ride sub-project 8's design
  conversation: research makes paying to look the prerequisite for progress; buildings must
  never yield passively, or they delete scarcity.

**Settled without code, for the record:** everything already randomises per new game, including
the map, terrain, and event order. `main()` and the new-run action both draw a fresh seed.

**Settled 2026-08-09, in slice 3:** the order is `Orders.scout`, not `Orders.explore`.
