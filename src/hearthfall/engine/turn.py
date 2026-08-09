"""The tick: resolve a turn, advance time.

Resolution order is load-bearing. Producing before consuming means this turn's foraging can
feed this turn's mouths; spoiling after consuming means you never rot food someone was
about to eat. Changing the order changes the balance of every constant in `balance.py`, so
the order is fixed here and documented step by step rather than left to be inferred.
"""

from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass, field

from hearthfall.engine import balance
from hearthfall.engine.events import table
from hearthfall.engine.events.loader import Event, load_tallies
from hearthfall.engine.intel import FactKind, Ledger
from hearthfall.engine.people import Household, Rationing, share_out
from hearthfall.engine.rng import Rng
from hearthfall.engine.state import (
    Effect,
    GameState,
    Orders,
    Outcome,
    PendingChoice,
    Population,
    Season,
    Stores,
)
from hearthfall.engine.world import Coord, Terrain, World


@dataclass(slots=True)
class TurnReport:
    """What happened, in numbers the caller can render and in lines it can print.

    The frontend computes nothing. If the player should see it, it is in here.
    """

    turn: int
    season: Season
    produced: int = 0
    # How many foragers the known ground supports, and how many had nowhere to go. Reported
    # rather than derived, because a hand that brought back nothing is the season's most
    # important fact and the frontend is not allowed to work it out for itself.
    forage_capacity: int = 0
    foragers_idle: int = 0
    consumed: int = 0
    shortfall: int = 0
    starved: int = 0
    spoiled: int = 0
    matured: int = 0
    born: int = 0
    # How the season's food was divided, and how many hearths went without while others ate.
    # Wronged is not the same as hungry: everyone going equally short wrongs nobody.
    rationing: Rationing = Rationing.EQUAL
    households_wronged: int = 0
    households_split: int = 0
    revealed: Coord | None = None
    revealed_terrain: Terrain | None = None
    # Where a big enough party stopped and worked out what the ground will feed. Separate from
    # `revealed` because they are two different things the same party can bring home, and
    # usually but not always the same tile.
    surveyed: Coord | None = None
    event_id: str | None = None
    log: list[str] = field(default_factory=list[str])
    pending: PendingChoice | None = None
    outcome: Outcome | None = None

    def note(self, line: str) -> None:
        self.log.append(line)


@dataclass(frozen=True, slots=True)
class ForageTake:
    """What the ground the clan knows gives to a number of foragers.

    `capacity` and `idle` are carried rather than left for the caller to derive, because the
    frontend computes nothing and "two of your hands had nowhere to go" is the entire point
    of the mechanic. If the ceiling is not visible before the season is committed, paying to
    look cannot pull the player forward and sub-project 1 fails its own question.
    """

    food: int
    capacity: int
    idle: int
    # Where they worked and what each tile gave, best ground first. Prose, not arithmetic:
    # the report reads it back so a season's foraging names real places.
    worked: tuple[tuple[Coord, Terrain, int], ...]


def forage_take(ledger: Ledger, foragers: int, season: Season) -> ForageTake:
    """Work the known ground with `foragers` hands. Pure; touches no state.

    Called by both `_produce` and `forecast`. Those two go on duplicating the *order* of the
    tick deliberately, because one mutates and one must not, but the per-tile arithmetic is
    written once: a greedy fill written twice is a real bug surface, and slices 3 and 5 both
    change it again.

    Note the signature takes a ledger and no world. That is the point of slice 2: the clan
    forages the ground it *believes* is there.
    """
    base = balance.FORAGE_YIELD[season]

    ground: list[tuple[Coord, Terrain, int]] = []
    capacity = 0
    for coord in ledger.revealed():
        terrain = _believed_terrain(ledger, coord)
        if terrain is None:
            continue
        tile_capacity = _believed_capacity(ledger, coord, terrain)
        capacity += tile_capacity
        ground.append((coord, terrain, tile_capacity))

    # Richest ground first. Greedy is optimal here, not merely convenient: a tile's yield per
    # forager does not depend on how many work it, so there is never a reason to pass over
    # better ground. Coordinate order breaks ties so two forests always fill in one sequence.
    ground.sort(key=lambda entry: (-_per_forager(base, entry[1]), entry[0]))

    remaining = max(0, foragers)
    food = 0
    worked: list[tuple[Coord, Terrain, int]] = []
    for coord, terrain, tile_capacity in ground:
        if remaining <= 0:
            break
        hands = min(remaining, tile_capacity)
        if not hands:
            continue  # dead ground: it must not swallow a hand better ground could use
        remaining -= hands
        taken = hands * _per_forager(base, terrain)
        food += taken
        worked.append((coord, terrain, taken))

    return ForageTake(
        food=food, capacity=capacity, idle=remaining, worked=tuple(worked)
    )


