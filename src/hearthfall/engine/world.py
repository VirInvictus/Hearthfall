"""The map: tiles, terrain, and fog.

In Phase 0 terrain is flavor and an event key. It gates no resources and no yields; that is
Phase 2's job. What matters here is that the fog exists, that revealing costs hands, and
that reveal order is reproducible from a seed.

Sizes and weights arrive as arguments rather than being read from `balance`, which keeps
this module a leaf and the import graph acyclic.
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


@dataclass
class Tile:
    terrain: Terrain
    revealed: bool = False


@dataclass
class World:
    width: int
    height: int
    home: Coord
    tiles: dict[Coord, Tile] = field(default_factory=dict)

    @classmethod
    def generate(
        cls,
        width: int,
        height: int,
        rng: Rng,
        weights: dict[Terrain, int],
    ) -> World:
        """Build a fogged map with the home tile revealed at the centre.

        Coordinates are walked in sorted order so the same seed lays down the same terrain
        regardless of how a dict happens to iterate.
        """
        home = (width // 2, height // 2)
        table = [(terrain, weight) for terrain, weight in weights.items()]
        tiles = {
            (x, y): Tile(terrain=rng.weighted(table))
            for y in range(height)
            for x in range(width)
        }
        # The hearth stands on ground you can live on, whatever the draw said.
        tiles[home] = Tile(terrain=Terrain.PLAIN, revealed=True)
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

    def revealed(self) -> list[Coord]:
        return sorted(coord for coord, tile in self.tiles.items() if tile.revealed)

    def frontier(self) -> list[Coord]:
        """Unrevealed tiles orthogonally adjacent to something known.

        This is the set the player may explore into: the map opens outward from the hearth
        rather than letting anyone poke at a far corner.
        """
        edge = {
            neighbour
            for coord in self.revealed()
            for neighbour in self.neighbours(coord)
            if not self.tiles[neighbour].revealed
        }
        return sorted(edge)

    def reveal(self, coord: Coord) -> Tile:
        tile = self.tiles[coord]
        tile.revealed = True
        return tile

    @property
    def known_count(self) -> int:
        return sum(1 for tile in self.tiles.values() if tile.revealed)

    @property
    def unknown_count(self) -> int:
        return len(self.tiles) - self.known_count

    @property
    def fully_explored(self) -> bool:
        return not self.frontier()
