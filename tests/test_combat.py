"""Slice 1 of SP 6: the dumb single-roll resolution. If these fail, violence
cannot be balanced or replayed, which is the whole point of the abstract form."""

from __future__ import annotations

import unittest

from hearthfall.engine import combat
from hearthfall.engine.combat import Outcome, resolve
from hearthfall.engine.intel import FactKind
from hearthfall.engine.orders import Orders
from hearthfall.engine.rng import Rng
from hearthfall.engine.turn import TurnReport


def _sweep(ours: int, theirs: int, seeds: int = 200) -> tuple[int, float]:
    """Run many seeds; return (wins, mean odds). Wide bounds only — the suite
    guards the arithmetic, not the tuning."""
    wins = 0
    odds_sum = 0.0
    for seed in range(seeds):
        outcome = resolve(ours, theirs, Rng(seed))
        wins += outcome.won
        odds_sum += outcome.odds
    return wins, odds_sum / seeds


def _state_with_band(strength: int):
    """A one-band world: populate_agents seeds several, and every extra band
    shares the rng stream — their drift would confound any guarded-vs-twin
    comparison. The band massed last season, so the read is aging and the raid
    matures this turn."""
    from hearthfall.engine.agents import Agent, AgentType
    from hearthfall.engine.turn import new_game

    state = new_game(seed=42)
    band = Agent(
        id="band_1",
        name="the Ashfang",
        type=AgentType.NEIGHBOUR,
        strength=strength,
    )
    state.agents = {"band_1": band}
    state.ledger.learn(
        FactKind.RAIDER_STRENGTH, band.id, strength, max(0, state.turn - 2)
    )
    band.intent = None
    return state, band


class TestResolution(unittest.TestCase):
    def test_same_seed_replays_exactly(self):
        a = resolve(8, 5, Rng(1312))
        b = resolve(8, 5, Rng(1312))
        self.assertEqual(a, b)

    def test_exactly_one_rng_draw_is_consumed(self):
        # The outcome's roll IS the first draw of the stream, and the rng is
        # left exactly one fraction() deep: a second resolve would then be
        # reproducible from the stream's next draw alone.
        fought, fresh = Rng(99), Rng(99)
        outcome = resolve(6, 4, fought)
        self.assertEqual(outcome.roll, fresh.fraction())
        self.assertEqual(fought.fraction(), fresh.fraction())

    def test_equal_strength_is_an_even_coin(self):
        outcome = resolve(5, 5, Rng(1))
        self.assertEqual(outcome.odds, 0.5)
        wins, mean_odds = _sweep(5, 5)
        self.assertGreaterEqual(mean_odds, 0.49)
        self.assertLessEqual(mean_odds, 0.51)
        # 200 seeds at even odds: all-way one side would mean the roll is bent.
        self.assertTrue(60 <= wins <= 140, f"even coin went {wins}/200")

    def test_odds_track_the_strength_ratio(self):
        self.assertGreater(resolve(10, 5, Rng(1)).odds, resolve(5, 5, Rng(1)).odds)
        self.assertGreater(resolve(5, 5, Rng(1)).odds, resolve(5, 10, Rng(1)).odds)
        # Sweep monotonicity, not just the point value.
        weak, _ = _sweep(2, 8)
        strong, _ = _sweep(8, 2)
        self.assertGreater(strong, weak)

    def test_overwhelming_strength_wins_the_sweep(self):
        wins, odds = _sweep(100, 1)
        # Odds 100/101 is about 0.99, so ~2 losses in 200 seeds is the math
        # working, not a bent coin.
        self.assertGreater(odds, 0.95)
        self.assertGreaterEqual(wins, 190)

    def test_zero_strength_loses_without_appeal(self):
        outcome = resolve(0, 5, Rng(1))
        self.assertFalse(outcome.won)
        self.assertEqual(outcome.odds, 0.0)
        self.assertEqual(resolve(0, 0, Rng(1)).odds, 0.0)

    def test_margin_sign_agrees_with_the_outcome(self):
        for seed in range(100):
            outcome = resolve(7, 5, Rng(seed))
            self.assertEqual(outcome.won, outcome.margin > 0)

    def test_outcome_is_a_frozen_value(self):
        outcome = resolve(3, 3, Rng(1))
        self.assertIsInstance(outcome, Outcome)
        with self.assertRaises(AttributeError):
            outcome.won = not outcome.won  # type: ignore[misc]


