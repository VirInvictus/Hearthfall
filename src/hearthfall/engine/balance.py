"""Every tuning constant, in one file.

Balance is an empirical question answered by playing, not by reasoning. Keeping the numbers
here means a balance pass is one diff and one review, instead of a hunt through the rules.
Nothing in here is sacred; all of it is a first guess aimed at the Phase 0 question, which
is whether the allocate-and-survive loop is tolerable for thirty minutes.

Rules live in `turn.py`. Numbers live here. Do not inline a constant into a rule.
"""

from __future__ import annotations

from hearthfall.engine.intel import FactKind
from hearthfall.engine.state import Season
from hearthfall.engine.world import Terrain

# --- The run ---------------------------------------------------------------------------

TURNS_PER_RUN = 20  # five winters
STARTING_ADULTS = 6
STARTING_CHILDREN = 2
# Year one is a drawdown by design: one known plain supports two foragers against eight
# mouths, so the clan cannot feed itself until it has walked more ground.
#
# Left at 30 after a measured attempt to raise it, and the attempt is worth recording because
# the obvious fix does not work. Year one is too harsh (half the clan dies under good play)
# while year two onward is too safe, and one scalar cannot move those in opposite directions:
# 30 buries 7 runs in 50, 32 buries 6, 34 buries 3 and trips the "nothing is at stake" guard.
# Raising it far enough to matter is worse still, because past BIRTH_FOOD_THRESHOLD the clan
# has a child it cannot feed and measured survival for a clan that never scouts *falls*
# (79% at 30, 53% at 60). The shape is wrong, not the magnitude, and the fix belongs with the
# mid-game plateau rather than here. See roadmap.md, the standing gate.
STARTING_FOOD = 30
STARTING_MORALE = 6

MORALE_MIN = 0
MORALE_MAX = 10

# --- Households --------------------------------------------------------------------------

# Kin groups the starting clan is dealt into. Three is the smallest number that makes
# rationing a real decision: with two, "feed the workers" is a coin toss between them, and
# with one there is nobody to feed instead. `spec.md` §5 sizes the mature game at ten to
# forty, which arrives with growth.
STARTING_HOUSEHOLDS = 3

# Resentment added to a household that got less than an even split would have given it. It
# accrues per season and never decays on its own, because being fed last is not something a
# kin group forgets when the stores recover. Being merely hungry costs nothing here: everyone
# going short together wrongs no one, and that is what makes EQUAL a real option rather than
# the safe one.
RESENTMENT_PER_SHORT_SHARE = 1

# What counts as a resentful household when content asks. Three seasons of being passed over.
RESENTFUL_AT = 3

# --- Food ------------------------------------------------------------------------------

# Food a single forager brings in per turn, by season. Winter is not merely lean: there is
# nothing out there to find, so hands cannot solve the problem at all. That is what makes
# the autumn stockpile a decision rather than a formality, and it hands winter a different
# allocation puzzle: with foraging worthless, the free hands go to tending or to the fog.
FORAGE_YIELD: dict[Season, int] = {
    Season.SPRING: 2,
    Season.SUMMER: 3,
    Season.AUTUMN: 5,
    Season.WINTER: 0,
}

FOOD_PER_ADULT = 2
FOOD_PER_CHILD = 1

# --- What the ground gives ---------------------------------------------------------------

# Ground you have walked is ground you can work. Both tables below are keyed on terrain the
# clan *believes* is there, read from the fact ledger rather than from the world, so a wrong
# belief will one day cost real food.
#
# Per-terrain yield, in tenths of the season's base. Multiplicative rather than additive so
# that winter, whose base is zero, stays zero on every terrain with no special case: nothing
# is out there to find and good ground does not change that. An additive bonus would have
# quietly made winter solvable with hands and deleted the season's whole allocation puzzle.
TERRAIN_FORAGE: dict[Terrain, int] = {
    Terrain.PLAIN: 10,
    Terrain.FOREST: 15,
    Terrain.HILLS: 7,
    Terrain.MARSH: 5,
    Terrain.WATER: 0,
}

# How many foragers a single known tile supports. Hands beyond the total capacity of the
# ground the clan has revealed bring back nothing at all, and that ceiling is the mechanism
# that makes scouting pay: it is the only thing that raises how much labour can be spent on
# food. Water supports nobody, so a bad reveal is genuinely bad and exploring stays a gamble
# rather than becoming a ratchet.
TERRAIN_CAPACITY: dict[Terrain, int] = {
    Terrain.PLAIN: 2,
    Terrain.FOREST: 3,
    Terrain.HILLS: 2,
    Terrain.MARSH: 1,
    Terrain.WATER: 0,
}

