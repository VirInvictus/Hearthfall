# Patch notes

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
