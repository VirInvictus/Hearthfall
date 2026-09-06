from dataclasses import dataclass, field

Coord = tuple[int, int]
from hearthfall.engine.people import Rationing


@dataclass(slots=True)
class Orders:
    """Labor allocation."""

    forage: int = 0
    scout: int = 0
    tend: int = 0
    # Adults standing guard instead of working. Every spear is a hand not
    # foraging: the raid trade is the scarcity trade. This is the spear line;
    # other lines stand beside it in `militia_lines`.
    militia: int = 0
    # Adults on the works: raising whatever the ladder calls for next. What
    # gets built is the engine's call; the hands are the decision.
    work: int = 0
    # Extra militia lines assembled from declared unit types, as type id ->
    # hands. The ids are checked against the state's unit registry when a raid
    # resolves, so a misspelled line fails loudly rather than fielding
    # nothing. Each hand here competes for the same adults as every other
    # order; what differs is what the line is worth when the band comes.
    militia_lines: dict[str, int] = field(default_factory=dict[str, int])
    scout_target: Coord | None = None
    rationing: Rationing = Rationing.EQUAL
    is_standing: bool = False

    @property
    def assigned(self) -> int:
        lines = sum(self.militia_lines.values())
        return self.forage + self.scout + self.tend + self.militia + self.work + lines

    def validate(self, adults: int) -> None:
        if self.assigned > adults:
            raise ValueError(f"orders require {self.assigned} hands, clan has {adults}")
        if (
            self.forage < 0
            or self.scout < 0
            or self.tend < 0
            or self.militia < 0
            or self.work < 0
        ):
            raise ValueError("orders cannot assign negative hands")
        if any(count < 0 for count in self.militia_lines.values()):
            raise ValueError("orders cannot assign negative hands")
