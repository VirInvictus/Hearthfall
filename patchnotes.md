# Patch notes

## v0.10.0 (2026-08-09)

**A hearth you keep feeding last will eventually stop being yours.** Resentment has been in the
game since v0.4.0 as a number nothing read; it now accrues where it could not before, changes
how food is divided, and past the last rung takes its people and walks out.

- **Burying somebody while another fire ate is its own grievance**, heavier than merely being
  passed over. That is the accrual that was missing: the old rule needed the store to be short
  *and* the player to have rationed unevenly, so measured across sixty runs the highest any
  hearth ever reached was the threshold itself.
- **Past `HOARDS_AT` a hearth stops waiting to be dealt a share** and takes what it thinks it is
  owed before anything is divided. Your rationing then applies only to what is left, so the
  decision narrows exactly in the season a short store made it matter.
- **Past `WALKS_OUT_AT` they are gone**, with their people and a proportional share of the
  store. The check runs on a grudge carried in from last season, so the season before is your
  chance to answer it.
- **An event can now mend one hearth's grudge.** `[event.choice.effect.household]` is a new
  structured effect table that lands on the hearth with the longest memory. Without it, effects
  were clan-wide and resentment was a one-way ratchet the player could only watch.

Four new corpus entries key on it, including the offer to sit with them and hear the whole list.
Measured over 120 runs of a policy that always feeds the workers first: a hoarding hearth in 35
runs and a walkout in 9. A policy that splits evenly still produces neither, ever, which is the
invariant the whole rationing decision rests on: everyone going short together wrongs nobody.

**One design catch worth recording.** The first version of the accrual charged resentment on
any starvation death, which quietly made an even split breed grudges and stopped `EQUAL` being a
real option. The suite caught it. It is now charged only to a hearth that was *also* passed over.

**And one measured wrinkle left alone:** losing a hearth slightly improves the clan's odds of
enduring, because it is fewer mouths. Total survivors do not improve, but "drive them off on
purpose" is not currently punished. The thing that should punish it is the walked-out hearth
turning up on the map as a neighbour, which is sub-project 4. Suite 294 to 303 tests.

## v0.9.0 (2026-08-09)

**The corpus went from 34 events to 82**, which is the thing the roadmap calls the actual
project. Five new files, written against vocabulary that did not exist when the old ones were:

- **`ground.toml`** is the second and third look at each terrain, gated on seasons and on how
  much the clan has worked out rather than on a scout coming home. A wood in winter, deadfall
  worth a hungry week, a charcoal pit somebody dug and abandoned, what the peat gives up.
- **`fog.toml`** is keyed on the intel layer: hands with nowhere to work, numbers nobody has
  checked in years, the map in the dirt becoming a map of what the clan *has*.
- **`hearths.toml`** is the household layer showing up outside the rationing prompt.
- **`hunger.toml`** carries the `hungry_winters` tally, read years later.
- **`debts.toml`** and **`dead.toml`** run three chains on tallies: generosity that is
  occasionally and unreliably repaid, ground given up out of caution, and the clan's own dead.
  Two new tallies, `strangers_taken_in` and `graves`.

**Three entries were cut rather than shipped, and the reason is the most useful thing here.**
All three were gated on `households_resentful`, and that key is not reachable content today:
across sixty runs of the harshest rationing the game offers, 142 seasons ran short and 138
household-seasons were wronged, and the highest resentment any hearth ever reached was exactly
the threshold, at the very end of runs. Lowering the threshold bought a window so narrow that
removing one of the three made another stop firing. They come back when sub-project 2 slice 4
gives resentment teeth.

**The reachability guard earned its place twice over.** It caught a condition on
`terrain_home == hills` that could never be true, because the hearth is always placed on plain,
and it caught that the test's own policy ladder predated slice 3: nothing in it ever sent a
third scout or rationed unevenly, so a whole file of content was unreachable by construction of
the harness rather than by anything wrong with the content. The ladder now includes surveying,
watchful and unequal-rationing policies.

**`EVENT_COOLDOWN` stays at 16, against the roadmap's own instruction to lower it.** Tripling
the corpus did help at a fixed cooldown (9 runs in 60 replaying an event, down to 3), but
lowering the cooldown is worse at 82 events than 16 was at 34. Repetition is governed by how
many entries are *eligible at once*, not by how many exist.

**One thing this slice made worse and did not fix:** every season now carries an event, where
it used to be about nine in ten. A quiet season no longer exists, and the fix belongs to the
director in sub-project 4 rather than to a number here.

## v0.8.0 (2026-08-09)

