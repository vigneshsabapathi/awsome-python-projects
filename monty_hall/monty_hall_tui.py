"""Monty Hall — Textual TUI.

Modes:
  - Play  : single-game mode. Press 1/2/3 to pick a door, then s/t to switch
            or stay (or click the buttons).
  - Sim   : Monte Carlo over N doors with a unicode bar chart.

Bindings:
  1, 2, 3 — pick door 1/2/3 (Play mode)
  s       — simulate (Sim mode) / switch (Play mode after pick)
  t       — toggle strategy (Sim mode) / stay (Play mode after pick)
  n       — new round / new sim
  Tab     — switch tabs
  Ctrl+Q  — quit

Run:
    uv run python monty_hall/monty_hall_tui.py
"""
from __future__ import annotations

import random

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.widgets import (
    Button, Footer, Header, Input, RadioButton, RadioSet, Static, TabbedContent,
    TabPane,
)

from monty_hall import simulate, theoretical, wilson_ci

DOOR_CLOSED = '\U0001F6AA'
GOAT = '\U0001F410'
CAR = '\U0001F697'

TRIALS_OPTIONS = (1_000, 10_000, 100_000)
DEFAULT_TRIALS = 10_000

BAR_WIDTH = 40
EIGHTHS = ('', '▏', '▎', '▍', '▌',
           '▋', '▊', '▉')


def render_bar(p: float, width: int = BAR_WIDTH) -> str:
    full_eighths = int(round(p * width * 8))
    full_eighths = max(0, min(full_eighths, width * 8))
    full_blocks, rem = divmod(full_eighths, 8)
    return '█' * full_blocks + EIGHTHS[rem]


