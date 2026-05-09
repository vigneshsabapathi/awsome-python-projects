"""Periodic Table — CLI reference and shared core.

Embeds all 118 elements (atomic number, symbol, name, atomic weight,
category, group, period, electron configuration). Provides a pure
``lookup(query)`` accepting symbol/number/name and a CLI that prints
the standard periodic-table grid with category color hints.

Run:
    uv run python periodic_table/periodic_table.py
    uv run python periodic_table/periodic_table.py Fe
    uv run python periodic_table/periodic_table.py --search noble
    uv run python periodic_table/periodic_table.py --quiz
"""
from __future__ import annotations

import argparse
import random
import sys
from dataclasses import dataclass


# Category keys used across CLI/GUI/TUI.
CATEGORIES = {
    'alkali':            'Alkali Metal',
    'alkaline-earth':    'Alkaline Earth Metal',
    'transition':        'Transition Metal',
    'post-transition':   'Post-Transition Metal',
    'metalloid':         'Metalloid',
    'nonmetal':          'Reactive Nonmetal',
    'halogen':           'Halogen',
    'noble-gas':         'Noble Gas',
    'lanthanide':        'Lanthanide',
    'actinide':          'Actinide',
    'unknown':           'Unknown / Predicted',
}


@dataclass(frozen=True)
class Element:
    number: int
    symbol: str
    name: str
    weight: float           # standard atomic weight (u); rounded for unstable
    category: str           # key into CATEGORIES
    group: int              # 1..18; 0 = lanthanide/actinide (off-grid)
    period: int             # 1..7
    config: str             # condensed electron configuration


