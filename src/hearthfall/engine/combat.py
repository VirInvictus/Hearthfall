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
    MORALE_COMBAT_CEIL,
    MORALE_COMBAT_FLOOR,
    TERRAIN_COMBAT_WEIGHT,
)
from hearthfall.engine.rng import Rng
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


def resolve(
    ours: int,
    theirs: int,
    rng: Rng,
    *,
    our_ground: Terrain | None = None,
    their_ground: Terrain | None = None,
    our_morale: int | None = None,
    their_morale: int | None = None,
) -> Outcome:
    """Resolve one fight: our strength against theirs, one roll.

    The modifiers scale each side's strength before the share is taken, and
    every one of them is optional — `None` means "not factored", which keeps
    slice 1's calls valid and the dumb version reachable. Terrain is the ground
    each side stands on (weighted per `balance.TERRAIN_COMBAT_WEIGHT`); morale
    is the clan-wide 0-10 average (`balance`'s floor/ceiling band, parity at 5).

    Zero effective strength on our side loses without appeal; a fight against
    nothing is won without a roll being meaningful.
    """
    ours_eff = (
        ours
        * (
            TERRAIN_COMBAT_WEIGHT.get(our_ground, 1.0)
            if our_ground is not None
            else 1.0
        )
        * (_morale_factor(our_morale) if our_morale is not None else 1.0)
    )
    theirs_eff = (
        theirs
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
