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
from hearthfall.engine.events.loader import Event
from hearthfall.engine.intel import Ledger
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


@dataclass
class TurnReport:
    """What happened, in numbers the caller can render and in lines it can print.

    The frontend computes nothing. If the player should see it, it is in here.
    """

    turn: int
    season: Season
    produced: int = 0
    consumed: int = 0
    shortfall: int = 0
    starved: int = 0
    spoiled: int = 0
    matured: int = 0
    born: int = 0
    revealed: Coord | None = None
    revealed_terrain: Terrain | None = None
    event_id: str | None = None
    log: list[str] = field(default_factory=list)
    pending: PendingChoice | None = None
    outcome: Outcome | None = None

    def note(self, line: str) -> None:
        self.log.append(line)


@dataclass(frozen=True)
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

    produced = orders.forage * balance.FORAGE_YIELD[season]
    opening = state.stores.food
    after_produce = opening + produced

    winter_extra = balance.WINTER_EXTRA_FOOD if season is Season.WINTER else 0
    demand = population.adults * (
        balance.FOOD_PER_ADULT + winter_extra
    ) + population.child_count * (balance.FOOD_PER_CHILD + winter_extra)
    eaten = min(demand, after_produce)
    shortfall = demand - eaten
    would_starve = (
        min(
            math.ceil(shortfall / balance.FOOD_PER_STARVATION_DEATH),
            population.total,
        )
        if shortfall
        else 0
    )

    after_eat = after_produce - eaten
    rate = max(
        balance.SPOIL_RATE_FLOOR,
        balance.SPOIL_RATE[season] - orders.tend * balance.SPOIL_REDUCTION_PER_TENDER,
    )
    spoiled = int(after_eat * rate)

    return Forecast(
        season=season,
        produced=produced,
        demand=demand,
        eaten=eaten,
        shortfall=shortfall,
        would_starve=would_starve,
        spoil_rate=rate,
        spoiled=spoiled,
        opening_food=opening,
        closing_food=after_eat - spoiled,
    )


def new_game(seed: int) -> GameState:
    """A fresh run. Everything downstream of this is a function of the seed."""
    rng = Rng(seed)
    world = World.generate(
        width=balance.MAP_WIDTH,
        height=balance.MAP_HEIGHT,
        rng=rng,
        weights=balance.TERRAIN_WEIGHTS,
    )
    # The clan knows the ground it is standing on and nothing else. Revealing home is a fact
    # about the clan, which is why it happens here and not inside World.generate.
    ledger = Ledger(halflives=balance.FACT_HALFLIFE)
    ledger.reveal(world, world.home, turn=0)
    return GameState(
        seed=seed,
        world=world,
        ledger=ledger,
        population=Population(
            adults=balance.STARTING_ADULTS,
            children=[balance.CHILD_MATURES_AFTER] * balance.STARTING_CHILDREN,
            morale=balance.STARTING_MORALE,
        ),
        stores=Stores(food=balance.STARTING_FOOD),
    )


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
    _consume(state, report)
    _starve(state, report)
    _spoil(state, orders, season, report)
    _explore(state, orders, rng, report)
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
    state.population.morale = _clamp_morale(state.population.morale + effect.morale)
    state.population.adults = max(0, state.population.adults + effect.adults)

    for _ in range(effect.children):
        state.population.children.append(balance.CHILD_MATURES_AFTER)
    for _ in range(-effect.children):
        _take_a_child(state.population)


# --- Steps, in resolution order ---------------------------------------------------------


def _produce(
    state: GameState, orders: Orders, season: Season, report: TurnReport
) -> None:
    produced = orders.forage * balance.FORAGE_YIELD[season]
    state.stores.food += produced
    report.produced = produced
    if produced:
        report.note(f"Foragers brought in {produced} food.")
    elif orders.forage:
        report.note("The foragers came back with nothing.")