# ---------------------------------------------------------------------------
# All 118 elements (data: IUPAC 2021 standard atomic weights, rounded;
# unstable elements use the most-stable mass number in brackets per IUPAC).
# ---------------------------------------------------------------------------
ELEMENTS: list[Element] = [
    Element(1,   'H',  'Hydrogen',       1.008,   'nonmetal',        1,  1, '1s1'),
    Element(2,   'He', 'Helium',         4.0026,  'noble-gas',      18,  1, '1s2'),
    Element(3,   'Li', 'Lithium',        6.94,    'alkali',          1,  2, '[He] 2s1'),
    Element(4,   'Be', 'Beryllium',      9.0122,  'alkaline-earth',  2,  2, '[He] 2s2'),
    Element(5,   'B',  'Boron',          10.81,   'metalloid',      13,  2, '[He] 2s2 2p1'),
    Element(6,   'C',  'Carbon',         12.011,  'nonmetal',       14,  2, '[He] 2s2 2p2'),
    Element(7,   'N',  'Nitrogen',       14.007,  'nonmetal',       15,  2, '[He] 2s2 2p3'),
    Element(8,   'O',  'Oxygen',         15.999,  'nonmetal',       16,  2, '[He] 2s2 2p4'),
    Element(9,   'F',  'Fluorine',       18.998,  'halogen',        17,  2, '[He] 2s2 2p5'),
    Element(10,  'Ne', 'Neon',           20.180,  'noble-gas',      18,  2, '[He] 2s2 2p6'),
    Element(11,  'Na', 'Sodium',         22.990,  'alkali',          1,  3, '[Ne] 3s1'),
    Element(12,  'Mg', 'Magnesium',      24.305,  'alkaline-earth',  2,  3, '[Ne] 3s2'),
    Element(13,  'Al', 'Aluminium',      26.982,  'post-transition',13,  3, '[Ne] 3s2 3p1'),
    Element(14,  'Si', 'Silicon',        28.085,  'metalloid',      14,  3, '[Ne] 3s2 3p2'),
    Element(15,  'P',  'Phosphorus',     30.974,  'nonmetal',       15,  3, '[Ne] 3s2 3p3'),
    Element(16,  'S',  'Sulfur',         32.06,   'nonmetal',       16,  3, '[Ne] 3s2 3p4'),
    Element(17,  'Cl', 'Chlorine',       35.45,   'halogen',        17,  3, '[Ne] 3s2 3p5'),
    Element(18,  'Ar', 'Argon',          39.948,  'noble-gas',      18,  3, '[Ne] 3s2 3p6'),
    Element(19,  'K',  'Potassium',      39.098,  'alkali',          1,  4, '[Ar] 4s1'),
    Element(20,  'Ca', 'Calcium',        40.078,  'alkaline-earth',  2,  4, '[Ar] 4s2'),
    Element(21,  'Sc', 'Scandium',       44.956,  'transition',      3,  4, '[Ar] 3d1 4s2'),
    Element(22,  'Ti', 'Titanium',       47.867,  'transition',      4,  4, '[Ar] 3d2 4s2'),
    Element(23,  'V',  'Vanadium',       50.942,  'transition',      5,  4, '[Ar] 3d3 4s2'),
    Element(24,  'Cr', 'Chromium',       51.996,  'transition',      6,  4, '[Ar] 3d5 4s1'),
    Element(25,  'Mn', 'Manganese',      54.938,  'transition',      7,  4, '[Ar] 3d5 4s2'),
    Element(26,  'Fe', 'Iron',           55.845,  'transition',      8,  4, '[Ar] 3d6 4s2'),
    Element(27,  'Co', 'Cobalt',         58.933,  'transition',      9,  4, '[Ar] 3d7 4s2'),
    Element(28,  'Ni', 'Nickel',         58.693,  'transition',     10,  4, '[Ar] 3d8 4s2'),
    Element(29,  'Cu', 'Copper',         63.546,  'transition',     11,  4, '[Ar] 3d10 4s1'),
    Element(30,  'Zn', 'Zinc',           65.38,   'transition',     12,  4, '[Ar] 3d10 4s2'),
    Element(31,  'Ga', 'Gallium',        69.723,  'post-transition',13,  4, '[Ar] 3d10 4s2 4p1'),
    Element(32,  'Ge', 'Germanium',      72.630,  'metalloid',      14,  4, '[Ar] 3d10 4s2 4p2'),
    Element(33,  'As', 'Arsenic',        74.922,  'metalloid',      15,  4, '[Ar] 3d10 4s2 4p3'),
    Element(34,  'Se', 'Selenium',       78.971,  'nonmetal',       16,  4, '[Ar] 3d10 4s2 4p4'),
    Element(35,  'Br', 'Bromine',        79.904,  'halogen',        17,  4, '[Ar] 3d10 4s2 4p5'),
    Element(36,  'Kr', 'Krypton',        83.798,  'noble-gas',      18,  4, '[Ar] 3d10 4s2 4p6'),
    Element(37,  'Rb', 'Rubidium',       85.468,  'alkali',          1,  5, '[Kr] 5s1'),
    Element(38,  'Sr', 'Strontium',      87.62,   'alkaline-earth',  2,  5, '[Kr] 5s2'),
    Element(39,  'Y',  'Yttrium',        88.906,  'transition',      3,  5, '[Kr] 4d1 5s2'),
    Element(40,  'Zr', 'Zirconium',      91.224,  'transition',      4,  5, '[Kr] 4d2 5s2'),
    Element(41,  'Nb', 'Niobium',        92.906,  'transition',      5,  5, '[Kr] 4d4 5s1'),
    Element(42,  'Mo', 'Molybdenum',     95.95,   'transition',      6,  5, '[Kr] 4d5 5s1'),
    Element(43,  'Tc', 'Technetium',     98.0,    'transition',      7,  5, '[Kr] 4d5 5s2'),
    Element(44,  'Ru', 'Ruthenium',      101.07,  'transition',      8,  5, '[Kr] 4d7 5s1'),
    Element(45,  'Rh', 'Rhodium',        102.91,  'transition',      9,  5, '[Kr] 4d8 5s1'),
    Element(46,  'Pd', 'Palladium',      106.42,  'transition',     10,  5, '[Kr] 4d10'),
    Element(47,  'Ag', 'Silver',         107.87,  'transition',     11,  5, '[Kr] 4d10 5s1'),
    Element(48,  'Cd', 'Cadmium',        112.41,  'transition',     12,  5, '[Kr] 4d10 5s2'),
    Element(49,  'In', 'Indium',         114.82,  'post-transition',13,  5, '[Kr] 4d10 5s2 5p1'),
    Element(50,  'Sn', 'Tin',            118.71,  'post-transition',14,  5, '[Kr] 4d10 5s2 5p2'),
    Element(51,  'Sb', 'Antimony',       121.76,  'metalloid',      15,  5, '[Kr] 4d10 5s2 5p3'),
    Element(52,  'Te', 'Tellurium',      127.60,  'metalloid',      16,  5, '[Kr] 4d10 5s2 5p4'),
    Element(53,  'I',  'Iodine',         126.90,  'halogen',        17,  5, '[Kr] 4d10 5s2 5p5'),
    Element(54,  'Xe', 'Xenon',          131.29,  'noble-gas',      18,  5, '[Kr] 4d10 5s2 5p6'),
    Element(55,  'Cs', 'Caesium',        132.91,  'alkali',          1,  6, '[Xe] 6s1'),
    Element(56,  'Ba', 'Barium',         137.33,  'alkaline-earth',  2,  6, '[Xe] 6s2'),
    Element(57,  'La', 'Lanthanum',      138.91,  'lanthanide',      0,  6, '[Xe] 5d1 6s2'),
    Element(58,  'Ce', 'Cerium',         140.12,  'lanthanide',      0,  6, '[Xe] 4f1 5d1 6s2'),
    Element(59,  'Pr', 'Praseodymium',   140.91,  'lanthanide',      0,  6, '[Xe] 4f3 6s2'),
    Element(60,  'Nd', 'Neodymium',      144.24,  'lanthanide',      0,  6, '[Xe] 4f4 6s2'),
    Element(61,  'Pm', 'Promethium',     145.0,   'lanthanide',      0,  6, '[Xe] 4f5 6s2'),
    Element(62,  'Sm', 'Samarium',       150.36,  'lanthanide',      0,  6, '[Xe] 4f6 6s2'),
    Element(63,  'Eu', 'Europium',       151.96,  'lanthanide',      0,  6, '[Xe] 4f7 6s2'),
    Element(64,  'Gd', 'Gadolinium',     157.25,  'lanthanide',      0,  6, '[Xe] 4f7 5d1 6s2'),
    Element(65,  'Tb', 'Terbium',        158.93,  'lanthanide',      0,  6, '[Xe] 4f9 6s2'),
    Element(66,  'Dy', 'Dysprosium',     162.50,  'lanthanide',      0,  6, '[Xe] 4f10 6s2'),
    Element(67,  'Ho', 'Holmium',        164.93,  'lanthanide',      0,  6, '[Xe] 4f11 6s2'),
    Element(68,  'Er', 'Erbium',         167.26,  'lanthanide',      0,  6, '[Xe] 4f12 6s2'),
    Element(69,  'Tm', 'Thulium',        168.93,  'lanthanide',      0,  6, '[Xe] 4f13 6s2'),
    Element(70,  'Yb', 'Ytterbium',      173.05,  'lanthanide',      0,  6, '[Xe] 4f14 6s2'),
    Element(71,  'Lu', 'Lutetium',       174.97,  'lanthanide',      3,  6, '[Xe] 4f14 5d1 6s2'),
    Element(72,  'Hf', 'Hafnium',        178.49,  'transition',      4,  6, '[Xe] 4f14 5d2 6s2'),
    Element(73,  'Ta', 'Tantalum',       180.95,  'transition',      5,  6, '[Xe] 4f14 5d3 6s2'),
    Element(74,  'W',  'Tungsten',       183.84,  'transition',      6,  6, '[Xe] 4f14 5d4 6s2'),
    Element(75,  'Re', 'Rhenium',        186.21,  'transition',      7,  6, '[Xe] 4f14 5d5 6s2'),
    Element(76,  'Os', 'Osmium',         190.23,  'transition',      8,  6, '[Xe] 4f14 5d6 6s2'),
    Element(77,  'Ir', 'Iridium',        192.22,  'transition',      9,  6, '[Xe] 4f14 5d7 6s2'),
    Element(78,  'Pt', 'Platinum',       195.08,  'transition',     10,  6, '[Xe] 4f14 5d9 6s1'),
    Element(79,  'Au', 'Gold',           196.97,  'transition',     11,  6, '[Xe] 4f14 5d10 6s1'),
    Element(80,  'Hg', 'Mercury',        200.59,  'transition',     12,  6, '[Xe] 4f14 5d10 6s2'),
    Element(81,  'Tl', 'Thallium',       204.38,  'post-transition',13,  6, '[Xe] 4f14 5d10 6s2 6p1'),
    Element(82,  'Pb', 'Lead',           207.2,   'post-transition',14,  6, '[Xe] 4f14 5d10 6s2 6p2'),
    Element(83,  'Bi', 'Bismuth',        208.98,  'post-transition',15,  6, '[Xe] 4f14 5d10 6s2 6p3'),
    Element(84,  'Po', 'Polonium',       209.0,   'post-transition',16,  6, '[Xe] 4f14 5d10 6s2 6p4'),
    Element(85,  'At', 'Astatine',       210.0,   'halogen',        17,  6, '[Xe] 4f14 5d10 6s2 6p5'),
    Element(86,  'Rn', 'Radon',          222.0,   'noble-gas',      18,  6, '[Xe] 4f14 5d10 6s2 6p6'),
    Element(87,  'Fr', 'Francium',       223.0,   'alkali',          1,  7, '[Rn] 7s1'),
    Element(88,  'Ra', 'Radium',         226.0,   'alkaline-earth',  2,  7, '[Rn] 7s2'),
    Element(89,  'Ac', 'Actinium',       227.0,   'actinide',        0,  7, '[Rn] 6d1 7s2'),
    Element(90,  'Th', 'Thorium',        232.04,  'actinide',        0,  7, '[Rn] 6d2 7s2'),
    Element(91,  'Pa', 'Protactinium',   231.04,  'actinide',        0,  7, '[Rn] 5f2 6d1 7s2'),
    Element(92,  'U',  'Uranium',        238.03,  'actinide',        0,  7, '[Rn] 5f3 6d1 7s2'),
    Element(93,  'Np', 'Neptunium',      237.0,   'actinide',        0,  7, '[Rn] 5f4 6d1 7s2'),
    Element(94,  'Pu', 'Plutonium',      244.0,   'actinide',        0,  7, '[Rn] 5f6 7s2'),
    Element(95,  'Am', 'Americium',      243.0,   'actinide',        0,  7, '[Rn] 5f7 7s2'),
    Element(96,  'Cm', 'Curium',         247.0,   'actinide',        0,  7, '[Rn] 5f7 6d1 7s2'),
    Element(97,  'Bk', 'Berkelium',      247.0,   'actinide',        0,  7, '[Rn] 5f9 7s2'),
    Element(98,  'Cf', 'Californium',    251.0,   'actinide',        0,  7, '[Rn] 5f10 7s2'),
    Element(99,  'Es', 'Einsteinium',    252.0,   'actinide',        0,  7, '[Rn] 5f11 7s2'),
    Element(100, 'Fm', 'Fermium',        257.0,   'actinide',        0,  7, '[Rn] 5f12 7s2'),
    Element(101, 'Md', 'Mendelevium',    258.0,   'actinide',        0,  7, '[Rn] 5f13 7s2'),
    Element(102, 'No', 'Nobelium',       259.0,   'actinide',        0,  7, '[Rn] 5f14 7s2'),
    Element(103, 'Lr', 'Lawrencium',     266.0,   'actinide',        3,  7, '[Rn] 5f14 7s2 7p1'),
    Element(104, 'Rf', 'Rutherfordium',  267.0,   'transition',      4,  7, '[Rn] 5f14 6d2 7s2'),
    Element(105, 'Db', 'Dubnium',        268.0,   'transition',      5,  7, '[Rn] 5f14 6d3 7s2'),
    Element(106, 'Sg', 'Seaborgium',     269.0,   'transition',      6,  7, '[Rn] 5f14 6d4 7s2'),
    Element(107, 'Bh', 'Bohrium',        270.0,   'transition',      7,  7, '[Rn] 5f14 6d5 7s2'),
    Element(108, 'Hs', 'Hassium',        269.0,   'transition',      8,  7, '[Rn] 5f14 6d6 7s2'),
    Element(109, 'Mt', 'Meitnerium',     278.0,   'unknown',         9,  7, '[Rn] 5f14 6d7 7s2'),
    Element(110, 'Ds', 'Darmstadtium',   281.0,   'unknown',        10,  7, '[Rn] 5f14 6d8 7s2'),
    Element(111, 'Rg', 'Roentgenium',    282.0,   'unknown',        11,  7, '[Rn] 5f14 6d9 7s2'),
    Element(112, 'Cn', 'Copernicium',    285.0,   'transition',     12,  7, '[Rn] 5f14 6d10 7s2'),
    Element(113, 'Nh', 'Nihonium',       286.0,   'unknown',        13,  7, '[Rn] 5f14 6d10 7s2 7p1'),
    Element(114, 'Fl', 'Flerovium',      289.0,   'unknown',        14,  7, '[Rn] 5f14 6d10 7s2 7p2'),
    Element(115, 'Mc', 'Moscovium',      290.0,   'unknown',        15,  7, '[Rn] 5f14 6d10 7s2 7p3'),
    Element(116, 'Lv', 'Livermorium',    293.0,   'unknown',        16,  7, '[Rn] 5f14 6d10 7s2 7p4'),
    Element(117, 'Ts', 'Tennessine',     294.0,   'unknown',        17,  7, '[Rn] 5f14 6d10 7s2 7p5'),
    Element(118, 'Og', 'Oganesson',      294.0,   'noble-gas',      18,  7, '[Rn] 5f14 6d10 7s2 7p6'),
]

