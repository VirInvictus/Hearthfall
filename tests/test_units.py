"""SP 7 slice 1: unit types with strengths and weaknesses.

The types are declared data, a group is counts per type, and the wall/press
grammar is what makes both numbers real: what holds the line is not what
hits. If these fail, composition cannot be balanced or replayed, which is
the whole point of keeping it abstract.
"""

from __future__ import annotations

import unittest

from hearthfall.engine import balance
from hearthfall.engine.combat import resolve
from hearthfall.engine.rng import Rng
from hearthfall.engine.units import (
    Composition,
    UnitDef,
    load_units,
    parse_units,
)

DEFS = load_units()


class TestTheShippedTypes(unittest.TestCase):
    def test_a_spear_is_the_scalar_militia(self):
        # The continuity pin: an order of N untyped militiamen and a line of
        # N spears price identically on both sides of the grammar, because
        # the spear carries MILITIA_STRENGTH_PER_ADULT as its two stats.
        spear = DEFS["spear"]
        self.assertEqual(spear.strength, balance.MILITIA_STRENGTH_PER_ADULT)
        self.assertEqual(spear.guard, balance.MILITIA_STRENGTH_PER_ADULT)

    def test_every_type_trades_press_against_hold(self):
        # The whole slice in one assertion: a type that is better at pressing
        # than a spear is worse at holding, or there is no decision here,
        # only a bigger number.
        for key, unit in DEFS.items():
            if key == "spear":
                continue
            self.assertNotEqual(
                unit.strength,
                unit.guard,
                f"{key} is balanced, and a balanced elite is just a spear",
            )

    def test_pressing_types_hold_badly(self):
        self.assertGreater(DEFS["bow"].strength, DEFS["bow"].guard)
        self.assertGreater(DEFS["axe"].strength, DEFS["axe"].guard)


class TestTheLoader(unittest.TestCase):
    def test_a_minimal_table_parses(self):
        defs = parse_units(
            """
            [unit.spear]
            name = "spear"
            strength = 2
            guard = 2
            """,
            "test.toml",
        )
        self.assertEqual(
            defs["spear"], UnitDef(key="spear", name="spear", strength=2, guard=2)
        )

    def test_unknown_top_level_keys_are_rejected(self):
        with self.assertRaises(ValueError) as ctx:
            parse_units("[units.spear]\nname = 'x'", "test.toml")
        self.assertIn("'units'", str(ctx.exception))

    def test_unknown_type_keys_are_rejected(self):
        with self.assertRaises(ValueError) as ctx:
            parse_units(
                """
                [unit.spear]
                name = "spear"
                strength = 2
                guard = 2
                reach = 3
                """,
                "test.toml",
            )
        self.assertIn("reach", str(ctx.exception))

    def test_negative_and_non_whole_stats_are_rejected(self):
        for text in (
            """
            [unit.spear]
            name = "spear"
            strength = -1
            guard = 2
            """,
            """
            [unit.spear]
            name = "spear"
            strength = 2.5
            guard = 2
            """,
        ):
            with self.subTest(text=text), self.assertRaises(ValueError):
                parse_units(text, "test.toml")

    def test_booleans_do_not_pass_as_whole_numbers(self):
        with self.assertRaises(ValueError):
            parse_units(
                """
                [unit.spear]
                name = "spear"
                strength = true
                guard = 2
                """,
                "test.toml",
            )

    def test_a_type_without_a_name_is_rejected(self):
        with self.assertRaises(ValueError):
            parse_units(
                """
                [unit.spear]
                strength = 2
                guard = 2
                """,
                "test.toml",
            )

    def test_broken_toml_names_its_source(self):
        with self.assertRaises(ValueError) as ctx:
            parse_units("[unit.spear", "test.toml")
        self.assertIn("test.toml", str(ctx.exception))

    def test_the_shipped_table_loads(self):
        self.assertIn("spear", DEFS)
        for unit in DEFS.values():
            self.assertGreaterEqual(unit.strength, 0)
            self.assertGreaterEqual(unit.guard, 0)


