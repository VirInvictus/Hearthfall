from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from hearthfall.engine.people import Person
    from hearthfall.engine.rng import Rng
    from hearthfall.engine.state import ChoiceOption, GameState


class Tier(StrEnum):
    CLAN = "clan"
    RING = "ring"
    # CITY = "city" # Planned


@dataclass(slots=True)
class Council:
    # A list of Person IDs sitting on the council
    advisors: list[str] = field(default_factory=list)  # type: ignore


def check_emergence(state: GameState, rng: Rng) -> str | None:
    """Check if the clan crosses a tier boundary. Returns an event_id if they do."""
    if state.tier == Tier.CLAN and state.population.living_households >= 3:
        # e.g., if we reach 3 households, the ring emerges
        # The ring emerges
        return "emergence.the_ring"
    return None


def generate_person(state: GameState, household_id: int, rng: Rng) -> Person:
    """Draw a new named person from a household."""
    from hearthfall.engine.people import Ambition, Person, Trait

    names = [
        "Kael",
        "Vara",
        "Torin",
        "Elara",
        "Bram",
        "Lyra",
        "Orn",
        "Sia",
        "Rorik",
        "Fenn",
        "Marna",
    ]
    name = rng.choice(names)
    person_id = f"p_{state.next_person_id}"
    state.next_person_id += 1

    trait = rng.choice(list(Trait))
    ambition = rng.choice(list(Ambition))
    age = rng.randint(20, 50)

    person = Person(
        id=person_id,
        name=name,
        household_id=household_id,
        age=age,
        trait=trait,
        ambition=ambition,
    )
    state.cast[person_id] = person
    return person


def get_endorsements(
    state: GameState, options: tuple[ChoiceOption, ...]
) -> dict[int, list[str]]:
    """Determine which advisor endorses which option.

    Returns a dict mapping the option index to a list of endorsing advisor names.
    Advisors have characteristic biases based on their Ambition.
    """
    from hearthfall.engine.people import Ambition

    if not state.council or not options:
        return {}

    endorsements: dict[int, list[str]] = {i: [] for i in range(len(options))}

    for advisor_id in state.council.advisors:
        advisor = state.cast.get(advisor_id)
        if not advisor or not advisor.alive:
            continue

        # Score each option from the perspective of this advisor
        scores: list[tuple[int, int]] = []
        for i, opt in enumerate(options):
            score = 0
            eff = opt.effect
            if advisor.ambition == Ambition.CAUTIOUS:
                score += eff.food * 2
                score += eff.adults * 10
                score += eff.children * 10
            elif advisor.ambition == Ambition.MILITARISTIC:
                # Dislikes losing morale, likes bold actions
                score += eff.morale * 5
                # Doesn't mind spending food for a result
                if eff.food < 0 and eff.morale > 0:
                    score += 10
            elif advisor.ambition == Ambition.EXPANSIONIST:
                # Willing to sacrifice for gains
                if eff.food < 0:
                    score += 5
            elif advisor.ambition == Ambition.COMMUNAL:
                score += eff.morale * 5

            scores.append((score, i))

        # The advisor endorses their highest scoring option, if there is a clear winner
        # and if the score is not strictly terrible. If all are 0, they might just pick the first.
        scores.sort(reverse=True, key=lambda x: x[0])
        _best_score, best_idx = scores[0]
        endorsements[best_idx].append(advisor.name)

    return endorsements
