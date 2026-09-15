"""The run's record, as typed entries the skin renders.

Engine-side on purpose (`spec.md` §3): the frontend computes nothing, and a
chronicle the skin assembled would break that on day one. One entry per
resolved season, in resolution order; the driver appends them and nothing
else writes to the list.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from hearthfall.engine.state import Season


@dataclass(slots=True)
class ChronicleEntry:
    turn: int
    season: Season
    # The season's lines, exactly as the TurnReport logged them.
    lines: list[str]
    # When the season ended on a fired event: the corpus's title and body,
    # filled by the driver from the event the id names. A quiet season has
    # neither, and the pane renders the season bare.
    event_title: str | None = None
    event_body: str | None = None
    # The answer, once an option is chosen (`turn.apply_choice` writes it).
    choice_taken: str | None = None
