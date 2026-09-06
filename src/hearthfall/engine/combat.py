"""Abstract combat resolution.

`spec.md` §"Combat (later)" is the contract: two stacks meet, the engine weighs what
it knows, and the outcome carries real stakes. This slice is that contract's dumb
first version, and deliberately so — your strength against theirs, one roll. Terrain,
morale, intel quality, and named stakes arrive in the slices that follow as modifiers
on the odds and grades on the margin; the roll itself stays a single draw so a fight
is always reproducible and always readable from the chronicle.

The odds are each side's share of the *effective* strength on the field, and slices
layer what "effective" means. Slice 1 was raw numbers. Slice 2 weights each side by
the ground it stands on and by morale, both as multipliers applied before the share
is taken — so a quarter-again of hills is worth exactly what the balance table says
it is, and nothing about the roll changes. One uniform draw against the share still
decides the fight, which keeps the whole thing a pure function of (strengths,
modifiers, rng draw) and keeps slice 5's stakes honest: the margin — how far the
roll landed from the decision boundary — says whether a win was a rout or a
coin-flip that happened to go our way.
"""

from __future__ import annotations

from dataclasses import dataclass

from hearthfall.engine.balance import (
    COUNTER_BONUS,
    INTEL_COMBAT_FACTOR,
    MORALE_COMBAT_CEIL,
    MORALE_COMBAT_FLOOR,
    TERRAIN_COMBAT_WEIGHT,
)
from hearthfall.engine.intel import Staleness
from hearthfall.engine.rng import Rng
from hearthfall.engine.units import Composition, UnitDefs
from hearthfall.engine.world import Terrain


@dataclass(frozen=True, slots=True)
class Outcome:
    """The result of one resolved fight.

    `odds` is the pre-roll probability of victory and `roll` the draw itself;
    both are recorded so the chronicle can show a fight as a *readable fact*
    ("we were three-to-one up and still nearly lost it") rather than a bare
    boolean. `margin` is `odds - roll`: positive when the fight was won, and
    its size is how far the roll landed from the decision boundary. Slice 5
    grades the stakes by this.
    """

    won: bool
    odds: float
    roll: float
    margin: float


def _morale_factor(morale: int) -> float:
    """The linear 0-10 morale read: floor at broken, ceiling at jubilant,
    parity at five. Clamped, because a caller passing a bad number should get
    the extreme mood, not an exploding multiplier."""
    span = MORALE_COMBAT_CEIL - MORALE_COMBAT_FLOOR
    return MORALE_COMBAT_FLOOR + span * (morale / 10)


def _side_number(
    units: Composition, enemy: Composition | None, stat: str, defs: UnitDefs
) -> float:
    """A composition's number on its side of the share, web included.

    Each line contributes count × stat, multiplied by the counter bonus where
    the line counters what it faces: the share of the enemy composition made
    of types this line has under its `counters`, times
    `balance.COUNTER_BONUS`. One direction only: the countered side gets
    nothing, which is what makes reading the massing matter. A scalar enemy
    (no composition) offers nothing to counter, so a wall facing a hand-built
    band fights at its plain stats.
    """
    enemy_total = enemy.total() if enemy is not None else 0
    number = 0.0
    for key, count in units.counts:
        unit = defs.get(key)
        if unit is None:
            raise ValueError(
                f"composition names {key!r}, which no declared unit type answers"
            )
        weight = 1.0
        if enemy is not None and enemy_total:
            countered = sum(enemy.count(target) for target in unit.counters)
            weight += COUNTER_BONUS * countered / enemy_total
        number += count * getattr(unit, stat) * weight
    return number


def resolve(
    ours: int,
    theirs: int,
    rng: Rng,
    *,
    our_ground: Terrain | None = None,
    their_ground: Terrain | None = None,
    our_morale: int | None = None,
    their_morale: int | None = None,
    intel_staleness: Staleness | None = None,
    our_units: Composition | None = None,
    their_units: Composition | None = None,
    unit_defs: UnitDefs | None = None,
) -> Outcome:
    """Resolve one fight: our strength against theirs, one roll.

    The modifiers scale each side's strength before the share is taken, and
    every one of them is optional — `None` means "not factored", which keeps
    slice 1's calls valid and the dumb version reachable. Terrain is the ground
    each side stands on (weighted per `balance.TERRAIN_COMBAT_WEIGHT`); morale
    is the clan-wide 0-10 average (`balance`'s floor/ceiling band, parity at 5);
    `intel_staleness` is how old our read of the enemy was when we committed
    (slice 3: stale intel scales OUR side down — you positioned for the enemy
    you read about, not the one across the field).

    A composition replaces its side's scalar number, and the game's grammar
    decides which stat prices it: the first side is the line that holds, so
    `our_units` is weighed by its *guard* — what a band must break to reach
    the granary. The second side is the one that presses, so `their_units` is
    weighed by its *strength* — what presses. The scalars keep playing both
    roles, which is why a scalar call and a spear line of the same count are
    the same wall. Both compositions together require `unit_defs`; one alone
    prices against the scalars on the other side.

    Zero effective strength on our side loses without appeal; a fight against
    nothing is won without a roll being meaningful.
    """
    our_number: float = float(ours)
    their_number: float = float(theirs)
    if our_units is not None or their_units is not None:
        if unit_defs is None:
            raise ValueError(
                "a composition needs the declared unit types to be priced against"
            )
        if our_units is not None:
            our_number = _side_number(our_units, their_units, "guard", unit_defs)
        if their_units is not None:
            their_number = _side_number(their_units, our_units, "strength", unit_defs)
    ours_eff = (
        our_number
        * (
            TERRAIN_COMBAT_WEIGHT.get(our_ground, 1.0)
            if our_ground is not None
            else 1.0
        )
        * (_morale_factor(our_morale) if our_morale is not None else 1.0)
        * (INTEL_COMBAT_FACTOR[intel_staleness] if intel_staleness is not None else 1.0)
    )
    theirs_eff = (
        their_number
        * (
            TERRAIN_COMBAT_WEIGHT.get(their_ground, 1.0)
            if their_ground is not None
            else 1.0
        )
        * (_morale_factor(their_morale) if their_morale is not None else 1.0)
    )
    total = ours_eff + theirs_eff
    odds = ours_eff / total if total > 0 else 0.0
    roll = rng.fraction()
    won = roll < odds
    return Outcome(won=won, odds=odds, roll=roll, margin=odds - roll)


def raid_deaths(margin: float) -> int:
    """Graves for a lost fight, graded by the margin.

    A near-run loss costs one — blood, but few graves. A rout costs the full
    band of them. The dead are the price of the read and the order, so they
    scale with how far the draw landed from the decision boundary, capped at
    what a small clan can bury.
    """
    from hearthfall.engine import balance

    deaths = round(-margin * balance.RAID_DEATHS_PER_MARGIN)
    return max(1, min(balance.RAID_DEATHS_MAX, deaths))


def is_rout(margin: float) -> bool:
    """Whether a won or lost fight was a rout — decisive enough that the band
    scattered beyond shadowing distance, marking its camp on the map."""
    from hearthfall.engine import balance

    return abs(margin) >= balance.RAID_WIN_REVEAL_MARGIN
