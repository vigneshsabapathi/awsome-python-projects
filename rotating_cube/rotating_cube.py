"""Rotating Cube — pure 3D wireframe renderer + CLI animation.

Builds a unit cube (or other Platonic solid) in 3D, rotates it via three
axis-rotation matrices, perspective-projects each vertex onto a 2D plane,
then rasterises the edges into an ASCII character buffer using a Bresenham
line algorithm.

Public API used by the GUI / TUI front-ends:

    Cube(size)                                  -> 8 vertices, 12 edges
    SHAPES = {'cube', 'tetrahedron', 'octahedron', 'dodecahedron'}
    make_shape(name, size)                      -> Shape instance
    cube.rotate(rx, ry, rz)                     -> new rotated Shape
    project(shape, distance, fov)               -> [(x, y, z), ...]
    edges_2d(shape, projected)                  -> [((x1,y1), (x2,y2), z), ...]
    render(width, height, edges_2d_list, fill)  -> ASCII frame

Run:
    uv run python rotating_cube/rotating_cube.py
    uv run python rotating_cube/rotating_cube.py --shape tetrahedron --fps 30
"""
from __future__ import annotations

import argparse
import math
import os
import sys
import time
from dataclasses import dataclass
from typing import Iterable

import numpy as np

# ---------------------------------------------------------------------------
# Geometry
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Shape:
    """A 3D wireframe shape: vertices in R^3 + integer edge index pairs.

    `vertices` is shape (N, 3). `edges` is a list of (i, j) pairs into vertices.
    Immutable so `rotate` can return a fresh shape without aliasing.
    """

    vertices: np.ndarray
    edges: tuple[tuple[int, int], ...]
    name: str = 'shape'

    def rotate(self, rx: float, ry: float, rz: float) -> 'Shape':
        """Return a new shape rotated by (rx, ry, rz) radians around X, Y, Z.

        Composed in X-Y-Z order: R = Rz @ Ry @ Rx, applied as v' = R @ v.
        """
        rotated = self.vertices @ _rotation_matrix(rx, ry, rz).T
        return Shape(rotated, self.edges, self.name)


def _rotation_matrix(rx: float, ry: float, rz: float) -> np.ndarray:
    """Compose the three axis-rotation matrices into one 3x3 matrix."""
    cx, sx = math.cos(rx), math.sin(rx)
    cy, sy = math.cos(ry), math.sin(ry)
    cz, sz = math.cos(rz), math.sin(rz)
    rot_x = np.array([[1, 0, 0],
                      [0, cx, -sx],
                      [0, sx, cx]], dtype=float)
    rot_y = np.array([[cy, 0, sy],
                      [0, 1, 0],
                      [-sy, 0, cy]], dtype=float)
    rot_z = np.array([[cz, -sz, 0],
                      [sz, cz, 0],
                      [0, 0, 1]], dtype=float)
    return rot_z @ rot_y @ rot_x


# ---------------------------------------------------------------------------
# Shape factories
# ---------------------------------------------------------------------------


def Cube(size: float = 1.0) -> Shape:
    """Build an axis-aligned cube of edge length 2*size centred at origin."""
    s = float(size)
    verts = np.array([
        [-s, -s, -s], [s, -s, -s], [s, s, -s], [-s, s, -s],
        [-s, -s, s],  [s, -s, s],  [s, s, s],  [-s, s, s],
    ], dtype=float)
    edges = (
        (0, 1), (1, 2), (2, 3), (3, 0),  # back face
        (4, 5), (5, 6), (6, 7), (7, 4),  # front face
        (0, 4), (1, 5), (2, 6), (3, 7),  # connecting edges
    )
    return Shape(verts, edges, 'cube')


