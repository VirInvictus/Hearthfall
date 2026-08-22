import re

with open('src/hearthfall/engine/turn.py', 'r') as f:
    content = f.read()

run_func = """
from enum import StrEnum

class InterruptReason(StrEnum):
    EVENT = "event"
    STARVATION = "starvation"
    GAME_OVER = "game_over"

def run_until_interrupted(state: GameState, rng: Rng, events: Sequence[Event] = ()) -> InterruptReason:
    \"\"\"Run turns using standing orders until an interrupt condition is met.\"\"\"
    if not state.standing_orders:
        raise ValueError("Cannot run without standing orders")
    
    from hearthfall.engine.chronicle import ChronicleEntry

    while True:
        if state.is_over:
            return InterruptReason.GAME_OVER
        if state.pending:
            return InterruptReason.EVENT
            
        projection = forecast(state, state.standing_orders)
        if projection.shortfall > 0:
            return InterruptReason.STARVATION

        report = resolve(state, state.standing_orders, rng, events)
        
        entry = ChronicleEntry(
            turn=report.turn,
            season=report.season,
            lines=list(report.log)
        )
        if state.pending:
            entry.event_title = "Event"
            # We don't have the event object here to get its title/body easily.
            # `events` list could be searched for `report.event_id`.
            if report.event_id:
                for ev in events:
                    if ev.id == report.event_id:
                        entry.event_title = ev.title
                        entry.event_body = ev.body
                        break

        state.chronicle.append(entry)
        
        if state.is_over:
            return InterruptReason.GAME_OVER
        if state.pending:
            return InterruptReason.EVENT
"""

content = content + "\n" + run_func

with open('src/hearthfall/engine/turn.py', 'w') as f:
    f.write(content)
