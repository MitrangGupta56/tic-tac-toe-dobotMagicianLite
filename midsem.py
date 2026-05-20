import math
import random
import time
import threading
import os
import subprocess
import sys
from pydobot import Dobot

# -------------------- Dobot Setup --------------------
PORT = '/dev/ttyACM0'
Z_DRAW = -59
Z_SAFE = -30
R_FIXED = 13.7

# Top-left corner of the 3x3 Tic-Tac-Toe grid
TOP_LEFT = (250.1, 4.3)

# Grid parameters
GRID_SIZE = 60  # 60x60 mm
CELL_SIZE = GRID_SIZE / 3  # 20 mm per cell

# Outer square coordinates (clockwise)
GRID_OUTER = [
    (TOP_LEFT[0], TOP_LEFT[1]),                          # top-left
    (TOP_LEFT[0] + GRID_SIZE, TOP_LEFT[1]),              # top-right
    (TOP_LEFT[0] + GRID_SIZE, TOP_LEFT[1] - GRID_SIZE),  # bottom-right
    (TOP_LEFT[0], TOP_LEFT[1] - GRID_SIZE),              # bottom-left
    (TOP_LEFT[0], TOP_LEFT[1])                            # back to top-left
]

# Vertical lines (first line = leftmost from human POV)
VERTICAL_LINES_X = [TOP_LEFT[0] + CELL_SIZE, TOP_LEFT[0] + 2*CELL_SIZE]

# Horizontal lines
HORIZONTAL_LINES_Y = [TOP_LEFT[1] - CELL_SIZE, TOP_LEFT[1] - 2*CELL_SIZE]

# Cell centers for X/O drawing
CELL_CENTERS = []
for row in range(3):
    row_centers = []
    for col in range(3):
        cx = TOP_LEFT[0] + CELL_SIZE/2 + col*CELL_SIZE
        cy = TOP_LEFT[1] - CELL_SIZE/2 - row*CELL_SIZE
        row_centers.append((cx, cy))
    CELL_CENTERS.append(row_centers)

# Home position (center area)
HOME = (TOP_LEFT[0]+21, TOP_LEFT[1]-21, Z_SAFE, R_FIXED)

# -------------------- NEW: Detection Process Management --------------------
def start_detection():
    """
    Start detection.py as a separate process
    """
    try:
        # Check if detection.py exists
        if not os.path.exists('detection.py'):
            print("❌ Error: detection.py not found in current directory!")
            return None
        
        print("🚀 Starting camera detection...")
        # Start detection.py as a separate process
        process = subprocess.Popen([sys.executable, 'detection.py'])
        print("✅ Detection started successfully!")
        return process
    except Exception as e:
        print(f"❌ Failed to start detection: {e}")
        return None

def stop_detection(process):
    """
    Stop the detection process
    """
    if process:
        try:
            process.terminate()
            process.wait(timeout=5)
            print("✅ Detection stopped successfully!")
        except:
            process.kill()
            print("⚠️  Detection process killed!")

# -------------------- File Reading Functions --------------------
def read_first_detection():
    """
    Read the first detection from abc.txt to determine human symbol and first move
    Returns (symbol, row, col) or None if no detection
    """
    try:
        if not os.path.exists('abc.txt'):
            return None
            
        with open('abc.txt', 'r') as f:
            lines = f.readlines()
        
        if not lines:
            return None
            
        # Read the first line to get symbol and first move
        first_line = lines[0].strip()
        if first_line:
            parts = first_line.split(',')
            if len(parts) == 3:
                symbol, row, col = parts[0], int(parts[1]), int(parts[2])
                return (symbol, row, col)
        
        return None
        
    except (FileNotFoundError, ValueError, IndexError):
        return None