def Tetrahedron(size: float = 1.0) -> Shape:
    """4 vertices of a regular tetrahedron inscribed in the cube."""
    s = float(size)
    verts = np.array([
        [s, s, s],
        [s, -s, -s],
        [-s, s, -s],
        [-s, -s, s],
    ], dtype=float)
    edges = ((0, 1), (0, 2), (0, 3), (1, 2), (1, 3), (2, 3))
    return Shape(verts, edges, 'tetrahedron')


def Octahedron(size: float = 1.0) -> Shape:
    """6 vertices on the principal axes — dual of the cube."""
    s = float(size)
    verts = np.array([
        [s, 0, 0], [-s, 0, 0],
        [0, s, 0], [0, -s, 0],
        [0, 0, s], [0, 0, -s],
    ], dtype=float)
    # Each apex on one axis connects to the four vertices on the other axes.
    edges = (
        (0, 2), (0, 3), (0, 4), (0, 5),
        (1, 2), (1, 3), (1, 4), (1, 5),
        (2, 4), (2, 5), (3, 4), (3, 5),
    )
    return Shape(verts, edges, 'octahedron')


def Dodecahedron(size: float = 1.0) -> Shape:
    """12 pentagonal faces, 20 vertices, 30 edges."""
    s = float(size)
    phi = (1 + math.sqrt(5)) / 2  # golden ratio
    inv = 1 / phi
    base = [
        # 8 cube vertices
        (1, 1, 1), (1, 1, -1), (1, -1, 1), (1, -1, -1),
        (-1, 1, 1), (-1, 1, -1), (-1, -1, 1), (-1, -1, -1),
        # 4 in y-z plane
        (0, phi, inv), (0, phi, -inv), (0, -phi, inv), (0, -phi, -inv),
        # 4 in x-z plane
        (inv, 0, phi), (-inv, 0, phi), (inv, 0, -phi), (-inv, 0, -phi),
        # 4 in x-y plane
        (phi, inv, 0), (phi, -inv, 0), (-phi, inv, 0), (-phi, -inv, 0),
    ]
    verts = np.array(base, dtype=float) * s
    # Connect each vertex to its 3 nearest neighbours (regular dodecahedron
    # has every vertex equidistant from 3 others — that defines its 30 edges).
    edges = _nearest_neighbour_edges(verts, neighbours=3)
    return Shape(verts, edges, 'dodecahedron')


def _nearest_neighbour_edges(verts: np.ndarray,
                             neighbours: int) -> tuple[tuple[int, int], ...]:
    """Return unique (i, j) pairs where j is among the n closest verts to i.

    Used for shapes where edges = "join every vertex to its k nearest peers"
    (true for Platonic solids with all-equal edge lengths).
    """
    n = len(verts)
    edge_set: set[tuple[int, int]] = set()
    for i in range(n):
        diffs = verts - verts[i]
        dists = np.sqrt((diffs * diffs).sum(axis=1))
        # Sort by distance, skip self (distance 0), take next k.
        order = np.argsort(dists)
        for j in order[1:1 + neighbours]:
            a, b = (i, int(j)) if i < j else (int(j), i)
            edge_set.add((a, b))
    return tuple(sorted(edge_set))


SHAPES = {
    'cube': Cube,
    'tetrahedron': Tetrahedron,
    'octahedron': Octahedron,
    'dodecahedron': Dodecahedron,
}


def make_shape(name: str, size: float = 1.0) -> Shape:
    """Build a shape by name. Raises ValueError on unknown name."""
    key = name.lower()
    if key not in SHAPES:
        raise ValueError(
            f'Unknown shape {name!r}. Choose from {sorted(SHAPES)}.')
    return SHAPES[key](size)


# ---------------------------------------------------------------------------
# Projection
# ---------------------------------------------------------------------------


