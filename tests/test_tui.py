"""The skin's load-bearing behaviors, tested.

Everything cosmetic about the skin stays untested (`CLAUDE.md`: tests are
engine tests). What is tested here is what ends the run if it breaks: the
event modal, the save/load path, the standing-orders editor, and the way
through the shortfall stop. All of it is driven through Textual's own pilot.
"""

from __future__ import annotations

import pickle
import tempfile
import unittest
from pathlib import Path

from textual.widgets import Button, Static

import hearthfall.tui.app as app_module
from hearthfall.engine import turn
from hearthfall.engine.orders import Orders
from hearthfall.engine.rng import Rng
from hearthfall.engine.turn import InterruptReason
from hearthfall.tui.app import (
    EventChoiceScreen,
    HearthfallApp,
    StandingOrdersScreen,
    interrupt_line,
)


def an_app(seed: int = 15) -> HearthfallApp:
    """The app on a seed known to put a choice event on the table by turn
    three under a plain standing policy. If this seed ever stops firing one,
    the test says so rather than passing vacuously."""
    state = turn.new_game(seed)
    state.standing_orders = Orders(forage=3, scout=2, tend=1, is_standing=True)
    return HearthfallApp(state, Rng(seed))


async def run_until_a_choice(app: HearthfallApp, pilot, limit: int = 12) -> None:
    for _ in range(limit):
        if app.state.pending is not None:
            return
        app.run_season()
        await pilot.pause()
    pending = app.state.pending
    assert pending is not None, "no choice event fired; pick another seed"


class TestTheEventModal(unittest.IsolatedAsyncioTestCase):
    async def test_an_event_fires_the_choice_renders_and_choosing_advances(self):
        app = an_app()
        async with app.run_test() as pilot:
            await run_until_a_choice(app, pilot)
            pending = app.state.pending
            assert pending is not None

            # The question is on screen, over the run, with every answer.
            self.assertIsInstance(app.screen, EventChoiceScreen)
            self.assertIn(
                pending.title, str(app.screen.query_one("#event-title", Static).content)
            )
            buttons = sorted(app.screen.query(Button), key=lambda b: b.id or "")
            self.assertEqual(len(buttons), len(pending.options))
            for button, option in zip(buttons, pending.options, strict=True):
                self.assertIn(option.text, str(button.label))

            turn_at_choice = app.state.turn
            await pilot.press("1")

            # The answer landed in the engine and in the chronicle, and the
            # run can move again: this is the pair of things that never
            # happened before the fix. The next run may resolve into another
            # question (the corpus is thick now) or stop short on the
            # forecast, in which case the accept action is the way through,
            # exactly as it is for a player.
            taken = app.state.chronicle[-1].choice_taken
            self.assertIsNotNone(taken)
            assert taken is not None
            self.assertTrue(taken.startswith(pending.options[0].text))
            app.run_season()
            if (
                app.last_interrupt is InterruptReason.STARVATION
                and app.state.pending is None
            ):
                app.accept_shortfall()
            self.assertGreater(app.state.turn, turn_at_choice)

    async def test_escaping_the_modal_leaves_the_choice_pending(self):
        app = an_app()
        async with app.run_test() as pilot:
            await run_until_a_choice(app, pilot)
            self.assertIsNotNone(app.state.pending)
            await pilot.press("escape")
            await pilot.pause()
            self.assertNotIsInstance(
                app.screen, EventChoiceScreen, "escape did not step back"
            )
            self.assertIsNotNone(
                app.state.pending, "peeking answered the question by itself"
            )

    async def test_loading_while_a_choice_is_up_dismisses_the_question(self):
        # Save/Load used to swap the state out from under a live modal: the
        # open screen held the old state by reference, so an answer landed in
        # discarded state and vanished, and a loaded pending choice stacked a
        # second modal. Now the state is read through the app at answer time
        # and load dismisses any question the old run left on screen.
        app = an_app()
        async with app.run_test() as pilot:
            app.save_game()  # the run as it stood at turn zero
            await run_until_a_choice(app, pilot)
            self.assertIsInstance(app.screen, EventChoiceScreen)
            app.load_game()
            await pilot.pause()
            self.assertEqual(app.state.turn, 0, "the live run was not replaced")
            self.assertNotIsInstance(
                app.screen, EventChoiceScreen, "the old question stayed up"
            )
            self.assertIsNone(app.state.pending)


