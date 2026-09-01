from tests.test_playthrough import play_with, surveying_orders
t = play_with(4, surveying_orders)
print("Turns:", t.turns, "Outcome:", t.outcome)