def _consume(state: GameState, report: TurnReport) -> None:
    population = state.population
    winter_extra = balance.WINTER_EXTRA_FOOD if state.season is Season.WINTER else 0
    demand = population.adults * (
        balance.FOOD_PER_ADULT + winter_extra
    ) + population.child_count * (balance.FOOD_PER_CHILD + winter_extra)
    eaten = min(demand, state.stores.food)
    state.stores.food -= eaten
    report.consumed = eaten
    report.shortfall = demand - eaten
    report.note(f"{population.total} mouths ate {eaten} food.")


def _starve(state: GameState, report: TurnReport) -> None:
    if not report.shortfall:
        return

    population = state.population
    deaths = math.ceil(report.shortfall / balance.FOOD_PER_STARVATION_DEATH)
    deaths = min(deaths, population.total)

    for _ in range(deaths):
        if population.children:
            _take_a_child(population)
        else:
            population.adults -= 1

    report.starved = deaths
    population.morale = _clamp_morale(
        population.morale
        - balance.MORALE_LOSS_PER_STARVATION
        - deaths * balance.MORALE_LOSS_PER_DEATH
    )
    report.note(
        f"The stores ran {report.shortfall} short. {deaths} did not survive it."
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


def _explore(state: GameState, orders: Orders, rng: Rng, report: TurnReport) -> None:
    if orders.explore < balance.EXPLORERS_PER_REVEAL:
        if orders.explore:
            report.note("Too few went out to find anything worth the walk.")
        return

    frontier = state.ledger.frontier(state.world)
    if not frontier:
        report.note("There is nothing left within reach to walk into.")
        return

    target = orders.explore_target
    if target is None:
        target = rng.choice(frontier)
    elif target not in frontier:
        raise ValueError(f"{target} is not on the frontier; it cannot be explored into")

    # Learned this turn, before _advance ticks the clock, so the fact is stamped with the
    # season the scouts actually walked it.
    state.ledger.reveal(state.world, target, state.turn)
    tile = state.world.tile(target)
    state.last_revealed = tile.terrain
    report.revealed = target
    report.revealed_terrain = tile.terrain
    report.note(
        f"The scouts came back knowing {tile.terrain} to the {_bearing(state, target)}."
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

    event = table.draw(events, state.snapshot(), rng, state.fired_events)
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

    remaining: list[int] = []
    matured = 0
    for turns_left in population.children:
        if turns_left <= 1:
            matured += 1
        else:
            remaining.append(turns_left - 1)
    population.children = remaining
    population.adults += matured
    report.matured = matured
    if matured:
        report.note(f"{matured} came of age.")

    if (
        state.stores.food >= balance.BIRTH_FOOD_THRESHOLD
        and population.morale >= balance.BIRTH_MORALE_THRESHOLD
        and rng.chance(balance.BIRTH_CHANCE)
    ):
        population.children.append(balance.CHILD_MATURES_AFTER)
        report.born = 1
        report.note("A child was born to the hearth.")

    # Morale drifts back toward the middle when nothing pushes it, so one bad winter does
    # not flatten the clan for the rest of the run and leave every later event landing on
    # the floor.
    if population.morale < balance.MORALE_DRIFT_TARGET:
        population.morale += 1
    elif population.morale > balance.MORALE_DRIFT_TARGET:
        population.morale -= 1


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


def _take_a_child(population: Population) -> None:
    """Remove the child furthest from maturity.

    Deterministic, and it leaves the clan the ones closest to being hands. That is the
    kinder outcome mechanically and the colder one to read, which is about right.
    """
    if not population.children:
        return
    population.children.remove(max(population.children))


def _clamp_morale(value: int) -> int:
    return max(balance.MORALE_MIN, min(balance.MORALE_MAX, value))


def _bearing(state: GameState, target: Coord) -> str:
    """A rough compass word for a revealed tile, relative to the hearth."""
    home_x, home_y = state.world.home
    x, y = target
    vertical = "north" if y < home_y else "south" if y > home_y else ""
    horizontal = "west" if x < home_x else "east" if x > home_x else ""
    return f"{vertical}{horizontal}" or "edge of the clearing"
