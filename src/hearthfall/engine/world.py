"""The map: tiles, terrain, and geometry. Nothing about what the player knows.

Knowledge used to live here as `Tile.revealed`. It moved to `intel.py` when the spine was
generalised (`spec.md` §1): fog is a property of a fact, not of a tile, and keeping a second
copy of it here would have meant two answers to "do we know this ground" that had to be kept
agreeing. The world is now just what is true; the ledger is what the clan believes.

Sizes and weights arrive as arguments rather than being read from `balance`, which keeps this
module a leaf and the import graph acyclic.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum

from hearthfall.engine.rng import Rng

Coord = tuple[int, int]


class Terrain(StrEnum):
    PLAIN = "plain"
    FOREST = "forest"
    HILLS = "hills"
    MARSH = "marsh"
    WATER = "water"


@dataclass(slots=True)
class Tile:
    terrain: Terrain


@dataclass(slots=True)
class World:
    width: int
    height: int
    home: Coord
    # The parameterised factory is not decoration: a bare `dict` makes the field's element
    # types unknown to a strict checker, and that unknown then spreads to every caller.
    tiles: dict[Coord, Tile] = field(default_factory=dict[Coord, Tile])

    @classmethod
    def generate(
        cls,
        width: int,
        height: int,
        rng: Rng,
        weights: dict[Terrain, int],
    ) -> World:
        """Build a map. Every tile exists and every tile is unknown to anybody.

        Coordinates are walked in sorted order so the same seed lays down the same terrain
        regardless of how a dict happens to iterate. Revealing the home tile is the caller's
        job now; it is a fact about the clan, not about the ground.
        """
        home = (width // 2, height // 2)
        table = [(terrain, weight) for terrain, weight in weights.items()]
        tiles = {
            (x, y): Tile(terrain=rng.weighted(table))
            for y in range(height)
            for x in range(width)
        }
        # The hearth stands on ground you can live on, whatever the draw said.
        tiles[home] = Tile(terrain=Terrain.PLAIN)
        return cls(width=width, height=height, home=home, tiles=tiles)

    def tile(self, coord: Coord) -> Tile:
        return self.tiles[coord]

    def in_bounds(self, coord: Coord) -> bool:
        x, y = coord
        return 0 <= x < self.width and 0 <= y < self.height

    def neighbours(self, coord: Coord) -> list[Coord]:
        """Orthogonal neighbours, in sorted order for determinism."""
        x, y = coord
        candidates = [(x, y - 1), (x - 1, y), (x + 1, y), (x, y + 1)]
        return sorted(c for c in candidates if self.in_bounds(c))
