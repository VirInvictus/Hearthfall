from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from hearthfall.engine import balance
from hearthfall.engine.agents import IntentKind

if TYPE_CHECKING:
    from hearthfall.engine.state import GameState


@dataclass(frozen=True, slots=True)
class DirectorInterrupt:
    """An interrupt raised by the Director to break standing orders."""

    cause: str
    message: str
    # The agent acting, when the interrupt is that agent's intent surfacing.
    agent_id: str | None = None


class Director:
    """Pacing, and nothing else.

    The director does not create threats. It chooses which already-justified intent surfaces now
    and which waits, and it decides when to break standing orders.
    """

    def evaluate(self, state: GameState) -> DirectorInterrupt | None:
        """Surface a ripe raid intent, or hold it for pacing. No draw is spent here.

        What makes the blow learnable is structure elsewhere, not this method:
        an intent exists only on an agent the world placed and starved into
        bitterness (`agents.grow` never invents one); the season it forms, the
        massing is announced and the band's strength and mix are learned into
        the ledger (`turn._agents_tick`); and the intent matures over
        `balance.RAID_MATURITY_TURNS` before this method will surface it. The
        player is not owed a scouting visit for the raid to be honest; they
        are owed the announcement, and the announcement is mechanical (the
        honesty guarantee, `spec.md` §1).

        The pacing heuristic reads the clan's slack: food per living
        household, less the longest grudge. High slack surfaces the raid the
        season it ripens; slack under 5 holds it on even-numbered turns,
        which delays the blow one season at a time. That parity is
        deterministic, which is exactly why this method takes no rng: there
        is no draw to inject, and claiming one would be the old comment's
        lie.
        """
        # Slack: how well is the clan actually doing? Rich and ungrudging is
        # the moment the world notices there is room.
        food = state.stores.food
        households = state.population.living_households
        worst_resentment = state.population.worst_resentment
        slack_score = (food / max(1, households)) - worst_resentment

        # The most mature intent wins; there is usually only one.
        for agent in state.agents.values():
            if agent.intent and agent.intent.kind == IntentKind.RAID:
                # The window is the read. A band is held until its intent
                # matures (`balance.RAID_MATURITY_TURNS`): the player gets the
                # massing, one season to act on it, then the blow. Without
                # this check the raid landed the same season the band formed,
                # with orders that had been committed before the band
                # existed, so the militia was structurally zero and the
                # promised window never opened. A target of zero is a
                # hand-built intent and is ripe now.
                if agent.intent.target_turn and state.turn < agent.intent.target_turn:
                    continue

                # Low slack holds the blow on even turns: a struggling clan
                # gets a season's reprieve, half the time, by the calendar
                # and not by a coin.
                if slack_score < 5 and state.turn % 2 == 0:
                    continue

                # If we surface it, the raid has executed: the intent is
                # spent, and `turn._raid` resolves the fight this interrupt
                # hands back to the driver.
                agent.intent = None
                # Whatever the raid's outcome, the band went home. How long it
                # stays quiet while still starving is a balance number, not a
                # rule: see `balance.MORALE_AFTER_RAID`.
                agent.mood = balance.MORALE_AFTER_RAID

                return DirectorInterrupt(
                    cause=f"raid_{agent.id}",
                    message=f"The {agent.name} comes over the border.",
                    agent_id=agent.id,
                )

        return None
