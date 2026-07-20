# Hearthfall: design and architecture spec

> A hearth is what you gather around and what you defend. A fall is what happens to most
> of them. The name holds both halves of the arc: grow a fire into a people, or bury them.

**Status:** pre-alpha, unbuilt. This document is a knife, not a wishlist. Its job is to
hold the line when the author is tired and wants to build the wrong thing.

---

## 0. The one-line pitch

A grimdark clan-survival game. Start with a handful of villagers and a fog-black map.
Send people out; the world reveals itself tile by tile through scarcity, story, and
violence. Grow a hearth into a war-band into a people, or bury them.

Think *A Dark Room* that grows a spine into *King of Dragon Pass*, rendered in a terminal.

## 1. The spine: read this before anything else

Every other system is negotiable. This one is the game:

**Scouts reveal the map _and_ reveal enemy composition. That intel lets you assemble a
counter-force before you commit.**

Exploration and combat are the same loop. You do not fight blind; you fight prepared, and
the fun lives in the preparation, not the swing. A scout that comes back with *"forty of
them, mostly spears, no archers, holding the high ground"* is worth more than a sword. The
player who reads the field and builds the right stack wins. The player who charges the fog
dies with questions.

If a proposed feature does not feed, sharpen, or pay off this loop, it is scope creep.
Cut it or shelve it.

## 2. What this game is _not_

Stated plainly because each of these is a trap the author will walk into by instinct.

- **Not a real-time RTS.** Turn-based. AoE2's rock-paper-scissors is fun because you micro
  it live. We don't have that. We have the *read* before the fight, not the fight. Build
  the knowing, not the swing.
- **Not a fortress sim.** Dwarf Fortress food is fun *inside DF*: z-levels, haulers,
  barrels. Bolted onto a menu it's spreadsheet janitoring. We take DF's *tension* (winter,
  spoilage, raiders in the granary), never its *mechanism* (individual hauling jobs).
  Legible scarcity beats simulationist depth here, always.
- **Not a procedural-narrative research project.** No generative story engine. That's an
  unsolved problem and it is not this project's problem. Content is hand-authored with
  systemic *framing*. See §6.
- **Not a graphics engine.** No 2D render, no sprites, no Cairo scribework. Glyphs. The map
  is generated, and generated terrain under painted art is uncanny: the seams show.
  Generated terrain as clean glyphs is *coherent*. The TUI is the correct render target,
  not the budget one.

## 3. Architecture: engine as library, frontend as skin

Non-negotiable separation. The author has done this in every app he's shipped; do it here
too.

```
src/hearthfall/
  engine/            # pure logic. no I/O, no rendering, no terminal. stdlib only.
    state.py         #   world/pop/stock/map state: plain data
    turn.py          #   the tick: resolve a turn, advance time
    world.py         #   tile model, fog, reveal, terrain tables
    pops.py          #   villagers, units, groups, morale
    combat.py        #   abstract resolution (phase 3+)
    events/          #   event tables + condition evaluator (§6)
    rng.py           #   ONE seeded source. determinism or nothing.
  tui/               # thin skin over engine. Textual. throwaway-able.
  data/              # TOML. events, terrain, units, peoples. no logic.
tests/               # engine is tested. the skin is not.
```

**The engine never imports the frontend.** You should be able to drive a full game from a
Python REPL or a test with zero terminal. This is what lets a GTK frontend bolt on later
without a rewrite, and it lets the whole thing be tested, which is the author's instinct
anyway.

**The engine is stdlib-only.** Textual is a frontend dependency and it lives in the
frontend. This is not asceticism: it is the mechanical proof that the separation above is
real. If `import textual` ever appears under `engine/`, the architecture has already
rotted. A test asserts this.

**One RNG, seeded, injectable.** A game whose runs can't be reproduced can't be balanced or
bug-fixed. Every random draw goes through `rng.py`. A seed reproduces a run exactly. This
is not optional; it is the difference between debugging and prayer.

## 4. Core loop (the turn)

Season-based time. A turn is a season; four to a year. Winter is the enemy that never
negotiates.

Each turn the player:

1. **Reads state:** population, stores, known map, standing threats.
2. **Allocates people:** to work (food, building), to explore, to war/raid, to defend.
   People are finite. Every assignment is an opportunity cost paid in something else not
   done.
