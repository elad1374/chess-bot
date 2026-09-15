import chess
from .enums_and_dicts import *
from collections.abc import Sequence
from math import hypot
import os
import subprocess
from common.typing import Vector


X, Y, Z, RX, RY, RZ = 0, 1, 2, 3, 4, 5
CLOSED = 255
HALF_OPENED = 140
OPENED = 0


def convert_square_to_coordinates(square: str):
    """
    Takes a string of chessboard square and converts to matrix coordinate (row, col)
    For example: e4 -> (4,4), a1 -> (7,0)
    """
    if len(square) != 2:
        raise ValueError(f"Invalid square: {square}")

    file, rank = square[0].lower(), square[1]

    if file not in "abcdefgh" or rank not in "12345678":
        raise ValueError(f"Invalid square: {square}")

    col = ord(file) - ord('a')
    row = 8 - int(rank)
    return row, col


def convert_coordinates_to_square(row: int, col: int) -> str:
    """
    Converts 0-indexed matrix coordinates (row, col) to algebraic chess square notation.
    Assumes standard FEN layout where row 0 = Rank 8 and col 0 = File 'a'.
    
    Examples:
        (0, 0) -> 'a8'
        (7, 4) -> 'e1'
        (6, 4) -> 'e2'
    """
    if not (0 <= row <= 7 and 0 <= col <= 7):
        raise ValueError(f"Coordinates ({row}, {col}) are out of bounds. Must be 0-7.")

    file_char = chr(ord('a') + col)
    rank_char = str(8 - row)

    return f"{file_char}{rank_char}"


def convert_string_to_chessType(letter: str) -> PieceType:
    """
    Converts a UCI promotion character ('q', 'r', 'b', 'n') to a PieceType.
    Raises ValueError if letter is None, empty, or an invalid piece character.
    """
    if letter.lower() not in PROMOTED_PIECES:
        raise ValueError(
            f"Invalid promotion piece: {letter}. "
            f"Expected one of: {list(PROMOTED_PIECES.keys())}"
        )

    return PROMOTED_PIECES[letter.lower()]


def parse_fen_to_int_grid(fen_string: str):
    """
    Converts FEN string into an 8x8 grid of integers (0-11, empty=-1)
    and extracts active turn (1 for white, 0 for black).
        
    Returns:
        tuple: (int_grid, active_turn)
    """
    parts = fen_string.split()
    board_part = parts[0]
        
    # 1 for white ('w'), 0 for black ('b')
    active_turn = 1 if (len(parts) > 1 and parts[1].lower() == 'w') else 0

    rows = board_part.split('/')
    int_grid = []

    for row_str in rows:
        grid_row = []
        for char in row_str:
            if char.isdigit():
                grid_row.extend([-1] * int(char))
            else:
                grid_row.append(FEN_TO_INT[char])
        int_grid.append(grid_row)

    return int_grid, active_turn    


def grid_to_fen(board_grid, active_turn=1):
    """
    Converts an 8x8 integer grid (0-11, -1) into a FEN string.
    """
    fen_rows = []
    for row in range(8):
        empty_count = 0
        row_str = ""
        for col in range(8):
            val = board_grid[row][col]
            if val == -1 or val is None:
                empty_count += 1
            else:
                if empty_count > 0:
                    row_str += str(empty_count)
                    empty_count = 0
                row_str += INT_TO_FEN[val]
        if empty_count > 0:
            row_str += str(empty_count)
        fen_rows.append(row_str)
    char_active_turn = "b" if active_turn == 0 else "w"
    board_fen = "/".join(fen_rows)
    return f"{board_fen} {char_active_turn} - - 0 1"


def get_color(label):
    if label<0:
        return -1
    elif label <= 5:
        return 0  # black
    else:
        return 1  # white


def weighted_avg(x: float | Vector, y: float | Vector, x_bias: float) -> float | Vector:
    if isinstance(x, Sequence):
        return [weighted_avg(a, b, x_bias) for a, b in zip(x, y)]
    return x*x_bias + y*(1-x_bias)


def distance(v: Vector, u: Vector) -> float:
    assert len(v) == len(u)
    return hypot(*(a - b for a, b in zip(v, u)))

def is_close(a: float | Vector, b: float | Vector, epsilon: float = 0.001) -> float:
    if isinstance(a, float) and isinstance(b, float):
        return (abs(a - b) < epsilon)
    if isinstance(a, Sequence) and isinstance(b, Sequence):
        return (distance(a, b) < epsilon)
    raise TypeError("bad type for a and b")

def convert_type_and_color_to_fen_char(type: PieceType, color: str):
    char_map = {
        PieceType.BISHOP: 'b',
        PieceType.KING: 'k',
        PieceType.KNIGHT: 'n',
        PieceType.PAWN: 'p',
        PieceType.QUEEN: 'q',
        PieceType.ROOK: 'r'
    }
    
    char = char_map.get(type)
    
    if not char:
        raise ValueError(f"Unknown piece type: {type}")
        
    return char.upper() if color.lower() == 'white' else char

def convert_fen_char_to_type_and_color(c: str):
    color = 'white' if c.isupper() else 'black'
    if c.lower() == 'b':
        return PieceType.BISHOP, color
    if c.lower() == 'k':
        return PieceType.KING, color
    if c.lower() == 'n':
        return PieceType.KNIGHT, color
    if c.lower() == 'p':
        return PieceType.PAWN, color
    if c.lower() == 'q':
        return PieceType.QUEEN, color
    if c.lower() == 'r':
        return PieceType.ROOK, color

def parse_board_to_int_grid(board: chess.Board):
    """
    Converts chess.Board into an 8x8 grid of integers (0-11, empty=-1)
    and extracts active turn (1 for white, 0 for black).
        
    Returns:
        tuple: (grid, turn)
    """    
    grid = [[-1 for _ in range(8)] for _ in range(8)]

    for square, piece in board.piece_map().items():
        row = 7 - chess.square_rank(square)
        col = chess.square_file(square)

        grid[row][col] = FEN_TO_INT[piece.symbol()]
    turn = 1 if (board.turn == chess.WHITE) else 0
    return grid, turn


_REPO_ROOT = None

def repo_path(path=""):
    """
    Gets a file path relative to the chess-bot repo root.
    Returns the absolute path.
    """
    global _REPO_ROOT
    if _REPO_ROOT is None:
        _REPO_ROOT = subprocess.check_output(["git", "rev-parse", "--show-toplevel"]).decode("utf-8").strip()
    return os.path.join(_REPO_ROOT, path)