def project(shape: Shape, distance: float = 4.0,
            fov: float = 90.0) -> list[tuple[float, float, float]]:
    """Perspective-project each 3D vertex onto a 2D image plane.

    `distance` translates the camera back along +Z so the shape sits in front
    of the lens. `fov` is the horizontal field of view in degrees — larger
    values shrink the projected image (wider lens), smaller values zoom in.
    Returns (x, y, z) where z is the camera-space depth (for back-face culling
    or z-sorting).
    """
    fov_rad = math.radians(max(1.0, min(179.0, fov)))
    # Focal length in normalised image units. Keeps a unit-edge cube
    # comfortably in frame at distance ~4 with fov 90.
    f = 1.0 / math.tan(fov_rad / 2)
    out: list[tuple[float, float, float]] = []
    for x, y, z in shape.vertices:
        depth = z + distance
        if depth <= 1e-6:
            # Vertex is at or behind the lens — clamp to a tiny depth so we
            # don't divide by zero. Frame will look weird but won't crash.
            depth = 1e-6
        px = (x * f) / depth
        py = (y * f) / depth
        out.append((px, py, depth))
    return out


def edges_2d(shape: Shape, projected: list[tuple[float, float, float]]
             ) -> list[tuple[tuple[float, float],
                              tuple[float, float], float]]:
    """Look up each edge's two projected endpoints + average depth.

    Average depth lets callers z-sort edges (paint farther ones first).
    """
    out = []
    for i, j in shape.edges:
        x1, y1, z1 = projected[i]
        x2, y2, z2 = projected[j]
        out.append(((x1, y1), (x2, y2), 0.5 * (z1 + z2)))
    return out


# ---------------------------------------------------------------------------
# Rasterisation — Bresenham line on a 2D char buffer
# ---------------------------------------------------------------------------


# Character ramp from 'far' (light) to 'near' (heavy). The renderer picks a
# character per line based on its depth so closer edges look bolder.
_DEPTH_RAMP = '.:-=+*#%@'


def render(width: int, height: int,
           edges: Iterable[tuple[tuple[float, float],
                                  tuple[float, float], float]],
           *,
           depth_range: tuple[float, float] | None = None,
           fill_char: str | None = None) -> str:
    """Rasterise projected edges into a width x height ASCII frame.

    Coordinates in `edges` are in normalised image space (~[-1, 1]) — we
    map them to character cells, accounting for terminal cells being roughly
    twice as tall as wide (so we scale x by 2 to keep the cube square).

    If `fill_char` is set every drawn pixel gets that single character.
    Otherwise depth-modulates with `_DEPTH_RAMP` for a 3D feel.
    """
    width = max(8, int(width))
    height = max(4, int(height))
    buf = [[' '] * width for _ in range(height)]

    # Aspect correction: terminal cells are ~2x tall, so x gets twice the
    # screen budget to stop the cube from looking like a vertical pancake.
    cx = width / 2
    cy = height / 2
    sx = (width - 2) / 2
    sy = (height - 2) / 2 * 2  # multiplied by 2 to compensate aspect

    edges_list = list(edges)
    if not edges_list:
        return '\n'.join(''.join(row) for row in buf)

    # Sort far-to-near so near edges paint over far ones.
    edges_list.sort(key=lambda e: -e[2])

    if depth_range is None:
        depths = [e[2] for e in edges_list]
        z_near, z_far = min(depths), max(depths)
    else:
        z_near, z_far = depth_range
    z_span = max(z_far - z_near, 1e-6)

    for (x1, y1), (x2, y2), z in edges_list:
        # World y points up; screen y points down — flip it.
        sx1 = int(round(cx + x1 * sx))
        sy1 = int(round(cy - y1 * sy / 2))
        sx2 = int(round(cx + x2 * sx))
        sy2 = int(round(cy - y2 * sy / 2))
        if fill_char is not None:
            ch = fill_char
        else:
            # Depth 0 -> nearest -> brightest char.
            t = (z - z_near) / z_span  # 0 near, 1 far
            t = max(0.0, min(1.0, t))
            ramp_idx = int(round((1 - t) * (len(_DEPTH_RAMP) - 1)))
            ch = _DEPTH_RAMP[ramp_idx]
        _draw_line(buf, sx1, sy1, sx2, sy2, ch)

    return '\n'.join(''.join(row) for row in buf)