# Sanity check at import.
assert len(ELEMENTS) == 118, f'Expected 118 elements, got {len(ELEMENTS)}'

# Indexes for O(1) lookup.
_BY_NUMBER = {e.number: e for e in ELEMENTS}
_BY_SYMBOL = {e.symbol.lower(): e for e in ELEMENTS}
_BY_NAME = {e.name.lower(): e for e in ELEMENTS}


def lookup(query: str | int) -> Element:
    """Return the Element matching ``query`` by atomic number, symbol, or name.

    Raises ``KeyError`` if no element matches.
    """
    if isinstance(query, int):
        if query in _BY_NUMBER:
            return _BY_NUMBER[query]
        raise KeyError(f'No element with atomic number {query}')

    s = str(query).strip()
    if not s:
        raise KeyError('Empty query')

    # Try as integer number first.
    if s.isdigit():
        n = int(s)
        if n in _BY_NUMBER:
            return _BY_NUMBER[n]
        raise KeyError(f'No element with atomic number {n}')

    key = s.lower()
    if key in _BY_SYMBOL:
        return _BY_SYMBOL[key]
    if key in _BY_NAME:
        return _BY_NAME[key]
    raise KeyError(f'No element matches {query!r}')


def search(term: str) -> list[Element]:
    """Return all elements whose name, symbol, or category contains ``term``."""
    t = term.strip().lower()
    if not t:
        return list(ELEMENTS)
    out: list[Element] = []
    for e in ELEMENTS:
        if (t in e.symbol.lower()
                or t in e.name.lower()
                or t in e.category.lower()
                or t in CATEGORIES.get(e.category, '').lower()):
            out.append(e)
    return out