class TestTheMassingWindow(unittest.TestCase):
    """Found 2026-09-06: the director never checked the intent's maturity, so
    a raid landed the same season the band massed, on orders committed before
    the band existed. The militia was structurally zero and the promised
    window — the read aging while the player reassigns hands — never opened.
    These pin the window shut-side and open-side."""

    def _run_three_turns(self):
        from hearthfall.engine.agents import Agent, AgentType, Intent
        from hearthfall.engine.turn import resolve as turn_resolve

        state = new_game_state()
        band = Agent(
            id="band_1",
            name="the Ashfang",
            type=AgentType.NEIGHBOUR,
            food=0,
            mood=0,
        )
        state.agents = {"band_1": band}
        # A real store: the militia line takes five of six adults off the
        # forage roll, and the window must close on a clan that is still
        # standing, not one the director's slack gate quietly shields.
        state.stores.food = 60
        turns: list[tuple[TurnReport, Intent | None]] = []
        for _ in range(3):
            report = turn_resolve(state, Orders(forage=1, militia=5), Rng(7))
            turns.append((report, band.intent))
        return state, band, turns

    def test_the_massing_is_announced_and_the_raid_held(self):
        from hearthfall.engine.agents import Intent, IntentKind

        state, band, turns = self._run_three_turns()
        first = "\n".join(turns[0][0].log)
        # The band forms its intent this season: the massing is public, with
        # the read on it, and the ledger holds the strength fact.
        self.assertIn("massing on the border", first)
        self.assertIn("The read says", first)
        assert isinstance(turns[0][1], Intent)
        self.assertEqual(turns[0][1].kind, IntentKind.RAID)
        self.assertTrue(
            state.ledger.knows(FactKind.RAIDER_STRENGTH, band.id),
            "the band's strength was never learned",
        )
        # Held through the massing season and the one after: the intent is
        # still on the band at the end of both, and no band has crossed.
        self.assertIsInstance(turns[1][1], Intent)
        self.assertNotIn("comes over the border", first)
        self.assertNotIn("comes over the border", "\n".join(turns[1][0].log))

    def test_the_band_crosses_when_the_window_closes(self):
        _state, band, turns = self._run_three_turns()
        # The window is RAID_MATURITY_TURNS; the third resolve is the blow.
        third = "\n".join(turns[2][0].log)
        self.assertIn("comes over the border", third)
        self.assertIn("broke against the militia", third)
        self.assertIsNone(band.intent)

    def test_the_read_ages_across_the_window(self):
        from hearthfall.engine.intel import Staleness

        state, band, _turns = self._run_three_turns()
        staleness = state.ledger.staleness(
            FactKind.RAIDER_STRENGTH, band.id, state.turn
        )
        # The fight already happened, but the fact ages from the massing: two
        # seasons on it is still fresh (halflife 4), which is the point — the
        # read the clan acted on was true when it acted.
        self.assertIs(staleness, Staleness.FRESH)


def new_game_state():
    from hearthfall.engine.turn import new_game

    return new_game(seed=42)


