# Hearthfall: design and architecture spec

> A hearth is what you gather around and what you defend. A fall is what happens to most
> of them. The name holds both halves of the arc: grow a fire into a people, or bury them.

**Status:** Phase 0 shipped (v0.1.1). Everything past it is unbuilt.

**This document was rewritten on 2026-08-08.** The original is in git history and should be
read by anyone who wants to know what was given up. It was a knife aimed at scope creep, and
it was right to be. This revision widens the spine on purpose, with the reasoning stated in
§1, and it keeps the knife pointed at everything the widening does *not* license.

---

## 0. The one-line pitch

A grimdark clan-survival game. Start with a handful of villagers and a fog-black map. Send
people out; the world reveals itself tile by tile through scarcity, story, and violence.
Grow a hearth into a war-band into a people, or bury them.

*A Dark Room* that grows a spine into *King of Dragon Pass*, rendered in a terminal, and
that keeps growing until the thing you are managing is a people rather than a household.

## 1. The spine: read this before anything else

Every other system is negotiable. This one is the game:

> **Read the unknown at cost. Then commit resources you cannot take back.**

The original spec stated this narrowly, as *scouts reveal enemy composition so you can
assemble a counter-force*. That is still true, and it is still the best single expression of
the loop. But it described one tier of a game that has five, and stating it narrowly made
every later tier look like scope creep rather than the same idea at a different scale.

The same verb, at every scale the game reaches:

| Tier | What you pay to look at | What you commit |
|---|---|---|
| Hearth | this tile is forest | foragers, to a season you cannot undo |
| Steading | that band is twelve, and armed | shelter, or refusal |
| Clan | Vethaven resents you | grain, or a seat on the ring |
| Tribe | Stonefold fields forty spears, no bows | a war-stack |
| People | the Wolfkin are split on the succession | a treaty that binds your grandchildren |

### Fog is over facts, not over tiles

This is the mechanical form of the spine and the reason the tiers are one game rather than
five. `world.py` currently knows which tiles are revealed. That is fog over terrain, and it
is a special case.

Generalise it: **every knowable thing is a fact with a value, a staleness, and a price to
refresh.** Terrain never goes stale. A neighbour's grain store goes stale in a season. Their
intent goes stale faster. You are always acting on a picture that is partly out of date, and
the game is choosing which part of it you can afford to be wrong about.

### The honesty guarantee

An agent may only form an intent that has a corresponding learnable fact.

This is not a style rule, it is enforced by the data structure, and it is what separates this
design from a storyteller that spawns threats at you. If Stonefold is going to raid, then
`stonefold.intent` existed as a scoutable fact for seasons beforehand. The director (§5)
chooses *when you feel it*; the fact ledger guarantees you *could have known*.

If a proposed feature does not feed, sharpen, or pay off this loop, it is scope creep. Cut it
or shelve it.

## 2. What this game is _not_

Stated plainly because each is a trap the author will walk into by instinct.

- **Not a real-time RTS.** Turn-based. AoE2's rock-paper-scissors is fun because you micro it
  live. We don't have that. We have the *read* before the fight, not the fight.
- **Not a fortress sim.** We take DF's *tension* (winter, spoilage, raiders in the granary),
  never its *mechanism* (individual hauling jobs). Legible scarcity beats simulationist depth
  here, always.
- **Not a procedural-narrative research project.** No generative story engine. Content is
  hand-authored with systemic *framing*. See §6.
- **Not a graphics engine.** Glyphs. The map is generated, and generated terrain under
  painted art is uncanny. The TUI is the correct render target, not the budget one.
- **Not a grand-strategy map game.** New, and load-bearing. See §9.8: the map is a knowledge
  surface and never a maneuvering surface. The moment you push armies around a front line,
  the terminal is the wrong medium and the project is in trouble.
- **Not three games in a trenchcoat.** The tiers must *abstract* the tier below, not sit
  beside it. If tier 3 adds a council screen while tier 1's allocation screen is still being
  operated by hand every season, the game has doubled its workload instead of deepening.

## 3. Architecture: engine as library, frontend as skin

Non-negotiable separation.

