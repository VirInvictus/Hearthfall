import re

with open('src/hearthfall/engine/state.py', 'r') as f:
    content = f.read()

orders_code = """class Orders:
    \"\"\"One turn's labor allocation. Everything not assigned still eats.\"\"\"

    forage: int = 0
    scout: int = 0
    tend: int = 0
    scout_target: Coord | None = None
    # How a short store gets divided. Only bites when there is not enough to go round, which
    # is what keeps it a decision about scarcity rather than a setting.
    rationing: Rationing = Rationing.EQUAL

    @property
    def assigned(self) -> int:
        return self.forage + self.scout + self.tend

    def validate(self, adults: int) -> None:
        if self.assigned > adults:
            raise ValueError(f"orders require {self.assigned} hands, clan has {adults}")
        if self.forage < 0 or self.scout < 0 or self.tend < 0:
            raise ValueError("orders cannot assign negative hands")
"""

content = content.replace(orders_code, "")
# We need to import Orders from hearthfall.engine.orders
content = content.replace("from hearthfall.engine.people import Household, Rationing, share_out", "from hearthfall.engine.people import Household, Rationing, share_out\nfrom hearthfall.engine.orders import Orders\nfrom hearthfall.engine.chronicle import ChronicleEntry")

# Add chronicle list to GameState
content = content.replace(
    "stores: Stores = field(default_factory=Stores)",
    "stores: Stores = field(default_factory=Stores)\n    chronicle: list[ChronicleEntry] = field(default_factory=list)"
)
# Add standing_orders to GameState
content = content.replace(
    "    pending: Effect | None = None\n    \"\"\"An event outcome waiting for the player to choose.\"\"\"",
    "    pending: Effect | None = None\n    \"\"\"An event outcome waiting for the player to choose.\"\"\"\n    standing_orders: Orders | None = None\n    \"\"\"The standing orders set by the player, to repeat until interrupted.\"\"\""
)

with open('src/hearthfall/engine/state.py', 'w') as f:
    f.write(content)