def grid_position(e: Element) -> tuple[int, int]:
    """Return the (row, col) cell on the 10-row x 18-col rendered table.

    Rows 1..7 are the main table; rows 9 and 10 carry the lanthanide and
    actinide series, each shifted to columns 4..17.
    """
    if e.category == 'lanthanide':
        return (9, 4 + (e.number - 57))
    if e.category == 'actinide':
        return (10, 4 + (e.number - 89))
    return (e.period, e.group)


def build_grid() -> list[list[Element | None]]:
    """Return a 10x18 grid of Element|None placed by ``grid_position``."""
    grid: list[list[Element | None]] = [
        [None for _ in range(18)] for _ in range(10)
    ]
    for e in ELEMENTS:
        r, c = grid_position(e)
        grid[r - 1][c - 1] = e
    return grid


# ---------------------------------------------------------------------------
# CLI rendering
# ---------------------------------------------------------------------------

# ANSI 256-color codes per category. Foreground stays default for contrast.
CATEGORY_BG = {
    'alkali':            '202',  # orange
    'alkaline-earth':    '178',  # gold
    'transition':        '67',   # steel blue
    'post-transition':   '109',  # slate
    'metalloid':         '108',  # teal-green
    'nonmetal':          '34',   # green
    'halogen':           '36',   # cyan
    'noble-gas':         '99',   # purple
    'lanthanide':        '168',  # rose
    'actinide':          '161',  # magenta
    'unknown':           '244',  # gray
}


