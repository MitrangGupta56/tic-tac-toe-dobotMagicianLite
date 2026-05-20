# Perception-Driven Robotic Tic-Tac-Toe

A closed-loop human-robot Tic-Tac-Toe system combining real-time YOLO-based symbol detection, Minimax AI decision-making, and physical gameplay execution on a Dobot Magician Lite robotic arm. The robot draws the grid, detects the human player's moves via webcam, computes optimal responses, and physically draws its own symbols — including win/tie result indicators.

**Detection accuracy:** ~93% · **Avg cycle time:** 10s/move · **Total game time:** ~2.5 min

---

## Architecture

```
Webcam → detection.py (YOLOv8 / Roboflow)
           │  writes symbol, row, col
           ▼
        abc.txt
           │  read by
           ▼
        midsem.py ── Minimax AI ── Dobot Magician Lite
```

`detection.py` and `midsem.py` run concurrently. `midsem.py` spawns `detection.py` as a subprocess automatically when a game mode is selected. State is exchanged through `abc.txt`.

---

## Repository structure

```
.
├── detection.py      # YOLO inference, grid mapping, abc.txt writer
├── midsem.py         # Dobot control, Minimax AI, game orchestration
├── abc.txt           # IPC file (auto-generated at runtime)
└── README.md
```

---

## Requirements

```bash
pip install opencv-python supervision inference pydobot
```

Requires a [Roboflow](https://roboflow.com) API key and a trained YOLOv8 model for X/O detection. Update `API_KEY` and `MODEL_ID` in `detection.py` before running.

Hardware:
- Dobot Magician Lite with pen attachment
- Webcam (USB, index 2 by default)
- Serial connection on `/dev/ttyACM0` (Linux) or `COMx` (Windows)

---

## Quick start

```bash
# 1. Connect Dobot to /dev/ttyACM0
# 2. Point webcam at the physical board
# 3. Run the main controller — detection.py launches automatically
python midsem.py
```

The robot will draw the physical grid first, then the game menu appears in the terminal.

---

## Configuration

Calibrate these constants to your physical setup before running:

**`detection.py`**

| Constant | Description |
|---|---|
| `API_KEY` | Roboflow API key |
| `MODEL_ID` | Roboflow model string |
| `GRID_TOP_LEFT` | Top-left pixel coordinate of the grid in the camera frame |
| `GRID_BOTTOM_RIGHT` | Bottom-right pixel coordinate of the grid |
| `DETECTION_INTERVAL` | Seconds between inference runs (default 15) |

**`midsem.py`**

| Constant | Description |
|---|---|
| `PORT` | Serial port for Dobot connection |
| `TOP_LEFT` | Grid origin in Dobot Cartesian coordinates (mm) |
| `Z_DRAW` | Z height for pen-down drawing (-59 mm default) |
| `Z_SAFE` | Z height for safe travel (-30 mm default) |
| `GRID_SIZE` | Total grid side length (60 mm default) |

---

## Game modes

| Mode | Description |
|---|---|
| **1 — Basic** | Human always goes first as X |
| **2 — B1** | Robot asks who goes first; symbol assigned from first camera detection |
| **3 — B2** | Error detection mode — flags double moves and symbol switches mid-game |

---

## How it works

1. Robot draws a 3x3 grid on paper using cartesian waypoints.
2. Human places their symbol (X or O) in a cell.
3. `detection.py` runs YOLOv8 inference every N seconds, maps bounding box centers to grid cells, and appends `SYMBOL,row,col` entries to `abc.txt`.
4. `midsem.py` reads the latest valid detection, updates the board state, and runs Minimax to select the robot's optimal move.
5. Robot physically draws its symbol (X via diagonal strokes, O via circular interpolation).
6. On game end, the robot draws the winning line and a result letter (H = human wins, R = robot wins, T = tie).

---

## Notes

- Move the Roboflow API key to an environment variable before committing to a public repo.
- Camera index defaults to `2` in `cv2.VideoCapture(2)` — adjust to match your system.
- All Dobot coordinates are in mm (Cartesian). Recalibrate `TOP_LEFT` and `Z_DRAW` for your physical grid placement.
- The `map_grid_position()` function in `detection.py` lets you remap camera cell indices to match your physical orientation if the camera is angled.

---

## References

- [YOLOv8 via Roboflow](https://roboflow.com)
- [Dobot Documentation](https://www.dobot.cc)
- [Minimax Algorithm](https://en.wikipedia.org/wiki/Minimax)
- [Training dataset](https://universe.roboflow.com/sding32/tic-tac-toe-fctyp-0e0ri/dataset/1)

---