```
src/hearthfall/
  engine/            # pure logic. no I/O, no rendering, no terminal. stdlib only.
    state.py         #   composes the pieces below; snapshot() is the content seam
    turn.py          #   the tick, plus the run-until-interrupted driver
    world.py         #   tiles and terrain. fog moves out to intel.py
    rng.py           #   ONE seeded source. determinism or nothing.
    balance.py       #   the numbers, with notes on what they were tuned against

    intel.py         #   NEW. the fact ledger: value, staleness, price. THE spine module.
    people.py        #   NEW. pool -> households -> named cast. absorbs Population.
    agents.py        #   NEW. neighbours, weather, wildlife: state, needs, intents.
    director.py      #   NEW. pacing only. picks which justified intent surfaces now.
    orders.py        #   NEW. per-season and standing orders as one type.
    chronicle.py     #   NEW. typed entries the skin renders.
    tiers.py         #   NEW. emergence conditions and the named moment.
    combat.py        #   LATER. abstract resolution.
  tui/               # thin skin over engine. Textual. throwaway-able.
  data/              # TOML. events, terrain, agents, peoples, names. no logic.
tests/               # engine is tested. the skin is not.
```

**The engine never imports the frontend.** You should be able to drive a full game from a
REPL or a test with zero terminal.

**The engine is stdlib-only.** Textual is a frontend dependency and lives in `tui/`. This is
the mechanical proof that the separation is real. A test asserts it.

**One RNG, seeded, injectable.** A seed reproduces a run exactly. This is the difference
between debugging and prayer, and it survives the director: the director is a pure function
of state, orders, seed, and content, like everything else.

**`chronicle.py` lives in the engine, not the skin.** The frontend computes nothing. A
chronicle the skin assembled would break that on day one.

## 4. The turn, and where it stops

A turn is a season; four to a year. Winter is the enemy that never negotiates.

**The engine always ticks one season. Forever.** Tiers do not change the clock; they change
how many seasons resolve before the game stops and asks you something.

- **Early:** the game stops every season. You assign hands, you read the ledger, you commit.
- **Later:** you set standing orders and the game runs until the director interrupts. Three
  quiet years cost three lines in the chronicle, not twelve screens of clicking.

**A season holds two decisions, not one.** Labour is the first: hands split between foraging,
scouting, and tending, against a forage ceiling that only new ground can raise. **Rationing is
the second, and it only exists when the store is short.** Equal shares, the workers first, or
the children first. It is deliberately absent in a good season, because a question with no
stakes asked every turn teaches the player to stop reading.

There is no dominant answer, and that is enforced by two invariants in the code: no policy may
waste food, and a full store must make the policy irrelevant. Measured, an even split is
*worse* for survival, because spreading a shortfall pushes every hearth into the starvation
threshold at once. What it buys is that nobody was wronged. Concentrating food saves people and
makes a household that was fed last and knows it.

A standing question, raised 2026-08-09 and **not yet designed**: whether a season should hold
*more* steps than these two. It is the most direct answer to an allocation that writes itself,
and it would reopen this section, so it gets a design conversation rather than an insertion.

This is what "under glass" means concretely. The food system does not vanish when you stop
allocating foragers by hand; it keeps running, and it can still kill you. It just stops
asking for your attention until it has something to say.

The tension is always the same shape: *not enough hands, not enough food, and the dark is
full of things you haven't scouted yet.*

## 5. Systems, in dependency order

### People: pool, households, named cast

Three layers, and the middle one is the load-bearing idea.

- **Pool.** Counts by role and stratum. The Victoria 3 substrate. This is what eats.
- **Households.** Ten to forty kin groups holding pops. **A household is what starves, what
  resents, what marries, and what feuds.** This is the join that makes the pool and the cast
  one system instead of two.
- **Named cast.** Five to twelve people drawn *from* households: ring members, rivals, heirs.
  Traits, ambitions, relationships. They age and they die.

The original spec forbade named individuals and the roadmap parked them under *Deferred,
deliberately*. That is knowingly overruled. The condition it was protecting still holds: the
pool comes first and names are a layer over it, never the foundation. A famine is resolved
against households, and *then* a rival emerges, because the household it starved has a name.

**The pool is derived, not stored.** `Population.adults`, `child_count`, `total`, and `morale`
are all computed from the households, so the aggregate can never drift from the kin groups it
is made of. `morale` is the average of the *living* households, which is what let households
arrive without touching a single shipped event. It is no longer the whole story though: a clan
averaging five with one hearth at zero is a different clan from one where everyone is at five,
and `worst_household_mood` is what tells them apart.

**Growth is a schedule a household earns, not a roll.** A hearth with two adults, a decent
mood, and a fed season builds a silent meter; when it comes due, a child. A hungry season sets
it back, so a famine costs years of growth rather than a turn of it. Hearths that outgrow
themselves split, which is how three kin groups head toward the ten to forty above.

