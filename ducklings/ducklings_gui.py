"""Ducklings — CustomTkinter GUI.

Dark-theme window with a monospace display, sliders for duck count and speed,
and colour buttons to tint the duck art (yellow / brown / white).

Run:
    uv run python ducklings/ducklings_gui.py
"""
from __future__ import annotations

import random
import tkinter as tk
from typing import Optional

import customtkinter as ctk

from ducklings import Pond, SPECIES_FRAMES

# ---------------------------------------------------------------------------
# Colour palettes — map palette name → ANSI-like hex for canvas text
# ---------------------------------------------------------------------------
DUCK_COLORS: dict[str, str] = {
    "yellow": "#FFD700",
    "brown":  "#8B4513",
    "white":  "#F0F0F0",
}

BG = "#0f172a"
PANEL = "#1e293b"
TEXT = "#f8fafc"
MUTED = "#94a3b8"
ACCENT = "#38bdf8"
BTN_ACTIVE = "#0ea5e9"

WIDTH = 80   # characters
HEIGHT = 7   # rows (pond render height)


class DucklingsApp(ctk.CTk):
    def __init__(self) -> None:
        super().__init__()
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")

        self.title("Ducklings 🦆")
        self.resizable(False, False)
        self.configure(fg_color=BG)

        self._duck_color = "yellow"
        self._running = True
        self._pond: Optional[Pond] = None
        self._fps = 10
        self._num_ducks = 5
        self._rebuild_pond()

        self._build_ui()
        self._tick()

    # ------------------------------------------------------------------
    # Pond management
    # ------------------------------------------------------------------

    def _rebuild_pond(self) -> None:
        self._pond = Pond(width=WIDTH, num_ducks=self._num_ducks, rng=random.Random())

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        pad = {"padx": 12, "pady": 6}

        # Title
        title = ctk.CTkLabel(self, text="🦆  Ducklings  🦆",
                             font=ctk.CTkFont(size=22, weight="bold"),
                             text_color=TEXT)
        title.pack(**pad)

        # Canvas — monospace label
        self._display = ctk.CTkLabel(
            self,
            text="",
            font=ctk.CTkFont(family="Courier New", size=14),
            text_color=DUCK_COLORS[self._duck_color],
            fg_color=PANEL,
            corner_radius=8,
            justify="left",
            anchor="w",
        )
        self._display.pack(padx=12, pady=4, fill="x")

        # Controls frame
        ctrl = ctk.CTkFrame(self, fg_color=PANEL, corner_radius=8)
        ctrl.pack(padx=12, pady=4, fill="x")

        # Duck count slider
        ctk.CTkLabel(ctrl, text="Ducks:", text_color=MUTED,
                     font=ctk.CTkFont(size=13)).grid(row=0, column=0, padx=8, pady=6, sticky="w")
        self._duck_var = tk.IntVar(value=self._num_ducks)
        duck_slider = ctk.CTkSlider(
            ctrl, from_=1, to=10, number_of_steps=9,
            variable=self._duck_var,
            command=self._on_duck_count,
            button_color=ACCENT, progress_color=ACCENT,
            width=180,
        )
        duck_slider.grid(row=0, column=1, padx=8, pady=6)
        self._duck_lbl = ctk.CTkLabel(ctrl, text=str(self._num_ducks),
                                      text_color=TEXT, width=30)
        self._duck_lbl.grid(row=0, column=2, padx=4)

        # Speed slider
        ctk.CTkLabel(ctrl, text="Speed:", text_color=MUTED,
                     font=ctk.CTkFont(size=13)).grid(row=1, column=0, padx=8, pady=6, sticky="w")
        self._fps_var = tk.IntVar(value=self._fps)
        fps_slider = ctk.CTkSlider(
            ctrl, from_=1, to=30, number_of_steps=29,
            variable=self._fps_var,
            command=self._on_fps,
            button_color=ACCENT, progress_color=ACCENT,
            width=180,
        )
        fps_slider.grid(row=1, column=1, padx=8, pady=6)
        self._fps_lbl = ctk.CTkLabel(ctrl, text=f"{self._fps} fps",
                                     text_color=TEXT, width=60)
        self._fps_lbl.grid(row=1, column=2, padx=4)

        # Color buttons
        color_frame = ctk.CTkFrame(self, fg_color=BG)
        color_frame.pack(padx=12, pady=4)
        ctk.CTkLabel(color_frame, text="Duck colour:", text_color=MUTED,
                     font=ctk.CTkFont(size=13)).pack(side="left", padx=(0, 8))
        for name, hex_color in DUCK_COLORS.items():
            btn = ctk.CTkButton(
                color_frame, text=name.capitalize(), width=90,
                fg_color=hex_color if name != "white" else "#888",
                hover_color=BTN_ACTIVE, text_color="#000" if name in ("yellow", "white") else TEXT,
                command=lambda n=name: self._set_color(n),
                font=ctk.CTkFont(size=12, weight="bold"),
            )
            btn.pack(side="left", padx=4)

        # Pause / Resume button
        self._pause_btn = ctk.CTkButton(
            self, text="Pause", width=100,
            command=self._toggle_pause,
            fg_color=ACCENT, hover_color=BTN_ACTIVE,
            font=ctk.CTkFont(size=13, weight="bold"),
        )
        self._pause_btn.pack(pady=6)

    # ------------------------------------------------------------------
    # Event handlers
    # ------------------------------------------------------------------

    def _on_duck_count(self, value: float) -> None:
        n = int(value)
        self._num_ducks = n
        self._duck_lbl.configure(text=str(n))
        self._rebuild_pond()

    def _on_fps(self, value: float) -> None:
        self._fps = max(1, int(value))
        self._fps_lbl.configure(text=f"{self._fps} fps")

    def _set_color(self, name: str) -> None:
        self._duck_color = name
        self._display.configure(text_color=DUCK_COLORS[name])

    def _toggle_pause(self) -> None:
        self._running = not self._running
        self._pause_btn.configure(text="Resume" if not self._running else "Pause")

    # ------------------------------------------------------------------
    # Animation tick
    # ------------------------------------------------------------------

    def _tick(self) -> None:
        if self._running and self._pond is not None:
            self._pond.step()
            rendered = self._pond.render()
            self._display.configure(text=rendered)

        delay_ms = max(33, int(1000 / max(self._fps, 1)))
        self.after(delay_ms, self._tick)


def main() -> None:
    app = DucklingsApp()
    app.mainloop()


if __name__ == "__main__":
    main()
