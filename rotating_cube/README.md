# Rotating Cube

A 3D wireframe cube spun by rotation matrices, perspective-projected, then rasterised into ASCII art. Three flavours:

| Version | File | Stack |
|---------|------|-------|
| CLI animation | `rotating_cube.py` | numpy + stdlib |
| Modern desktop GUI | `rotating_cube_gui.py` | CustomTkinter |
| Modern terminal UI | `rotating_cube_tui.py` | Textual |

## Run

```bash
# CLI (animates forever — Ctrl+C to stop)
uv run python rotating_cube/rotating_cube.py

# Desktop GUI (CustomTkinter)
uv run python rotating_cube/rotating_cube_gui.py

# Terminal UI (Textual)
uv run python rotating_cube/rotating_cube_tui.py
```

The CLI accepts flags: `--shape {cube,tetrahedron,octahedron,dodecahedron}`, `--fps`, `--rx --ry --rz` (degrees/sec), `--fov`, `--distance`, `--size`, `--width --height`.

## Pipeline

```
3D vertices  ──rotate──>  rotated vertices  ──project──>  2D points
                                                              │
                                                              ▼
                                            Bresenham line on char buffer
```

1. **Build** — `Cube(size)` produces 8 vertices and 12 edges (other shapes available: tetrahedron/octahedron/dodecahedron).
2. **Rotate** — `cube.rotate(rx, ry, rz)` composes three axis rotation matrices `Rz @ Ry @ Rx` and returns a new shape with `vertices @ R.T`.
3. **Project** — `project(shape, distance, fov)` translates the camera back, then divides by depth: `px = x*f/depth`, `py = y*f/depth` where `f = 1 / tan(fov/2)`.
4. **Rasterise** — `render(width, height, edges_2d)` z-sorts edges far-to-near and walks each one with Bresenham's algorithm into a 2D char grid. The character itself is depth-modulated (`. : - = + * # % @`) for a 3D feel.

## Shapes (the twist)

Press `s` in the TUI or use the dropdown in the GUI to cycle Platonic solids:

| Shape | Verts | Edges |
|---|---|---|
| Cube | 8 | 12 |
| Tetrahedron | 4 | 6 |
| Octahedron | 6 | 12 |
| Dodecahedron | 20 | 30 |

The dodecahedron's edges are computed from the regular construction (cube + 3 rectangles in the coordinate planes) by joining each vertex to its three nearest peers — equivalent to the standard graph but generic enough to work for any shape with all-equal edge lengths.

## Bindings (TUI)

| Key | Action |
|---|---|
| `space` | Pause / resume |
| `x` / `y` / `z` | Toggle rotation around that axis |
| `s` | Cycle shape |
| `r` | Reset angles + state |
| `f` / `g` | Narrower / wider FOV |
| `a` / `d` | Smaller / bigger |
| `Ctrl+Q` | Quit |

## Notes

- Aspect correction: terminal cells are roughly 2:1 tall, so the renderer halves vertical scaling, which keeps a "square" object actually square.
- The depth ramp picks one character per edge (avg edge depth) rather than per pixel, so close edges look bolder without the rasteriser doing per-pixel z-buffering.
- Field of view inversion: smaller FOV = telephoto = bigger projected image, larger FOV = fisheye = smaller. Confusing at first, intuitive once you see it move.