It is deterministic on purpose, and this is the one place the seeded RNG is deliberately *not*
used. The RNG exists so runs reproduce, not so every mechanic must be a lottery, and a lottery
here would sever the connection between how you rationed and whether the clan grew. That
connection is the point: **the hearth you feed last is the hearth that stops growing.**

Two things Brandon asked for that live here and are **not yet designed**: a compatibility or
attraction meter deciding *which* households pair, and characteristics for it to read. Both
belong at this layer, not at the named-cast layer, because §5's own ordering says a household
is what marries. Names are drawn from these later; they are never the foundation.

### Intel: the fact ledger

The spine as code (§1). Facts have a value, a staleness, and a price to refresh. Tile fog is
its first client, not a separate system. Scouting is paying to refresh a fact. A report is
rendered facts. Enemy composition is a fact that goes stale.

### Agents: things in the world that want something

Neighbouring clans, weather systems, wolf packs, and your own resentful households hold state
and form intents. Stonefold raids because Stonefold is starving. Nothing spawns from nowhere.

### The director: pacing, and nothing else

The director does not create threats. It chooses which already-justified intent surfaces now
and which waits, and it decides when to break your standing orders. Its input is how much
slack the clan has; its constraint is the honesty guarantee (§1).

This is the fix for a real defect measured in Phase 0: a player who finds the winter insight
survives 190 runs in 200. The pressure is not that the world got harder, it is that the world
noticed you had room.

### The chronicle

The running record, engine-side and typed. Quiet seasons are one dim line each. Decisions
land inline, in the same column, in the same voice. It is the interface spine (§8) because it
is the only shape that makes time compression readable.

### Tiers

There is no tier number in the fiction and no menu that says TIER 3. Systems surface when
world state makes them relevant, and the transition is a named narrative beat. The engine
tracks a tier internally for pacing and content gating; the player experiences a moment.

### Combat (later)

Abstract, pre-committed, resolved not micro'd. Two stacks meet; the engine weighs composition,
terrain, numbers, morale, and the quality of your intel, then reports an outcome with real
stakes. Build the dumb version first: your strength vs. theirs, one roll. Earn the depth.

### The AoE2 layer (the reward, not the foundation)

Unit types, groups assembled from types, counters that make composition a puzzle, peoples with
different doctrines. **This is dessert. It is not the meal. Do not cook it first.**

## 6. Content: still the actual boss fight

The event engine is a weekend. Authoring the corpus is the project. Phase 0 shipped thirty
events; this design wants something in the range of 250 to 400. That number is the real cost
of this document and it should be read as such.

- **Hand-authored, systemically framed.** Events are TOML, gated by conditions on world state.
- **The condition evaluator is a small thing and it stays small.** A list of `key op value`
  clauses, AND-ed, evaluated against a flat dict. No OR. No parentheses. No functions. No
  arithmetic.
- **`snapshot()` grows. The evaluator never does.** This is how the small evaluator survives
  households, neighbours, and a ring. Every "any / count / worst / nearest" question is
  answered *by the engine* into a flat scalar before conditions run:

  ```
  households_resentful   = 2
  neighbours_hostile     = 1
  nearest_threat_seasons = 2
  ring_dominant_agenda   = "war"
  ```

  A new concept costs one snapshot key, not one grammar feature. `state.py` already declares
  this rule ("Adding a condition key means adding it here and nowhere else"); it is now the
  thing that holds the whole content layer up.
- **Effects are structured tables, not expression strings.** `food = -5` needs no parser.
- **Tallies are how the corpus remembers.** A tally is one integer that persists for the run,
  written by an effect and read by a condition as `tally_<name>`:

  ```toml
  [event.choice.effect.tally]
  elder_resentment = 3
  ```
  ```toml
  when = ["tally_elder_resentment > 5", "year > 2"]
  ```

  Because the write hangs off a **choice**, a later event can require not merely that something
  happened but that you answered it a particular way. That single addition buys silent progress
  meters, chains needing several prior events, and payoffs earned across years, and **the
  evaluator did not grow by one line** to get them. It is the rule above being cashed: a new
  concept cost one snapshot key.

  Every tally is declared in `data/tallies.toml`, and declaring it is what makes it exist.
  Effects validate names against the same reference snapshot conditions use, so a misspelled
  tally fails at load rather than incrementing a counter no condition will ever read.

  **Actors can be roles rather than people.** "The elder" is two integers to the engine and a
  man with a memory to the player. This is how King of Dragon Pass gets most of its depth, and
  it means the corpus does not have to wait for the named cast in sub-project 5.