def read_latest_detection(human_symbol):
    """
    Read the latest detection from abc.txt for the human's symbol only
    Returns (row, col) if found, None if not
    """
    try:
        if not os.path.exists('abc.txt'):
            return None
            
        with open('abc.txt', 'r') as f:
            lines = f.readlines()
        
        if not lines:
            return None
            
        # Read from bottom to top to get the latest detection
        for line in reversed(lines):
            line = line.strip()
            if line:
                parts = line.split(',')
                if len(parts) == 3:
                    symbol, row, col = parts[0], int(parts[1]), int(parts[2])
                    if symbol == human_symbol:
                        return (row, col)
        
        return None
        
    except (FileNotFoundError, ValueError, IndexError):
        return None

def wait_for_human_move_from_file(board, human_symbol):
    """
    Wait for human to make a move by reading from abc.txt
    """
    print(f"Your turn! Place {human_symbol} on the board and make sure it's detected by the camera.")
    print("Waiting for your move detection...")
    
    while True:
        # Read the latest detection from file
        move = read_latest_detection(human_symbol)
        
        if move is not None:
            row, col = move
            if board[row][col] == EMPTY:
                print(f"Detected {human_symbol} at position ({row}, {col})")
                return (row, col)
            else:
                print(f"Cell ({row}, {col}) is already taken. Place your {human_symbol} in an empty cell.")
        
        time.sleep(0.5)  # Small delay to avoid excessive CPU usage

# -------------------- Basic Dobot helpers --------------------
def move_to(device, x, y, z, r=0):
    device.move_to(x, y, z, r)
    time.sleep(0.25)

def go_home(device):
    move_to(device, *HOME)

# -------------------- Dobot grid drawing --------------------
def draw_dobot_grid(device):
    # Outer Square
    for start, end in zip(GRID_OUTER[:-1], GRID_OUTER[1:]):
        move_to(device, start[0], start[1], Z_SAFE, R_FIXED)
        move_to(device, start[0], start[1], Z_DRAW, R_FIXED)
        move_to(device, end[0], end[1], Z_DRAW, R_FIXED)
        move_to(device, end[0], end[1], Z_SAFE, R_FIXED)

    # Vertical Lines
    for x in VERTICAL_LINES_X:
        move_to(device, x, TOP_LEFT[1], Z_SAFE, R_FIXED)
        move_to(device, x, TOP_LEFT[1], Z_DRAW, R_FIXED)
        move_to(device, x, TOP_LEFT[1] - GRID_SIZE, Z_DRAW, R_FIXED)
        move_to(device, x, TOP_LEFT[1] - GRID_SIZE, Z_SAFE, R_FIXED)

    # Horizontal Lines
    for y in HORIZONTAL_LINES_Y:
        move_to(device, TOP_LEFT[0], y, Z_SAFE, R_FIXED)
        move_to(device, TOP_LEFT[0], y, Z_DRAW, R_FIXED)
        move_to(device, TOP_LEFT[0] + GRID_SIZE, y, Z_DRAW, R_FIXED)
        move_to(device, TOP_LEFT[0] + GRID_SIZE, y, Z_SAFE, R_FIXED)

    # Move to center cell after grid drawn
    center_x, center_y = CELL_CENTERS[1][1]
    move_to(device, center_x, center_y, Z_SAFE, R_FIXED)

    # Shift to camera-friendly absolute position
    move_to(device, 192.8, -11.8, -30.3, 13.7)

# -------------------- Core Tic-Tac-Toe --------------------
EMPTY = ' '

def create_board():
    return [[EMPTY for _ in range(3)] for _ in range(3)]

def print_board(board):
    print("\n    0   1   2")
    print("  +---+---+---+")
    for i, row in enumerate(board):
        row_str = f"{i} | " + " | ".join(cell if cell != EMPTY else ' ' for cell in row) + " |"
        print(row_str)
        print("  +---+---+---+")
    print()

def is_board_full(board):
    return all(cell != EMPTY for row in board for cell in row)

