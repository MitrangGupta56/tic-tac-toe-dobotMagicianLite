# tic-tac-toe-dobotMagicianLite
Perception-Driven Robotic Tic-Tac-Toe
Python
YOLOv8
Dobot Magician Lite
OpenCV
A closed-loop human-robot Tic-Tac-Toe system combining real-time YOLO-based symbol detection, Minimax AI decision-making, and physical gameplay execution on a Dobot Magician Lite robotic arm. The robot draws the grid, detects the human player's moves via webcam, computes optimal responses, and physically draws its own symbols — including win/tie result indicators.
Detection accuracy: ~93%  ·  Avg cycle time: 10s/move  ·  Total game time: ~2.5 min

Architecture
Webcam → detection.py (YOLOv8 / Roboflow)
           │  writes symbol, row, col
           ▼
        abc.txt
           │  read by
           ▼
        midsem.py ── Minimax AI ── Dobot Magician Lite
Repository structure
.
├── detection.py      # YOLO inference, grid mapping, abc.txt writer
├── midsem.py         # Dobot control, Minimax AI, game orchestration
├── abc.txt           # IPC file (auto-generated at runtime)
└── README.md
Requirements
pip install opencv-python supervision inference pydobot
Requires a Roboflow API key and a trained YOLOv8 model for X/O detection. Update API_KEY and MODEL_ID in detection.py before running.
Quick start
# 1. Connect Dobot to /dev/ttyACM0
# 2. Point webcam at the physical board (index 2 by default)
# 3. Run the main controller — detection.py launches automatically
python midsem.py
Configuration
Key constants to calibrate for your physical setup:
detection.py
GRID_TOP_LEFT
GRID_BOTTOM_RIGHT
DETECTION_INTERVAL
MODEL_ID / API_KEY
midsem.py
PORT
TOP_LEFT
Z_DRAW / Z_SAFE
GRID_SIZE / CELL_SIZE
Game modes
1 — Basic: Human always goes first as X.
2 — B1: Robot asks who goes first; symbol assigned from first camera detection.
3 — B2: Error detection mode — flags double moves and symbol switches mid-game.
Notes
The Roboflow API key in detection.py should be moved to an environment variable before committing. Camera index defaults to 2 — adjust cv2.VideoCapture(2) to match your setup. All Dobot coordinates are in mm (Cartesian); recalibrate TOP_LEFT and Z_DRAW for your physical grid placement.
