from __future__ import annotations

import argparse
import os
import pickle
import typing
from dataclasses import replace
from enum import StrEnum
from pathlib import Path

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.command import Hit, Hits, Provider
from textual.containers import Horizontal, Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, Footer, RichLog, Static

from hearthfall import VERSION
from hearthfall.engine import balance, turn
from hearthfall.engine.chronicle import ChronicleEntry
from hearthfall.engine.events.loader import load_corpus
from hearthfall.engine.intel import FactKind
from hearthfall.engine.orders import Orders
from hearthfall.engine.people import Rationing
from hearthfall.engine.rng import Rng
from hearthfall.engine.state import SEASONS, GameState, PendingChoice
from hearthfall.engine.turn import (
    InterruptReason,
    apply_choice,
    forecast,
    resolve_and_record,
    run_until_interrupted,
)
from hearthfall.engine.world import Terrain

# One save file, in the user's state directory. A save written to "whatever
# the working directory was" is a save the player cannot find again tomorrow.
SAVE_PATH = Path.home() / ".local" / "state" / "hearthfall" / "savegame.pkl"
# The save envelope's format stamp. Bump when the pickled shape changes: a
# load refuses anything that is not the current format outright, rather than
# unpickling an older shape and dying seasons later on a slot the state
# did not have when the save was made.
SAVE_FORMAT = 1


class GlyphTier(StrEnum):
    ASCII = "ascii"
    UNICODE = "unicode"
    NERD = "nerd"


GLYPHS = {
    GlyphTier.ASCII: {
        Terrain.PLAIN: ".",
        Terrain.FOREST: "T",
        Terrain.HILLS: "^",
        Terrain.MARSH: "%",
        Terrain.WATER: "~",
        "FOG": "░",
        "HEARTH": "@",
    },
    GlyphTier.UNICODE: {
        Terrain.PLAIN: "·",
        Terrain.FOREST: "♣",
        Terrain.HILLS: "▲",
        Terrain.MARSH: "⚑",
        Terrain.WATER: "≈",
        "FOG": "░",
        "HEARTH": "⌂",
    },
    GlyphTier.NERD: {
        Terrain.PLAIN: "󰝤",
        Terrain.FOREST: "󰔎",
        Terrain.HILLS: "󰎙",
        Terrain.MARSH: "󰏠",
        Terrain.WATER: "󰖌",
        "FOG": "▒",
        "HEARTH": "󰋜",
    },
}

COLOURS: dict[Terrain, str] = {
    Terrain.PLAIN: "#a6a69c",
    Terrain.FOREST: "#8a9a7b",
    Terrain.HILLS: "#c0a36e",
    Terrain.MARSH: "#8992a7",
    Terrain.WATER: "#8ba4b0",
}


class ActionProvider(Provider):
    async def search(self, query: str) -> Hits:
        matcher = self.matcher(query)
        actions = [
            ("Orders: Edit Standing Orders", "set_orders"),
            ("Time: Run until Interrupted", "run_season"),
            ("Time: Accept the Shortfall (Resolve Anyway)", "accept_shortfall"),
            ("View: Change Glyph Tier", "pick_glyph"),
            ("View: Glyph Test Card (Font Advisor)", "show_test_card"),
            ("System: Save Game", "save_game"),
            ("System: Load Game", "load_game"),
        ]
        for title, action in actions:
            score = matcher.match(title)
            if score > 0:
                yield Hit(
                    score,
                    matcher.highlight(title),
                    lambda a=action: typing.cast(
                        "HearthfallApp", self.app
                    ).action_dispatch(a),
                )


def interrupt_line(reason: InterruptReason) -> str:
    """Why the background run handed control back, as one chronicle line.

    A stop the player is never told the reason for reads as a hang, which is
    exactly what a fired event used to be: the run broke and nothing said why.
    The starvation line names both ways through, because a stop with no exit
    is a hang wearing a different colour.
    """
    return {
        InterruptReason.EVENT: "[bold #c0a36e]Interrupted: the clan faces a choice.[/]",
        InterruptReason.STARVATION: "[bold #c4746e]Interrupted: Starvation predicted! "
        "Change the standing orders, or accept the shortfall and resolve anyway.[/]",
        InterruptReason.DIRECTOR: "[bold #c0a36e]Interrupted: the director broke the standing orders. The chronicle tells it.[/]",
        InterruptReason.GAME_OVER: "[bold #c4746e]The hearth goes out.[/]",
    }[reason]