class TestTerrainAndMorale(unittest.TestCase):
    """Slice 2: the modifiers scale effective strength before the share, and
    every one of them is optional — defaults must reproduce slice 1 exactly."""

    def test_defaults_reproduce_slice_one(self):
        a = resolve(5, 5, Rng(42))
        b = resolve(5, 5, Rng(42), our_ground=None, their_morale=None)
        self.assertEqual(a, b)

    def test_hills_favor_and_marsh_punishes(self):
        from hearthfall.engine.world import Terrain

        even = resolve(5, 5, Rng(1)).odds
        hills = resolve(5, 5, Rng(1), our_ground=Terrain.HILLS).odds
        marsh = resolve(5, 5, Rng(1), our_ground=Terrain.MARSH).odds
        self.assertGreater(hills, even)
        self.assertLess(marsh, even)
        # Same ground on both sides cancels: the share is back to even.
        both = resolve(
            5, 5, Rng(1), our_ground=Terrain.HILLS, their_ground=Terrain.HILLS
        )
        self.assertAlmostEqual(both.odds, 0.5)

    def test_terrain_weight_comes_from_balance(self):
        from hearthfall.engine.balance import TERRAIN_COMBAT_WEIGHT
        from hearthfall.engine.world import Terrain

        p = resolve(5, 5, Rng(1), our_ground=Terrain.HILLS).odds
        expected = (
            5
            * TERRAIN_COMBAT_WEIGHT[Terrain.HILLS]
            / (5 * TERRAIN_COMBAT_WEIGHT[Terrain.HILLS] + 5)
        )
        self.assertAlmostEqual(p, expected)

    def test_morale_shifts_the_odds_with_parity_at_five(self):
        from hearthfall.engine.balance import (
            MORALE_COMBAT_CEIL,
            MORALE_COMBAT_FLOOR,
        )

        parity = resolve(5, 5, Rng(1), our_morale=5).odds
        self.assertAlmostEqual(parity, 0.5)
        jubilant = resolve(5, 5, Rng(1), our_morale=10).odds
        broken = resolve(5, 5, Rng(1), our_morale=0).odds
        self.assertGreater(jubilant, 0.5)
        self.assertLess(broken, 0.5)
        # The extremes are the balance band itself: 1.2 strength vs 0.8 is
        # odds 0.6, the exact legible number the band promises.
        both = resolve(5, 5, Rng(1), our_morale=10, their_morale=0).odds
        self.assertAlmostEqual(
            both, MORALE_COMBAT_CEIL / (MORALE_COMBAT_CEIL + MORALE_COMBAT_FLOOR)
        )

    def test_modified_fights_stay_deterministic_and_one_draw(self):
        from hearthfall.engine.world import Terrain

        fought, fresh = Rng(7), Rng(7)
        outcome = resolve(6, 4, fought, our_ground=Terrain.HILLS, our_morale=8)
        self.assertEqual(outcome.roll, fresh.fraction())
        self.assertEqual(fought.fraction(), fresh.fraction())


class TestIntelQuality(unittest.TestCase):
    """Slice 3: a stale fact should cost you. The staleness bands price the
    read; the truth still wins on the numbers."""

    def test_fresh_intel_costs_nothing(self):
        from hearthfall.engine.intel import Staleness

        plain = resolve(6, 4, Rng(1)).odds
        fresh = resolve(6, 4, Rng(1), intel_staleness=Staleness.FRESH).odds
        self.assertAlmostEqual(plain, fresh)

    def test_staleness_steps_the_penalty(self):
        from hearthfall.engine.intel import Staleness

        fresh = resolve(6, 4, Rng(1), intel_staleness=Staleness.FRESH).odds
        aging = resolve(6, 4, Rng(1), intel_staleness=Staleness.AGING).odds
        stale = resolve(6, 4, Rng(1), intel_staleness=Staleness.STALE).odds
        never = resolve(6, 4, Rng(1), intel_staleness=Staleness.NEVER).odds
        self.assertGreater(fresh, aging)
        self.assertGreater(aging, stale)
        self.assertGreater(stale, never)

    def test_never_scouted_pays_the_full_price(self):
        from hearthfall.engine.balance import INTEL_COMBAT_FACTOR
        from hearthfall.engine.intel import Staleness

        # Equal stacks, never scouted: the band says 0.7 vs 1.0 — odds exactly
        # 0.7/(0.7+1.0), the legible number the table promises.
        odds = resolve(5, 5, Rng(1), intel_staleness=Staleness.NEVER).odds
        self.assertAlmostEqual(
            odds,
            INTEL_COMBAT_FACTOR[Staleness.NEVER]
            / (INTEL_COMBAT_FACTOR[Staleness.NEVER] + 1.0),
        )

    def test_stale_intel_stacks_with_terrain_and_morale(self):
        from hearthfall.engine.intel import Staleness
        from hearthfall.engine.world import Terrain

        fought, fresh = Rng(11), Rng(11)
        outcome = resolve(
            8,
            6,
            fought,
            our_ground=Terrain.HILLS,
            our_morale=7,
            intel_staleness=Staleness.STALE,
        )
        self.assertEqual(outcome.roll, fresh.fraction())
        self.assertGreater(
            outcome.odds, 0.5
        )  # hills + morale beat one band of staleness


