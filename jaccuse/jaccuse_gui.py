"""J'Accuse! — CustomTkinter GUI.

A film-noir desktop UI for the J'Accuse mystery deduction game.
Sepia accents on a near-black background. Suspect cards on the left,
witnesses to visit on the right, clue log scrolling below. An accusation
modal locks in the player's pick.

Run:
    uv run python jaccuse/jaccuse_gui.py
"""
from __future__ import annotations

import random
import tkinter as tk

import customtkinter as ctk

from jaccuse import (
    LIE_PROBABILITY, MAX_ROUNDS, NUM_SUSPECTS, NUM_WITNESSES,
    Game,
)

# Film-noir palette — near-black backgrounds with sepia/parchment accents.
BG_DARK = '#0b0a08'
BG_PANEL = '#171411'
BG_CARD = '#22201d'
BG_CARD_DIM = '#181614'
SEPIA = '#c9a063'
SEPIA_DIM = '#8a6f44'
PARCHMENT = '#e8d8b6'
TEXT_MUTED = '#9a8f7a'
TEXT_FAINT = '#5d5547'
ACCENT_RED = '#a23f3f'
ACCENT_GREEN = '#6b8a4a'

TITLE_FONT = ('Georgia', 30, 'bold')
SECTION_FONT = ('Georgia', 14, 'bold')
LABEL_FONT = ('Georgia', 12)
SMALL_FONT = ('Georgia', 11)
CARD_NAME_FONT = ('Georgia', 13, 'bold')
CARD_DETAIL_FONT = ('Consolas', 10)
INITIAL_FONT = ('Georgia', 22, 'bold')