- **Rarity comes from conditions, never from a weight lottery.** A powerful event should be
  rare because it is hard to reach. Earned reads as consequence; rolled reads as noise.
- **A repeatable event is repeatable across a run, not across consecutive seasons.** Measured
  at v0.5.0, every run in a sixty-seed sample replayed an event verbatim and the worst came
  round an extra forty-nine times. A cooldown in the draw fixed it without touching the TOML.
  That is a rule about *drawing*, not an enrichment of the format, and it is a stopgap: the
  real answer to a thin corpus is more of it. Lower the cooldown as the corpus grows.

> **DIRECT WARNING TO THE AUTHOR.** You built a query grammar for Atrium. You built a taxonomy
> DSL for your library. You will want to build the perfect event language before you write a
> single event. **Do not.** This revision makes the temptation worse, not better, because
> households and agents give you genuinely richer things to test against. The answer is always
> another snapshot key. If you find yourself designing a selector syntax, you have stopped
> making the game.

## 7. Build order: nothing is ever fully broken

Eight sub-projects. Each is playable, each answers a question, each gets its own spec and
plan. `roadmap.md` holds the detail. The order is load-bearing.

1. **The fact ledger.** Scouts, reports, staleness. **Holds the kill switch.**
2. **Households.** Resentment, famine that produces a rival, aggregate snapshot keys.
3. **The chronicle.** Standing orders, the TUI rebuild, save/load.
4. **Neighbours and the director.** Agents with intents, pacing, the honesty guarantee.
5. **The ring.** Named cast, advisors with agendas, the emergence moment.
6. **Violence.** Abstract combat, raiders, real stakes.
7. **Composition.** Unit types, the counter-web, intel driving assembly.
8. **The long game.** Doctrine, borders, attrition, the endgame.

**The kill switch moved earlier, from the old Phase 2 to sub-project 1.** Scouts and reports
used to be a map feature scheduled after a content phase. Under this design they are the
foundation, so the question that can cancel the project gets asked first and cheapest: *does
paying to look pull the player forward?* If the answer is no, the premise is wrong and no
amount of council drama or combat depth retrofits a reason to explore. Stop there.

**It answered yes** (2026-08-09, sub-project 1 slice 2). Over 200 seeds a clan that never
scouts ends with 1.4 people, one that scouts ends with 6.5, one that also reads winter ends
with 7.8. The premise holds and the project continues.

### What the build order is now actually solving

Three sub-projects in, the game's real defect has been measured rather than guessed at, and it
changes what the later sub-projects are *for*.

**The game plateaus.** Partway through a run the allocation stops changing, because exploration
switches itself off. Two plausible causes were chased and both were wrong:

1. *Not starting food.* The game is too harsh in year one and too safe from year two, and one
   scalar cannot move those in opposite directions.
2. *Not population growth.* Growth shipped and works, and tiles known moved 3.8 → 4.0. A sweep
   closed both levers: faster growth pushes endurance to 98%, and halving what ground yields
   collapses survival to 62%.

**The cause is that foraging is the clan's only sink for labour, and one sink saturates.**
About four tiles already support more foragers than a clan of ten can staff, so ground stays
permanently ahead of hands and scouting has nothing left to buy.

So **sub-projects 6 to 8 are not garnish on a working economy; they are the fix for it.** A
war-band is a second thing worth spending people on, and that is what makes ground worth taking
again. Two corollaries follow, and both are load-bearing:

- **A bigger map does not help** and stays deferred. More ground nobody needs is not a game.
- **More growth does not help either.** Do not reach for either lever again; the measurements
  are recorded in `balance.py` and `roadmap.md`.

## 8. Tech decisions and their trade-offs