3. **Resolves:** the engine ticks. Food produced and consumed, spoilage, exploration
   outcomes, events fired, combat resolved.
4. **Faces consequences:** an event, a council decision, a raid, a death, a discovery.

The tension is always the same shape: *not enough hands, not enough food, and the dark is
full of things you haven't scouted yet.*

## 5. Systems, in dependency order

Listed so the build order in §7 is obvious.

### Population and labor

Villagers are the atomic resource. They eat, work, explore, fight, and die. Early on,
tracked as pools with roles (a KoDP-style abstraction), **not** as named individuals with
DF-style needs. Named characters can come later as a flavor layer over the pool; do not
start there.

### Food and stores

Produced by assigned labor, modified by season and terrain. Consumed per capita per turn.
**Spoilage and a hard winter draw-down are the whole point.** A stockpile that never rots
is just a number going up. Raiders can steal stores; a granary is a target. That's the DF
*tension* without the DF *machinery*.

### The map and fog

Starts black except the home tile. Exploration reveals adjacent tiles. Each tile has
terrain, which gates resources, animals (hunt/hazard), and which peoples live there.
**Generated, not hand-painted**, which is exactly why glyphs are right (§2). Reveal is the
reward that keeps the explore loop pulling.

### Exploration

An action that spends people and time to reveal tiles and fire events off a table keyed to
terrain. **Scouts explore better and, critically, return enemy composition intel.** This is
the spine (§1) made mechanical.

### Events and council

The narrative engine (§6). Fires from tables on turn-resolve. Some are flavor, some are
forks, some are council votes with advisors who have agendas. This is where grimdark lives:
hard choices, no clean options, someone always pays.

### Combat (phase 3+)

Abstract, pre-committed, resolved not micro'd. Two stacks meet; the engine weighs
composition, terrain, numbers, morale, and the quality of your intel, then reports an
outcome with real stakes (dead people, lost stores, ground gained). The counter-web (below)
is what makes the *read* matter. Build the dumb version first: your strength vs. theirs, one
roll, real consequences. Earn the depth.

### The AoE2 layer (phase 4: the reward, not the foundation)

Unit types with strengths and weaknesses. Groups you assemble from types. Counters that make
composition a puzzle. Different *peoples* using different group structures, so you
strategize against a civilization's doctrine, not just its headcount. **This is dessert. It
is not the meal. Do not cook it first.**

## 6. Content strategy: the actual boss fight

The event engine is a weekend. Authoring two hundred events that don't feel like reruns is
the real project. Decide the strategy now, in ink:

- **Hand-authored, systemically framed.** Events are data (TOML), gated by conditions on
  world state (season, stores, morale, tiles known, threats standing). The *engine* is
  small; the *corpus* is the work.
- **The condition evaluator is a small thing and it stays small.** A list of
  `key op value` clauses, AND-ed together, evaluated against a state dict. That is enough.
  It ships content.
- **Effects are structured tables, not expression strings.** `food = -5` in a TOML table
  needs no parser. `"stores.food -= 5"` needs one, and a parser is a language, and a
  language is the trap below wearing a different coat.

> **DIRECT WARNING TO THE AUTHOR.** You built a query grammar for Atrium. You built a
> taxonomy DSL for your library. You will want to build the perfect event language before
> you write a single event. **Do not.** A TOML table and a fifty-line condition evaluator
> ship a game. A beautiful parser starves it. The DSL is a procrastination that wears the
> mask of engineering. Write events first. If the data format genuinely strains after a
> hundred real events, *then* reconsider, with evidence, not aesthetics.

Example event shape (illustrative, not final):

```toml
[[event]]
id = "winter.granary_rats"
weight = 3
when = ["season == winter", "stores.food > 20"]
title = "Something in the Grain"
body = "The stores are lighter than the tally says. Small teeth in the dark."

  [[event.choice]]
  text = "Set the children to hunting them. Cruel, but hands are hands."
  [event.choice.effect]
  food = -5
  morale = -1

  [[event.choice]]
  text = "Do nothing. Pray the cold kills them first."
  [event.choice.effect]
  food = -12
```

## 7. Build phases: nothing is ever fully broken

Ship in slices. Each slice is playable and answers a question. If a slice's question comes
back *no*, you stop and you've saved a year.