**The ground stopped holding still, and the clan's picture of it can now be wrong.** Until now
the fact ledger could only be *out of date* in principle: nothing in the world ever moved, so
belief and truth always agreed and the whole spine was a promise rather than a mechanic.

- **Ground the clan leans on thins out, and ground it rests comes back.** A tile carries all
  but its last hand forever; the last one is borrowed against next year.
- **A survey records how rich a place was the season it was made.** The ground goes on being
  worked afterwards and that number does not follow it, so a clan living off a wood for four
  years without sending anyone back is planning its seasons on how good that wood used to be.
- **The season ledger is now the clan's expectation rather than a guarantee**, and the gap
  shows up as prose: "The forest to the west gave 3 less than it should have. It is not the
  ground the clan remembers."
- **A party out looks over the clan's own ground as well as the dark.** That single rule is
  what makes this a decision instead of a tax, and it was measured: without it a clan that
  scouted every season was disappointed 6.7 times a run and one that never scouted 7.0, because
  a party can look at one tile while the clan works five. With it, keeping a party out in
  winter costs 161 food to stale numbers across thirty seeds against 403 for letting the
  picture rot.

**Two designs were built, measured, and thrown away before this one.** Wear first took a tile's
*capacity*, which does nothing at all: this clan is hands-limited, so a tile losing a forager it
never had the people to send is free, and a clan that stopped scouting ended a run half a person
behind one that never stopped. Wear also first healed only tiles nobody touched, which has no
equilibrium: anything worked every season accrues forever, and the clan's best forest fell to
the floor inside a year. The healing allowance also has to scale with the tile, because a flat
one-hand allowance is exactly what a clan that only walks ground puts on a tile, and depletion
became a tax on surveying alone that flattened v0.6.0's gradient from 4.8-against-3.1 survivors
to 2.5-against-2.4.

`stale_surveys` is the first staleness key content can read, the allocation panel warns when the
numbers above it are memories, and `FACT_HALFLIFE[FORAGE]` finally means something. The economy
is about 20% tighter than v0.7.0 (a season-reading policy ends with 7.1 people against 7.6, and
endures 110 runs in 120), which is the price of ground that can be spent. Suite 278 to 294 tests.

## v0.7.0 (2026-08-09)

**The scouts came back with something to say.** `spec.md` §1 says a report is rendered facts,
and until now the two sentences a party produced were f-strings buried inside the steps that
moved the state. They are a module, `engine/reports.py`, and the party speaks once, at the end,
in one voice.

- **The walk names where and what:** "The scouts walked north into marsh."
- **And what it is worth, when that is worth saying.** The best ground the clan has found says
  so; so does ground poorer than anything it already holds, and water that will feed nobody. A
  middling tile among middling tiles gets no verdict at all, because a line that fires every
  season is a line the player stops reading. Measured across sixty runs: 6.4 walks a run and
  2.2 verdicts.
- **The survey reads as one visit or two,** depending on whether the party stopped where it
  walked or gave its proper look to ground the clan already knew. That second case used to
  read as a non sequitur.
- Numbers in prose are words. "Three can work it" is a sentence; "3 can work it" is a readout
  that happens to be in a paragraph.

**A family of lines counting the ways still open into the dark was written, measured, and
deleted.** A clan walks six to ten tiles of twenty-five, so the frontier never narrows and
every one of those sentences fired exactly zero times in sixty runs. What survives is the one
case that can happen: a party sent out to a closed frontier says so, rather than costing hands
and reporting silence.

`TurnReport.learned` now carries the facts themselves alongside the prose, so a second frontend
can render its own sentences, and `Ledger.learn` returns what it stored. No mechanic changed:
the same 200 seeds end with the same survivors, which is the point of a slice that is about
voice. Suite 255 to 278 tests.

## v0.6.0 (2026-08-09)

**Scouts became a gradient.** How many you send now decides what they come back with, instead
of two being the price of a tile and every hand past that being wasted.

- **Two scouts walk.** They go into the dark and learn what the ground is, and the clan can
  work that ground thinly: one forager, at the tile's full yield.
- **Three scouts also survey.** The party stops somewhere and works out what the place will
  actually feed, which lifts that tile to the whole crew its terrain will carry. A forest is
  worth one hand walked and three surveyed.
- **Which tile gets surveyed is the engine's call, not a new order.** The party looks at the
  best ground the clan knows of and has never worked out, usually but not always the tile it
  just walked into. Orders stay scalar and the engine places the work, exactly as it places
  foragers. A survey that would raise nothing is not made, and the report says so rather than
  logging a survey that moved no number.