class TestRaidWiring(unittest.TestCase):
    """Slice 4: the raid end-to-end. A miserable band masses, the militia
    order was the decision, and the granary pays on a loss."""

    def test_militia_repels_and_keeps_the_granary(self):
        from hearthfall.engine.agents import Intent, IntentKind
        from hearthfall.engine.turn import resolve as turn_resolve

        def run(with_raid: bool) -> tuple[int, str]:
            state, band = _state_with_band(strength=6)
            if with_raid:
                band.intent = Intent(kind=IntentKind.RAID, target_turn=state.turn)
                band.mood = 0
            else:
                # Content, and holding no intent: nothing raids the twin.
                band.mood = 5
            state.stores.food = 30
            report = turn_resolve(state, Orders(forage=1, militia=5), Rng(7))
            return state.stores.food, "\n".join(report.log)

        guarded, guarded_log = run(with_raid=True)
        twin_food, _ = run(with_raid=False)  # no band massing: no raid at all
        self.assertIn("broke against the militia", guarded_log)
        # A repelled raid costs the granary nothing: the guarded run ends
        # exactly where the no-raid twin does.
        self.assertEqual(guarded, twin_food)

    def test_no_militia_loses_the_granary(self):
        from hearthfall.engine.agents import Intent, IntentKind
        from hearthfall.engine.balance import RAID_STORE_LOSS
        from hearthfall.engine.turn import resolve as turn_resolve

        def run(militia: int) -> tuple[int, str]:
            state, band = _state_with_band(strength=6)
            band.intent = Intent(kind=IntentKind.RAID, target_turn=state.turn)
            band.mood = 0
            state.stores.food = 30
            report = turn_resolve(state, Orders(forage=1, militia=militia), Rng(7))
            return state.stores.food, "\n".join(report.log)

        # Paired runs: identical everything but the guard. Same season economy,
        # so the difference is exactly the raid's take.
        guarded, guarded_log = run(militia=5)
        open_granary, open_log = run(militia=0)
        self.assertIn("broke against the militia", guarded_log)
        self.assertIn("hit the granary", open_log)
        self.assertGreater(open_granary, 0)  # the clamp held: raiders leave some
        self.assertEqual(guarded - open_granary, RAID_STORE_LOSS)

    def test_raid_is_replayable_from_the_seed(self):
        from hearthfall.engine.agents import Intent, IntentKind
        from hearthfall.engine.turn import resolve as turn_resolve

        def run():
            state, band = _state_with_band(strength=6)
            band.intent = Intent(kind=IntentKind.RAID, target_turn=state.turn)
            band.mood = 0
            state.stores.food = 30
            report = turn_resolve(state, Orders(forage=1, militia=2), Rng(7))
            return state.stores.food, "\n".join(report.log)

        self.assertEqual(run(), run())


class TestAssemblyWiring(unittest.TestCase):
    """Slice 2: the clan assembles a group from types. The untyped militia
    line is the spear line; typed lines stand beside it and pay for their
    stats in the same hands every other order spends."""

    def test_the_untyped_militia_line_is_a_spear_line(self):
        from hearthfall.engine.agents import Intent, IntentKind
        from hearthfall.engine.turn import resolve as turn_resolve

        def run(lines: dict[str, int], militia: int) -> tuple[int, str]:
            state, band = _state_with_band(strength=6)
            band.intent = Intent(kind=IntentKind.RAID, target_turn=state.turn)
            band.mood = 0
            state.stores.food = 30
            orders = Orders(forage=1, militia=militia, militia_lines=lines)
            report = turn_resolve(state, orders, Rng(7))
            return state.stores.food, "\n".join(report.log)

        untyped = run({}, militia=5)
        split = run({"spear": 2}, militia=3)
        self.assertEqual(untyped, split)

    def test_a_bow_line_holds_worse_than_a_spear_line_of_the_same_count(self):
        from hearthfall.engine.agents import Intent, IntentKind
        from hearthfall.engine.turn import resolve as turn_resolve

        def run(lines: dict[str, int]) -> int:
            # Paired against the same seed: the season economy is identical,
            # so the difference is exactly what each wall let through.
            food = 0
            for seed in range(20):
                state, band = _state_with_band(strength=6)
                band.intent = Intent(kind=IntentKind.RAID, target_turn=state.turn)
                band.mood = 0
                state.stores.food = 30
                turn_resolve(state, Orders(forage=1, militia_lines=lines), Rng(seed))
                food += state.stores.food
            return food

        spear_wall = run({"spear": 5})
        bow_wall = run({"bow": 5})
        self.assertGreater(
            spear_wall,
            bow_wall,
            "the bow line held as well as spears; the stats are not real",
        )

    def test_the_line_is_named_in_the_chronicle(self):
        from hearthfall.engine.agents import Intent, IntentKind
        from hearthfall.engine.turn import resolve as turn_resolve

        state, band = _state_with_band(strength=2)
        band.intent = Intent(kind=IntentKind.RAID, target_turn=state.turn)
        band.mood = 0
        state.stores.food = 30
        orders = Orders(forage=1, militia=3, militia_lines={"bow": 2})
        report = turn_resolve(state, orders, Rng(7))
        self.assertIn("broke against the militia", "\n".join(report.log))
        self.assertIn("The line: 3 spear, 2 bow.", "\n".join(report.log))

    def test_an_undeclared_line_is_refused_at_the_top_of_the_tick(self):
        from hearthfall.engine.turn import resolve as turn_resolve

        state, _band = _state_with_band(strength=6)
        orders = Orders(forage=4, militia_lines={"sling": 2})
        with self.assertRaises(ValueError) as ctx:
            turn_resolve(state, orders, Rng(7))
        self.assertIn("sling", str(ctx.exception))

    def test_typed_lines_compete_for_the_same_hands(self):
        from hearthfall.engine.turn import resolve as turn_resolve

        state, _band = _state_with_band(strength=6)
        over = Orders(forage=1, militia=4, militia_lines={"bow": 2})
        with self.assertRaises(ValueError):
            turn_resolve(state, over, Rng(7))