def check_winner(board):
    for i in range(3):
        if board[i][0] != EMPTY and board[i][0] == board[i][1] == board[i][2]:
            return (board[i][0], 'row', i)
        if board[0][i] != EMPTY and board[0][i] == board[1][i] == board[2][i]:
            return (board[0][i], 'col', i)
    if board[0][0] != EMPTY and board[0][0] == board[1][1] == board[2][2]:
        return (board[0][0], 'diag', 0)
    if board[0][2] != EMPTY and board[0][2] == board[1][1] == board[2][0]:
        return (board[0][2], 'diag', 1)
    return None

def available_moves(board):
    return [(r, c) for r in range(3) for c in range(3) if board[r][c] == EMPTY]

# -------------------- Minimax AI --------------------
def minimax(board, depth, maximizing, ai_symbol, human_symbol, alpha=-math.inf, beta=math.inf):
    winner_info = check_winner(board)
    if winner_info:
        winner = winner_info[0]
        if winner == ai_symbol:
            return 10 - depth, None
        elif winner == human_symbol:
            return depth - 10, None
    elif is_board_full(board):
        return 0, None

    if maximizing:
        max_eval = -math.inf
        best_move = None
        for (r, c) in available_moves(board):
            board[r][c] = ai_symbol
            eval_score, _ = minimax(board, depth + 1, False, ai_symbol, human_symbol, alpha, beta)
            board[r][c] = EMPTY
            if eval_score > max_eval:
                max_eval = eval_score
                best_move = (r, c)
            alpha = max(alpha, eval_score)
            if beta <= alpha:
                break
        return max_eval, best_move
    else:
        min_eval = math.inf
        best_move = None
        for (r, c) in available_moves(board):
            board[r][c] = human_symbol
            eval_score, _ = minimax(board, depth + 1, True, ai_symbol, human_symbol, alpha, beta)
            board[r][c] = EMPTY
            if eval_score < min_eval:
                min_eval = eval_score
                best_move = (r, c)
            beta = min(beta, eval_score)
            if beta <= alpha:
                break
        return min_eval, best_move

def ai_move(board, ai_symbol, human_symbol, device=None):
    _, move = minimax(board, 0, True, ai_symbol, human_symbol)
    if move is None:
        moves = available_moves(board)
        move = random.choice(moves) if moves else None
    if move:
        r, c = move
        board[r][c] = ai_symbol
        if device is not None:
            draw_symbol_on_cell(device, r, c, ai_symbol)
            # Move to absolute camera coordinates
            move_to(device, 192.8, -11.8, -30.3, 13.7)
    return move

# -------------------- Modified human_move function --------------------
def human_move(board, human_symbol):
    """
    Modified to read from file instead of keyboard input
    """
    print(f"\n=== Your turn: {human_symbol} ===")
    print("Place your symbol on the board and wait for camera detection...")
    
    return wait_for_human_move_from_file(board, human_symbol)

# -------------------- Drawing primitives for Dobot --------------------
# -------------------- Rotated Coordinate Mapping --------------------
# Hard-coded logical->physical cell mapping (no math/logic)
# -------------------- HARD-CODED DOBOT COORDINATES (90° ANTICLOCKWISE) --------------------
# Each (row, col) below maps directly to a PHYSICAL (x, y) coordinate in mm
# Update values as per your grid calibration if needed.

CELL_COORDS = {
    (0, 0): (CELL_CENTERS[0][2][0], CELL_CENTERS[0][2][1]),  # top-left -> rightmost top
    (0, 1): (CELL_CENTERS[1][2][0], CELL_CENTERS[1][2][1]),  # top-middle -> right-middle
    (0, 2): (CELL_CENTERS[2][2][0], CELL_CENTERS[2][2][1]),  # top-right -> right-bottom

    (1, 0): (CELL_CENTERS[0][1][0], CELL_CENTERS[0][1][1]),  # mid-left -> top-middle
    (1, 1): (CELL_CENTERS[1][1][0], CELL_CENTERS[1][1][1]),  # center stays center
    (1, 2): (CELL_CENTERS[2][1][0], CELL_CENTERS[2][1][1]),  # mid-right -> bottom-middle

    (2, 0): (CELL_CENTERS[0][0][0], CELL_CENTERS[0][0][1]),  # bottom-left -> left-top
    (2, 1): (CELL_CENTERS[1][0][0], CELL_CENTERS[1][0][1]),  # bottom-mid -> left-middle
    (2, 2): (CELL_CENTERS[2][0][0], CELL_CENTERS[2][0][1]),  # bottom-right -> left-bottom
}