class MontyHallTUI(App):
    CSS = """
    Screen { background: #0f172a; color: #f8fafc; }

    #title { text-align: center; text-style: bold; padding-top: 1; }
    #subtitle { text-align: center; color: #94a3b8; padding-bottom: 1; }

    TabbedContent { margin: 0 2; }

    .panel {
        background: #1e293b;
        padding: 1 2;
        margin: 1 0;
    }

    .doors-row {
        height: 9;
        align: center middle;
        padding: 1 0;
    }
    .door {
        width: 14;
        height: 7;
        margin: 0 1;
        background: #1e293b;
        color: #f8fafc;
        border: tall #334155;
        content-align: center middle;
    }
    .door-open-goat {
        background: #475569;
        color: #cbd5e1;
        border: tall #475569;
    }
    .door-car {
        background: #34d399;
        color: #0f172a;
        border: tall #34d399;
        text-style: bold;
    }
    .door-final-bad {
        background: #ef4444;
        color: #f8fafc;
        border: tall #ef4444;
        text-style: bold;
    }

    #play-status {
        text-align: center;
        padding: 1 2;
        margin: 1 2;
        background: #1e293b;
    }

    #play-stats {
        text-align: center;
        color: #94a3b8;
        padding: 0 2 1 2;
    }

    #decide-row {
        height: 3;
        align: center middle;
    }
    #switch-btn { background: #38bdf8; color: #0f172a; text-style: bold; margin: 0 1; }
    #stay-btn { background: #f59e0b; color: #0f172a; text-style: bold; margin: 0 1; }

    #sim-controls {
        height: 5;
        padding: 1 2;
        background: #1e293b;
        margin: 1 0;
    }
    Input {
        width: 8;
        background: #0f172a;
        color: #f8fafc;
        border: tall #334155;
    }
    Input:focus { border: tall #38bdf8; }
    RadioSet { background: transparent; border: none; layout: horizontal; width: auto; }
    RadioButton { margin: 0 1; background: transparent; }

    #sim-chart {
        padding: 1 2;
        background: #1e293b;
        margin: 0 0 1 0;
    }
    #sim-status {
        text-align: center;
        color: #cbd5e1;
        padding: 1 2;
        background: #1e293b;
    }

    #bayes-body { padding: 1 2; }
    """

    BINDINGS = [
        Binding('1', 'pick(0)', 'Pick 1', show=False),
        Binding('2', 'pick(1)', 'Pick 2', show=False),
        Binding('3', 'pick(2)', 'Pick 3', show=False),
        Binding('s', 'switch_or_sim', 'Switch / Sim'),
        Binding('t', 'stay_or_toggle', 'Stay / Toggle'),
        Binding('n', 'new', 'New'),
        Binding('ctrl+q', 'quit', 'Quit'),
    ]
    TITLE = 'Monty Hall'

    def __init__(self) -> None:
        super().__init__()
        self.rng = random.Random()
        # Play state
        self.num_doors_play = 3
        self.car_door = 0
        self.pick: int | None = None
        self.opened: int | None = None
        self.final_pick: int | None = None
        self.phase = 'pick'  # 'pick' | 'decide' | 'reveal'
        self.play_stats = {'switch_wins': 0, 'switch_n': 0,
                           'stay_wins': 0, 'stay_n': 0}

        # Sim state
        self.sim_n = 3
        self.sim_trials = DEFAULT_TRIALS
        self.sim_strategy = 'switch'  # toggle target
        self.sim_results: dict | None = None  # {'switch': dict, 'stay': dict}

    def compose(self) -> ComposeResult:
        yield Header()
        yield Static('MONTY HALL', id='title')
        yield Static('1/2/3 pick · s switch/sim · t stay/toggle · n new · Ctrl+Q quit',
                     id='subtitle')

        with TabbedContent(initial='play-tab'):
            with TabPane('Play', id='play-tab'):
                yield Static('Pick a door (press 1, 2, or 3, or click below).',
                             id='play-status')
                with Horizontal(classes='doors-row'):
                    yield Button(f'{DOOR_CLOSED}\n  1', id='door-0',
                                 classes='door')
                    yield Button(f'{DOOR_CLOSED}\n  2', id='door-1',
                                 classes='door')
                    yield Button(f'{DOOR_CLOSED}\n  3', id='door-2',
                                 classes='door')
                with Horizontal(id='decide-row'):
                    yield Button('SWITCH (s)', id='switch-btn',
                                 disabled=True)
                    yield Button('STAY (t)', id='stay-btn', disabled=True)
                yield Static('', id='play-stats')
                yield Static('', id='play-spacer')

            with TabPane('Simulate', id='sim-tab'):
                with Vertical(id='sim-controls'):
                    with Horizontal():
                        yield Static('Doors (N): ', classes='label')
                        yield Input(value='3', id='n-input',
                                    max_length=3, restrict=r'\d*')
                        yield Static('  Trials: ', classes='label')
                        with RadioSet(id='trials'):
                            for t in TRIALS_OPTIONS:
                                lab = f'{t // 1000}k' if t >= 1000 else str(t)
                                yield RadioButton(
                                    lab, value=(t == DEFAULT_TRIALS),
                                    id=f'trials-{t}')
                        yield Button('Run (s)', id='run-btn',
                                     variant='primary')
                yield Static('', id='sim-chart')
                yield Static('', id='sim-status')

            with TabPane('Bayes', id='bayes-tab'):
                yield Static(self._bayes_text(), id='bayes-body')

        yield Footer()

    # ------------------------------------------------------------------
    def on_mount(self) -> None:
        self._new_round()
        self._run_sim()

    # --- helpers -------------------------------------------------------
    def _bayes_text(self) -> str:
        return (
            '[bold cyan]Why switching wins 2/3 of the time[/]\n\n'
            '[bold]1. Prior[/]  3 doors, 1 car. Before any choice:\n'
            '   P(car=A) = P(car=B) = P(car=C) = 1/3\n\n'
            '[bold]2. You pick door A[/]  (WLOG — uniform pick)\n'
            '   P(car=A) = 1/3      ← the "stay" probability\n'
            '   P(car ∈ {B,C}) = 2/3\n\n'
            '[bold]3. Monty opens a goat[/]\n'
            '   He KNOWS the car location, and never opens it.\n'
            '   • car=A → he picks B or C uniformly\n'
            '   • car=B → he MUST open C\n'
            '   • car=C → he MUST open B\n\n'
            '[bold]4. Bayes (you saw him open C)[/]\n'
            '   P(open=C | car=A) = 1/2\n'
            '   P(open=C | car=B) = 1\n'
            '   P(open=C | car=C) = 0\n\n'
            '   Posterior ∝ prior × likelihood:\n'
            '     car=A: (1/3)(1/2) = 1/6 → 1/3\n'
            '     car=B: (1/3)(1)   = 2/6 → 2/3\n'
            '     car=C: 0\n\n'
            '[bold green]5. Therefore: SWITCH.[/]\n'
            '   stay   wins 1/3,  switch wins 2/3.\n\n'
            '[bold]N-door generalization[/]\n'
            '   P(stay)   = 1 / N\n'
            '   P(switch) = (N - 1) / (N · (N - 2))\n'
            '   Switch always beats stay by a factor (N-1)/(N-2).'
        )

    # --- play mode -----------------------------------------------------
    def _new_round(self) -> None:
        self.car_door = self.rng.randrange(self.num_doors_play)
        self.pick = None
        self.opened = None
        self.final_pick = None
        self.phase = 'pick'
        self._refresh_doors()
        self.query_one('#play-status', Static).update(
            'Pick a door (press 1, 2, or 3, or click below).')
        self.query_one('#switch-btn', Button).disabled = True
        self.query_one('#stay-btn', Button).disabled = True
        self._refresh_play_stats()

    def _refresh_doors(self) -> None:
        for i in range(self.num_doors_play):
            btn = self.query_one(f'#door-{i}', Button)
            btn.classes = 'door'
            if self.phase == 'pick':
                btn.label = f'{DOOR_CLOSED}\n  {i + 1}'
                btn.disabled = False
            elif self.phase == 'decide':
                btn.disabled = True
                if i == self.opened:
                    btn.label = f'{GOAT}\n  {i + 1}'
                    btn.add_class('door-open-goat')
                else:
                    btn.label = f'{DOOR_CLOSED}\n  {i + 1}'
            elif self.phase == 'reveal':
                btn.disabled = True
                if i == self.car_door:
                    btn.label = f'{CAR}\n  {i + 1}'
                    btn.add_class('door-car')
                    if i == self.final_pick:
                        # already car-styled is enough
                        pass
                else:
                    btn.label = f'{GOAT}\n  {i + 1}'
                    if i == self.final_pick:
                        btn.add_class('door-final-bad')
                    else:
                        btn.add_class('door-open-goat')

    def _refresh_play_stats(self) -> None:
        s = self.play_stats
        sw_p = s['switch_wins'] / s['switch_n'] if s['switch_n'] else 0.0
        st_p = s['stay_wins'] / s['stay_n'] if s['stay_n'] else 0.0
        self.query_one('#play-stats', Static).update(
            f'Session — '
            f'[cyan]switch[/]: {s["switch_wins"]}/{s["switch_n"]} ({sw_p * 100:.1f}%)   '
            f'[yellow]stay[/]: {s["stay_wins"]}/{s["stay_n"]} ({st_p * 100:.1f}%)')

    def action_pick(self, door: int) -> None:
        # Only meaningful on the play tab and pick phase.
        if self._active_tab() != 'play-tab':
            return
        if self.phase != 'pick':
            return
        if door >= self.num_doors_play:
            return
        self._do_pick(door)

    def _do_pick(self, door: int) -> None:
        self.pick = door
        candidates = [d for d in range(self.num_doors_play)
                      if d != self.pick and d != self.car_door]
        self.opened = self.rng.choice(candidates)
        self.phase = 'decide'
        self._refresh_doors()
        self.query_one('#play-status', Static).update(
            f'You picked door [bold cyan]{door + 1}[/]. '
            f'Monty opens door [bold]{self.opened + 1}[/] — a goat! '
            f'[cyan]s[/]witch or s[yellow]t[/]ay?')
        self.query_one('#switch-btn', Button).disabled = False
        self.query_one('#stay-btn', Button).disabled = False

    def _decide(self, choice: str) -> None:
        if self.phase != 'decide' or self.pick is None or self.opened is None:
            return
        if choice == 'stay':
            self.final_pick = self.pick
        else:
            remaining = [d for d in range(self.num_doors_play)
                         if d != self.pick and d != self.opened]
            self.final_pick = self.rng.choice(remaining)
        won = self.final_pick == self.car_door
        if choice == 'switch':
            self.play_stats['switch_n'] += 1
            self.play_stats['switch_wins'] += int(won)
        else:
            self.play_stats['stay_n'] += 1
            self.play_stats['stay_wins'] += int(won)
        self.phase = 'reveal'
        self._refresh_doors()
        word = 'SWITCHED' if choice == 'switch' else 'STAYED'
        if won:
            msg = (f'You [bold]{word}[/] -> door {self.final_pick + 1}. '
                   f'[bold green]CAR! You win![/]   (n for new round)')
        else:
            msg = (f'You [bold]{word}[/] -> door {self.final_pick + 1}. '
                   f'[bold red]Goat.[/] Car was behind '
                   f'door {self.car_door + 1}.   (n for new round)')
        self.query_one('#play-status', Static).update(msg)
        self.query_one('#switch-btn', Button).disabled = True
        self.query_one('#stay-btn', Button).disabled = True
        self._refresh_play_stats()

    # --- sim mode ------------------------------------------------------
    def _run_sim(self) -> None:
        chart = self.query_one('#sim-chart', Static)
        chart.update('Running simulations...')
        self.refresh()
        sw = simulate('switch', self.sim_trials, num_doors=self.sim_n,
                      rng=self.rng)
        st = simulate('stay', self.sim_trials, num_doors=self.sim_n,
                      rng=self.rng)
        self.sim_results = {'switch': sw, 'stay': st}
        self._redraw_sim()

    def _redraw_sim(self) -> None:
        if self.sim_results is None:
            return
        sw = self.sim_results['switch']
        st = self.sim_results['stay']
        t_sw = theoretical('switch', self.sim_n)
        t_st = theoretical('stay', self.sim_n)
        ci_sw = wilson_ci(sw['wins'], sw['trials'])
        ci_st = wilson_ci(st['wins'], st['trials'])

        # Scale bars: longest of the four values controls the scale (max 1.0)
        scale = max(sw['p_win'], st['p_win'], t_sw, t_st, 0.05)
        # Bars rendered as if scale=1 maps to BAR_WIDTH; rescale.
        def bar(p: float) -> str:
            return render_bar(p / scale * 1.0 if scale > 0 else 0)

        sw_color = 'cyan'
        st_color = 'yellow'
        toggle_marker = ' [bold]<- toggled[/]'
        sw_arrow = toggle_marker if self.sim_strategy == 'switch' else ''
        st_arrow = toggle_marker if self.sim_strategy == 'stay' else ''

        lines = [
            f'[bold]N = {self.sim_n} doors,  {self.sim_trials:,} trials[/]',
            '',
            f'[{sw_color}]SWITCH empirical[/] {bar(sw["p_win"]):<{BAR_WIDTH}}  '
            f'{sw["p_win"] * 100:6.2f}%{sw_arrow}',
            f'[{sw_color}]SWITCH theory   [/] {bar(t_sw):<{BAR_WIDTH}}  '
            f'{t_sw * 100:6.2f}%',
            '',
            f'[{st_color}]STAY   empirical[/] {bar(st["p_win"]):<{BAR_WIDTH}}  '
            f'{st["p_win"] * 100:6.2f}%{st_arrow}',
            f'[{st_color}]STAY   theory   [/] {bar(t_st):<{BAR_WIDTH}}  '
            f'{t_st * 100:6.2f}%',
        ]
        self.query_one('#sim-chart', Static).update('\n'.join(lines))

        ratio = t_sw / t_st if t_st > 0 else float('inf')
        self.query_one('#sim-status', Static).update(
            f'95% CI — switch [cyan][{ci_sw[0] * 100:.2f}%, {ci_sw[1] * 100:.2f}%][/]   '
            f'stay [yellow][{ci_st[0] * 100:.2f}%, {ci_st[1] * 100:.2f}%][/]   '
            f'switch beats stay by [bold]{ratio:.2f}x[/]'
        )

    # --- events --------------------------------------------------------
    def _active_tab(self) -> str:
        try:
            return self.query_one(TabbedContent).active
        except Exception:
            return 'play-tab'

    def on_button_pressed(self, event: Button.Pressed) -> None:
        bid = event.button.id or ''
        if bid.startswith('door-'):
            i = int(bid.split('-')[1])
            self._do_pick(i)
        elif bid == 'switch-btn':
            self._decide('switch')
        elif bid == 'stay-btn':
            self._decide('stay')
        elif bid == 'run-btn':
            self._run_sim()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        if event.input.id == 'n-input':
            self._update_sim_n(event.value)

    def on_input_changed(self, event: Input.Changed) -> None:
        if event.input.id == 'n-input':
            self._update_sim_n(event.value)

    def _update_sim_n(self, raw: str) -> None:
        if raw.isdigit():
            n = max(3, min(100, int(raw)))
            if n != self.sim_n:
                self.sim_n = n
                # Don't auto-rerun on every keystroke; only on Run button.
                # But redraw theoretical bars if results exist.
                self._run_sim()

    def on_radio_set_changed(self, event: RadioSet.Changed) -> None:
        if event.radio_set.id == 'trials':
            label = str(event.pressed.label).strip()
            self.sim_trials = (int(label[:-1]) * 1000
                               if label.endswith('k') else int(label))

    def action_switch_or_sim(self) -> None:
        if self._active_tab() == 'sim-tab':
            self._run_sim()
        elif self._active_tab() == 'play-tab' and self.phase == 'decide':
            self._decide('switch')

    def action_stay_or_toggle(self) -> None:
        if self._active_tab() == 'sim-tab':
            self.sim_strategy = 'stay' if self.sim_strategy == 'switch' else 'switch'
            self._redraw_sim()
        elif self._active_tab() == 'play-tab' and self.phase == 'decide':
            self._decide('stay')

    def action_new(self) -> None:
        if self._active_tab() == 'play-tab':
            self._new_round()
        elif self._active_tab() == 'sim-tab':
            self._run_sim()


if __name__ == '__main__':
    MontyHallTUI().run()
