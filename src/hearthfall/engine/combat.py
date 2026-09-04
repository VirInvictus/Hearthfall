"""Abstract combat resolution.

`spec.md` §"Combat (later)" is the contract: two stacks meet, the engine weighs what
it knows, and the outcome carries real stakes. This slice is that contract's dumb
first version, and deliberately so — your strength against theirs, one roll. Terrain,
morale, intel quality, and named stakes arrive in the slices that follow as modifiers
on the odds and grades on the margin; the roll itself stays a single draw so a fight
is always reproducible and always readable from the chronicle.

The odds are our share of the total strength on the field. One uniform draw against
that share decides the fight, which makes the whole thing a pure function of
(strengths, rng draw) and keeps slice 5's stakes honest: the margin — how far the
roll landed from the decision boundary — says whether a win was a rout or a
coin-flip that happened to go our way.
"""

from __future__ import annotations

from dataclasses import dataclass

from hearthfall.engine.rng import Rng


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


def resolve(ours: int, theirs: int, rng: Rng) -> Outcome:
    """Resolve one fight: our strength against theirs, one roll.

    The odds are `ours / (ours + theirs)` — our share of the strength on the
    field. Zero strength on our side loses without appeal; a fight against
    nothing is won without a roll being meaningful.
    """
    total = ours + theirs
    odds = ours / total if total > 0 else 0.0
    roll = rng.fraction()
    won = roll < odds
    return Outcome(won=won, odds=odds, roll=roll, margin=odds - roll)