def get_rotated_coordinates(row, col):
    """Return hardcoded 90° anticlockwise (x, y) coordinates directly."""
    return CELL_COORDS[(row, col)]


# -------------------- Modified Drawing Functions --------------------
def draw_symbol_on_cell(device, row, col, symbol):
    """Draw X or O at the hardcoded 90° anticlockwise cell position."""
    cx, cy = get_rotated_coordinates(row, col)

    half = CELL_SIZE * 0.4
    if symbol == 'X':
        move_to(device, cx - half, cy + half, Z_SAFE, R_FIXED)
        move_to(device, cx - half, cy + half, Z_DRAW, R_FIXED)
        move_to(device, cx + half, cy - half, Z_DRAW, R_FIXED)
        move_to(device, cx + half, cy - half, Z_SAFE, R_FIXED)

        move_to(device, cx - half, cy - half, Z_SAFE, R_FIXED)
        move_to(device, cx - half, cy - half, Z_DRAW, R_FIXED)
        move_to(device, cx + half, cy + half, Z_DRAW, R_FIXED)
        move_to(device, cx + half, cy + half, Z_SAFE, R_FIXED)

    else:  # O
        r = half * 0.9
        n_points = 16
        move_to(device, cx + r, cy, Z_SAFE, R_FIXED)
        move_to(device, cx + r, cy, Z_DRAW, R_FIXED)
        for k in range(1, n_points + 1):
            theta = 2 * math.pi * (k / n_points)
            px = cx + r * math.cos(theta)
            py = cy + r * math.sin(theta)
            move_to(device, px, py, Z_DRAW, R_FIXED)
        move_to(device, cx + r, cy, Z_SAFE, R_FIXED)



def draw_winning_line_physical(device, winner_info):
    """Draw winning line over cells using hardcoded anticlockwise coordinates."""
    if winner_info is None:
        return
    _, line_type, idx = winner_info

    # Hardcoded logical cell endpoints
    ROWS = {0: [(0, 0), (0, 2)], 1: [(1, 0), (1, 2)], 2: [(2, 0), (2, 2)]}
    COLS = {0: [(0, 0), (2, 0)], 1: [(0, 1), (2, 1)], 2: [(0, 2), (2, 2)]}
    DIAGS = {0: [(0, 0), (2, 2)], 1: [(0, 2), (2, 0)]}

    if line_type == 'row':
        start, end = ROWS[idx]
    elif line_type == 'col':
        start, end = COLS[idx]
    elif line_type == 'diag':
        start, end = DIAGS[idx]
    else:
        return

    sx, sy = get_rotated_coordinates(*start)
    ex, ey = get_rotated_coordinates(*end)

    move_to(device, sx, sy, Z_SAFE, R_FIXED)
    move_to(device, sx, sy, Z_DRAW, R_FIXED)
    move_to(device, ex, ey, Z_DRAW, R_FIXED)
    move_to(device, ex, ey, Z_SAFE, R_FIXED)