class EventChoiceScreen(ModalScreen[None]):
    """The event the world just put to the clan, and the answers it will take.

    Everything on this screen is engine-formed: title, body, and options are
    `state.pending` (`PendingChoice`), built by the tick that fired the event.
    Choosing calls `turn.apply_choice`, which is the only way a pending choice
    clears; before this screen existed, a fired choice re-interrupted the run
    forever, and the game could not be played past the first event that asked
    a question.

    The pending choice is read through the app at answer time and is never
    held on the screen itself: Save/Load while a question is up swaps the
    app's state, and an answer kept against the old object would land in the
    discarded state and silently vanish.
    """

    CSS = """
    EventChoiceScreen { align: center middle; }
    #event-modal { background: #1d1c19; padding: 1 2; border: solid #c0a36e; width: 64; height: auto; max-height: 80%; }
    #event-title { text-style: bold; color: #c0a36e; margin-bottom: 1; }
    #event-body { margin-bottom: 1; }
    EventChoiceScreen Button { width: 100%; margin-bottom: 1; }
    """

    BINDINGS: typing.ClassVar = [
        Binding("escape", "peek", "Read the chronicle", priority=True),
        Binding("1", "answer(0)"),
        Binding("2", "answer(1)"),
        Binding("3", "answer(2)"),
        Binding("4", "answer(3)"),
        Binding("5", "answer(4)"),
        Binding("6", "answer(5)"),
        Binding("7", "answer(6)"),
        Binding("8", "answer(7)"),
        Binding("9", "answer(8)"),
    ]

    def _pending(self) -> PendingChoice | None:
        return typing.cast("HearthfallApp", self.app).state.pending

    def compose(self) -> ComposeResult:
        pending = self._pending()
        if (
            pending is None
        ):  # unreachable: the screen is only pushed for a pending choice
            return
        with Vertical(id="event-modal"):
            yield Static(pending.title, id="event-title")
            yield Static(pending.body, id="event-body")
            for index, option in enumerate(pending.options):
                label = f"{index + 1}. {option.text}"
                if option.endorsements:
                    label += "\n" + ", ".join(option.endorsements)
                yield Button(label, id=f"option-{index}")

    def action_peek(self) -> None:
        """Step back over the modal without answering. The choice stays
        pending; the next run puts the question straight back."""
        self.dismiss()

    def action_answer(self, index: int) -> None:
        app = typing.cast("HearthfallApp", self.app)
        pending = app.state.pending
        if pending is None or not 0 <= index < len(pending.options):
            return
        option = pending.options[index]
        apply_choice(app.state, index)
        log = self.app.query_one("#chronicle", RichLog)
        taken = option.text
        if option.endorsements:
            # The same wording the chronicle itself records, so the live line
            # and the pane's replay of it read identically.
            taken += f" (Endorsed by {', '.join(option.endorsements)})"
        log.write(f"[#8ea4a2]→ {taken}[/]")
        app.update_rail()
        self.dismiss()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id and event.button.id.startswith("option-"):
            self.action_answer(int(event.button.id.removeprefix("option-")))