def _refresh_ground(state: GameState) -> None:
    """Re-count what the known ground supports, after the ledger has changed.

    Called from `new_game`, after a reveal, and after a survey, which are the only moments the
    answer can move. Season is irrelevant to capacity, so any season gives the same count.
    """
    state.forage_capacity = forage_take(
        state.ledger, foragers=0, season=state.season
    ).capacity


def _per_forager(base: int, terrain: Terrain) -> int:
    """One forager's take on one tile, in whole food.

    Tenths, multiplied then floored, so winter's zero base stays zero on every terrain
    without a special case anywhere.
    """
    return base * balance.TERRAIN_FORAGE[terrain] // 10


def _believed_capacity(ledger: Ledger, coord: Coord, terrain: Terrain) -> int:
    """How many hands the clan knows how to use on a tile.

    Slice 3's gradient, in one expression. A surveyed tile is worth what its terrain supports;
    a tile the scouts only walked past is worth a token crew. The `min` is what stops a survey
    from making water workable, and it means a marsh survey buys nothing, with no special case
    for either.

    A surveyed capacity is read back out of the ledger rather than recomputed from the terrain
    table, because the fact is what the clan believes and slice 5 exists to let that fact age
    out from under the ground it describes.
    """
    surveyed = ledger.value(FactKind.FORAGE, coord)
    if isinstance(surveyed, int):
        return max(0, surveyed)
    return min(balance.WALKED_CAPACITY, balance.TERRAIN_CAPACITY[terrain])


def _believed_terrain(ledger: Ledger, coord: Coord) -> Terrain | None:
    """What the clan thinks is on a tile, or None if nobody has walked it.

    Read from the ledger and never from `world.tile`. The two agree today because `reveal`
    copies the ground faithfully, and slice 5 exists to make them disagree; food math that
    reads the world would ignore staleness forever. A test in `test_forage` pins this.
    """
    value = ledger.value(FactKind.TERRAIN, coord)
    return Terrain(value) if isinstance(value, str) else None


@dataclass(frozen=True, slots=True)
class Forecast:
    """What this season's allocation would do to the store, before luck gets a vote.

    The frontend is not allowed to compute numbers, so a player who wants to see the
    consequence of an allocation before committing to it needs the engine to say. This is
    that answer: the deterministic prefix of `resolve`, run without touching state.

    It stops at spoilage on purpose. Everything after that in the tick (exploration, the
    event draw, births) consumes the RNG, and a forecast that guessed at those would be
    lying about the one thing a forecast is for. `certain` is the honest boundary.
    """

    season: Season
    produced: int
    # The ceiling the known ground puts on foraging, and the hands this allocation wastes
    # against it. This is the number slice 2 exists to put in front of the player before the
    # season is committed: it is what makes scouting legible as an investment.
    forage_capacity: int
    foragers_idle: int
    demand: int
    eaten: int
    shortfall: int
    would_starve: int
    spoil_rate: float
    spoiled: int
    opening_food: int
    closing_food: int

    @property
    def net(self) -> int:
        """Change in the store across the season. Negative means the pile is shrinking."""
        return self.closing_food - self.opening_food