def draw_result_letter(device, letter):
    """Draw H, R, or T to the right of the grid."""
    # starting anchor (right side of grid)
    anchor_x = TOP_LEFT[0] + GRID_SIZE + 20
    anchor_y = TOP_LEFT[1] - GRID_SIZE / 2  # middle height
    s = 8  # stroke length in mm (tweak as necessary)

    if letter == 'H':
        # left vertical
        move_to(device, anchor_x - 6, anchor_y + s, Z_SAFE, R_FIXED)
        move_to(device, anchor_x - 6, anchor_y + s, Z_DRAW, R_FIXED)
        move_to(device, anchor_x - 6, anchor_y - s, Z_DRAW, R_FIXED)
        move_to(device, anchor_x - 6, anchor_y - s, Z_SAFE, R_FIXED)
        # right vertical
        move_to(device, anchor_x + 6, anchor_y + s, Z_SAFE, R_FIXED)
        move_to(device, anchor_x + 6, anchor_y + s, Z_DRAW, R_FIXED)
        move_to(device, anchor_x + 6, anchor_y - s, Z_DRAW, R_FIXED)
        move_to(device, anchor_x + 6, anchor_y - s, Z_SAFE, R_FIXED)
        # middle horizontal
        move_to(device, anchor_x - 6, anchor_y, Z_SAFE, R_FIXED)
        move_to(device, anchor_x - 6, anchor_y, Z_DRAW, R_FIXED)
        move_to(device, anchor_x + 6, anchor_y, Z_DRAW, R_FIXED)
        move_to(device, anchor_x + 6, anchor_y, Z_SAFE, R_FIXED)

    elif letter == 'R':
        # vertical
        move_to(device, anchor_x - 8, anchor_y + s, Z_SAFE, R_FIXED)
        move_to(device, anchor_x - 8, anchor_y + s, Z_DRAW, R_FIXED)
        move_to(device, anchor_x - 8, anchor_y - s, Z_DRAW, R_FIXED)
        move_to(device, anchor_x - 8, anchor_y - s, Z_SAFE, R_FIXED)
        # top curve (rectangle-like)
        move_to(device, anchor_x - 8, anchor_y + s, Z_SAFE, R_FIXED)
        move_to(device, anchor_x - 8, anchor_y + s, Z_DRAW, R_FIXED)
        move_to(device, anchor_x + 2, anchor_y + s, Z_DRAW, R_FIXED)
        move_to(device, anchor_x + 2, anchor_y, Z_DRAW, R_FIXED)
        move_to(device, anchor_x - 8, anchor_y, Z_DRAW, R_FIXED)
        move_to(device, anchor_x - 8, anchor_y, Z_SAFE, R_FIXED)
        # diagonal leg
        move_to(device, anchor_x - 2, anchor_y, Z_SAFE, R_FIXED)
        move_to(device, anchor_x - 2, anchor_y, Z_DRAW, R_FIXED)
        move_to(device, anchor_x + 6, anchor_y - s, Z_DRAW, R_FIXED)
        move_to(device, anchor_x + 6, anchor_y - s, Z_SAFE, R_FIXED)

    elif letter == 'T':
        # top horizontal
        move_to(device, anchor_x - 10, anchor_y + s, Z_SAFE, R_FIXED)
        move_to(device, anchor_x - 10, anchor_y + s, Z_DRAW, R_FIXED)
        move_to(device, anchor_x + 10, anchor_y + s, Z_DRAW, R_FIXED)
        move_to(device, anchor_x + 10, anchor_y + s, Z_SAFE, R_FIXED)
        # middle vertical
        move_to(device, anchor_x, anchor_y + s, Z_SAFE, R_FIXED)
        move_to(device, anchor_x, anchor_y + s, Z_DRAW, R_FIXED)
        move_to(device, anchor_x, anchor_y - s, Z_DRAW, R_FIXED)
        move_to(device, anchor_x, anchor_y - s, Z_SAFE, R_FIXED)