**Phase 0: prove the foundation holds.**
Turn loop, food, population, one explore action that reveals a tile and fires an event from
a ~20-entry table. Win/lose by survival. **No combat.** No units. No map beyond a small
grid.
*Question: is the allocate-and-survive loop tolerable to sit inside for thirty minutes?*

Read that question precisely. Phase 0 does **not** test the spine (§1), because the spine
needs scouts, intel, and an enemy, and none of those exist yet. A yes here means the floor
is solid enough to build the spine on top of. It does not mean the game works. A no here
means the floor is rotten and nothing built on it will stand, so fix the floor or stop.
Phase 0 is a foundation test with the authority a foundation test has, and no more.

**Phase 1: make it a game.**
Real event corpus (aim 60 to 80 events), the condition evaluator, council decisions with
advisors, seasons that bite. Balance winter so it's survivable but never safe.
*Question: does anyone want a second run?*

**Phase 2: make the map matter.**
Larger generated map, terrain-gated resources and events, scouts as a distinct role,
exploration intel returned as readable reports.
*Question: does the fog pull the player forward?*

**This is the phase that holds the kill switch.** Phase 2 is the first slice where the
spine is legible: a scout goes out, a report comes back, and the report changes what you do
next. If the fog does not pull here, the central premise of the game is wrong, and no amount
of combat depth in phases 3 and 4 will retrofit a reason to explore. Stop here if the answer
is no. This is the honest kill gate; it costs more than Phase 0 did, and it is still cheap
next to phases 3 through 5.

**Phase 3: introduce violence.**
Abstract single-stack combat. Your strength vs. theirs, terrain and morale modifiers, real
stakes. Raiders that hit stores. The spine's payoff, in its dumbest working form.
*Question: is losing people to a fight you misread painful in the right way?*

**Phase 4: the reward.**
Unit types, group composition, the counter-web, scout-intel driving pre-battle assembly.
This is the AoE2 dessert. It only tastes right if phases 0 through 3 built the appetite.
*Question: is assembling the right stack against a read enemy the best decision in the
game?*

**Phase 5: the long game.**
Multiple peoples with distinct doctrines, resource variance across terrain, the 4X arc from
hearth to city to power. Grimdark endgame: attrition, hard borders, a people that endures or
is buried.

Do not let a later phase's shininess pull work forward. The order is load-bearing.

## 8. Tech decisions and their trade-offs

- **Language: Python.** This game is 90% data and logic, the author's
  CalibreQuarry/Lattice wheelhouse. Balance iteration velocity dominates every other concern
  at this stage; Python wins on iteration. Not C. Not yet, maybe not ever.
- **Frontend: Textual.** CSS-ish layout, reactive state, real widgets, iteration speed
  curses can't match. *Trade-off, stated honestly:* it's a fat modern dependency and it cuts
  against the Techno-Peasant grain. Accepted anyway. It's a local render lib, not a cloud
  tentacle, and it's shed-able because the engine doesn't know it exists. If purity itches
  badly, curses is stdlib and the author writes closer to the metal than that. But eat the
  dependency for the prototype; velocity on *is-it-fun* is worth more than spartan points.
- **The engine takes no dependencies at all.** See §3. Textual stops at the `tui/` boundary.
- **Data: TOML.** Human-writable, diff-able, no logic. Events, terrain, units, peoples all
  live here. Read with stdlib `tomllib`.
- **Determinism: seeded RNG, one source, injectable.** (§3.) Repeated for weight.
- **Tests: the engine is tested; the skin is not.** Turn resolution, food math, combat
  resolution, condition evaluation: all covered. The author writes tests before shipping by
  instinct; this is just naming the instinct.

## 9. The knife (invariants: violate these and the project rots)

1. The engine imports nothing from the frontend. Ever.
2. The engine imports nothing from PyPI either. Textual lives in `tui/`.
3. One seeded RNG. Runs reproduce.
4. No feature that doesn't feed the scout-intel spine ships before phase 5.
5. Content is authored before the tooling to author it is beautiful. Effects are tables,
   not expressions.
6. Phase 2 holds the kill switch. Phase 0 tests the floor, not the game. Respect the
   difference.
7. Take the *tension* from your references, never the *mechanism*.

---

*If future-you is reading this six weeks in, tempted to build the event DSL or the unit
roster instead of the boring loop: that temptation is the enemy in the fog. You already know
what it does to people who charge it unscouted.*