class JaccuseApp(ctk.CTk):
    def __init__(self) -> None:
        super().__init__()
        ctk.set_appearance_mode('dark')

        self.title("J'Accuse!")
        self.geometry('1080x720')
        self.minsize(960, 640)
        self.configure(fg_color=BG_DARK)

        self.game: Game = Game(rng=random.Random())
        self.suspect_cards: dict[str, dict[str, ctk.CTkBaseClass]] = {}
        self.selected_suspect: str | None = None

        self._build_ui()
        self._refresh()

    # ------------------------------------------------------------------ UI
    def _build_ui(self) -> None:
        # Header.
        header = ctk.CTkFrame(self, fg_color='transparent')
        header.pack(side='top', fill='x', padx=24, pady=(18, 4))
        ctk.CTkLabel(header, text="J'ACCUSE !", font=TITLE_FONT,
                     text_color=SEPIA).pack(side='left')
        self.round_lbl = ctk.CTkLabel(
            header, text='', font=SECTION_FONT, text_color=PARCHMENT)
        self.round_lbl.pack(side='right')

        ctk.CTkLabel(self,
                     text=('A crime in the Belle Epoque. Visit witnesses, '
                           'gather clues, accuse the guilty. Beware: some '
                           f'witnesses lie {int(LIE_PROBABILITY*100)}% of the time.'),
                     font=SMALL_FONT, text_color=TEXT_MUTED,
                     wraplength=1000, justify='left'
                     ).pack(side='top', fill='x', padx=24, pady=(0, 8))

        # Main 3-column layout.
        body = ctk.CTkFrame(self, fg_color='transparent')
        body.pack(side='top', fill='both', expand=True, padx=24, pady=(4, 8))
        body.grid_columnconfigure(0, weight=3)
        body.grid_columnconfigure(1, weight=2)
        body.grid_columnconfigure(2, weight=3)
        body.grid_rowconfigure(0, weight=1)

        # Left: suspect cards in a scrollable frame.
        left = ctk.CTkFrame(body, fg_color=BG_PANEL, corner_radius=8)
        left.grid(row=0, column=0, sticky='nsew', padx=(0, 8))
        ctk.CTkLabel(left, text='SUSPECTS', font=SECTION_FONT,
                     text_color=SEPIA).pack(anchor='w', padx=14, pady=(10, 4))
        self.suspect_frame = ctk.CTkScrollableFrame(
            left, fg_color='transparent', corner_radius=0)
        self.suspect_frame.pack(side='top', fill='both', expand=True,
                                padx=8, pady=(0, 10))

        # Middle: witness list.
        mid = ctk.CTkFrame(body, fg_color=BG_PANEL, corner_radius=8)
        mid.grid(row=0, column=1, sticky='nsew', padx=4)
        ctk.CTkLabel(mid, text='WITNESSES', font=SECTION_FONT,
                     text_color=SEPIA).pack(anchor='w', padx=14, pady=(10, 4))
        self.witness_frame = ctk.CTkScrollableFrame(
            mid, fg_color='transparent', corner_radius=0)
        self.witness_frame.pack(side='top', fill='both', expand=True,
                                padx=8, pady=(0, 10))

        # Right: clue log + hint.
        right = ctk.CTkFrame(body, fg_color=BG_PANEL, corner_radius=8)
        right.grid(row=0, column=2, sticky='nsew', padx=(8, 0))
        ctk.CTkLabel(right, text='CASE NOTES', font=SECTION_FONT,
                     text_color=SEPIA).pack(anchor='w', padx=14, pady=(10, 4))

        self.log = ctk.CTkTextbox(
            right, fg_color=BG_CARD_DIM, text_color=PARCHMENT,
            font=('Georgia', 12), wrap='word', border_width=0,
            corner_radius=6)
        self.log.pack(side='top', fill='both', expand=True,
                      padx=10, pady=(0, 6))
        self.log.configure(state='disabled')

        hint_row = ctk.CTkFrame(right, fg_color='transparent')
        hint_row.pack(side='top', fill='x', padx=10, pady=(0, 10))
        self.hint_lbl = ctk.CTkLabel(hint_row, text='',
                                     font=SMALL_FONT, text_color=TEXT_MUTED,
                                     anchor='w', justify='left',
                                     wraplength=320)
        self.hint_lbl.pack(side='left', fill='x', expand=True)
        ctk.CTkButton(hint_row, text='Auto-deduce',
                      fg_color=BG_CARD, hover_color=SEPIA_DIM,
                      text_color=PARCHMENT, font=SMALL_FONT,
                      width=110, command=self._auto_deduce
                      ).pack(side='right')

        # Footer: status line + action buttons.
        footer = ctk.CTkFrame(self, fg_color='transparent')
        footer.pack(side='top', fill='x', padx=24, pady=(4, 16))
        self.status = ctk.CTkLabel(footer, text='', font=LABEL_FONT,
                                   text_color=PARCHMENT, anchor='w')
        self.status.pack(side='left', fill='x', expand=True)
        ctk.CTkButton(footer, text='New Case',
                      fg_color=BG_CARD, hover_color=SEPIA_DIM,
                      text_color=PARCHMENT, command=self._new_game
                      ).pack(side='right', padx=(8, 0))
        self.accuse_btn = ctk.CTkButton(
            footer, text="J'Accuse !",
            fg_color=ACCENT_RED, hover_color='#7e2d2d',
            text_color=PARCHMENT, font=('Georgia', 13, 'bold'),
            command=self._open_accusation)
        self.accuse_btn.pack(side='right')

    # ------------------------------------------------------------- helpers
    def _build_suspect_cards(self) -> None:
        for child in self.suspect_frame.winfo_children():
            child.destroy()
        self.suspect_cards.clear()
        for s in self.game.suspects:
            card = ctk.CTkFrame(self.suspect_frame, fg_color=BG_CARD,
                                corner_radius=8)
            card.pack(side='top', fill='x', padx=4, pady=4)
            card.grid_columnconfigure(1, weight=1)

            initial = ctk.CTkLabel(card, text=s.initial(), font=INITIAL_FONT,
                                   text_color=SEPIA, fg_color=BG_CARD_DIM,
                                   width=52, height=52, corner_radius=26)
            initial.grid(row=0, column=0, rowspan=2, padx=10, pady=10)

            name = ctk.CTkLabel(card, text=s.name, font=CARD_NAME_FONT,
                                text_color=PARCHMENT, anchor='w')
            name.grid(row=0, column=1, sticky='ew', padx=(0, 10), pady=(10, 0))

            details = (f'hair: {s.hair}\n'
                       f'wears: {s.clothing}\n'
                       f'has: {s.accessory}')
            detail_lbl = ctk.CTkLabel(card, text=details, font=CARD_DETAIL_FONT,
                                      text_color=TEXT_MUTED, anchor='w',
                                      justify='left')
            detail_lbl.grid(row=1, column=1, sticky='ew', padx=(0, 10),
                            pady=(0, 10))
            self.suspect_cards[s.name] = {
                'card': card, 'initial': initial,
                'name': name, 'detail': detail_lbl,
            }

    def _build_witness_buttons(self) -> None:
        for child in self.witness_frame.winfo_children():
            child.destroy()
        if self.game.finished:
            ctk.CTkLabel(self.witness_frame, text='Case closed.',
                         font=LABEL_FONT, text_color=TEXT_MUTED
                         ).pack(anchor='w', padx=4, pady=4)
            return
        for w in self.game.witnesses:
            visited = w in self.game.visited
            disabled = visited or self.game.rounds_remaining == 0
            btn = ctk.CTkButton(
                self.witness_frame,
                text=('  ' + w + ('  (spoken to)' if visited else '')),
                anchor='w',
                fg_color=BG_CARD_DIM if disabled else BG_CARD,
                hover_color=SEPIA_DIM,
                text_color=TEXT_FAINT if disabled else PARCHMENT,
                font=LABEL_FONT,
                state='disabled' if disabled else 'normal',
                command=lambda name=w: self._visit(name),
            )
            btn.pack(side='top', fill='x', padx=4, pady=3)

    def _refresh(self) -> None:
        self._build_suspect_cards()
        self._build_witness_buttons()
        self.round_lbl.configure(
            text=f'Round {min(self.game.round_no + 1, self.game.max_rounds)} '
                 f'of {self.game.max_rounds}   |   '
                 f'Visits left: {self.game.rounds_remaining}')
        self._render_log()
        self._update_hint()
        if self.game.finished and self.game.result is not None:
            self.status.configure(text=self.game.result.verdict(),
                                  text_color=(ACCENT_GREEN
                                              if self.game.result.correct
                                              else ACCENT_RED))
            self.accuse_btn.configure(state='disabled')
        else:
            self.status.configure(text='Visit a witness, then make your accusation.',
                                  text_color=TEXT_MUTED)
            self.accuse_btn.configure(state='normal')

    def _render_log(self) -> None:
        self.log.configure(state='normal')
        self.log.delete('1.0', 'end')
        if not self.game.clues:
            self.log.insert('end', 'No clues yet. The case is fresh.\n')
        for clue in self.game.clues:
            self.log.insert(
                'end',
                f'Round {clue.round_no} — {clue.sentence()}\n\n')
        self.log.configure(state='disabled')
        self.log.see('end')

    def _update_hint(self) -> None:
        strict = self.game.deduce_strict()
        tolerant = self.game.deduce_tolerant()
        if not self.game.clues:
            self.hint_lbl.configure(
                text='Auto-deduce will narrow suspects once you have clues.')
            return
        strict_names = ', '.join(s.name for s in strict) or '(none — a witness lied)'
        tolerant_names = ', '.join(s.name for s in tolerant)
        self.hint_lbl.configure(
            text=(f'Strict ({len(strict)}): {strict_names}\n'
                  f'Lie-tolerant ({len(tolerant)}): {tolerant_names}'))

    # -------------------------------------------------------------- actions
    def _visit(self, witness: str) -> None:
        if self.game.finished:
            return
        try:
            self.game.visit(witness)
        except (ValueError, RuntimeError) as e:
            self.status.configure(text=str(e), text_color=ACCENT_RED)
            return
        self._refresh()

    def _auto_deduce(self) -> None:
        tolerant = self.game.deduce_tolerant()
        if not self.game.clues:
            self.status.configure(
                text='Gather some clues first.', text_color=TEXT_MUTED)
            return
        # Highlight the surviving suspects.
        survivors = {s.name for s in tolerant}
        for name, parts in self.suspect_cards.items():
            card = parts['card']
            if name in survivors:
                card.configure(fg_color=BG_CARD,
                               border_width=2, border_color=SEPIA)
            else:
                card.configure(fg_color=BG_CARD_DIM,
                               border_width=0)
        self.status.configure(
            text=f'Auto-deduce: {len(tolerant)} candidate(s) highlighted.',
            text_color=SEPIA)

    def _open_accusation(self) -> None:
        if self.game.finished:
            return
        modal = ctk.CTkToplevel(self)
        modal.title('Make your accusation')
        modal.configure(fg_color=BG_PANEL)
        modal.geometry('420x420')
        modal.transient(self)
        modal.grab_set()

        ctk.CTkLabel(modal, text="J'Accuse !", font=('Georgia', 22, 'bold'),
                     text_color=SEPIA).pack(pady=(16, 4))
        ctk.CTkLabel(modal, text='Choose the guilty party.',
                     font=LABEL_FONT, text_color=PARCHMENT
                     ).pack(pady=(0, 10))

        var = tk.StringVar(value=self.selected_suspect or '')
        list_frame = ctk.CTkScrollableFrame(modal, fg_color=BG_DARK,
                                            corner_radius=6)
        list_frame.pack(fill='both', expand=True, padx=20, pady=8)
        for s in self.game.suspects:
            ctk.CTkRadioButton(
                list_frame, text=f'{s.name}  ({s.hair} hair, {s.clothing})',
                variable=var, value=s.name,
                fg_color=SEPIA, hover_color=SEPIA_DIM,
                text_color=PARCHMENT, font=LABEL_FONT,
            ).pack(anchor='w', padx=8, pady=4)

        def confirm() -> None:
            chosen = var.get()
            if not chosen:
                return
            self.selected_suspect = chosen
            modal.destroy()
            self._submit_accusation(chosen)

        button_row = ctk.CTkFrame(modal, fg_color='transparent')
        button_row.pack(fill='x', padx=20, pady=(4, 16))
        ctk.CTkButton(button_row, text='Cancel',
                      fg_color=BG_CARD, hover_color=BG_CARD_DIM,
                      text_color=PARCHMENT,
                      command=modal.destroy).pack(side='right', padx=(8, 0))
        ctk.CTkButton(button_row, text='Accuse',
                      fg_color=ACCENT_RED, hover_color='#7e2d2d',
                      text_color=PARCHMENT, font=('Georgia', 13, 'bold'),
                      command=confirm).pack(side='right')

    def _submit_accusation(self, name: str) -> None:
        try:
            self.game.accuse(name)
        except ValueError as e:
            self.status.configure(text=str(e), text_color=ACCENT_RED)
            return
        self._refresh()

    def _new_game(self) -> None:
        self.game = Game(rng=random.Random())
        self.selected_suspect = None
        self._refresh()


if __name__ == '__main__':
    JaccuseApp().mainloop()