- **Language: Python.** 90% data and logic. Balance iteration velocity dominates. Not C. Not
  yet, maybe not ever.

  **Re-opened and confirmed 2026-08-09**, against Rust specifically, on the grounds that the
  game is heading somewhere complicated and the port is cheapest now. It stays Python, and
  the reasoning is worth keeping because the question will come back:

  - *Performance is not in play and structurally cannot be.* A full 20-turn playthrough
    measures **~0.5 ms**. One tick per season, tens of tiles, hundreds of agents at the
    ceiling. §9.9 refuses the maneuvering map, which is the one feature that would have made
    this a compute problem.
  - *Nor is measurement throughput*, which is the better Rust argument for a game whose thesis
    is empirical balance. At 0.5 ms a run, 100,000 seeds is under a minute. Even assuming
    sub-project 8 makes a tick 100× heavier, a 100,000-seed sweep is ~80 minutes serial and
    seeded runs parallelise perfectly.
  - *The risk this project actually carries is content*, and Python is what protects it. The
    corpus is the game; the engine is a weekend. Anything that taxes the
    write-event, sweep, read-the-numbers loop taxes the thing most likely to kill Hearthfall.
  - *Textual is a real asset.* §5's chronicle spine, the Ctrl+P palette, and the glyph tiers
    are weeks of work at ratatui's level of abstraction.

  **What Rust would genuinely have bought is type safety, so buy that directly instead.**
  Pyright runs in **strict** mode over `engine/` and as a CI gate over the whole tree, and
  every engine dataclass is `slots=True` (frozen where it is a value). That covers the two
  real Python hazards here: a new `FactKind` or `Effect` field that some site forgot, and
  accidental attribute aliasing on the mutable state graph. It does not cover exhaustive
  matching, which remains the honest gap.
- **Frontend: Textual.** A fat modern dependency, accepted for velocity, shed-able because the
  engine does not know it exists.
- **The engine takes no dependencies at all.**
- **Data: TOML**, read with stdlib `tomllib`.
- **Determinism: seeded RNG, one source, injectable.** Repeated for weight.
- **Tests: the engine is tested; the skin is not.** Stdlib `unittest`, with `hypothesis`
  available for the invariants that are genuinely properties rather than examples (forecast
  parity, determinism, no order sequence driving a store negative).
- **Dev tooling is pinned in the lockfile, not by CI.** `ruff` and `pyright` are dependency-group
  entries, so `uv run ruff check` locally is the exact binary CI runs. They drifted once, with
  CI on a ruff whose default rule set was narrower than the developer's, which meant a working
  tree could fail locally and pass in CI.
- **The interface spine is the chronicle.** A running saga is the permanent centre; the map,
  the ring, and the households are panes over it. This is the only layout that makes
  unattended seasons readable, and it is native to a terminal in a way it would not be in GTK.
- **Command palette on Ctrl+P.** Textual provides it free (`COMMAND_PALETTE_BINDING`). It is
  not a convenience, it is the navigation architecture for a game with a ring, a fact ledger,
  households, a map, and save/load.
- **Glyphs come in three tiers, not two.**

  | Tier | Example | Risk |
  |---|---|---|
  | `ascii` | `. T ^ % ~` | none, works over ssh from a phone |
  | `unicode` | `░ ▲ ▓ ● ◐ ─` | near zero; present in any modern monospace font |
  | `nerd` | Font Awesome range | needs a patched or stacked symbols font |

  `unicode` is the default. `nerd` is opt-in and **must carry information, not decoration**:
  the staleness ramp in the fact ledger (seen / was true once / guessing / never looked) is
  the case that justifies it. The palette hosts the picker, a glyph test card (tofu occupies
  one cell, so no escape sequence can detect it; the player's eyes are the only detector), and
  a font advisor that scans installed fonts and prints the config line for the user's terminal.
  A launcher may spawn its own terminal window with a font stack via one-shot CLI overrides,
  which never touch the user's config.
- **Save/load is no longer deferrable.** It was correct to park it for a 30-minute run. A
  campaign that reaches tier 4 outlives a sitting.

## 9. The knife (invariants: violate these and the project rots)

1. The engine imports nothing from the frontend. Ever.
2. The engine imports nothing from PyPI either. Textual lives in `tui/`.
3. One seeded RNG. Runs reproduce. The director does not get an exemption.
4. No feature that does not feed the spine in §1 ships before sub-project 8.
5. Content is authored before the tooling to author it is beautiful. Effects are tables, not
   expressions. **`snapshot()` grows; the evaluator does not.**
6. Sub-project 1 holds the kill switch. Phase 0 tested the floor, not the game. Respect the
   difference.
7. Take the *tension* from your references, never the *mechanism*.
8. **The map is a knowledge surface, never a maneuvering surface.** Glyphs answer *what do I
   know and what is stale*. The moment they answer *where is my army*, the terminal is the
   wrong medium.
9. **Each tier abstracts the one below it.** A new tier that adds a screen without retiring a
   chore has made the game longer, not deeper.
10. **The director never invents a threat.** Every interrupt traces to a fact that was
    learnable before it fired.

---

*If future-you is reading this six weeks in, tempted to build the event DSL or the unit roster
instead of the boring fact ledger: that temptation is the enemy in the fog. You already know
what it does to people who charge it unscouted.*