class StandingOrdersScreen(ModalScreen[None]):
    """The standing orders, and what the forecast says they would do.

    This is the skin's one edit surface, and for most of this project's life
    it was a stub: the run went out on the all-zero default orders, the first
    shortfall forecast stopped it, and there was nothing to change. The five
    labour lines compete for the same adults; the forecast underneath is the
    engine's own `turn.forecast` against the working orders, so what you are
    looking at is exactly what Run will do, including the shortfall that
    would stop it.
    """

    CSS = """
    StandingOrdersScreen { align: center middle; }
    #orders-modal { background: #1d1c19; padding: 1 2; border: solid #c0a36e; width: 52; height: auto; }
    #orders-title { text-style: bold; color: #c0a36e; margin-bottom: 1; }
    #orders-hands { margin-bottom: 1; color: #8ea4a2; }
    StandingOrdersScreen .orders-label { width: 12; padding-top: 1; }
    StandingOrdersScreen .orders-value { width: 4; content-align: center middle; }
    StandingOrdersScreen Button { margin: 0 1; min-width: 5; }
    #orders-rationing { margin-top: 1; width: 100%; }
    #orders-forecast { margin-top: 1; color: #8ea4a2; }
    #orders-buttons { margin-top: 1; }
    """

    BINDINGS: typing.ClassVar = [
        Binding("escape", "cancel", "Cancel"),
    ]

    # The labour lines, in the order the spec's turn section names them.
    LINES: typing.ClassVar = [
        ("forage", "Forage"),
        ("scout", "Scout"),
        ("tend", "Tend"),
        ("militia", "Militia"),
        ("work", "Work"),
    ]
    RATIONING_LABELS: typing.ClassVar = {
        Rationing.EQUAL: "Rationing: equal shares",
        Rationing.WORKERS: "Rationing: workers first",
        Rationing.CHILDREN: "Rationing: children first",
    }
    # The scalar fields the editor owns. `militia_lines` is deliberately not
    # one of them: this is the minimal editor, and the spear line is the
    # militia order.
    SCALARS: typing.ClassVar = ("forage", "scout", "tend", "militia", "work")

    def _orders(self) -> Orders:
        app = typing.cast("HearthfallApp", self.app)
        assert app.state.standing_orders is not None
        return app.state.standing_orders

    def compose(self) -> ComposeResult:
        with Vertical(id="orders-modal"):
            yield Static("Standing Orders", id="orders-title")
            yield Static("", id="orders-hands")
            for key, label in self.LINES:
                with Horizontal(classes="orders-row"):
                    yield Static(label, classes="orders-label")
                    yield Button("-", id=f"dec-{key}")
                    yield Static("0", id=f"value-{key}", classes="orders-value")
                    yield Button("+", id=f"inc-{key}")
            yield Button("", id="orders-rationing")
            yield Static("", id="orders-forecast")
            with Horizontal(id="orders-buttons"):
                yield Button("Done", id="orders-done")
                yield Button("Cancel", id="orders-cancel")

    def on_mount(self) -> None:
        # The cancel lever: the orders as they stood when the editor opened.
        self._snapshot = replace(self._orders())
        self.refresh_editor()

    def refresh_editor(self) -> None:
        orders = self._orders()
        adults = typing.cast("HearthfallApp", self.app).state.population.adults
        for key, _label in self.LINES:
            self.query_one(f"#value-{key}", Static).update(str(getattr(orders, key)))
        self.query_one("#orders-hands", Static).update(
            f"{orders.assigned} of {adults} hands assigned"
        )
        self.query_one("#orders-rationing", Button).label = self.RATIONING_LABELS[
            orders.rationing
        ]
        self.query_one("#orders-forecast", Static).update(
            typing.cast("HearthfallApp", self.app).forecast_line()
        )

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id is None:
            return
        orders = self._orders()
        adults = typing.cast("HearthfallApp", self.app).state.population.adults
        if event.button.id == "orders-done":
            self.dismiss()
        elif event.button.id == "orders-cancel":
            live = orders
            for field_name in self.SCALARS:
                setattr(live, field_name, getattr(self._snapshot, field_name))
            live.rationing = self._snapshot.rationing
            self.dismiss()
        elif event.button.id == "orders-rationing":
            order = list(Rationing)
            orders.rationing = order[(order.index(orders.rationing) + 1) % len(order)]
            self.refresh_editor()
        elif event.button.id.startswith("inc-"):
            key = event.button.id.removeprefix("inc-")
            if orders.assigned < adults:
                setattr(orders, key, getattr(orders, key) + 1)
            self.refresh_editor()
        elif event.button.id.startswith("dec-"):
            key = event.button.id.removeprefix("dec-")
            if getattr(orders, key) > 0:
                setattr(orders, key, getattr(orders, key) - 1)
            self.refresh_editor()