class TestBandComposition(unittest.TestCase):
    """Slice 3 wiring: a mustering band draws a mix of types, announces it,
    and presses with it. The web only bites when both sides have types."""

    def _state_with_mustering_band(self):
        from hearthfall.engine.agents import Agent, AgentType
        from hearthfall.engine.turn import resolve as turn_resolve

        state = new_game_state()
        band = Agent(id="band_1", name="the Ashfang", type=AgentType.NEIGHBOUR)
        state.agents = {"band_1": band}
        state.stores.food = 60
        report = turn_resolve(state, Orders(forage=6), Rng(7))
        return state, band, report

    def test_mustering_draws_a_mix_and_presses_with_it(self):
        from hearthfall.engine.units import Composition

        state, band, _report = self._state_with_mustering_band()
        assert band.intent is not None
        self.assertIsInstance(band.composition, Composition)
        assert band.composition is not None
        self.assertEqual(band.strength, band.composition.strength(state.unit_defs))
        # The same seed musters the same band.
        _twin, twin_band, _ = self._state_with_mustering_band()
        assert twin_band.composition is not None
        self.assertEqual(band.composition, twin_band.composition)

    def test_the_massing_line_names_the_mix(self):
        _state, _band, report = self._state_with_mustering_band()
        log = "\n".join(report.log)
        self.assertIn("massing on the border:", log)
        self.assertIn("The read says", log)

    def test_an_axe_band_punishes_a_spear_wall_and_fears_a_bow_wall(self):
        from hearthfall.engine.agents import Agent, AgentType, Intent, IntentKind
        from hearthfall.engine.turn import resolve as turn_resolve
        from hearthfall.engine.units import Composition

        def run(wall: dict[str, int]) -> int:
            food = 0
            for seed in range(20):
                state = new_game_state()
                band = Agent(
                    id="band_1",
                    name="the Ashfang",
                    type=AgentType.NEIGHBOUR,
                    strength=8,
                )
                band.composition = Composition.of({"axe": 2})
                band.intent = Intent(kind=IntentKind.RAID, target_turn=state.turn)
                state.agents = {"band_1": band}
                state.stores.food = 60
                orders = Orders(forage=1, militia_lines=wall)
                turn_resolve(state, orders, Rng(seed))
                food += state.stores.food
            return food

        spear_wall = run({"spear": 5})
        bow_wall = run({"bow": 5})
        self.assertGreater(
            bow_wall,
            spear_wall,
            "the web did not bite: spears held an axe band as well as bows",
        )

    def test_a_scalar_band_fights_the_old_way(self):
        # The hand-built fixtures of slices 4 and 5 set strength and no
        # composition; the raid must resolve exactly as it did before the web.
        from hearthfall.engine.agents import Intent, IntentKind
        from hearthfall.engine.turn import resolve as turn_resolve

        def run() -> tuple[int, str]:
            state, band = _state_with_band(strength=6)
            band.intent = Intent(kind=IntentKind.RAID, target_turn=state.turn)
            band.mood = 0
            state.stores.food = 30
            report = turn_resolve(state, Orders(forage=1, militia=5), Rng(7))
            return state.stores.food, "\n".join(report.log)

        self.assertEqual(run(), run())
        food, log = run()
        self.assertIn("broke against the militia", log)
        self.assertGreater(food, 0)


