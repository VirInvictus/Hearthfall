"""The Textual skin.

Everything here is presentation. The app holds a `GameState`, hands the engine an `Orders`
when the player commits a turn, and renders the `TurnReport` that comes back. It computes
no game logic of its own: if a number appears on screen, the engine produced it.

That is not tidiness for its own sake. It is what makes this whole module throwaway-able,
which `spec.md` §8 promises about the Textual dependency.
"""

from __future__ import annotations

import argparse
import random
import sys
from typing import ClassVar

from rich.text import Text
from textual import on
from textual.app import App, ComposeResult
from textual.binding import BindingType
from textual.containers import Horizontal, Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, Footer, Label, RichLog, Static

from hearthfall import VERSION
from hearthfall.engine import balance, turn
from hearthfall.engine.events.loader import load_corpus
from hearthfall.engine.intel import FactKind
from hearthfall.engine.people import Rationing
from hearthfall.engine.rng import Rng
from hearthfall.engine.state import (
    GameState,
    Orders,
    Outcome,
    PendingChoice,
    Season,
)
from hearthfall.engine.world import Terrain

# ASCII where it can be, so nothing depends on a font being installed. The fog block is the
# one exception and it is old enough to be everywhere.
GLYPHS: dict[Terrain, str] = {
    Terrain.PLAIN: ".",
    Terrain.FOREST: "T",
    Terrain.HILLS: "^",
    Terrain.MARSH: "%",
    Terrain.WATER: "~",
}
FOG = "░"
HEARTH = "@"

COLOURS: dict[Terrain, str] = {
    Terrain.PLAIN: "#a6a69c",
    Terrain.FOREST: "#8a9a7b",
    Terrain.HILLS: "#c0a36e",
    Terrain.MARSH: "#8992a7",
    Terrain.WATER: "#8ba4b0",
}

RATION_WORDS: dict[Rationing, str] = {
    Rationing.EQUAL: "equal shares",
    Rationing.WORKERS: "the workers first",
    Rationing.CHILDREN: "the children first",
}

JOBS = [
    ("forage", "Forage", "food from the season"),
    ("explore", "Explore", "reveals a tile of the dark"),
    ("tend", "Tend", "slows the rot in the store"),
]


def flow(text: str) -> str:
    """Collapse the corpus's hard-wrapped source lines back into paragraphs.

    Event bodies are written wrapped in the TOML so they stay readable and diffable. Those
    line breaks are an authoring convenience, not layout: the terminal does the wrapping.
    """
    return "\n\n".join(" ".join(block.split()) for block in text.strip().split("\n\n"))


class EventScreen(ModalScreen[int]):
    """A fork, waiting for an answer. Dismisses with the chosen option's index."""

    def __init__(self, pending: PendingChoice) -> None:
        super().__init__()
        self.pending = pending

    def compose(self) -> ComposeResult:
        with Vertical(id="event"):
            yield Label(self.pending.title, id="event-title")
            yield Label(flow(self.pending.body), id="event-body")
            for index, option in enumerate(self.pending.options):
                yield Button(option.text, id=f"option-{index}", classes="option")

    @on(Button.Pressed, ".option")
    def choose(self, event: Button.Pressed) -> None:
        self.dismiss(int(str(event.button.id).removeprefix("option-")))


class EndScreen(ModalScreen[bool]):
    """The verdict. Dismisses True when the player wants another run."""

    def __init__(self, state: GameState) -> None:
        super().__init__()
        self.state = state

    def compose(self) -> ComposeResult:
        endured = self.state.outcome is Outcome.ENDURED
        title = "The fire is still lit." if endured else "The hearth goes out."
        with Vertical(id="event"):
            yield Label(title, id="event-title")
            yield Label(self._summary(), id="event-body")
            yield Button("Another run", id="again", classes="option")
            yield Button("Enough", id="quit", classes="option")

    def _summary(self) -> str:
        state = self.state
        return (
            f"Seed {state.seed}. {state.turn} seasons, year {state.year}.\n"
            f"{state.population.total} left standing, {state.stores.food} food in the store, "
            f"{state.ledger.known_count} of {len(state.world.tiles)} tiles known."
        )

    @on(Button.Pressed, "#again")
    def again(self) -> None:
        self.dismiss(True)

    @on(Button.Pressed, "#quit")
    def stop(self) -> None:
        self.dismiss(False)