class HearthfallApp(App):
    CSS = """
    Screen { background: #181616; color: #c5c9c5; }
    #main { height: 1fr; }
    #rail { width: 40; height: 1fr; overflow-y: auto; background: #1d1c19; padding: 1; }
    #chronicle { height: 1fr; width: 1fr; padding: 1 2; border-left: solid #2d2b28; }
    #status { margin-bottom: 1; }
    #forecast { margin-bottom: 1; color: #8ea4a2; }
    ModalScreen { align: center middle; background: #181616 70%; }
    #modal-container { background: #1d1c19; padding: 1 2; border: solid #c0a36e; width: 50; height: auto; }
    """

    COMMANDS = App.COMMANDS | {ActionProvider}

    BINDINGS: typing.ClassVar = [
        Binding("ctrl+p", "command_palette", "Commands"),
        Binding("q", "quit", "Quit"),
    ]

    def __init__(self, state: GameState, rng: Rng) -> None:
        super().__init__()
        self.state = state
        self.rng = rng
        self.glyph_tier = GlyphTier.UNICODE
        self.corpus = load_corpus(state.snapshot())
        # Why the last background run stopped. Surfaced for tests, and honest
        # state for any future widget that wants to show it.
        self.last_interrupt: InterruptReason | None = None

    def compose(self) -> ComposeResult:
        with Horizontal(id="main"):
            with Vertical(id="rail"):
                yield Static(id="status")
                yield Static(id="forecast")
                yield Static(id="map")
            yield RichLog(id="chronicle", wrap=True, markup=True)
        yield Footer()

    def on_mount(self) -> None:
        if not self.state.standing_orders:
            self.state.standing_orders = Orders(is_standing=True)
        self.update_rail()
        log = self.query_one("#chronicle", RichLog)
        log.write(
            f"[#c0a36e]Hearthfall {VERSION}[/][#625e5a] · seed [/]{self.state.seed}"
        )
        for entry in self.state.chronicle:
            self._write_entry(log, entry)

    def on_resize(self) -> None:
        rail = self.query_one("#rail")
        if self.size.width < 80:
            rail.display = False
        else:
            rail.display = True

    def forecast_line(self) -> str:
        """The standing orders' season, in the engine's own numbers.

        The engine built this instrument (`turn.forecast`) and for most of
        the project's life the skin never called it. Produced, demand, net,
        and the idle hands the known ground cannot use, before the season is
        committed: this is the line that makes the allocation a decision
        instead of a guess, and its shortfall is the same one Run would stop
        on.
        """
        orders = self.state.standing_orders
        if orders is None:
            return ""
        projection = forecast(self.state, orders)
        line = (
            f"Forecast: +{projection.produced} food, demand {projection.demand}, "
            f"net {projection.net:+d}, idle hands {projection.foragers_idle}"
        )
        if projection.shortfall:
            line += f" [bold #c4746e]short {projection.shortfall}[/]"
        return line

    def update_rail(self) -> None:
        st = self.state
        status = f"[bold]Year {st.year}, {st.season.value.title()}[/]\nPeople: {st.population.total} ({st.population.adults} adults)\nFood: {st.stores.food}  Morale: {st.population.morale}/10\n"
        self.query_one("#status", Static).update(status)
        self.query_one("#forecast", Static).update(self.forecast_line())
        self.query_one("#map", Static).update(self.render_map())

    def render_map(self) -> str:
        world = self.state.world
        ledger = self.state.ledger
        target = (
            self.state.standing_orders.scout_target
            if self.state.standing_orders
            else None
        )
        lines = []
        g = GLYPHS[self.glyph_tier]
        for y in range(world.height):
            cells = []
            for x in range(world.width):
                coord = (x, y)
                tile = world.tile(coord)
                if coord == world.home:
                    cells.append(f"[bold #c4746e]{g['HEARTH']}[/]")
                elif ledger.knows(FactKind.TERRAIN, coord):
                    style = COLOURS[tile.terrain]
                    if not ledger.knows(FactKind.FORAGE, coord):
                        style = f"dim {style}"
                    cells.append(f"[{style}]{g[tile.terrain]}[/]")
                elif coord == target:
                    cells.append("[bold #c0a36e]?[/]")
                else:
                    cells.append(f"[#3a3733]{g['FOG']}[/]")
            lines.append(" ".join(cells))

        # Legend
        lines.append("")
        lines.append(
            f" {g['HEARTH']} hearth   {g[Terrain.PLAIN]} plain   {g[Terrain.FOREST]} forest"
        )
        lines.append(
            f" {g[Terrain.HILLS]} hills    {g[Terrain.MARSH]} marsh   {g[Terrain.WATER]} water"
        )

        return "\n".join(lines)

    def action_dispatch(self, action: str) -> None:
        if action == "run_season":
            self.run_season()
        elif action == "accept_shortfall":
            self.accept_shortfall()
        elif action == "save_game":
            self.save_game()
        elif action == "load_game":
            self.load_game()
        elif action == "show_test_card":
            log = self.query_one("#chronicle", RichLog)
            log.write("[bold #c0a36e]Glyph Test Card[/]")
            for t in GlyphTier:
                g = GLYPHS[t]
                log.write(
                    f"{t.value.upper():8} | {g['HEARTH']} {g[Terrain.PLAIN]} {g[Terrain.FOREST]} {g[Terrain.HILLS]} {g[Terrain.MARSH]} {g[Terrain.WATER]} {g['FOG']}"
                )
            log.write(
                "[italic #8ba4b0]Advisor: If you see empty boxes or overlapping characters in Unicode or Nerd tiers, your terminal font lacks those glyphs. Use the command palette (Ctrl+P) to switch to ASCII.[/]"
            )
        elif action == "pick_glyph":
            tiers = list(GlyphTier)
            idx = tiers.index(self.glyph_tier)
            self.glyph_tier = tiers[(idx + 1) % len(tiers)]
            self.update_rail()
        elif action == "set_orders":
            self.push_screen(StandingOrdersScreen())

    def _write_entry(self, log: RichLog, entry: ChronicleEntry) -> None:
        """One chronicle entry, exactly as the run wrote it: the season
        header, the event with its prose, the season's lines, and the answer
        if one was given."""
        log.write(
            f"[bold]{entry.season.value.title()}, Year {entry.turn // len(SEASONS) + 1}[/bold]"
        )
        if entry.event_title:
            log.write(f"[bold #c0a36e]Event: {entry.event_title}[/]")
        if entry.event_body:
            log.write(entry.event_body)
        for line in entry.lines:
            # The tick notes the fired event's title into the log lines; it
            # renders above with the event's prose, and twice is a stutter.
            if entry.event_title and line == entry.event_title:
                continue
            log.write(line)
        if entry.choice_taken:
            log.write(f"[#8ea4a2]→ {entry.choice_taken}[/]")

    def _render_chronicle(self) -> None:
        """Rebuild the whole pane from the state's chronicle. Used on mount
        and after a load; before the rewrite, a loaded run kept the old
        run's seasons on screen above its own."""
        log = self.query_one("#chronicle", RichLog)
        log.clear()
        for entry in self.state.chronicle:
            self._write_entry(log, entry)

    def _write_new_entries(self, start_turn: int, log: RichLog) -> None:
        for entry in self.state.chronicle[start_turn:]:
            self._write_entry(log, entry)

    def run_season(self) -> None:
        if self.state.is_over:
            return

        start_turn = self.state.turn
        reason = run_until_interrupted(self.state, self.rng, self.corpus)
        self.last_interrupt = reason

        log = self.query_one("#chronicle", RichLog)
        self._write_new_entries(start_turn, log)

        log.write(interrupt_line(reason))
        if reason is InterruptReason.EVENT and self.state.pending is not None:
            self.push_screen(EventChoiceScreen())

        self.update_rail()

    def accept_shortfall(self) -> None:
        """Resolve one season despite the shortfall forecast.

        The starvation stop is the engine asking for different orders, not a
        wall: some shortfalls (a winter past the store's end) cannot be
        ordered away, and a stop with no way through would keep the run from
        ever resolving again, which is how the skin spent its whole life
        unable to lose. This is the deliberate override: the season resolves
        on the standing orders, deaths and all, and is recorded exactly as a
        background season would be (`turn.resolve_and_record`).
        """
        if self.state.is_over or self.state.pending is not None:
            return
        if self.state.standing_orders is None:
            self.state.standing_orders = Orders(is_standing=True)

        start_turn = self.state.turn
        resolve_and_record(self.state, self.rng, self.corpus)
        log = self.query_one("#chronicle", RichLog)
        self._write_new_entries(start_turn, log)
        self.update_rail()

    def save_game(self) -> None:
        """Pickle the state and the rng into one stamped envelope.

        The envelope is a dict carrying `SAVE_FORMAT` and the game version
        around the payload, so a save from an older shape of the game is
        refused at load instead of being unpickled and dying seasons later
        on a slot it never had. The payload is the tuple `(GameState, Rng)`;
        the rng must ride along or the revived run draws from a different
        stream and stops replaying exactly.

        The save lives in the user's state directory rather than in whatever
        the working directory happened to be when the game launched, and it
        lands via a temp file and a rename so a crash mid-write cannot leave
        a torn save where a good one used to be.
        """
        SAVE_PATH.parent.mkdir(parents=True, exist_ok=True)
        tmp_path = SAVE_PATH.with_suffix(".pkl.tmp")
        with open(tmp_path, "wb") as f:
            pickle.dump(
                {
                    "format": SAVE_FORMAT,
                    "version": VERSION,
                    "state": self.state,
                    "rng": self.rng,
                },
                f,
            )
        os.replace(tmp_path, SAVE_PATH)
        log = self.query_one("#chronicle", RichLog)
        log.write(f"[italic #8ba4b0]Game saved to {SAVE_PATH}[/]")

    def load_game(self) -> None:
        """Swap in the saved state, or say why not.

        A missing save is a normal state, not an error. An unreadable one
        (truncated, corrupt, or from another format of the game) is refused
        and the running game keeps going; the old code would have replaced
        the live run with the exception mid-load.
        """
        log = self.query_one("#chronicle", RichLog)
        if not SAVE_PATH.exists():
            log.write(f"[italic #8ba4b0]No saved game at {SAVE_PATH}.[/]")
            return
        try:
            with open(SAVE_PATH, "rb") as f:
                data = pickle.load(f)
            if not isinstance(data, dict) or data.get("format") != SAVE_FORMAT:
                raise TypeError("not a Hearthfall save in the current format")
            state, rng = data["state"], data["rng"]
            if not isinstance(state, GameState) or not isinstance(rng, Rng):
                raise TypeError("not a Hearthfall save")
        except (
            pickle.PickleError,
            EOFError,
            AttributeError,
            ImportError,
            IndexError,
            KeyError,
            TypeError,
            ValueError,
        ):
            # The set of exceptions a corrupt or hostile pickle file can
            # raise while being read, per the pickle module's own docs.
            log.write(
                "[bold #c4746e]The save could not be read. It may be corrupt "
                "or from an older version of the game. This run continues.[/]"
            )
            return
        self.state, self.rng = state, rng
        # Any live question belonged to the run just left behind; it is
        # answered by nothing now, and a modal held over the loaded run
        # would stack on the one the loaded state may itself be carrying.
        while isinstance(self.screen, EventChoiceScreen):
            self.pop_screen()
        if not self.state.standing_orders:
            self.state.standing_orders = Orders(is_standing=True)
        # The corpus parses conditions against a state's snapshot for
        # validation only; reload it against the loaded state so the skin
        # carries nothing over from the run it was showing.
        self.corpus = load_corpus(self.state.snapshot())
        self.last_interrupt = None
        self._render_chronicle()
        log.write(f"[italic #8ba4b0]Game loaded from {SAVE_PATH}[/]")
        self.update_rail()


