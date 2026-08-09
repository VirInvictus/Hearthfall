"""What the scouts say.

`spec.md` §1: a report is rendered facts. These tests hold the renderer to that literally.
Every sentence it produces has to come from something in the ledger, and a season where the
party learned nothing has to be a season where it says nothing, because prose that appears
whether or not anything happened is prose the player learns to skip.
"""

from __future__ import annotations

import unittest

from hearthfall.engine import balance, reports
from hearthfall.engine.intel import Ledger
from hearthfall.engine.world import Terrain, Tile, World

HOME = (2, 2)


def a_world(*, filled: Terrain = Terrain.PLAIN) -> World:
    """A 5x5 world of one terrain, so a test can place the exceptions it cares about."""
    tiles = {(x, y): Tile(terrain=filled) for y in range(5) for x in range(5)}
    return World(width=5, height=5, home=HOME, tiles=tiles)


def a_ledger(world: World, *coords: tuple[int, int]) -> Ledger:
    ledger = Ledger(halflives=balance.FACT_HALFLIFE)
    for coord in (HOME, *coords):
        ledger.reveal(world, coord, turn=0)
    return ledger


class TestVoice(unittest.TestCase):
    def test_small_numbers_are_words(self):
        # "three can work it" is a sentence; "3 can work it" is a readout in a paragraph.
        self.assertEqual(reports.count(3), "three")
        self.assertEqual(reports.count(0), "no one")

    def test_large_numbers_fall_back_to_digits(self):
        self.assertEqual(reports.count(40), "40")

    def test_a_bearing_is_relative_to_the_hearth(self):
        world = a_world()
        self.assertEqual(reports.bearing(world, (2, 0)), "north")
        self.assertEqual(reports.bearing(world, (0, 4)), "southwest")
        self.assertEqual(reports.bearing(world, HOME), "edge of the clearing")

    def test_the_hearth_is_named_as_the_hearth(self):
        world = a_world()
        self.assertEqual(
            reports.place(world, HOME, Terrain.PLAIN), "the plain at the hearth"
        )


class TestTheWalk(unittest.TestCase):
    def test_the_party_says_where_it_went_and_what_is_there(self):
        world = a_world()
        world.tiles[(2, 1)] = Tile(terrain=Terrain.FOREST)
        ledger = a_ledger(world, (2, 1))
        lines = reports.scout_report(world, ledger, (2, 1), None, looked=False)
        self.assertIn("The scouts walked north into forest.", lines)

    def test_the_best_ground_yet_is_worth_saying_out_loud(self):
        world = a_world()
        world.tiles[(2, 1)] = Tile(terrain=Terrain.FOREST)
        ledger = a_ledger(world, (2, 1))
        lines = reports.scout_report(world, ledger, (2, 1), None, looked=False)
        self.assertIn("It is the best ground the clan has found.", lines)

    def test_dead_ground_is_named_as_dead(self):
        world = a_world()
        world.tiles[(2, 1)] = Tile(terrain=Terrain.WATER)
        ledger = a_ledger(world, (2, 1))
        lines = reports.scout_report(world, ledger, (2, 1), None, looked=False)
        self.assertIn("Nothing will be taken from it.", lines)

    def test_middling_ground_gets_no_verdict_at_all(self):
        # The line exists for the seasons that are worth something. A verdict on every tile
        # is a verdict on none, and the player stops reading it by year two.
        world = a_world()
        ledger = a_ledger(world, (2, 1))
        lines = reports.scout_report(world, ledger, (2, 1), None, looked=False)
        self.assertEqual(lines, ["The scouts walked north into plain."])

    def test_the_first_ground_past_the_hearth_is_judged_against_the_hearth(self):
        world = a_world()
        world.tiles[(2, 1)] = Tile(terrain=Terrain.MARSH)
        ledger = a_ledger(world, (2, 1))
        lines = reports.scout_report(world, ledger, (2, 1), None, looked=False)
        self.assertIn("Poorer ground than anything the clan already holds.", lines)