def play_tic_tac_toe_B1(device):
    print("\n--- Tic-Tac-Toe B1 (Robot asks who goes first) ---")

    # Start detection process once
    detection_process = start_detection()
    if not detection_process:
        print("❌ Cannot start game without detection!")
        return

    try:
        board = create_board()

        # Ask who goes first
        print("Robot asks: Who goes first?")
        turn = ''
        while turn not in ('H', 'A'):
            turn = input("Enter H for Human or A for AI: ").upper().strip()

        # Decide symbols
        if turn == 'H':
            # Human first: detect human symbol from the very first camera detection, as you already do
            print("\n🔍 Analyzing camera detection to determine your symbol...")
            print("Please place your first symbol on the board...")
            first_detection = None
            while first_detection is None:
                first_detection = read_first_detection()
                if first_detection is None:
                    print("Waiting for first detection...")
                    time.sleep(2)

            human_symbol, first_row, first_col = first_detection
            ai_symbol = 'O' if human_symbol == 'X' else 'X'
            print(f"✅ Detected: You are playing {human_symbol} (first move at {first_row},{first_col})")
            print(f"🤖 AI will play {ai_symbol}")

            # Apply first human move
            board[first_row][first_col] = human_symbol
            print_board(board)
            # Next turn is AI
            turn = 'A'
        else:
            # AI first: pick symbol randomly and start
            ai_symbol = random.choice(['X', 'O'])
            human_symbol = 'O' if ai_symbol == 'X' else 'X'
            print(f"🤖 Robot goes first and randomly chooses: {ai_symbol}")
            print(f"🙋 Human will be: {human_symbol}")

        # Main game loop
        while True:
            if check_winner(board) or is_board_full(board):
                break

            if turn == 'A':
                print("AI thinking...")
                move = ai_move(board, ai_symbol, human_symbol, device=device)
                print(f"AI played: {move}")
                print_board(board)
                if check_winner(board) or is_board_full(board):
                    break
                turn = 'H'
            else:
                mv = human_move(board, human_symbol)
                if mv is None:
                    print("Game cancelled.")
                    return
                r, c = mv
                board[r][c] = human_symbol
                print_board(board)
                if check_winner(board) or is_board_full(board):
                    break
                turn = 'A'

        # Endgame: draw line/letter
        winner_info = check_winner(board)
        if winner_info:
            print("Drawing winning line physically...")
            draw_winning_line_physical(device, winner_info)
            winner_symbol = winner_info[0]
            letter = 'H' if winner_symbol == human_symbol else 'R'
            draw_result_letter(device, letter)
            print(f"Result: {letter}")
        else:
            print("It's a tie. Drawing T physically...")
            draw_result_letter(device, 'T')

    finally:
        go_home(device)
        stop_detection(detection_process)

