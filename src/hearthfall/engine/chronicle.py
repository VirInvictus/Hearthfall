from dataclasses import dataclass

from hearthfall.engine.state import Season


@dataclass(slots=True)
class ChronicleEntry:
    turn: int
    season: Season
    # The summary of the season, akin to the lines in TurnReport
    lines: list[str]
    # For events
    event_title: str | None = None
    event_body: str | None = None
    choice_taken: str | None = None
