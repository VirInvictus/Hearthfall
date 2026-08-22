"""Households: the layer that makes a famine land on somebody.

`spec.md` §5 calls this the load-bearing idea, and the reason is arithmetic. A clan of eight
that goes three short loses one person and a point of morale, and that is a number moving. The
same clan split into three kin groups, one of which was fed last, loses a child *from a
household*, and that household remembers. The famine is identical; only one of them can
produce a rival.

A household is what starves, what resents, what marries, and what feuds. It is deliberately
not a person: nobody here has a name, and the named cast in sub-project 5 gets drawn *from*
these, never bolted alongside them.

The pool has not gone away, it has moved. `Population` still answers `adults`, `child_count`,
`total`, and `morale`, so every caller and every event condition keeps working, but it answers
them by asking the households rather than by holding a count of its own. One source of truth,
and the aggregate is the derived thing.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum



class Trait(StrEnum):
    HEARTH = "hearth"
    IRON = "iron"
    WOLF = "wolf"
    OWL = "owl"

TRAIT_COMPATIBILITY = {
    Trait.HEARTH: {Trait.HEARTH: 1, Trait.IRON: 1, Trait.WOLF: 0, Trait.OWL: 1},
    Trait.IRON: {Trait.HEARTH: 1, Trait.IRON: 2, Trait.WOLF: 2, Trait.OWL: -1},
    Trait.WOLF: {Trait.HEARTH: -1, Trait.IRON: 2, Trait.WOLF: 0, Trait.OWL: 1},
    Trait.OWL: {Trait.HEARTH: 1, Trait.IRON: -1, Trait.WOLF: 1, Trait.OWL: 2},
}

class Rationing(StrEnum):
    """How a short store gets divided. There is no right answer, which is the point."""

    EQUAL = "equal"  # everyone equally hungry, nobody wronged
    WORKERS = "workers"  # next season's production survives; the passed-over remember
    CHILDREN = "children"  # this season costs you; the clan outlives you


@dataclass(slots=True)
class Household:
    """A kin group holding a share of the pool."""

    id: int
    adults: int
    # One entry per child, holding turns remaining until they can be assigned work.
    children: list[int] = field(default_factory=list[int])
    # This household's own morale. The clan-wide number is the average of these.
    mood: int = 5
    # Silent, unbounded, never shown. What they hold against the hearth for being fed last.
    # Read by content through aggregate snapshot keys, never as a number on screen.
    resentment: int = 0
    # The other silent meter, and the kinder one: how settled and provided-for this household
    # is, building toward a child. Fed and content seasons raise it, hungry ones set it back.
    # Never shown either, so growth arrives as an event in the chronicle rather than as a
    # progress bar the player optimises against.
    bond: int = 0
    # Seasons this household went short. Read by `_grow`, so hunger costs growth as well as
    # people, and by content that wants to know who has been carrying the lean years.
    went_short: int = 0
    # The fundamental character of this kin group.
    trait: Trait = Trait.HEARTH
    # The silent meter behind who pairs with whom. Maps Household ID to attraction score.
    attraction: dict[int, int] = field(default_factory=dict)

    @property
    def child_count(self) -> int:
        return len(self.children)

    @property
    def size(self) -> int:
        return self.adults + self.child_count

    @property
    def is_empty(self) -> bool:
        return self.size == 0

    def demand(self, per_adult: int, per_child: int) -> int:
        return self.adults * per_adult + self.child_count * per_child

    def take_a_child(self) -> bool:
        """Remove the child furthest from maturity. Deterministic, and the colder reading.

        It leaves the household the ones closest to being hands, which is the kinder outcome
        mechanically and the harder one to read, which is about right.
        """
        if not self.children:
            return False
        self.children.remove(max(self.children))
        return True

    def take_a_person(self) -> bool:
        """Lose one member: a child first, an adult only when there are no children left.

        Children first is the grimdark reading and the mechanically correct one, since adults
        are what keep the hearth fed and losing them first would make every shortfall
        terminal.
        """
        if self.take_a_child():
            return True
        if self.adults:
            self.adults -= 1
            return True
        return False


def first_claim(
    households: list[Household],
    food: int,
    hoards_at: int,
    per_adult: int,
    per_child: int,
) -> list[int]:
    """What the hearths that have stopped waiting take before anything is divided.

    Slice 4's first rung. A household past `hoards_at` does not accept a share any more, it
    takes what it thinks it is owed, and the player's rationing then applies to what is left.
    That is the teeth: the decision does not disappear, it narrows, and it narrows most in the
    season a short store made it matter.

    Angriest first, so when there is not even enough for the claimants the one with the longest
    memory eats. Pure, like `share_out`, and returns a list in the households' own order.
    """
    claims = [0] * len(households)
    left = food
    order = sorted(
        range(len(households)),
        key=lambda i: (-households[i].resentment, i),
    )
    for index in order:
        household = households[index]
        if household.resentment < hoards_at or not left:
            continue
        claims[index] = min(left, household.demand(per_adult, per_child))
        left -= claims[index]
    return claims


def share_out(
    households: list[Household],
    food: int,
    policy: Rationing,
    per_adult: int,
    per_child: int,
) -> list[int]:
    """Divide `food` among households, returning what each one gets, in list order.

    Pure. Never hands a household more than it can eat, and never leaves food undealt while
    somebody is still short, so the three policies differ in *who goes without* rather than in
    how much is eaten in total. That matters: if a policy quietly wasted food it would be
    strictly worse than the others and the choice would collapse to a right answer.

    EQUAL spreads the shortfall proportionally. The other two sort the queue and fill from the
    front, so the households at the back get whatever is left, which is frequently nothing.
    """
    demands = [h.demand(per_adult, per_child) for h in households]
    total = sum(demands)
    if food >= total:
        return demands
    if not total:
        return [0] * len(households)

    if policy is Rationing.EQUAL:
        # Largest-remainder, so the shares are proportional and every unit is dealt. A plain
        # floor would silently lose up to one unit per household, which at this scale is a
        # meaningful amount of food vanishing on a rule nobody asked for.
        exact = [food * demand / total for demand in demands]
        shares = [int(value) for value in exact]
        for index in sorted(
            range(len(shares)), key=lambda i: (-(exact[i] - shares[i]), i)
        )[: food - sum(shares)]:
            shares[index] += 1
        return shares

    if policy is Rationing.WORKERS:
        # Most hands first, and fewest dependents as the tiebreak: feeding the workers means
        # putting food where it buys the most labour, so a hearth of two adults outranks one
        # of two adults and a child. Without that second key the founding clan, which starts
        # with the same number of adults in every household, ordered identically under this
        # policy and under CHILDREN, and the two were the same function wearing two names.
        order = sorted(
            range(len(households)),
            key=lambda i: (-households[i].adults, households[i].child_count, i),
        )
    else:
        order = sorted(
            range(len(households)),
            key=lambda i: (-households[i].child_count, households[i].adults, i),
        )

    shares = [0] * len(households)
    left = food
    for index in order:
        take = min(left, demands[index])
        shares[index] = take
        left -= take
        if not left:
            break
    return shares