Measured over 200 seeds, the third scout used to be worth *less* than nothing (5.8 survivors
against 6.2 for a policy that never sent it). It is now worth 4.9 against 3.1. `WALKED_CAPACITY`
is the number the whole slice rides on and it was chosen by sweeping it: at 0 a walking party
is useless (14 runs in 200 endured) and the cliff has merely moved to three scouts; at 2 only a
forest gains anything from a survey and the gap collapses to 5.2 against 5.6.

**What it does not do is fix the plateau.** Parties still stop going out once the ground is
ahead of the hands, in the same 5.9 seasons of 20 as before. That was expected: the fix is a
second thing worth spending people on, which is sub-projects 6 to 8.

**`Orders.explore` is now `Orders.scout`**, settled while the code was already open. The spec
and every design conversation said scout; only the code said explore. The key binding moves
from `e` to `s` with it.

Also: the map fades ground that has been walked but never surveyed, and the panel under it
prices the party before you commit, naming the tile it would survey and the hands that would
buy. Both rungs are visible before the season is spent, which is the season ledger's idiom
applied to the fog. Suite 238 to 255 tests.

## v0.5.1 (2026-08-09)

Six defects found by playing the game rather than by testing it.

- **The starvation warning was being cut off.** "4 would starve" and the rationing prompt are
  the last two lines of the season ledger, and on a short terminal they fell below the fold, so
  a player about to lose four people saw only the store going to zero. The verdict now comes
  *above* the arithmetic, where it cannot be clipped, and the column scrolls as a safety net.
- **Households were invisible.** The layer that starves, resents, and bears children had no
  representation on screen at all, which made rationing a choice about people you could not
  see. The status panel now shows each hearth's size and mood. Resentment stays hidden, because
  a meter you can watch is a meter you optimise against.
- **"Every hand assigned" was rendered in the danger colour**, so a good state read as a
  warning. The CSS class was painting the whole widget red regardless of what it said.
- **Every run repeated an event verbatim.** All sixty runs in a sample did, and the worst
  offender came round an extra forty-nine times across them. Repeatable events now sit out a
  cooldown before they can fire again, which takes it to nine runs in sixty with no loss of
  event density. The real fix is a larger corpus; this stops the thinness being loud.
- **The clan bore children in batches.** All three hearths started level, so they reached the
  bond target on the same season and the chronicle read "3 children were born to the clan",
  which is a batch job rather than three things that happened. The founding bond is staggered,
  and single births went from a minority to 151 of 174 birth seasons.
- **The map legend wrapped mid-item** in the 52-column panel, breaking between "%" and "marsh"
  so it read as a layout bug. Two deliberate lines instead of one accidental one.

Also fixed a trap in the cooldown's own implementation: `xs[-0:]` is the whole list, not the
empty one, so a cooldown of zero would have silently meant "never repeat, ever". Suite 234 to
238 tests.

## v0.5.0 (2026-08-09)

The clan can grow, and how you fed it decides whether it does.

- **Households bear children on a schedule they earn.** A hearth with two adults, a decent
  mood, and a fed season builds a silent meter; when it comes due, a child is born. A hungry
  season knocks the meter back, so a famine costs years of growth rather than a turn of it.
- **No dice.** The old rule gave the clan forty food and decent morale and then rolled. It
  asked about the clan as a whole, which is a question about nobody, and it came back yes so
  rarely that across a full run the clan never grew at all. A schedule instead of a lottery is
  what ties growth to the rationing decision: the hearth you feed last is the hearth that
  stops growing.
- **Hearths that outgrow themselves split**, which is how three kin groups start heading
  toward the ten to forty the design wants, and every new hearth is somewhere a grievance can
  live that was not there before.
- **Fixed: "feed the workers" and "feed the children" were the same function.** The founding
  clan gives every household the same number of adults, so ordering by adults tied everywhere
  and fell back to list order, which is exactly what ordering by children produced. Measured
  across 150 seeds the two were indistinguishable. Each now breaks ties on dependents, and
  under real scarcity they diverge properly (89 runs survived against 73).
- Suite 231 to 233 tests.

**The plateau is not fixed, and the diagnosis has moved.** Clans now grow (65 runs in 120 rise
above their starting eight), but exploration still switches itself off, because four tiles
already support more foragers than a clan of ten can staff. A sweep says neither obvious lever
closes it: faster growth pushes survival to 98%, and halving what ground yields collapses it to
62%. The real cause is that foraging is the only thing worth spending hands on, and one sink
saturates. What is needed is another use for people, not more people.