def _supports_color() -> bool:
    return sys.stdout.isatty() and sys.platform != 'emscripten'


def _cell(e: Element | None, color: bool) -> str:
    if e is None:
        return '   .  '
    sym = e.symbol.center(4)
    text = f'{e.number:>3}{sym}'  # 7 chars wide
    if not color:
        return text
    bg = CATEGORY_BG.get(e.category, '244')
    return f'\x1b[48;5;{bg}m\x1b[97m{text}\x1b[0m'


def render_grid(color: bool | None = None) -> str:
    """Render the periodic table as ASCII (or ANSI if a TTY supports it)."""
    if color is None:
        color = _supports_color()
    grid = build_grid()
    lines: list[str] = []

    # Column header
    header = '    ' + ''.join(f'{g:>7}' for g in range(1, 19))
    lines.append(header)
    lines.append('')

    for ri, row in enumerate(grid, start=1):
        if ri == 8:
            continue  # spacer slot, never used directly
        # Map our 10-row layout to printed period labels.
        if ri <= 7:
            label = f'P{ri} '
        elif ri == 9:
            label = 'La '
        else:
            label = 'Ac '
        cells = ''.join(_cell(e, color) for e in row)
        lines.append(f'{label} {cells}')
        if ri == 7:
            lines.append('')

    lines.append('')
    legend = ' '.join(
        (f'\x1b[48;5;{CATEGORY_BG[k]}m\x1b[97m {CATEGORIES[k]} \x1b[0m'
         if color else f'[{CATEGORIES[k]}]')
        for k in CATEGORIES
    )
    lines.append('Legend: ' + legend)
    return '\n'.join(lines)


