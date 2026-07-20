"""Choosing which event fires.

Filter the corpus down to what the world currently permits, then draw one by weight. Both
halves go through the injected `Rng`, so a seed replays the same story beats in the same
order.
"""

from __future__ import annotations

from collections.abc import Collection, Sequence

from hearthfall.engine.events.conditions import Snapshot, matches
from hearthfall.engine.events.loader import Event
from hearthfall.engine.rng import Rng


def eligible(
    events: Sequence[Event],
    snapshot: Snapshot,
    already_fired: Collection[str] = (),
) -> list[Event]:
    """Every event whose conditions hold and which has not been used up."""
    return [
        event
        for event in events
        if not (event.once and event.id in already_fired)
        and matches(event.when, snapshot)
    ]


def draw(
    events: Sequence[Event],
    snapshot: Snapshot,
    rng: Rng,
    already_fired: Collection[str] = (),
) -> Event | None:
    """Draw one eligible event by weight, or None when the world permits nothing.

    A turn with no eligible event is a normal, quiet turn, not an error. Early corpora will
    have plenty of them.
    """
    candidates = eligible(events, snapshot, already_fired)
    if not candidates:
        return None
    return rng.weighted([(event, event.weight) for event in candidates])