class TestScoutIntelDrivesAssembly(unittest.TestCase):
    """Slice 4: the read is a fact that ages, bands reinforce in silence, and
    a party at the camp is what refreshes it. The massing read is public
    once; everything after that is the scouts' job."""

    def _massing_state(self):
        from hearthfall.engine.agents import Agent, AgentType

        state = new_game_state()
        band = Agent(id="band_1", name="the Ashfang", type=AgentType.NEIGHBOUR)
        band.location = min(state.ledger.frontier(state.world))
        state.agents = {"band_1": band}
        state.stores.food = 60
        return state, band

    def test_the_massing_learns_strength_and_mix_as_facts(self):
        from hearthfall.engine import balance
        from hearthfall.engine.intel import FactKind
        from hearthfall.engine.turn import _named_mix
        from hearthfall.engine.turn import resolve as turn_resolve

        old = balance.RAID_RESHUFFLE_CHANCE
        balance.RAID_RESHUFFLE_CHANCE = 0.0
        try:
            state, band = self._massing_state()
            turn_resolve(state, Orders(forage=6), Rng(7))
            assert band.composition is not None
            self.assertEqual(
                state.ledger.value(FactKind.RAIDER_STRENGTH, band.id),
                band.strength,
            )
            self.assertEqual(
                state.ledger.value(FactKind.RAIDER_COMPOSITION, band.id),
                _named_mix(state, band.composition),
            )
        finally:
            balance.RAID_RESHUFFLE_CHANCE = old

    def test_a_reinforcement_breaks_the_read_in_silence(self):
        from hearthfall.engine import balance
        from hearthfall.engine.intel import FactKind
        from hearthfall.engine.turn import _named_mix
        from hearthfall.engine.turn import resolve as turn_resolve

        old = balance.RAID_RESHUFFLE_CHANCE
        balance.RAID_RESHUFFLE_CHANCE = 1.0
        try:
            state, band = self._massing_state()
            turn_resolve(state, Orders(forage=6), Rng(7))
            assert band.intent is not None
            # The band keeps massing while the director waits.
            band.intent.target_turn = state.turn + 10
            turn_resolve(state, Orders(forage=6), Rng(7))
            # The camp grew behind the border and nothing announced it: the
            # fact the clan holds is not the band that is there now.
            assert band.composition is not None
            self.assertNotEqual(
                state.ledger.value(FactKind.RAIDER_COMPOSITION, band.id),
                _named_mix(state, band.composition),
                "the reshuffle never diverged on seed 42; pick another seed",
            )
        finally:
            balance.RAID_RESHUFFLE_CHANCE = old

    def test_a_party_at_the_camp_refreshes_the_read_and_says_so(self):
        from hearthfall.engine import balance
        from hearthfall.engine.intel import FactKind
        from hearthfall.engine.turn import _named_mix
        from hearthfall.engine.turn import resolve as turn_resolve

        old = balance.RAID_RESHUFFLE_CHANCE
        balance.RAID_RESHUFFLE_CHANCE = 1.0
        try:
            state, band = self._massing_state()
            turn_resolve(state, Orders(forage=6), Rng(7))
            assert band.intent is not None
            band.intent.target_turn = state.turn + 10
            turn_resolve(state, Orders(forage=6), Rng(7))
            report = turn_resolve(
                state,
                Orders(forage=1, scout=3, scout_target=band.location),
                Rng(7),
            )
            log = "\n".join(report.log)
            self.assertIn("camp has changed", log)
            assert band.composition is not None
            self.assertEqual(
                state.ledger.value(FactKind.RAIDER_COMPOSITION, band.id),
                _named_mix(state, band.composition),
                "the party stood in the camp and the read did not refresh",
            )
        finally:
            balance.RAID_RESHUFFLE_CHANCE = old

    def test_the_raid_prices_a_stale_read(self):
        from hearthfall.engine import balance
        from hearthfall.engine.turn import resolve as turn_resolve

        old = balance.RAID_RESHUFFLE_CHANCE
        balance.RAID_RESHUFFLE_CHANCE = 1.0
        try:
            state, band = self._massing_state()
            # A deep store: the director holds the band six seasons and the
            # clan must still be standing when the blow falls.
            state.stores.food = 600
            turn_resolve(state, Orders(forage=6), Rng(7))
            assert band.intent is not None
            band.intent.target_turn = state.turn + 6
            report = None
            while band.intent is not None and not state.is_over:
                adults = state.population.adults
                report = turn_resolve(
                    state, Orders(forage=1, militia=adults - 1), Rng(7)
                )
            assert report is not None
            log = "\n".join(report.log)
            self.assertIn("comes over the border", log)
            self.assertIn("(read: aging", log)
        finally:
            balance.RAID_RESHUFFLE_CHANCE = old