## v0.4.0 (2026-08-09)

A famine now lands on somebody.

- **Households.** The clan is dealt into kin groups, and a kin group is what starves, what
  resents, and later what marries and feuds. A clan of eight going three short used to lose
  one person and a point of morale, which is a number moving. The same shortfall now takes a
  child *from a hearth*, and that hearth remembers.
- **The pool moved rather than gained a neighbour.** `adults`, `child_count`, `total` and
  `morale` all still answer, and all four are now derived from the households, so there is one
  source of truth and nothing can drift. Morale is the average of the living households, which
  is why the shipped corpus needed no changes at all.
- **Rationing is a decision you make when the store is short.** Equal shares, the workers
  first, or the children first. There is deliberately no right answer. Measured over 120
  seeds, an even split is *worse* for survival, because spreading a shortfall pushes every
  hearth into the starvation threshold at once, but it wrongs nobody. Concentrating the food
  saves people and creates a household that was fed last and knows it.
- **Being wronged is not the same as being hungry.** Everyone going short together breeds no
  resentment. Watching another hearth eat does. That distinction is what keeps equal shares a
  real option rather than the safe one.
- The forecast accounts for rationing, so the projected deaths change as you choose. A
  forecast that averaged it away would be silent about the one thing being decided.
- `snapshot()` gains `households`, `worst_household_mood` and `households_resentful`. Two
  clans averaging five morale are not the same clan if one of them has a hearth at zero.
- The game is less safe: a scouting policy fell from 99% of seeds survived to 93%, because
  famine now concentrates instead of averaging.
- Suite 205 to 231 tests.

**Known, and recorded rather than papered over.** In competent play none of this shows up. The
rationing prompt never appeared across eight seasons of a well-played run, because a good
player is rarely short, and the three households stayed identical for the same reason. Both
the new decision and the new structure are currently invisible unless things are already going
wrong. Households need reasons to diverge that are not famine, which is what the next slices
are for.

## v0.3.0 (2026-08-09)

The clan remembers what you did.

- **Tallies.** One integer, persisting for the whole run, written by an event effect and read
  by an event condition as `tally_<name>`. It is a small addition and it is what turns a
  corpus into something with a memory: a slight in year one can be the condition on a
  reckoning in year four.
- **Chains gate on the answer, not on the event.** Because a tally is written by a *choice*,
  a later event can require not merely that something happened but that you handled it a
  particular way. A chain gated on which events had fired could only ever ask the first
  question.
- **The condition evaluator did not grow by a single line.** It is still `key op value`,
  AND-ed, exactly as `spec.md` §6 insists. Every new question a tally makes askable is
  precomputed into `snapshot()` instead, which is the rule that lets a fifty-line evaluator
  survive households and neighbours later.
- **Every tally is declared in `data/tallies.toml`, and declaring it is what makes it exist.**
  Effects validate names against the same reference snapshot conditions already use, so an
  effect writing `tally.elder_resentmnt` fails when the corpus loads rather than incrementing
  a counter nothing will ever read. Content that looks authored but does nothing is
  indistinguishable from content that needs rewriting, and this corpus is heading for
  hundreds of entries.
- **The elder chain ships as the worked example.** Four events over several years. Overrule
  him early and it runs toward a man who stops arguing and starts arranging; defer, at a cost
  you pay that evening, and it runs somewhere else entirely.
- **Rarity comes from conditions, not from a weight lottery.** The powerful entry in that
  chain is rare because reaching resentment above five takes a run's worth of choices. A
  payoff you earned reads as a consequence; a payoff you rolled reads as noise.
- Tallies never fall below zero. A negative grudge is not forgiveness, it is an event with the
  sign wrong.
- Suite 190 to 205 tests.

## v0.2.0 (2026-08-09)

Ground you have walked is ground you can work.

- **Exploring finally pays.** Every known tile now carries a per-terrain yield and a forager
  capacity, and hands beyond the capacity of revealed ground bring back nothing. Before this,
  a forager was worth the same whether the clan had walked the ground or not, so the fog was
  scenery and scouting was a hand thrown away.
- **Measured over 200 seeds:** a clan that never scouts ends with 1.4 people, one that scouts
  while the map is the binding constraint ends with 6.5, one that also reads winter ends with
  7.8. Sub-project 1's kill-switch question ("does paying to look pull the player forward?")
  answers yes, and a test now asserts it rather than a roadmap note claiming it.
- **Terrain multiplies the season rather than adding to it**, so winter's zero stays zero on
  every terrain with no special case. An additive bonus would have made good ground foragable
  in winter and quietly deleted that season's whole allocation puzzle.