def format_element(e: Element) -> str:
    return (f'#{e.number:>3}  {e.symbol:<3} {e.name}\n'
            f'  Category : {CATEGORIES[e.category]}\n'
            f'  Weight   : {e.weight} u\n'
            f'  Period   : {e.period}    Group: '
            f'{e.group if e.group else "-"}\n'
            f'  Config   : {e.config}')


# ---------------------------------------------------------------------------
# Quiz mode (twist)
# ---------------------------------------------------------------------------

def quiz(rounds: int = 10, rng: random.Random | None = None) -> None:
    rng = rng or random.Random()
    pool = list(ELEMENTS)
    score = 0
    print(f'\nPeriodic Table Quiz - {rounds} rounds. Type symbol or name. '
          'Enter "q" to quit.\n')
    for i in range(1, rounds + 1):
        e = rng.choice(pool)
        print(f'Round {i}/{rounds}: '
              f'#{e.number} (period {e.period}, '
              f'{CATEGORIES[e.category].lower()}) - what element?')
        try:
            ans = input('> ').strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break
        if ans.lower() == 'q':
            break
        ok = (ans.lower() == e.symbol.lower()
              or ans.lower() == e.name.lower())
        if ok:
            score += 1
            print(f'  Correct! {e.symbol} = {e.name}\n')
        else:
            print(f'  Nope - it was {e.symbol} ({e.name}).\n')
    print(f'Final score: {score}/{rounds}')


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog='periodic_table',
        description='Interactive periodic table reference (118 elements).',
    )
    parser.add_argument('query', nargs='?',
                        help='Element to look up (number, symbol, or name)')
    parser.add_argument('--search', '-s', metavar='TERM',
                        help='List elements matching TERM (name/symbol/category)')
    parser.add_argument('--quiz', '-q', action='store_true',
                        help='Run a quick 10-round identification quiz')
    parser.add_argument('--no-color', action='store_true',
                        help='Disable ANSI color even in a TTY')
    args = parser.parse_args(argv)

    color = False if args.no_color else None  # None = auto

    if args.quiz:
        quiz()
        return 0

    if args.search:
        results = search(args.search)
        if not results:
            print(f'No elements matched {args.search!r}')
            return 1
        for e in results:
            print(f'  #{e.number:>3}  {e.symbol:<3}  {e.name:<14}'
                  f'  {CATEGORIES[e.category]}')
        print(f'\n{len(results)} match(es).')
        return 0

    if args.query:
        try:
            e = lookup(args.query)
        except KeyError as exc:
            print(exc)
            return 1
        print(format_element(e))
        return 0

    # Default: print the full grid.
    print(render_grid(color))
    print('\nTip: pass an element name, symbol, or atomic number for details.')
    print('     --search <term>  filter   |   --quiz   identification game')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