class TestTheShortfallStopsTheRunAndTheRunCanStillBeLost(
    unittest.IsolatedAsyncioTestCase
):
    """The 2026-09-13 terminal-loop finding, pinned from the skin's side.

    On the shipped all-zero standing orders the first forecast is short and
    `run_until_interrupted` stops before every resolve, forever. The stop is
    correct (it is the engine asking for different orders); what was missing
    was any way through for a shortfall the orders cannot fix. These tests
    pin both halves: the stop happens before the season resolves, and the
    accept action resolves it anyway, deaths and all, until the run can end.
    """

    def an_app_on_default_orders(self) -> HearthfallApp:
        state = turn.new_game(4)
        state.standing_orders = Orders(is_standing=True)
        return HearthfallApp(state, Rng(4))

    async def test_the_stop_repeats_before_resolving(self):
        # The all-zero clan lives off its stores for a few seasons, and then
        # the forecast goes short. From that season on, every Run stops
        # before resolving: this is the terminal loop, and the stop firing
        # twice in a row at the same turn is exactly what it looks like.
        app = self.an_app_on_default_orders()
        async with app.run_test():
            for _ in range(12):
                if app.last_interrupt is InterruptReason.STARVATION:
                    break
                app.run_season()
                if app.state.pending is not None:
                    turn.apply_choice(app.state, 0)
            self.assertIs(app.last_interrupt, InterruptReason.STARVATION)
            stuck = app.state.turn
            app.run_season()
            self.assertEqual(
                app.state.turn,
                stuck,
                "the run resolved a season the forecast called short",
            )
            self.assertIs(app.last_interrupt, InterruptReason.STARVATION)

    async def test_accepting_the_shortfall_resolves_and_can_lose_the_run(self):
        app = self.an_app_on_default_orders()
        async with app.run_test():
            entries = 0
            for _ in range(40):
                if app.state.is_over:
                    break
                if app.state.pending is not None:
                    turn.apply_choice(app.state, 0)
                else:
                    before = app.state.turn
                    app.accept_shortfall()
                    self.assertGreater(
                        app.state.turn, before, "accept did not resolve a season"
                    )
                    self.assertGreater(len(app.state.chronicle), entries)
                    entries = len(app.state.chronicle)
            self.assertTrue(
                app.state.is_over,
                "an all-zero run could not be lost through the skin",
            )
            self.assertGreater(app.state.turn, 0)


class TestTheStandingOrdersEditor(unittest.IsolatedAsyncioTestCase):
    """The editor is what converts the watchable into the playable: the
    shipped default orders are all zero and nothing could change them."""

    async def open_editor(self, app: HearthfallApp, pilot):
        app.action_dispatch("set_orders")
        await pilot.pause()
        screen = app.screen
        assert isinstance(screen, StandingOrdersScreen)
        return screen

    async def test_the_editor_edits_orders_and_shows_the_forecast(self):
        app = an_app()
        async with app.run_test() as pilot:
            orders = app.state.standing_orders
            assert orders is not None
            self.assertEqual(orders.forage, 3)
            screen = await self.open_editor(app, pilot)
            # The fixture's orders are at the clan's hand cap, so free a hand
            # first: the editor must refuse to overassign, not queue the wish.
            await pilot.click("#dec-tend")
            await pilot.pause()
            self.assertEqual(orders.tend, 0)
            await pilot.click("#inc-forage")
            await pilot.pause()
            self.assertEqual(orders.forage, 4, "the + button did nothing")
            self.assertIn(
                "Forecast", str(screen.query_one("#orders-forecast", Static).content)
            )
            await pilot.click("#orders-done")
            await pilot.pause()
            self.assertEqual(orders.forage, 4, "Done did not keep the edit")
            self.assertNotIsInstance(app.screen, StandingOrdersScreen)
            # The rail renders the forecast for the orders as they now stand.
            self.assertIn("Forecast", str(app.query_one("#forecast", Static).content))

    async def test_cancel_undoes_the_edits(self):
        app = an_app()
        async with app.run_test() as pilot:
            orders = app.state.standing_orders
            assert orders is not None
            await self.open_editor(app, pilot)
            await pilot.click("#dec-tend")
            await pilot.pause()
            self.assertEqual(orders.tend, 0)
            await pilot.click("#orders-cancel")
            await pilot.pause()
            self.assertEqual(orders.tend, 1, "Cancel left the edit in the live orders")
            self.assertNotIsInstance(app.screen, StandingOrdersScreen)

    async def test_the_editor_will_not_overassign_the_clan(self):
        app = an_app()
        async with app.run_test() as pilot:
            orders = app.state.standing_orders
            assert orders is not None
            adults = app.state.population.adults
            await self.open_editor(app, pilot)
            for _ in range(adults + 5):
                await pilot.click("#inc-forage")
                await pilot.pause()
            self.assertEqual(
                orders.assigned, adults, "the editor assigned more hands than exist"
            )


