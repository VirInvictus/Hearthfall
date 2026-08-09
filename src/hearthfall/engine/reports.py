"""What the scouts say, rendered from what they learned.

`spec.md` §1 puts it in four words: **a report is rendered facts.** Nothing here decides
anything or changes anything. It reads the ledger and says, in the clan's own voice, what the
party came back with, and every sentence it produces is a fact the player could also have read
off the map. That constraint is the point. A report that knew something the ledger does not
would be the game lying to the player about what scouting bought.

It lives in the engine rather than the skin for the same reason every other number does: the
frontend computes nothing (`spec.md` §9.1). A second frontend renders the same sentences, or
reads `TurnReport.learned` and writes its own.

Prose only. If a rule wants to know whether ground is good, it asks `balance`, not this.
"""

from __future__ import annotations

from collections.abc import Sequence

from hearthfall.engine import balance
from hearthfall.engine.intel import FactKind, Ledger
from hearthfall.engine.world import Coord, Terrain, World

# Small numbers read as words in prose and as digits in a ledger. "three can work it" is a
# sentence; "3 can work it" is a readout that happens to be in a paragraph. Past this the
# words get long and the digit is clearer, which is roughly where English gives up too.
NUMBERS = (
    "no one",
    "one",
    "two",
    "three",
    "four",
    "five",
    "six",
    "seven",
    "eight",
    "nine",
    "ten",
)


def count(value: int) -> str:
    return NUMBERS[value] if 0 <= value < len(NUMBERS) else str(value)


def bearing(world: World, target: Coord) -> str:
    """A rough compass word for a tile, relative to the hearth."""
    home_x, home_y = world.home
    x, y = target
    vertical = "north" if y < home_y else "south" if y > home_y else ""
    horizontal = "west" if x < home_x else "east" if x > home_x else ""
    return f"{vertical}{horizontal}" or "edge of the clearing"


def place(world: World, coord: Coord, terrain: Terrain) -> str:
    """Name a tile the way somebody standing at the hearth would name it."""
    if coord == world.home:
        return f"the {terrain} at the hearth"
    return f"the {terrain} to the {bearing(world, coord)}"


def scout_report(
    world: World,
    ledger: Ledger,
    walked: Coord | None,
    surveyed: Coord | None,
    looked: bool,
) -> list[str]:
    """The party's whole account of the season, as lines the caller prints in order.

    Called once, after the party has come home, which is why the steps that move the state say
    nothing themselves. Prose written from inside three separate steps arrives in whatever
    order the steps happen to run and cannot be read as one voice.

    `walked` is ground nobody had stood on before; `surveyed` is the tile the party stopped at
    and worked out, which is often the same one and often not. Either may be None: a party that
    finds the frontier closed still has a survey to make, and one that finds every known tile
    already understood comes back with nothing at all. `looked` says the party was big enough
    to survey, which is what separates "found nothing worth a closer look" from a party that
    was never going to look in the first place.
    """
    lines: list[str] = []
    if walked is not None:
        lines.extend(_walked_lines(world, ledger, walked))
    if surveyed is not None:
        lines.append(_surveyed_line(world, ledger, surveyed, walked))
    elif looked:
        lines.append("They found nothing else worth a closer look.")
    lines.extend(_frontier_lines(world, ledger))
    return lines


def _walked_lines(world: World, ledger: Ledger, walked: Coord) -> list[str]:
    terrain = _terrain(ledger, walked)
    if terrain is None:  # unreachable in a real turn; a walk is what learns the terrain
        return []

    lines = [f"The scouts walked {bearing(world, walked)} into {terrain}."]
    verdict = _verdict(ledger, walked, terrain)
    if verdict:
        lines.append(verdict)
    return lines


def _verdict(ledger: Ledger, walked: Coord, terrain: Terrain) -> str:
    """What the new ground is worth, said in comparison rather than in numbers.

    Only speaks when it has something to say. A middling tile among middling tiles gets no
    line at all, because a sentence that appears every single season stops being read, and the
    seasons where the party comes back with the best ground the clan has ever seen are the
    ones this exists for.
    """
    if not balance.TERRAIN_CAPACITY[terrain]:
        return "Nothing will be taken from it."

    others = [
        found
        for coord in ledger.revealed()
        if coord != walked and (found := _terrain(ledger, coord)) is not None
    ]
    if not others:
        return ""

    worth = balance.TERRAIN_FORAGE[terrain]
    if worth > max(balance.TERRAIN_FORAGE[other] for other in others):
        return "It is the best ground the clan has found."
    if worth < min(balance.TERRAIN_FORAGE[other] for other in others):
        return "Poorer ground than anything the clan already holds."
    return ""


def _surveyed_line(
    world: World, ledger: Ledger, surveyed: Coord, walked: Coord | None
) -> str:
    terrain = _terrain(ledger, surveyed)
    hands = balance.TERRAIN_CAPACITY[terrain] if terrain is not None else 0
    if surveyed == walked:
        return f"They stayed to work out what it will feed: {count(hands)} can work it."
    # Naming the place is what stops this reading as a non sequitur when the party surveys
    # somewhere other than the tile it walked into, which it does whenever better ground is
    # already known and still not understood.
    where = place(world, surveyed, terrain) if terrain is not None else "the ground"
    return f"On the way back they worked out {where}: {count(hands)} can work it."


def _frontier_lines(world: World, ledger: Ledger) -> list[str]:
    """Said once, when there is nowhere left to walk.

    This started as a family of lines counting the ways still open, and measurement killed
    them: across sixty runs a clan walks six to ten tiles of twenty-five, so the frontier
    never narrows and every one of those sentences fired exactly zero times. What is left is
    the one case that can happen, and it has to exist, because a party sent out to a closed
    frontier with nothing to survey would otherwise cost hands and report silence.
    """
    if ledger.frontier(world):
        return []
    return ["There is nothing more within reach to walk into."]


def _terrain(ledger: Ledger, coord: Coord) -> Terrain | None:
    value = ledger.value(FactKind.TERRAIN, coord)
    return Terrain(value) if isinstance(value, str) else None


def shortfall_lines(
    world: World, short: Sequence[tuple[Coord, Terrain, int]]
) -> list[str]:
    """Ground that gave less than the clan was counting on.

    This is the only way a player finds out that a survey has gone out of date, which is why
    it names the place rather than reporting a total: "the store came up nine short" is a
    number, and "the forest to the west is not what it was" is somewhere to send a party.

    One line for the worst offender, because a season where three tiles all disappointed is
    still one piece of news, and listing them buries it.
    """
    if not short:
        return []

    coord, terrain, missing = max(short, key=lambda entry: (entry[2], entry[0]))
    where = place(world, coord, terrain).capitalize()
    return [
        (
            f"{where} gave {missing} less than it should have. "
            "It is not the ground the clan remembers."
        )
    ]


def ground_worked(world: World, worked: Sequence[tuple[Coord, Terrain, int]]) -> str:
    """Name the ground a season's foraging was actually done on.

    Takes places and amounts rather than the engine's own record type, which is not squeamish-
    ness about coupling: `turn` imports this module, so this module cannot import `turn` back.
    A renderer that speaks in places and numbers is the right shape anyway.

    Two forms only. Listing five tiles would bury the number the line exists to carry, and
    naming the best one is what the player needs in order to think about where to scout next.
    """
    if not worked:
        return "nowhere"

    coord, terrain, _ = worked[0]
    best = place(world, coord, terrain)
    others = len(worked) - 1
    if not others:
        return best
    return f"{best} and {others} place{'s' if others > 1 else ''} besides"