def forecast(state: GameState, orders: Orders) -> Forecast:
    """Project this turn's food ledger for `orders`, mutating nothing.

    Mirrors `_produce`, `_consume`, `_starve`, and `_spoil` in that order, because the
    order is what determines the numbers (this turn's foraging feeds this turn's mouths;
    rot lands on what is left rather than on what someone was about to eat).

    The duplication with those functions is deliberate and thin: they mutate, this does
    not, and coupling them would mean either making resolution non-mutating or making the
    forecast run a throwaway copy of the world. `test_turn` asserts the two agree, so drift
    is caught rather than designed out.
    """
    season = state.season
    population = state.population

    take = forage_take(state.ledger, orders.forage, season)
    opening = state.stores.food
    after_produce = opening + take.food

    per_adult, per_child = rations(season)
    households = [h for h in population.households if not h.is_empty]
    demand = sum(h.demand(per_adult, per_child) for h in households)
    eaten = min(demand, after_produce)
    shortfall = demand - eaten

    # Deaths are counted per household, exactly as `_consume` counts them, because the
    # rationing choice changes who goes without and therefore how many die. Feeding three
    # households evenly can kill nobody where feeding one of them fully kills two, off the
    # same shortfall. A forecast that averaged that away would be hiding the consequence of
    # the very decision it exists to inform.
    would_starve = 0
    for household, share in zip(
        households,
        share_out(households, eaten, orders.rationing, per_adult, per_child),
        strict=True,
    ):
        short = household.demand(per_adult, per_child) - share
        if short > 0:
            would_starve += min(
                math.ceil(short / balance.FOOD_PER_STARVATION_DEATH), household.size
            )

    after_eat = after_produce - eaten
    rate = max(
        balance.SPOIL_RATE_FLOOR,
        balance.SPOIL_RATE[season] - orders.tend * balance.SPOIL_REDUCTION_PER_TENDER,
    )
    spoiled = int(after_eat * rate)

    return Forecast(
        season=season,
        produced=take.food,
        forage_capacity=take.capacity,
        foragers_idle=take.idle,
        demand=demand,
        eaten=eaten,
        shortfall=shortfall,
        would_starve=would_starve,
        spoil_rate=rate,
        spoiled=spoiled,
        opening_food=opening,
        closing_food=after_eat - spoiled,
    )


def new_game(seed: int, tallies: Sequence[str] | None = None) -> GameState:
    """A fresh run. Everything downstream of this is a function of the seed.

    Every declared tally starts at zero and is present from the first turn, so `snapshot()`
    has a stable key set and the loader can validate both conditions and effects against it.
    The registry is read from `data/tallies.toml` unless a caller injects one, which is how a
    test builds a state without depending on shipped content.
    """
    rng = Rng(seed)
    world = World.generate(
        width=balance.MAP_WIDTH,
        height=balance.MAP_HEIGHT,
        rng=rng,
        weights=balance.TERRAIN_WEIGHTS,
    )
    # The clan knows the ground it is standing on and nothing else. Revealing home is a fact
    # about the clan, which is why it happens here and not inside World.generate. Home starts
    # surveyed as well as walked: whatever else the clan has not looked at, it knows what its
    # own ground will feed.
    ledger = Ledger(halflives=balance.FACT_HALFLIFE)
    ledger.reveal(world, world.home, turn=0)
    ledger.survey(
        world.home, balance.TERRAIN_CAPACITY[world.tile(world.home).terrain], turn=0
    )
    state = GameState(
        seed=seed,
        world=world,
        ledger=ledger,
        population=_founding_households(),
        resentful_at=balance.RESENTFUL_AT,
        stores=Stores(food=balance.STARTING_FOOD),
        tallies={
            name: 0 for name in (load_tallies() if tallies is None else tuple(tallies))
        },
    )
    _refresh_ground(state)
    return state


