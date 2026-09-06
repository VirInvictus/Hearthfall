from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from hearthfall.engine import balance
from hearthfall.engine.agents import IntentKind

if TYPE_CHECKING:
    from hearthfall.engine.rng import Rng
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

    def evaluate(self, state: GameState, rng: Rng) -> DirectorInterrupt | None:
        """Evaluate all agent intents and return an interrupt if one surfaces.

        The pacing logic looks at clan slack. If the clan is doing well,
        threats surface faster.
        """
        # Determine "slack": How well is the player doing?
        food = state.stores.food
        households = state.population.living_households
        worst_resentment = state.population.worst_resentment

        # A simple slack heuristic: high food per household and low resentment means high slack.
        # If slack is high, the director might pull the trigger on a raid sooner.
        # If slack is low, it might delay it to avoid a death spiral.
        slack_score = (food / max(1, households)) - worst_resentment

        # Look for the most mature intent
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

                # Does the player know about this intent?
                # The honesty guarantee says the intent must be learnable. It exists on the agent,
                # so the ledger COULD have it. We don't strictly require the player to have
                # actually scouted it to fire it (the world doesn't wait for you to look),
                # but the fact MUST have existed for at least a few turns.

                # For pacing: if slack is very low (< 5), give them a break 50% of the time.
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