class TestTheSurvey(unittest.TestCase):
    def test_surveying_what_it_walked_into_reads_as_one_visit(self):
        world = a_world()
        world.tiles[(2, 1)] = Tile(terrain=Terrain.FOREST)
        ledger = a_ledger(world, (2, 1))
        lines = reports.scout_report(world, ledger, (2, 1), (2, 1), looked=True)
        self.assertIn(
            "They stayed to work out what it will feed: three can work it.", lines
        )

    def test_surveying_elsewhere_names_the_place(self):
        # Otherwise the sentence is a non sequitur, which is exactly what it reads like when
        # the party walks one way and gives its proper look to ground it already knew.
        world = a_world()
        world.tiles[(1, 2)] = Tile(terrain=Terrain.FOREST)
        ledger = a_ledger(world, (1, 2), (2, 1))
        lines = reports.scout_report(world, ledger, (2, 1), (1, 2), looked=True)
        self.assertIn(
            "On the way back they worked out the forest to the west: three can work it.",
            lines,
        )

    def test_a_party_that_looked_and_found_nothing_says_so(self):
        world = a_world()
        ledger = a_ledger(world, (2, 1))
        lines = reports.scout_report(world, ledger, (2, 1), None, looked=True)
        self.assertIn("They found nothing else worth a closer look.", lines)

    def test_a_party_too_small_to_survey_is_not_made_to_apologise_for_it(self):
        world = a_world()
        ledger = a_ledger(world, (2, 1))
        lines = reports.scout_report(world, ledger, (2, 1), None, looked=False)
        self.assertNotIn("They found nothing else worth a closer look.", lines)


class TestTheFrontier(unittest.TestCase):
    """How much dark is left, said only when it is news."""

    def test_a_wide_open_map_is_not_counted_out_every_season(self):
        world = a_world()
        ledger = a_ledger(world, (2, 1))
        lines = reports.scout_report(world, ledger, (2, 1), None, looked=False)
        self.assertFalse([line for line in lines if "dark" in line])

    def test_a_frontier_still_open_is_not_remarked_on_at_all(self):
        world = a_world()
        ledger = Ledger(halflives=balance.FACT_HALFLIFE)
        for coord in world.tiles:
            if coord != (0, 0):
                ledger.reveal(world, coord, turn=0)
        lines = reports.scout_report(world, ledger, (1, 0), None, looked=False)
        self.assertFalse([line for line in lines if "within reach" in line])

    def test_a_closed_frontier_is_the_end_of_walking(self):
        world = a_world()
        ledger = Ledger(halflives=balance.FACT_HALFLIFE)
        for coord in world.tiles:
            ledger.reveal(world, coord, turn=0)
        lines = reports.scout_report(world, ledger, None, None, looked=True)
        self.assertIn("There is nothing more within reach to walk into.", lines)


class TestItOnlySpeaksFromTheLedger(unittest.TestCase):
    def test_a_tile_the_clan_has_not_walked_produces_no_account_of_it(self):
        # The renderer reads belief, like the food math does. If it reached into the world for
        # convenience it would be narrating ground nobody has stood on.
        world = a_world()
        world.tiles[(2, 1)] = Tile(terrain=Terrain.FOREST)
        ledger = a_ledger(world)  # (2, 1) never revealed
        lines = reports.scout_report(world, ledger, (2, 1), None, looked=False)
        self.assertFalse([line for line in lines if "forest" in line])

    def test_the_ground_worked_phrase_names_the_best_tile_and_counts_the_rest(self):
        world = a_world()
        worked = [
            ((1, 2), Terrain.FOREST, 9),
            (HOME, Terrain.PLAIN, 4),
            ((2, 1), Terrain.PLAIN, 2),
        ]
        self.assertEqual(
            reports.ground_worked(world, worked),
            "the forest to the west and 2 places besides",
        )

    def test_foraging_nowhere_says_nowhere(self):
        self.assertEqual(reports.ground_worked(a_world(), []), "nowhere")


if __name__ == "__main__":
    unittest.main()
