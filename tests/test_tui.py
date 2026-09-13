"""The skin's one load-bearing behavior, tested.

Everything cosmetic about the skin stays untested (`CLAUDE.md`: tests are
engine tests). What is tested here is the regression the 2026-09-12 audit
called HIGH: `run_until_interrupted` returned EVENT and nothing in the skin
rendered `state.pending` or called `apply_choice`, so a fired choice
re-interrupted the run forever and the game soft-locked. A run that can
dead-end its driver is behavior the skin owes a proof for, driven here
through Textual's own pilot.
"""

from __future__ import annotations

import unittest

from textual.widgets import Button, Static

from hearthfall.engine import turn
from hearthfall.engine.orders import Orders
from hearthfall.engine.rng import Rng
from hearthfall.engine.turn import InterruptReason
from hearthfall.tui.app import EventChoiceScreen, HearthfallApp, interrupt_line


def an_app(seed: int = 15) -> HearthfallApp:
    """The app on a seed known to put a choice event on the table by turn
    three under a plain standing policy. If this seed ever stops firing one,
    the test says so rather than passing vacuously."""
    state = turn.new_game(seed)
    state.standing_orders = Orders(forage=4, tend=1, is_standing=True)
    return HearthfallApp(state, Rng(seed))


class TestTheEventModal(unittest.IsolatedAsyncioTestCase):
    async def test_an_event_fires_the_choice_renders_and_choosing_advances(self):
        app = an_app()
        async with app.run_test() as pilot:
            for _ in range(12):
                if app.state.pending is not None:
                    break
                app.run_season()
                await pilot.pause()
            pending = app.state.pending
            self.assertIsNotNone(
                pending, "seed 15 stopped firing a choice event; pick another"
            )
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
            # happened before the fix.
            self.assertIsNone(app.state.pending)
            taken = app.state.chronicle[-1].choice_taken
            self.assertIsNotNone(taken)
            assert taken is not None
            self.assertTrue(taken.startswith(pending.options[0].text))
            app.run_season()
            self.assertGreater(app.state.turn, turn_at_choice)

    async def test_escaping_the_modal_leaves_the_choice_pending(self):
        app = an_app()
        async with app.run_test() as pilot:
            for _ in range(12):
                if app.state.pending is not None:
                    break
                app.run_season()
                await pilot.pause()
            self.assertIsNotNone(app.state.pending)
            await pilot.press("escape")
            await pilot.pause()
            self.assertNotIsInstance(
                app.screen, EventChoiceScreen, "escape did not step back"
            )
            self.assertIsNotNone(
                app.state.pending, "peeking answered the question by itself"
            )


class TestInterruptLines(unittest.TestCase):
    """Every reason a run can stop must say why. The DIRECTOR branch exists
    because a raid used to stop the run with no signpost at all."""

    def test_every_reason_has_a_line(self):
        # Every stop says why; the one stop that is an ending is worded as one.
        for reason in (
            InterruptReason.EVENT,
            InterruptReason.STARVATION,
            InterruptReason.DIRECTOR,
        ):
            self.assertIn("Interrupted", interrupt_line(reason))
        self.assertNotIn("Interrupted", interrupt_line(InterruptReason.GAME_OVER))


if __name__ == "__main__":
    unittest.main()