# -------------------- Game Loop with Dobot drawing for AI --------------------
def play_game_mode(device, force_human_first=False, ask_who_first=False):
    """
    Runs the game. Camera detection is handled by detection.py process.
    AI moves are physically drawn by the Dobot and robot returns to camera view after each draw.
    """
    # Start detection process
    detection_process = start_detection()
    if not detection_process:
        print("❌ Cannot start game without detection!")
        return
    
    try:
        board = create_board()
        
        # Auto-detect human symbol from first detection in file
        print("\n🔍 Analyzing camera detection to determine your symbol...")
        print("Please place your first symbol on the board...")
        first_detection = None
        while first_detection is None:
            first_detection = read_first_detection()
            if first_detection is None:
                print("Waiting for first detection...")
                time.sleep(2)
        
        human_symbol, first_row, first_col = first_detection
        ai_symbol = 'O' if human_symbol == 'X' else 'X'
        
        print(f"✅ Detected: You are playing {human_symbol} (first move at {first_row},{first_col})")
        print(f"🤖 AI will play {ai_symbol}")
        
        # Auto-place first human move
        if force_human_first:
            board[first_row][first_col] = human_symbol
            print(f"📍 Auto-placed your first {human_symbol} at ({first_row}, {first_col})")
            turn = 'A'  # AI goes next since human first move is already placed
        elif ask_who_first:
            print("Robot asks: Who goes first?")
            turn = ''
            while turn not in ('H', 'A'):
                turn = input("Enter H for Human or A for AI: ").upper().strip()
        else:
            turn = 'H'

        print_board(board)

        while True:
            if check_winner(board) or is_board_full(board):
                break
            if turn == 'H':
                mv = human_move(board, human_symbol)
                if mv is None: 
                    print("Game cancelled.")
                    return
                r, c = mv
                board[r][c] = human_symbol
                print_board(board)
                if check_winner(board) or is_board_full(board): break
                turn = 'A'
            else:
                print("AI thinking...")
                move = ai_move(board, ai_symbol, human_symbol, device=device)
                print(f"AI played: {move}")
                print_board(board)
                if check_winner(board) or is_board_full(board): break
                turn = 'H'

        # Game finished: physical draw of winning line and letter
        winner_info = check_winner(board)
        if winner_info:
            # draw physical winning line
            print("Drawing winning line physically...")
            draw_winning_line_physical(device, winner_info)
            # decide letter: 'H' if human won, 'R' if robot won
            winner_symbol = winner_info[0]
            if winner_symbol == human_symbol:
                letter = 'H'
            else:
                letter = 'R'
            # draw the result letter
            draw_result_letter(device, letter)
            print(f"Result: {letter}")
        else:
            # tie
            print("It's a tie. Drawing T physically...")
            draw_result_letter(device, 'T')

    finally:
        # always return to home
        go_home(device)
        # stop detection process
        stop_detection(detection_process)

# -------------------- Menu --------------------
def play_basic_tic_tac_toe(device):
    print("\n--- Basic Tic-Tac-Toe (Human first) ---")
    play_game_mode(device, force_human_first=True)


def play_tic_tac_toe_B2(device):
    print("\n--- Tic-Tac-Toe B2 (Error detection: double-move & symbol switch) ---")

    # Start detection process once
    detection_process = start_detection()
    if not detection_process:
        print("❌ Cannot start game without detection!")
        return

    try:
        board = create_board()

        # Determine human symbol from first detection (same as your normal flow)
        print("\n🔍 Analyzing camera detection to determine your symbol...")
        print("Please place your first symbol on the board...")
        first_detection = None
        while first_detection is None:
            first_detection = read_first_detection()
            if first_detection is None:
                print("Waiting for first detection...")
                time.sleep(2)

        human_symbol, first_row, first_col = first_detection
        ai_symbol = 'O' if human_symbol == 'X' else 'X'
        print(f"✅ Detected: You are playing {human_symbol} (first move at {first_row},{first_col})")
        print(f"🤖 AI will play {ai_symbol}")

        # Apply first human move
        board[first_row][first_col] = human_symbol
        print_board(board)

        turn = 'A'  # AI next

        # Game loop with error checks on human turns
        while True:
            if check_winner(board) or is_board_full(board):
                break

            if turn == 'A':
                print("AI thinking...")
                move = ai_move(board, ai_symbol, human_symbol, device=device)
                print(f"AI played: {move}")
                print_board(board)
                if check_winner(board) or is_board_full(board):
                    break
                turn = 'H'
            else:
                # Human turn with extra validations
                mv = human_move_with_error_checks(board, human_symbol, ai_symbol)
                if mv is None:
                    print("Game cancelled.")
                    return
                r, c = mv
                board[r][c] = human_symbol
                print_board(board)
                if check_winner(board) or is_board_full(board):
                    break
                turn = 'A'

        # Endgame: draw line/letter
        winner_info = check_winner(board)
        if winner_info:
            print("Drawing winning line physically...")
            draw_winning_line_physical(device, winner_info)
            winner_symbol = winner_info[0]
            letter = 'H' if winner_symbol == human_symbol else 'R'
            draw_result_letter(device, letter)
            print(f"Result: {letter}")
        else:
            print("It's a tie. Drawing T physically...")
            draw_result_letter(device, 'T')

    finally:
        go_home(device)
        stop_detection(detection_process)


