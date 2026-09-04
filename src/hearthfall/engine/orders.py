from dataclasses import dataclass

Coord = tuple[int, int]
from hearthfall.engine.people import Rationing


@dataclass(slots=True)
class Orders:
    """Labor allocation."""

    forage: int = 0
    scout: int = 0
    tend: int = 0
    # Adults standing guard instead of working. Every spear is a hand not
    # foraging: the raid trade is the scarcity trade.
    militia: int = 0
    scout_target: Coord | None = None
    rationing: Rationing = Rationing.EQUAL
    is_standing: bool = False

    @property
    def assigned(self) -> int:
        return self.forage + self.scout + self.tend + self.militia

    def validate(self, adults: int) -> None:
        if self.assigned > adults:
            raise ValueError(f"orders require {self.assigned} hands, clan has {adults}")
        if self.forage < 0 or self.scout < 0 or self.tend < 0 or self.militia < 0:
            raise ValueError("orders cannot assign negative hands")