def _founding_households() -> Population:
    """Deal the starting clan into kin groups, as evenly as the numbers allow.

    Deterministic and seed-independent: who is in which household at turn zero is not
    something a run should differ on, and making it random would add variance to the opening
    without adding a decision.
    """
    count = balance.STARTING_HOUSEHOLDS
    households = [
        # Staggered bond, so the hearths do not move in lockstep. Started level, all three
        # reached BOND_TO_BEAR on the same season and the chronicle read "3 children were born
        # to the clan", which is a batch job rather than a thing that happened. Spread out,
        # each birth is its own line in its own season.
        Household(
            adults=0,
            mood=balance.STARTING_MORALE,
            bond=index * (balance.BOND_TO_BEAR // count),
        )
        for index in range(count)
    ]
    for index in range(balance.STARTING_ADULTS):
        households[index % count].adults += 1
    for index in range(balance.STARTING_CHILDREN):
        households[index % count].children.append(balance.CHILD_MATURES_AFTER)
    return Population(households=households)


def resolve(
    state: GameState,
    orders: Orders,
    rng: Rng,
    events: Sequence[Event] = (),
) -> TurnReport:
    """Advance the world by one season.

    The corpus is passed in rather than loaded here. Loading touches storage; resolving
    must not, so that a turn is a pure function of state, orders, seed, and content.
    """
    if state.is_over:
        raise RuntimeError("the run is over; no further turns resolve")
    if state.pending is not None:
        raise RuntimeError(
            "an event choice is outstanding; call apply_choice before the next turn"
        )
    orders.validate(state.population.adults)

    season = state.season
    report = TurnReport(turn=state.turn, season=season)

    _produce(state, orders, season, report)
    _consume(state, orders, report)
    _spoil(state, orders, season, report)
    _scout(state, orders, rng, report)
    _draw_event(state, rng, report, events)
    _grow(state, rng, report)
    _advance(state, report)

    return report


def apply_choice(state: GameState, index: int) -> Effect:
    """Answer the outstanding event choice.

    The effect lands on the state the turn left behind, which means a choice made at the
    end of turn N is felt at the start of turn N+1. That is deliberate: the player sees the
    consequence in the numbers they allocate against next.
    """
    pending = state.pending
    if pending is None:
        raise RuntimeError("no event choice is outstanding")
    if not 0 <= index < len(pending.options):
        raise IndexError(
            f"choice {index} is out of range for event {pending.event_id!r}"
        )

    effect = pending.options[index].effect
    state.pending = None
    apply_effect(state, effect)
    _judge(state)
    return effect


def apply_effect(state: GameState, effect: Effect) -> None:
    """Apply a bundle of deltas, clamped so the state stays legal."""
    state.stores.food = max(0, state.stores.food + effect.food)
    state.population.shift_mood(effect.morale, balance.MORALE_MIN, balance.MORALE_MAX)
    state.population.add_adults(max(0, effect.adults))
    state.population.take_people(max(0, -effect.adults))

    for _ in range(effect.children):
        state.population.add_child(balance.CHILD_MATURES_AFTER)
    for _ in range(-effect.children):
        state.population.take_people(1)

    # Tallies are unclamped and unbounded on purpose. A grudge does not saturate at ten, and
    # the corpus, not the engine, decides what counts as "enough". They never go below zero
    # though: a negative resentment is not forgiveness, it is a bug in an event.
    for name, delta in effect.tally:
        state.tallies[name] = max(0, state.tallies.get(name, 0) + delta)


# --- Steps, in resolution order ---------------------------------------------------------


def _produce(
    state: GameState, orders: Orders, season: Season, report: TurnReport
) -> None:
    take = forage_take(state.ledger, orders.forage, season)
    state.stores.food += take.food
    report.produced = take.food
    report.forage_capacity = take.capacity
    report.foragers_idle = take.idle

    if take.food:
        report.note(
            f"Foragers brought in {take.food} food from {_ground_phrase(state, take)}."
        )
    elif orders.forage:
        report.note("The foragers came back with nothing.")

    # Named separately from the yield, because idle hands are not a smaller harvest, they are
    # the game telling the player that the map is now the constraint.
    if take.idle:
        report.note(
            f"{take.idle} had no ground to work. The clan knows nowhere else to forage."
        )


def rations(season: Season) -> tuple[int, int]:
    """What one adult and one child need this season. Winter costs everyone extra."""
    extra = balance.WINTER_EXTRA_FOOD if season is Season.WINTER else 0
    return balance.FOOD_PER_ADULT + extra, balance.FOOD_PER_CHILD + extra


def _consume(state: GameState, orders: Orders, report: TurnReport) -> None:
    """Feed the households, by the rationing the player chose.

    Eating and starving are one step now rather than two, because who starves depends on who
    ate, and that depended on a decision. The clan-wide totals in the report are unchanged, so
    everything reading them keeps working; what is new is that the same shortfall now lands on
    named ground instead of on an average.
    """
    population = state.population
    per_adult, per_child = rations(state.season)
    households = [h for h in population.households if not h.is_empty]

    demand = sum(h.demand(per_adult, per_child) for h in households)
    eaten = min(demand, state.stores.food)
    state.stores.food -= eaten
    report.consumed = eaten
    report.shortfall = demand - eaten
    report.rationing = orders.rationing
    report.note(f"{population.total} mouths ate {eaten} food.")

    shares = share_out(households, eaten, orders.rationing, per_adult, per_child)
    # What each household would have got under an even split, which is the yardstick for
    # whether it was *wronged* as opposed to merely hungry. Everyone going equally short
    # breeds far less resentment than one household watching another eat.
    fair = share_out(households, eaten, Rationing.EQUAL, per_adult, per_child)

    starved = 0
    wronged = 0
    for household, share, even in zip(households, shares, fair, strict=True):
        short = household.demand(per_adult, per_child) - share
        if short > 0:
            deaths = min(
                math.ceil(short / balance.FOOD_PER_STARVATION_DEATH), household.size
            )
            for _ in range(deaths):
                household.take_a_person()
            starved += deaths
            household.mood = _clamp_morale(
                household.mood
                - balance.MORALE_LOSS_PER_STARVATION
                - deaths * balance.MORALE_LOSS_PER_DEATH
            )
        if short > 0:
            household.went_short += 1
        if share < even:
            household.resentment += balance.RESENTMENT_PER_SHORT_SHARE
            wronged += 1

    report.starved = starved
    report.households_wronged = wronged
    if report.shortfall:
        report.note(
            f"The stores ran {report.shortfall} short. {starved} did not survive it."
        )
    if wronged:
        report.note(
            f"{wronged} of the hearths went without while others ate. They know it."
        )


def _spoil(
    state: GameState, orders: Orders, season: Season, report: TurnReport
) -> None:
    rate = max(
        balance.SPOIL_RATE_FLOOR,
        balance.SPOIL_RATE[season] - orders.tend * balance.SPOIL_REDUCTION_PER_TENDER,
    )
    spoiled = int(state.stores.food * rate)
    state.stores.food -= spoiled
    report.spoiled = spoiled
    if spoiled:
        report.note(f"{spoiled} food rotted in the store.")


def _scout(state: GameState, orders: Orders, rng: Rng, report: TurnReport) -> None:
    """Send a party out. What it comes back with depends on how many went.

    Two can cover ground: they walk into the dark and learn what is there. A third means the
    party can also stop somewhere and work out what the place will actually feed, which is the
    only thing that raises the ceiling on foraging. The walk happens first, so the tile just
    found is a candidate for the same season's survey.
    """
    if orders.scout < balance.SCOUTS_TO_WALK:
        if orders.scout:
            report.note("Too few went out to find anything worth the walk.")
        return

    _walk(state, orders, rng, report)
    if orders.scout >= balance.SCOUTS_TO_SURVEY:
        _survey(state, report)


def _walk(state: GameState, orders: Orders, rng: Rng, report: TurnReport) -> None:
    frontier = state.ledger.frontier(state.world)
    if not frontier:
        report.note("There is nothing left within reach to walk into.")
        return

    target = orders.scout_target
    if target is None:
        target = rng.choice(frontier)
    elif target not in frontier:
        raise ValueError(f"{target} is not on the frontier; it cannot be scouted into")

    # Learned this turn, before _advance ticks the clock, so the fact is stamped with the
    # season the scouts actually walked it.
    state.ledger.reveal(state.world, target, state.turn)
    _refresh_ground(state)
    tile = state.world.tile(target)
    state.last_revealed = tile.terrain
    report.revealed = target
    report.revealed_terrain = tile.terrain
    report.note(
        f"The scouts came back knowing {tile.terrain} to the {_bearing(state, target)}."
    )


@dataclass(frozen=True, slots=True)
class SurveyPlan:
    """Where a big enough party would stop and look, and what it would buy.

    Public because the skin has to be able to show the price of the third scout before the
    season is committed, and the frontend computes nothing. `_survey` and the allocation panel
    read the same answer, so what the player is promised is what the turn then does.
    """

    coord: Coord
    terrain: Terrain  # believed, not true: it is what the clan is deciding on
    gain: int  # hands the survey would add to the forage ceiling


def survey_plan(state: GameState) -> SurveyPlan | None:
    """The best ground the clan knows of but has never worked out. None if there is none.

    Which tile that is, is the engine's call rather than an order, exactly as the placement of
    foragers is: orders stay scalar and the map stays a knowledge surface (`spec.md` §9.9).
    Candidates are ranked on what the clan *believes* is out there, because a decision to go
    and look can only be made on belief.
    """
    ledger = state.ledger
    best: SurveyPlan | None = None
    for coord in ledger.revealed():
        believed = _believed_terrain(ledger, coord)
        if believed is None:
            continue
        gain = balance.TERRAIN_CAPACITY[believed] - _believed_capacity(
            ledger, coord, believed
        )
        if gain <= 0:
            continue
        # Richest ground first when two tiles would gain the same, so a forest gets looked at
        # before a plain. Season is deliberately not in the ranking: how good a place is does
        # not depend on when you ask, and in winter every yield is zero and it would collapse.
        if best is None or (
            -gain,
            -balance.TERRAIN_FORAGE[believed],
            coord,
        ) < (-best.gain, -balance.TERRAIN_FORAGE[best.terrain], best.coord):
            best = SurveyPlan(coord=coord, terrain=believed, gain=gain)
    return best


def _survey(state: GameState, report: TurnReport) -> None:
    """Carry out the plan.

    What the survey *learns* comes from the world even though the plan was made on belief,
    because looking is how a belief gets corrected.

    A survey that would raise nothing is not made. The scouts are not going to walk out to a
    marsh to confirm it is still a marsh, and saying so is more honest than logging a survey
    that moved no number.
    """
    ledger = state.ledger
    plan = survey_plan(state)
    if plan is None:
        report.note("The party found nothing else worth a closer look.")
        return

    coord = plan.coord
    terrain = state.world.tile(coord).terrain
    # A survey re-learns the ground as well as measuring it: the party is standing on the
    # tile, so this is the moment a wrong belief about it gets corrected.
    ledger.reveal(state.world, coord, state.turn)
    ledger.survey(coord, balance.TERRAIN_CAPACITY[terrain], state.turn)
    _refresh_ground(state)
    report.surveyed = coord
    report.note(
        f"They worked out what {_place(state, coord, terrain)} will feed: "
        f"{balance.TERRAIN_CAPACITY[terrain]} can work it now."
    )


def _draw_event(
    state: GameState, rng: Rng, report: TurnReport, events: Sequence[Event]
) -> None:
    """Fire at most one event from the corpus.

    A turn where nothing is eligible is a quiet turn, not an error. Events that ask a
    question stop here and wait; events that simply happen apply themselves and move on.
    """
    if not events:
        return

    event = table.draw(
        events,
        state.snapshot(),
        rng,
        state.fired_events,
        # Guarded, because `xs[-0:]` is the whole list, not the empty one, so a cooldown
        # of zero would silently mean "never repeat, ever" rather than "no cooldown".
        recent=(
            state.fired_events[-balance.EVENT_COOLDOWN :]
            if balance.EVENT_COOLDOWN
            else ()
        ),
    )
    if event is None:
        return

    state.fired_events.append(event.id)
    report.event_id = event.id
    report.note(event.title)

    if event.has_choices:
        state.pending = PendingChoice(
            event_id=event.id,
            title=event.title,
            body=event.body,
            options=event.options,
        )
    elif not event.effect.is_empty:
        apply_effect(state, event.effect)


def _grow(state: GameState, rng: Rng, report: TurnReport) -> None:
    population = state.population

    matured = population.mature()
    report.matured = matured
    if matured:
        report.note(f"{matured} came of age.")

    # Growth is per household and deterministic. The old gate asked whether the *clan* had
    # forty food and decent morale, which is a question about nobody, and it almost never came
    # back yes: measured across a full run the clan simply never grew, labour stayed capped at
    # the six it started with, and ground past what six hands could work was worthless. That
    # is the plateau, and this is the fix for it.
    born = population.grow(
        target=balance.BOND_TO_BEAR,
        mood_floor=balance.BOND_MOOD_THRESHOLD,
        needs_adults=balance.BOND_NEEDS_ADULTS,
        lost=balance.BOND_LOST_TO_HUNGER,
        matures_after=balance.CHILD_MATURES_AFTER,
    )
    report.born = born
    if born:
        report.note(
            f"{born} child was born to the hearth."
            if born == 1
            else f"{born} children were born to the clan."
        )

    split = population.split_crowded(balance.HOUSEHOLD_SPLITS_AT)
    report.households_split = split
    if split:
        report.note(
            f"{split} hearth outgrew itself and set up its own fire."
            if split == 1
            else f"{split} hearths outgrew themselves and set up their own fires."
        )

    # Hunger is remembered for exactly one season by the growth rules; the lasting record of
    # it is the bond that was knocked back and the resentment that was not.
    population.clear_hunger()

    # Morale drifts back toward the middle when nothing pushes it, so one bad winter does
    # not flatten the clan for the rest of the run and leave every later event landing on
    # the floor.
    for household in population.households:
        if household.mood < balance.MORALE_DRIFT_TARGET:
            household.mood += 1
        elif household.mood > balance.MORALE_DRIFT_TARGET:
            household.mood -= 1


def _advance(state: GameState, report: TurnReport) -> None:
    state.turn += 1
    _judge(state)
    report.outcome = state.outcome
    report.pending = state.pending
    if state.outcome is Outcome.BURIED:
        report.note("No one is left to keep the fire. The hearth goes out.")
    elif state.outcome is Outcome.ENDURED:
        report.note("Five winters. The fire is still lit.")


# --- Helpers -----------------------------------------------------------------------------


def _judge(state: GameState) -> None:
    """Decide whether the run is over.

    Dying overrides having finished, and can do so after the fact: an event choice answered
    on the last turn that kills the last adult buries the clan even though the clock had
    already run out. Surviving the run is not a shield against the answer you just gave.
    """
    if state.population.adults <= 0:
        state.outcome = Outcome.BURIED
    elif state.outcome is None and state.turn >= balance.TURNS_PER_RUN:
        state.outcome = Outcome.ENDURED


def _clamp_morale(value: int) -> int:
    return max(balance.MORALE_MIN, min(balance.MORALE_MAX, value))


def _ground_phrase(state: GameState, take: ForageTake) -> str:
    """Name the ground a season's foraging was actually done on.

    Two forms only. Listing five tiles would bury the number the line exists to carry, and
    naming the best one is what the player needs in order to think about where to scout next.
    """
    if not take.worked:
        return "nowhere"

    coord, terrain, _ = take.worked[0]
    best = _place(state, coord, terrain)
    others = len(take.worked) - 1
    if not others:
        return best
    return f"{best} and {others} place{'s' if others > 1 else ''} besides"


def _place(state: GameState, coord: Coord, terrain: Terrain) -> str:
    if coord == state.world.home:
        return f"the {terrain} at the hearth"
    return f"the {terrain} to the {_bearing(state, coord)}"


def _bearing(state: GameState, target: Coord) -> str:
    """A rough compass word for a revealed tile, relative to the hearth."""
    home_x, home_y = state.world.home
    x, y = target
    vertical = "north" if y < home_y else "south" if y > home_y else ""
    horizontal = "west" if x < home_x else "east" if x > home_x else ""
    return f"{vertical}{horizontal}" or "edge of the clearing"