def replay_orders(state: GameState) -> Orders:
    """The harness's naive policy, ported for headless runs.

    A scouting party and a tender, forage with the rest: the same fixed rule
    the suite's comparisons measure against, kept deliberately crude so a
    replay is a reading instrument and not a tuned strategy.
    """
    adults = state.population.adults
    scout = (
        balance.SCOUTS_TO_WALK
        if adults >= 5 and state.ledger.frontier(state.world)
        else 0
    )
    tend = 1 if adults - scout >= 3 else 0
    return Orders(forage=adults - scout - tend, scout=scout, tend=tend)


def run_replay(seed: int) -> None:
    """Play one run headless and print the annotated chronicle.

    Season by season: the allocation offered, the forecast it started from,
    what actually happened, and every event with the answer given. This is
    the standing gate's "print an annotated year" as a command; before it
    existed the gate's reading was done by editing tests.
    """
    state = turn.new_game(seed)
    rng = Rng(seed)
    corpus = load_corpus(state.snapshot())
    print(f"Hearthfall {VERSION} replay, seed {seed}")
    while not state.is_over:
        orders = replay_orders(state)
        projection = forecast(state, orders)
        print(
            f"\n== {state.season.value.title()}, Year {state.year} == "
            f"{orders.forage} forage, {orders.scout} scout, {orders.tend} tend "
            f"(forecast +{projection.produced}, net {projection.net:+d})"
        )
        report = turn.resolve(state, orders, rng, corpus)
        for line in report.log:
            if state.pending is not None and line == state.pending.title:
                continue
            print(line)
        if state.pending is not None:
            pending = state.pending
            print(f"Event: {pending.title}")
            print(pending.body)
            turn.apply_choice(state, 0)
            print(f"-> {pending.options[0].text}")
    assert state.outcome is not None
    print(
        f"\n{state.outcome.value}: {state.population.total} alive after "
        f"{state.turn} seasons."
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--seed",
        type=int,
        help="replay a run exactly; 0 is a valid seed, not a default",
    )
    parser.add_argument(
        "--replay",
        action="store_true",
        help="play one run headless and print the annotated chronicle",
    )
    args = parser.parse_args()

    seed = (
        args.seed if args.seed is not None else int.from_bytes(os.urandom(8), "little")
    )
    if args.replay:
        run_replay(seed)
        return

    rng = Rng(seed)
    state = turn.new_game(seed)

    app = HearthfallApp(state, rng)
    app.run()


if __name__ == "__main__":
    main()
