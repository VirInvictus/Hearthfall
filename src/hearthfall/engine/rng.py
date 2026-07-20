"""The one random source.

Every random draw in the engine goes through an `Rng` instance that was handed to it. No
engine module may call `random` directly. The point is reproducibility: a seed replays a
run exactly, which is the difference between balancing a game and guessing at one.
"""

from __future__ import annotations

import random
from collections.abc import Sequence


class Rng:
    """A seeded, injectable random source."""

    def __init__(self, seed: int) -> None:
        self.seed = seed
        self._random = random.Random(seed)

    def __repr__(self) -> str:
        return f"Rng(seed={self.seed})"

    def chance(self, probability: float) -> bool:
        """True with the given probability. `chance(0.0)` and `chance(1.0)` are absolute."""
        return self._random.random() < probability

    def randint(self, low: int, high: int) -> int:
        """An integer in [low, high], both ends inclusive."""
        return self._random.randint(low, high)

    def choice[T](self, options: Sequence[T]) -> T:
        return self._random.choice(options)

    def shuffled[T](self, options: Sequence[T]) -> list[T]:
        """A shuffled copy. The input is left alone so callers can hold stable tables."""
        pool = list(options)
        self._random.shuffle(pool)
        return pool

    def weighted[T](self, options: Sequence[tuple[T, int]]) -> T:
        """Pick from (option, weight) pairs. This is how event tables draw.

        Weights of zero are excluded rather than merely improbable, so an event table can
        disable an entry by weighting it out.
        """
        pool = [(option, weight) for option, weight in options if weight > 0]
        if not pool:
            raise ValueError(
                "weighted() needs at least one option with a positive weight"
            )
        return self._random.choices(
            [option for option, _ in pool],
            weights=[weight for _, weight in pool],
            k=1,
        )[0]