# Extra food every mouth needs in winter. Cold is a cost, not just a lack of yield, and this
# is what turns winter from a lean season into the one that decides the run.
WINTER_EXTRA_FOOD = 1

# --- Spoilage --------------------------------------------------------------------------

# Fraction of surviving stores lost per turn before tending. Summer rots, winter preserves.
# This is what stops a stockpile from being a number that only goes up.
SPOIL_RATE: dict[Season, float] = {
    Season.SPRING: 0.10,
    Season.SUMMER: 0.15,
    Season.AUTUMN: 0.08,
    Season.WINTER: 0.04,
}

# Each tender removes this much spoilage fraction, down to SPOIL_RATE_FLOOR. Tending can
# never fully defeat rot; three tenders on a summer store is a real dent, not a solution.
SPOIL_REDUCTION_PER_TENDER = 0.03
SPOIL_RATE_FLOOR = 0.02

# --- Starvation ------------------------------------------------------------------------

# One death per this much unmet food demand, rounded up. Children die first: it is the
# grimdark reading and the mechanically correct one, since adults are what keep the hearth
# fed and losing them first would make every shortfall terminal.
FOOD_PER_STARVATION_DEATH = 3
MORALE_LOSS_PER_STARVATION = 2
MORALE_LOSS_PER_DEATH = 1

# --- Population ------------------------------------------------------------------------

CHILD_MATURES_AFTER = 4  # turns, so a child born in spring works the following spring

# A birth needs surplus in the store and morale above the line. Both gates matter: a
# well-fed miserable clan does not grow, and neither does a happy starving one.
# A household that is fed, settled, and has two adults in it builds toward a child. The meter
# is silent, slow, and deterministic: no roll, so growth is something the clan *earns* rather
# than something that either fires or does not. A player who keeps a hearth fed can watch it
# come, without ever being shown the number.
#
# Deterministic on purpose. The seeded RNG exists so runs reproduce, not so every mechanic has
# to be a lottery, and a lottery here would sever the connection between how you rationed and
# whether the clan grew. That connection is the whole point: the hearth you feed last is the
# hearth that stops growing, which is what finally makes "feed the children" different from
# "feed the workers".
BOND_TO_BEAR = 6  # seasons of being fed and content
BOND_MOOD_THRESHOLD = 5
BOND_NEEDS_ADULTS = 2
# A hungry season does not merely pause a household, it sets it back, so famine costs years of
# growth rather than a turn of it.
BOND_LOST_TO_HUNGER = 2

# A hearth this size stops being one household. Splitting is how three kin groups become the
# ten to forty `spec.md` §5 describes, and it gives resentment more places to live.
HOUSEHOLD_SPLITS_AT = 6

BIRTH_FOOD_THRESHOLD = (
    40  # retained: content reads `food` against it, and it reads well
)

# --- Morale ----------------------------------------------------------------------------

# Morale drifts toward this value when nothing pushes it. Without the drift, a single bad
# winter permanently flattens the clan and every later event lands on the floor.
MORALE_DRIFT_TARGET = 5

# --- World -----------------------------------------------------------------------------

MAP_WIDTH = 5
MAP_HEIGHT = 5

# Explorers needed to reveal one tile. Fewer than this reveals nothing, which is what makes
# an explore assignment a commitment rather than a spare-hand default.
EXPLORERS_PER_REVEAL = 2

# Terrain draw weights at generation. Water is rare and, in Phase 0, purely scenery.
TERRAIN_WEIGHTS: dict[Terrain, int] = {
    Terrain.PLAIN: 8,
    Terrain.FOREST: 6,
    Terrain.HILLS: 4,
    Terrain.MARSH: 3,
    Terrain.WATER: 2,
}

# --- Intel -------------------------------------------------------------------------------

# Seasons a fact stays trustworthy. Past one half-life it reads as aging, past two as stale.
# None means it never rots.
#
# Terrain is None because ground does not move, which is what lets the old boolean fog keep
# working underneath the ledger. Presence is deliberately shorter than a year: a band seen
# last spring tells you almost nothing this spring, and that decay is the pressure that makes
# scouting a standing cost rather than a thing you finish.
FACT_HALFLIFE: dict[FactKind, int | None] = {
    FactKind.TERRAIN: None,
    FactKind.FORAGE: 8,
    FactKind.PRESENCE: 2,
}