def _draw_line(buf: list[list[str]], x1: int, y1: int,
               x2: int, y2: int, ch: str) -> None:
    """Bresenham's line algorithm, clipped to the buffer bounds."""
    height = len(buf)
    width = len(buf[0]) if height else 0
    dx = abs(x2 - x1)
    dy = -abs(y2 - y1)
    sx = 1 if x1 < x2 else -1
    sy = 1 if y1 < y2 else -1
    err = dx + dy
    x, y = x1, y1
    # Cap iterations defensively in case of pathological coords.
    for _ in range((dx - dy) + 2):
        if 0 <= x < width and 0 <= y < height:
            buf[y][x] = ch
        if x == x2 and y == y2:
            return
        e2 = 2 * err
        if e2 >= dy:
            err += dy
            x += sx
        if e2 <= dx:
            err += dx
            y += sy


# ---------------------------------------------------------------------------
# CLI animation loop
# ---------------------------------------------------------------------------


def _terminal_size(default=(80, 24)) -> tuple[int, int]:
    try:
        size = os.get_terminal_size()
        return size.columns, size.lines
    except OSError:
        return default


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        description='Rotating ASCII wireframe — cube and friends.')
    parser.add_argument('--shape', default='cube',
                        choices=sorted(SHAPES.keys()),
                        help='Which polyhedron to spin (default: cube).')
    parser.add_argument('--fps', type=float, default=24.0,
                        help='Target frames per second.')
    parser.add_argument('--rx', type=float, default=30.0,
                        help='X-axis spin rate, degrees/second.')
    parser.add_argument('--ry', type=float, default=45.0,
                        help='Y-axis spin rate, degrees/second.')
    parser.add_argument('--rz', type=float, default=15.0,
                        help='Z-axis spin rate, degrees/second.')
    parser.add_argument('--fov', type=float, default=70.0,
                        help='Camera field of view in degrees.')
    parser.add_argument('--distance', type=float, default=4.0,
                        help='Camera distance from origin.')
    parser.add_argument('--size', type=float, default=1.0,
                        help='Half-edge length of the shape.')
    parser.add_argument('--width', type=int, default=0,
                        help='Frame width (0 = auto from terminal).')
    parser.add_argument('--height', type=int, default=0,
                        help='Frame height (0 = auto from terminal).')
    parser.add_argument('--frames', type=int, default=0,
                        help='Stop after N frames (0 = run forever).')
    args = parser.parse_args(argv)

    base = make_shape(args.shape, args.size)
    angle = np.array([0.0, 0.0, 0.0])
    rates = np.radians([args.rx, args.ry, args.rz])
    frame_dt = 1.0 / max(args.fps, 1.0)

    cols, rows = _terminal_size()
    width = args.width or cols
    height = args.height or max(rows - 2, 12)

    last = time.perf_counter()
    frame_no = 0
    try:
        while True:
            now = time.perf_counter()
            dt = now - last
            last = now
            angle = angle + rates * dt
            rotated = base.rotate(*angle)
            projected = project(rotated, args.distance, args.fov)
            frame = render(width, height, edges_2d(rotated, projected))
            # Move cursor home + clear from cursor-down. Cheaper than
            # clearing the whole screen each frame.
            sys.stdout.write('\x1b[H\x1b[J' + frame + '\n')
            sys.stdout.flush()
            frame_no += 1
            if args.frames and frame_no >= args.frames:
                break
            sleep_for = frame_dt - (time.perf_counter() - now)
            if sleep_for > 0:
                time.sleep(sleep_for)
    except KeyboardInterrupt:
        pass
    finally:
        sys.stdout.write('\n')
        sys.stdout.flush()


if __name__ == '__main__':
    main()