class TestGradedStakes(unittest.TestCase):
    """Slice 5: the dead and the ground grade by the margin. A near-run raid
    costs a grave; a rout costs the band and marks the map."""

    def test_raid_deaths_grade_by_margin(self):
        # Near-run: one grave. Rout: the full band of them. Capped. The slope
        # is 4 deaths per full unit of lost margin (retuned 2026-09-06 with the
        # band economy: at 6, an unguarded run bled out on top of the granary).
        self.assertEqual(combat.raid_deaths(0.0), 1)
        self.assertEqual(combat.raid_deaths(-0.1), 1)
        self.assertEqual(combat.raid_deaths(-0.3), 1)
        self.assertEqual(combat.raid_deaths(-0.5), 2)
        self.assertEqual(combat.raid_deaths(-0.75), 3)
        self.assertEqual(combat.raid_deaths(-1.0), 3)  # capped
        self.assertEqual(combat.raid_deaths(0.4), 1)  # a won fight buries nobody

    def test_is_rout_threshold(self):
        self.assertFalse(combat.is_rout(0.24))
        self.assertTrue(combat.is_rout(0.25))
        self.assertTrue(combat.is_rout(-0.25))  # a lost fight can be a rout too


class TestRaidStakesWiring(unittest.TestCase):
    """Slice 5 wiring: deaths land on the households, a rout marks the camp."""

    def _paired_raid_runs(self, seed: int, band_strength: int):
        from hearthfall.engine.agents import Intent, IntentKind
        from hearthfall.engine.turn import resolve as turn_resolve

        def run(militia: int):
            state, band = _state_with_band(strength=band_strength)
            band.location = (0, 0)
            # Both runs raid; only the guard differs. Same seed -> same roll.
            band.intent = Intent(kind=IntentKind.RAID, target_turn=state.turn)
            band.mood = 0
            state.stores.food = 30
            report = turn_resolve(state, Orders(forage=1, militia=militia), Rng(seed))
            return state.population.total, "\n".join(report.log), state

        guarded_pop, guarded_log, guarded_state = run(5)
        open_pop, open_log, _ = run(0)
        won = "broke against the militia" in guarded_log
        # The guarded run's state is the one that fought (and possibly routed)
        # the band; the open run only prices the granary pairing.
        return won, guarded_pop, open_pop, guarded_log, open_log, guarded_state

    def test_raid_deaths_land_on_the_households(self):
        deaths_seen = set()
        for seed in range(20):
            won, guarded_pop, open_pop, _g, _o, _ = self._paired_raid_runs(seed, 6)
            if not won:
                continue  # a guarded loss muddies the pairing; sweep skips it
            deaths = guarded_pop - open_pop
            self.assertIn(deaths, {1, 2, 3}, f"seed {seed}: {deaths} raid deaths")
            deaths_seen.add(deaths)
        self.assertGreaterEqual(
            len(deaths_seen), 2, "grading never varied across 20 seeds"
        )

    def test_rout_marks_the_camp_on_the_map(self):

        revealed_on_rout = 0
        for seed in range(20):
            won, _, _, _, _, state = self._paired_raid_runs(seed, 2)
            if not won:
                continue
            knows_camp = state.ledger.knows(FactKind.TERRAIN, (0, 0))
            if knows_camp:
                revealed_on_rout += 1
        # Odds 10:2 is 0.833; over 20 seeds most wins are routs (threshold
        # 0.25 means roll <= 0.583), so the camp must have surfaced at least
        # once for the reveal wiring to count as proven.
        self.assertGreaterEqual(revealed_on_rout, 1)


if __name__ == "__main__":
    unittest.main()