class TestInterruptLines(unittest.TestCase):
    """Every reason a run can stop must say why. The DIRECTOR branch exists
    because a raid used to stop the run with no signpost at all, and the
    starvation stop names its two ways through because a stop with no exit
    is a hang wearing a different colour."""

    def test_every_reason_has_a_line(self):
        # Every stop says why; the one stop that is an ending is worded as one.
        for reason in (
            InterruptReason.EVENT,
            InterruptReason.STARVATION,
            InterruptReason.DIRECTOR,
        ):
            self.assertIn("Interrupted", interrupt_line(reason))
        self.assertNotIn("Interrupted", interrupt_line(InterruptReason.GAME_OVER))

    def test_the_starvation_line_names_the_way_through(self):
        line = interrupt_line(InterruptReason.STARVATION)
        self.assertIn("orders", line)
        self.assertIn("accept the shortfall", line)


class TestSaveAndLoad(unittest.IsolatedAsyncioTestCase):
    """The audit's load-hygiene findings: a save that lands wherever the
    working directory was, a load that swapped the state without rewriting
    the chronicle pane, and an unreadable file that would have replaced the
    live run with a traceback. Every test here points SAVE_PATH at a
    throwaway directory; the player's real save is never touched."""

    def setUp(self) -> None:
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.save_path = Path(tmp.name) / "savegame.pkl"
        self.addCleanup(setattr, app_module, "SAVE_PATH", app_module.SAVE_PATH)
        app_module.SAVE_PATH = self.save_path

    async def test_a_save_round_trips_and_the_pane_follows_the_loaded_run(self):
        # A run already six seasons old, so the save carries a real chronicle.
        # resolve() leaves the chronicle alone; entries are the driver's job,
        # so the fixture appends them the way run_until_interrupted does.
        from test_playthrough import CORPUS, steady_orders

        from hearthfall.engine.chronicle import ChronicleEntry

        state, rng = turn.new_game(3), Rng(3)
        for _ in range(6):
            if state.is_over:
                break
            report = turn.resolve(state, steady_orders(state), rng, CORPUS)
            state.chronicle.append(
                ChronicleEntry(
                    turn=report.turn, season=report.season, lines=list(report.log)
                )
            )
            if state.pending is not None:
                turn.apply_choice(state, 0)
        app = HearthfallApp(state, rng)
        async with app.run_test():
            app.save_game()
            self.assertTrue(self.save_path.exists())
            saved_snapshot = app.state.snapshot()
            saved_entries = len(app.state.chronicle)
            self.assertGreater(saved_entries, 0)

            log = app.query_one("#chronicle", app_module.RichLog)
            log.write("[spring]a season the loaded run never saw[/]")

            app.load_game()
            self.assertEqual(app.state.snapshot(), saved_snapshot)
            self.assertEqual(len(app.state.chronicle), saved_entries)
            # The pane was rebuilt from the loaded chronicle: the junk season
            # is gone, and the load said so.
            texts = [strip.text for strip in log.lines]
            self.assertFalse(
                any("the loaded run never saw" in text for text in texts),
                "the pane still shows seasons that are not in the loaded state",
            )
            self.assertTrue(any("Game loaded" in text for text in texts))

    async def test_a_missing_save_is_a_message_not_an_error(self):
        app = an_app()
        async with app.run_test():
            state = app.state
            app.load_game()  # nothing saved yet; must not raise
            self.assertIs(app.state, state)

    async def test_a_corrupt_save_is_refused_and_the_run_survives(self):
        app = an_app()
        self.save_path.write_bytes(b"this is not a hearthfall save")
        async with app.run_test():
            state = app.state
            app.load_game()  # must not raise, must not swap the state
            self.assertIs(app.state, state)
            self.assertIsNotNone(app.state.world)

    async def test_a_save_from_another_format_is_refused(self):
        # The save is a stamped envelope now. The old unstamped tuple shape
        # (or any future shape with a bumped stamp) is refused outright
        # instead of being unpickled and dying seasons later on a slot it
        # never had.
        app = an_app()
        legacy = pickle.dumps((turn.new_game(3), Rng(3)))
        self.save_path.write_bytes(legacy)
        async with app.run_test():
            state = app.state
            app.load_game()
            self.assertIs(app.state, state, "an old-format save replaced the run")
            self.assertIsNone(app.last_interrupt)


if __name__ == "__main__":
    unittest.main()