class TestComposition(unittest.TestCase):
    def test_counts_sort_and_zeroes_fall_away(self):
        group = Composition.of({"bow": 2, "spear": 0, "axe": -1})
        self.assertEqual(group.counts, (("bow", 2),))

    def test_a_group_is_an_immutable_value(self):
        group = Composition.of({"spear": 1})
        self.assertEqual(group, Composition.of({"spear": 1}))
        with self.assertRaises(AttributeError):
            group.counts = ()  # type: ignore[misc]

    def test_total_counts_heads(self):
        self.assertEqual(Composition.of({"spear": 2, "bow": 3}).total(), 5)

    def test_pricing_sums_the_declared_numbers(self):
        group = Composition.of({"spear": 2, "bow": 1})
        self.assertEqual(group.strength(DEFS), 2 * 2 + 3)
        self.assertEqual(group.guard(DEFS), 2 * 2 + 1)

    def test_an_undeclared_type_fails_loudly(self):
        group = Composition.of({"sling": 4})
        with self.assertRaises(ValueError) as ctx:
            group.strength(DEFS)
        self.assertIn("sling", str(ctx.exception))

    def test_an_empty_group_is_worth_nothing(self):
        empty = Composition.of({})
        self.assertEqual(empty.strength(DEFS), 0)
        self.assertEqual(empty.guard(DEFS), 0)


class TestCompositionCombat(unittest.TestCase):
    def test_a_spear_wall_prices_as_its_count_of_spears(self):
        scalar = resolve(10, 5, Rng(1))
        walled = resolve(
            10, 5, Rng(1), our_units=Composition.of({"spear": 5}), unit_defs=DEFS
        )
        self.assertEqual(scalar, walled)

    def test_the_pressing_side_is_weighed_by_strength(self):
        scalar = resolve(5, 4, Rng(1))
        pressing = resolve(
            5, 4, Rng(1), their_units=Composition.of({"axe": 1}), unit_defs=DEFS
        )
        self.assertEqual(scalar, pressing)

    def test_a_bow_wall_holds_worse_than_a_spear_wall(self):
        spears = resolve(
            10, 8, Rng(1), our_units=Composition.of({"spear": 5}), unit_defs=DEFS
        ).odds
        bows = resolve(
            10, 8, Rng(1), our_units=Composition.of({"bow": 5}), unit_defs=DEFS
        ).odds
        self.assertLess(bows, spears)

    def test_an_axe_band_presses_harder_than_spears_its_count(self):
        spears = resolve(
            10, 6, Rng(1), their_units=Composition.of({"spear": 3}), unit_defs=DEFS
        ).odds
        axes = resolve(
            10, 6, Rng(1), their_units=Composition.of({"axe": 3}), unit_defs=DEFS
        ).odds
        self.assertLess(axes, spears)

    def test_modifiers_stack_on_a_priced_composition(self):
        from hearthfall.engine.world import Terrain

        plain = resolve(
            10, 8, Rng(1), our_units=Composition.of({"spear": 5}), unit_defs=DEFS
        ).odds
        hills = resolve(
            10,
            8,
            Rng(1),
            our_units=Composition.of({"spear": 5}),
            unit_defs=DEFS,
            our_ground=Terrain.HILLS,
        ).odds
        self.assertGreater(hills, plain)

    def test_a_composition_without_the_declared_types_is_refused(self):
        with self.assertRaises(ValueError):
            resolve(5, 5, Rng(1), our_units=Composition.of({"spear": 1}))

    def test_exactly_one_draw_is_consumed_with_compositions(self):
        fought, fresh = Rng(9), Rng(9)
        resolve(
            10,
            5,
            fought,
            our_units=Composition.of({"spear": 5}),
            their_units=Composition.of({"bow": 2, "axe": 1}),
            unit_defs=DEFS,
        )
        fresh.fraction()  # the draw resolve consumed
        self.assertEqual(fought.fraction(), fresh.fraction())


if __name__ == "__main__":
    unittest.main()