- **Water is dead ground**, yielding nothing and supporting nobody, which keeps a reveal a
  gamble instead of a ratchet.
- **The engine places foragers, best ground first.** Orders stay scalar and the map stays a
  knowledge surface rather than becoming a placement surface (`spec.md` §9.9). The season
  report names where they worked.
- **The allocation shows its ceiling before you commit to it.** "Ground known holds 4 · 2
  idle" sits above the food ledger. A mechanic the player cannot see is not a decision.
- Foraging reads terrain from the fact ledger and never from the world, so the clan works the
  ground it *believes* is there. The two agree today; slice 5 exists to make them disagree.
- `snapshot()` gains `forage_capacity` and `hands_without_ground`, so content can fire on a
  clan with more hands than ground. The condition evaluator is unchanged, as always.
- Suite 169 to 189 tests.

**Known, recorded, not yet fixed.** A playtest of a full run says the game plateaus: from year
two onward the allocation is identical every season, and exploration switches itself off once
capacity exceeds the hands available. `roadmap.md` carries the detail under the standing gate.

## v0.1.2 (2026-08-09)

No gameplay change. The language question got asked properly and the answer got enforced.

- **Python is confirmed as the language, on the record, against Rust.** `spec.md` §8 carries
  the reasoning: a full playthrough measures ~0.5 ms, so neither gameplay performance nor
  balance-sweep throughput is a constraint, and the risk this project actually carries is a
  corpus that never gets written. Re-opening it was legitimate rather than second-guessing,
  because the port is cheapest now and gets dearer every sub-project.
- **What Rust would have bought is bought directly instead.** Pyright runs in strict mode over
  `engine/` and gates the whole tree in CI, at **0 errors**. Every engine dataclass is
  `slots=True`, frozen where it is a value type, which closes off accidental attribute
  aliasing on the mutable state graph.
- **The TOML boundary in `events/loader.py` is now typed end to end.** It was the source of 37
  of the 53 strict findings, all of them `Unknown` leaking out of `tomllib` and spreading into
  every validation rule. Two narrowing helpers confine the casts to one place, so the parse
  rules read as being about content again. This is the highest-value half of the change: the
  loader is where malformed content meets the engine, and its entire job is catching it.
- **Fixed a silent local/CI split.** CI pinned `ruff==0.15.20` while a newer local ruff had
  widened its default rule set, so `ruff check` failed on a tree CI called clean (two findings
  predating this work). `ruff` and `pyright` are now dependency-group entries resolved through
  the committed lockfile, so local and CI run the same binaries by construction.
- `hypothesis` and `textual-dev` added as dev-only dependencies. Neither is imported by the
  engine, the skin, or the shipped wheel; the engine remains dependency-free, and
  `test_architecture` still enforces it.
- `tests/support.py` adds `not_none` and `an_int`, because `assertIsNotNone` does not narrow a
  type and `snapshot()` values are deliberately `int | str`.

## v0.1.1 (2026-08-08)

The allocation stops being a guess.

- **A season ledger sits under the allocation and moves as you assign.** Foragers
  bring, mouths eat, rot takes, and the store goes from one number to another with
  the net beside it. Until now you committed three foragers and found out
  afterwards whether that fed anyone, which made the central decision of the game
  something you could only learn by losing.
- **`turn.forecast` is the engine half.** It projects the food ledger for a set of
  orders while mutating nothing. The skin is forbidden from computing numbers (if
  a number is on screen, the engine produced it), so showing the consequence of an
  allocation required the engine to be able to say it.
- **It stops at spoilage on purpose.** Everything later in the tick (exploration,
  the event draw, births) consumes the RNG, and a forecast that guessed at those
  would be lying about the one thing a forecast is for. What it reports is
  certain; what it omits is genuinely unknowable.
- The projection duplicates the food math rather than sharing code with the
  mutating resolution steps, because coupling them would mean either making
  resolution non-mutating or making the forecast run against a throwaway copy of
  the world. `TestForecast` asserts the two agree across every season, store
  level, and household shape, so a retuned constant or a reordered tick fails the
  suite instead of quietly desynchronising the display. Suite 148 to 153 tests.
- The chronicle gained a maximum width. On a wide terminal an unbounded log
  stretched event prose to a line length nobody can track back from.

This is groundwork for Phase 1 rather than Phase 1 itself. Spoilage tuning and the
winter draw-down are both decisions the player cannot weigh while the numbers are
invisible, so the ledger comes first.

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