class Hearthfall(App[None]):
    TITLE = "Hearthfall"

    CSS = """
    Screen { background: #181616; color: #c5c9c5; }
    #main { height: 1fr; }
    /* Scrollable as a safety net. The ledger's last two lines are the starvation warning
       and the rationing prompt, and on a short terminal they were being clipped below the
       fold, so a player about to lose four people saw only the store going to zero. */
    #left { width: 52; overflow-y: auto; }
    #status { padding: 1 2; background: #1d1c19; }
    #map { padding: 1 2; height: auto; }
    #spacer { height: 1fr; }
    #allocation { padding: 1 2; height: auto; background: #1d1c19; }
    /* The ledger sits directly under the allocation because it is the allocation
       answered: the numbers move as you assign. */
    #ledger { padding: 1 2; height: auto; background: #1d1c19; border-top: solid #2d2b28; }

    /* Textual's stock button variants are a different palette's blue. */
    Button { background: #2d2b28; color: #c5c9c5; border: none; height: 3; }
    Button:hover { background: #3a3733; color: #c0a36e; }
    Button:focus { text-style: bold; }
    #commit { color: #c0a36e; text-style: bold; }
    #commit:disabled { color: #625e5a; }
    /* max-width keeps prose readable: on a wide terminal an unbounded RichLog
       stretches event text to a line length nobody can track back from. */
    #chronicle { width: 1fr; max-width: 100; padding: 1 2; border-left: solid #2d2b28; }
    * {
        scrollbar-background: #1d1c19;
        scrollbar-color: #2d2b28;
        scrollbar-color-hover: #3a3733;
        scrollbar-color-active: #c0a36e;
    }
    .row { height: 3; }
    /* Widths are explicit because a Static defaults to 1fr, which otherwise eats the row
       and pushes the + button clean out of the column, where it cannot be clicked. */
    .step { width: 5; min-width: 5; }
    .count { width: 4; height: 3; content-align: center middle; }
    .job { width: 1fr; height: 3; content-align: left middle; }
    #commit { width: 100%; margin-top: 1; }
    ModalScreen { align: center middle; background: #181616 70%; }
    #event {
        padding: 1 4;
        width: 72;
        height: auto;
        max-height: 90%;
        border: round #c0a36e;
        background: #1d1c19;
    }
    #event-title { text-style: bold; color: #c0a36e; width: 100%; margin-bottom: 1; }
    #event-body { width: 100%; margin-bottom: 1; }
    .option { width: 100%; height: auto; text-align: left; content-align: left middle; margin-bottom: 1; }
    """

    BINDINGS: ClassVar[list[BindingType]] = [
        ("f", "assign('forage', 1)", "Forage"),
        ("F", "assign('forage', -1)", ""),
        ("e", "assign('explore', 1)", "Explore"),
        ("E", "assign('explore', -1)", ""),
        ("t", "assign('tend', 1)", "Tend"),
        ("T", "assign('tend', -1)", ""),
        ("w", "cycle_target", "Where to scout"),
        ("r", "cycle_rationing", "How to ration"),
        ("space", "commit", "Resolve the season"),
        ("n", "new_run", "New run"),
        ("q", "quit", "Quit"),
    ]

    def __init__(self, seed: int) -> None:
        super().__init__()
        self.corpus = load_corpus(turn.new_game(0).snapshot())
        self.start(seed)

    def start(self, seed: int) -> None:
        self.state = turn.new_game(seed)
        self.rng = Rng(seed)
        self.counts = {"forage": 0, "explore": 0, "tend": 0}
        self.rationing = Rationing.EQUAL
        self.target_index = 0

    # --- Layout ---------------------------------------------------------------------

    def compose(self) -> ComposeResult:
        with Horizontal(id="main"):
            with Vertical(id="left"):
                yield Static(id="status")
                yield Static(id="map")
                yield Static(id="spacer")
                with Vertical(id="allocation"):
                    for job, label, _ in JOBS:
                        with Horizontal(classes="row"):
                            yield Button("-", id=f"{job}-down", classes="step")
                            yield Static(id=f"{job}-count", classes="count")
                            yield Button("+", id=f"{job}-up", classes="step")
                            yield Static(f" {label}", classes="job")
                    yield Static(id="idle", classes="idle")
                    yield Static(
                        "[#625e5a]f/e/t to assign · hold shift to take back[/]",
                        id="hint",
                    )
                    yield Button("Resolve the season", id="commit")
                yield Static(id="ledger")
            yield RichLog(id="chronicle", wrap=True, markup=True)
        yield Footer()

    def on_mount(self) -> None:
        self.refresh_view()

    def on_ready(self) -> None:
        # Written here rather than on_mount: RichLog wraps against the width it had when a
        # line was written, and on_mount runs before the layout has one.
        chronicle = self.query_one("#chronicle", RichLog)
        chronicle.write(
            f"[#c0a36e]Hearthfall {VERSION}[/][#625e5a] · seed [/]{self.state.seed}"
        )
        chronicle.write(
            "[#625e5a]Six adults, two children, and everything past the clearing "
            "is guesswork.[/]"
        )

    # --- Rendering ------------------------------------------------------------------

    def refresh_view(self) -> None:
        state = self.state
        population = state.population

        # Built as a Text rather than a markup string so the column padding is literal and
        # obvious. This is the panel the player reads every turn; it should line up.
        status = Text()
        status.append(f"{str(state.season).title()}, year {state.year}", "bold #c0a36e")
        status.append(
            f"   season {state.turn + 1} of {balance.TURNS_PER_RUN}\n", "#625e5a"
        )
        status.append("People ")
        status.append(f"{population.total}", "bold")
        status.append("   ·   ", "#625e5a")
        status.append(f"{population.adults} grown", "#8a9a7b")
        status.append("   ·   ", "#625e5a")
        status.append(f"{population.child_count} young\n", "#8992a7")
        status.append("Food   ")
        status.append(f"{state.stores.food}", "bold")
        status.append("   ·   ", "#625e5a")
        status.append("Morale ")
        status.append(f"{population.morale}", "bold")
        status.append(f"/{balance.MORALE_MAX}", "#625e5a")
        status.append("\n")
        self.append_hearths(status, population)
        self.query_one("#status", Static).update(status)
        self.query_one("#map", Static).update(self.render_map())

        for job, _, _ in JOBS:
            self.query_one(f"#{job}-count", Static).update(
                f"[bold]{self.counts[job]:>2}[/]"
            )

        idle = population.adults - sum(self.counts.values())
        self.query_one("#idle", Static).update(
            Text(f"{idle} idle, and everyone eats regardless.", "#c4746e")
            if idle
            else Text("Every hand assigned.", "#8a9a7b")
        )
        self.query_one("#ledger", Static).update(self.render_ledger())
        self.query_one("#commit", Button).disabled = state.is_over

    def append_hearths(self, status: Text, population) -> None:
        """The kin groups, as size and mood.

        Households arrived in v0.4.0 and were invisible: the layer that starves, resents, and
        now bears children had no representation on screen at all, which made rationing a
        choice about people the player could not see.

        Mood is shown; resentment deliberately is not. It is meant to stay a quiet meter, and
        a number the player can watch is a number the player optimises against.
        """
        hearths = [h for h in population.households if not h.is_empty]
        status.append("Hearths", "#625e5a")
        if not hearths:
            status.append("  none left", "#c4746e")
            return

        # Past a handful the row would wrap and stop being readable, so it collapses to the
        # count and the one that is worst off, which is the household that matters anyway.
        if len(hearths) > 4:
            worst = min(h.mood for h in hearths)
            status.append(f"  {len(hearths)}", "bold")
            status.append("   worst mood ", "#625e5a")
            status.append(f"{worst}", "bold #c4746e" if worst <= 3 else "bold")
            return

        for household in hearths:
            status.append("  ")
            status.append(f"{household.size}", "bold")
            status.append("/", "#625e5a")
            status.append(
                f"{household.mood}", "#c4746e" if household.mood <= 3 else "#8a9a7b"
            )

    def render_ledger(self) -> Text:
        """The season's food ledger for the current allocation.

        Every number here comes from `turn.forecast`; this method only lays them out. It
        exists because the allocation was previously a guess: you committed three foragers
        and found out afterwards whether that fed anyone. Seeing the arithmetic move as you
        assign is what turns the allocation into a decision you can reason about.
        """
        if self.state.is_over:
            return Text("The run is over.", "#625e5a")

        f = turn.forecast(
            self.state,
            Orders(
                forage=self.counts["forage"],
                explore=self.counts["explore"],
                tend=self.counts["tend"],
                rationing=self.rationing,
            ),
        )

        def row(label: str, value: int, style: str) -> None:
            ledger.append(f"  {label:<20}", "#625e5a")
            ledger.append(f"{value:>+5}\n", style)

        ledger = Text()
        ledger.append("This season\n", "bold #c0a36e")

        # The verdict before the arithmetic. A player scanning this panel wants to know
        # whether anyone dies; the breakdown is why, and why can wait one line. This also
        # keeps the warning at the top of the block, where a short terminal cannot cut it off.
        if f.would_starve:
            ledger.append(f"  {f.would_starve} would starve.", "bold #c4746e")
            ledger.append("   Ration by ", "#625e5a")
            ledger.append(f"{RATION_WORDS[self.rationing]}", "bold #c0a36e")
            ledger.append(" (r)\n\n", "#625e5a")
        elif f.shortfall:
            ledger.append("  Not enough. Ration by ", "#625e5a")
            ledger.append(f"{RATION_WORDS[self.rationing]}", "bold #c0a36e")
            ledger.append(" (r)\n\n", "#625e5a")

        # The ceiling comes first, above the arithmetic, because it is the one number that
        # tells the player what to do about a bad season: walk further. Hands with nowhere to
        # go are silent otherwise, and a mechanic the player cannot see is not a decision.
        ledger.append("  Ground known holds ", "#625e5a")
        ledger.append(f"{f.forage_capacity}", "bold")
        if f.foragers_idle:
            ledger.append(f"  ·  {f.foragers_idle} idle\n", "bold #c4746e")
        else:
            ledger.append("\n", "#625e5a")

        row("Foragers bring", f.produced, "#8a9a7b" if f.produced else "#625e5a")
        row(f"{self.state.population.total} mouths eat", -f.eaten, "#c4746e")
        row("Rot in the store", -f.spoiled, "#c4746e" if f.spoiled else "#625e5a")

        ledger.append("  " + "─" * 25 + "\n", "#2d2b28")
        # The store reads as a transition rather than a total, because what the player is
        # deciding is which direction the pile moves, not what it happens to be.
        ledger.append("  Store  ", "#625e5a")
        ledger.append(f"{f.opening_food}", "#625e5a")
        ledger.append(" → ", "#625e5a")
        ledger.append(f"{f.closing_food}", "bold")
        ledger.append(f"  ({f.net:+})\n", "#8a9a7b" if f.net >= 0 else "#c4746e")

        if f.season is Season.WINTER and not f.shortfall:
            ledger.append("\n  Nothing grows in winter.\n", "#8992a7")
        return ledger

    def render_map(self) -> str:
        world = self.state.world
        ledger = self.state.ledger
        target = self.explore_target()
        lines = []
        for y in range(world.height):
            cells = []
            for x in range(world.width):
                coord = (x, y)
                tile = world.tile(coord)
                if coord == world.home:
                    cells.append(f"[bold #c4746e]{HEARTH}[/]")
                elif ledger.knows(FactKind.TERRAIN, coord):
                    cells.append(f"[{COLOURS[tile.terrain]}]{GLYPHS[tile.terrain]}[/]")
                elif coord == target:
                    cells.append("[bold #c0a36e]?[/]")
                else:
                    cells.append(f"[#3a3733]{FOG}[/]")
            lines.append(" ".join(cells))

        # Two lines on purpose. One line is 58 characters and the panel is 52, so it used to
        # wrap between "%" and "marsh" and read as a layout bug rather than a legend.
        legend = (
            f"[#625e5a]{HEARTH} hearth   . plain   T forest\n"
            f"^ hills    % marsh   ~ water[/]"
        )
        scouting = (
            f"[#c0a36e]Scouts head for {target}.[/]"
            if target and self.counts["explore"] >= balance.EXPLORERS_PER_REVEAL
            else "[#625e5a]Nobody is going out.[/]"
        )
        return "\n".join(lines) + f"\n\n{legend}\n{scouting}"

    def explore_target(self) -> tuple[int, int] | None:
        frontier = self.state.ledger.frontier(self.state.world)
        if not frontier:
            return None
        return frontier[self.target_index % len(frontier)]

    # --- Actions --------------------------------------------------------------------

    @on(Button.Pressed, ".step")
    def step(self, event: Button.Pressed) -> None:
        job, direction = str(event.button.id).rsplit("-", 1)
        self.action_assign(job, 1 if direction == "up" else -1)

    def action_assign(self, job: str, delta: int) -> None:
        if delta > 0 and sum(self.counts.values()) >= self.state.population.adults:
            return
        self.counts[job] = max(0, self.counts[job] + delta)
        self.refresh_view()

    def action_cycle_rationing(self) -> None:
        order = list(Rationing)
        self.rationing = order[(order.index(self.rationing) + 1) % len(order)]
        self.refresh_view()

    def action_cycle_target(self) -> None:
        self.target_index += 1
        self.refresh_view()

    def action_new_run(self) -> None:
        self.start(random.randrange(1_000_000))
        self.query_one("#chronicle", RichLog).write(
            f"\n[#c0a36e]A new hearth. Seed {self.state.seed}.[/]"
        )
        self.refresh_view()

    @on(Button.Pressed, "#commit")
    def commit_pressed(self) -> None:
        self.action_commit()

    def action_commit(self) -> None:
        if self.state.is_over or self.state.pending is not None:
            return

        orders = Orders(
            forage=self.counts["forage"],
            explore=self.counts["explore"],
            tend=self.counts["tend"],
            rationing=self.rationing,
            explore_target=self.explore_target()
            if self.counts["explore"] >= balance.EXPLORERS_PER_REVEAL
            else None,
        )
        report = turn.resolve(self.state, orders, self.rng, self.corpus)

        chronicle = self.query_one("#chronicle", RichLog)
        chronicle.write(
            f"\n[bold #c0a36e]{str(report.season).title()}, year {report.turn // 4 + 1}[/]"
        )
        for line in report.log:
            chronicle.write(f"  {line}")

        self.counts = {"forage": 0, "explore": 0, "tend": 0}
        self.target_index = 0
        self.refresh_view()

        if self.state.pending is not None:
            self.push_screen(EventScreen(self.state.pending), self.answered)
        elif self.state.is_over:
            self.finish()

    def answered(self, index: int | None) -> None:
        if index is None:
            return
        pending = self.state.pending
        assert pending is not None
        turn.apply_choice(self.state, index)
        self.query_one("#chronicle", RichLog).write(
            f"  [#8992a7]{pending.options[index].text}[/]"
        )
        self.refresh_view()
        if self.state.is_over:
            self.finish()

    def finish(self) -> None:
        self.push_screen(EndScreen(self.state), self.restart_or_stop)

    def restart_or_stop(self, again: bool | None) -> None:
        if again:
            self.action_new_run()
        else:
            self.exit()


def main() -> int:
    parser = argparse.ArgumentParser(
        prog="hearthfall", description="A grimdark clan-survival game"
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=None,
        help="replay a specific run; the same seed always plays out the same way",
    )
    arguments = parser.parse_args()
    seed = arguments.seed if arguments.seed is not None else random.randrange(1_000_000)
    Hearthfall(seed).run()
    return 0


if __name__ == "__main__":
    sys.exit(main())
