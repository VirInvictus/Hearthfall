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
    recent: Collection[str] = (),
) -> list[Event]:
    """Every event whose conditions hold, is not used up, and is not still fresh in the mouth.

    `recent` is the cooldown. A repeatable event is repeatable across a run, not across three
    consecutive seasons: measured before this existed, every single run in a sixty-seed sample
    replayed at least one event verbatim, and the worst offender came round an extra 49 times
    across those runs. Reading the same paragraph three times in twenty seasons is what makes a
    corpus feel thin, whatever its size.

    This is a rule about the draw, not an enrichment of the event format. Nothing in the TOML
    changes, and the fix for a thin corpus is still to write more of it.
    """
    return [
        event
        for event in events
        if not (event.once and event.id in already_fired)
        and event.id not in recent
        and matches(event.when, snapshot)
    ]


def draw(
    events: Sequence[Event],
    snapshot: Snapshot,
    rng: Rng,
    already_fired: Collection[str] = (),
    recent: Collection[str] = (),
) -> Event | None:
    """Draw one eligible event by weight, or None when the world permits nothing.

    A turn with no eligible event is a normal, quiet turn, not an error. Early corpora will
    have plenty of them, and a cooldown makes them slightly more common, which is the right
    trade: a quiet season reads as a quiet season, a repeated one reads as a bug.
    """
    candidates = eligible(events, snapshot, already_fired, recent)
    if not candidates:
        return None
    return rng.weighted([(event, event.weight) for event in candidates])