def show_menu(device):
    # draw the grid first
    draw_dobot_grid(device)
    time.sleep(10)

    while True:
        print("\n=== Tic-Tac-Toe Robot Menu ===")
        print("1. Basic Tic-Tac-Toe (Human first)")
        print("2. Tic-Tac-Toe B1 (Robot asks who goes first)")
        print("3. Tic-Tac-Toe B2 (reserved for extra credit)")
        print("4. Quit")

        choice = input("Enter choice (1/2/3/4): ")
        if choice == '1':
            play_basic_tic_tac_toe(device)
        elif choice == '2':
            play_tic_tac_toe_B1(device)
        elif choice == '3':
            play_tic_tac_toe_B2(device)
        elif choice == '4':
            print("Exiting program...")
            break
        else:
            print("Invalid choice!")
# ---------- Detection parsing helpers ----------
def parse_detections_file():
    """
    Read all unique detections from abc.txt as a list of (symbol, row, col)
    Returns [] if file doesn't exist or empty.
    """
    entries = []
    try:
        if not os.path.exists('abc.txt'):
            return entries
        with open('abc.txt', 'r') as f:
            for line in f:
                s = line.strip()
                if not s:
                    continue
                parts = s.split(',')
                if len(parts) != 3:
                    continue
                sym, r, c = parts[0].upper(), int(parts[1]), int(parts[2])
                if sym in ('X', 'O') and 0 <= r <= 2 and 0 <= c <= 2:
                    entries.append((sym, r, c))
    except Exception:
        pass
    return entries

def pending_new_moves_from_camera(board, symbol):
    """
    Returns list of (r,c) that the camera has detected for 'symbol' which are not yet on 'board'.
    """
    entries = parse_detections_file()
    pending = []
    for sym, r, c in entries:
        if sym == symbol and board[r][c] == EMPTY:
            pending.append((r, c))
    return pending

def human_move_with_error_checks(board, human_symbol, ai_symbol):
    """
    Waits for a valid single human move, with error detection:
      - If two or more new human cells are detected -> error
      - If any new AI-symbol cell appears during human turn -> error (human switched symbol)
    Returns (r,c) when exactly one valid human move is detected.
    """
    print(f"\n=== Your turn: {human_symbol} ===")
    print("Place your symbol on the board. Waiting for camera detection with error checks...")

    while True:
        # New moves since current board state
        human_new = pending_new_moves_from_camera(board, human_symbol)
        ai_new = pending_new_moves_from_camera(board, ai_symbol)

        # Error: human placed robot's symbol (switched symbol)
        if len(ai_new) >= 1:
            print("❌ Error detected: A move with the robot's symbol appeared during your turn.")
            print(f"   Offending cell(s): {ai_new}. Please remove/fix, then try again.")
            time.sleep(1.0)
            continue

        # Error: multiple human moves before robot
        if len(human_new) > 1:
            print("❌ Error detected: Multiple human moves before the robot's turn.")
            print(f"   Offending cells: {human_new}. Please remove extras, leaving only one.")
            time.sleep(1.0)
            continue

        # Valid: exactly one new move
        if len(human_new) == 1:
            r, c = human_new[0]
            print(f"✅ Detected your move at ({r}, {c})")
            return (r, c)

        # Otherwise, keep waiting
        time.sleep(0.4)

# -------------------- Main --------------------
if __name__ == "__main__":
    print("🎮 Welcome to Tic-Tac-Toe with Camera Detection and Dobot!")
    print("Note: This program will automatically start the camera detection when you select a game mode.")
    
    try:
        device = Dobot(PORT)
        time.sleep(1)
        print("Moving to home...")
        go_home(device)
        show_menu(device)
    except Exception as e:
        print("Error:", e)
    finally:
        if 'device' in locals() and device is not None:
            device.close()
            print("Connection closed.")
