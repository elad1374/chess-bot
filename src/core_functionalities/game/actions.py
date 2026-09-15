from abc import ABC, abstractmethod
from typing import Optional
from src.arm.behaviors.playing_robot import PlayingRobot
from common.utils import *
from common.enums_and_dicts import *




class ChessAction(ABC):
    """Abstract base interface for all executable chess actions."""

    @abstractmethod
    def execute_on_robot(self, robot: PlayingRobot) -> bool:
        """
        Executes the physical sequence required for this action using the robot arm.
        Returns True if successful, False otherwise.
        """
        pass

    @abstractmethod
    def update_fen(self, old_fen: str) -> str:
        """
        Calculates and returns the updated FEN string after this action is applied.
        """
        pass


class Move(ChessAction):
    """Represents a standard piece move (non-capturing, non-special)."""

    def __init__(self, from_square: str, to_square: str, piece: PieceType):
        self.from_square = from_square
        self.to_square = to_square
        self.piece = piece

    def execute_on_robot(self, robot: PlayingRobot) -> bool:
        return robot.move(self.from_square, self.to_square, self.piece)

    def update_fen(self, old_fen: str) -> str:
        from_cell = convert_square_to_coordinates(self.from_square)
        to_cell = convert_square_to_coordinates(self.to_square)

        grid, turn = parse_fen_to_int_grid(old_fen)
        grid[from_cell[0]][from_cell[1]] = -1
        grid[to_cell[0]][to_cell[1]] = 6*turn+self.piece

        return grid_to_fen(grid, 1-turn)


class Capture(ChessAction):
    """Represents a standard piece capture."""

    def __init__(self, from_square: str, to_square: str, remove_square: str, moving_piece: PieceType, captured_piece: PieceType):
        self.from_square = from_square
        self.to_square = to_square
        self.remove_square = remove_square
        self.moving_piece = moving_piece
        self.captured_piece = captured_piece

    def execute_on_robot(self, robot: PlayingRobot) -> bool:
        return robot.capture(self.from_square, self.to_square, self.remove_square, self.moving_piece, self.captured_piece)

    def update_fen(self, old_fen: str) -> str:
        from_cell = convert_square_to_coordinates(self.from_square)
        to_cell = convert_square_to_coordinates(self.to_square)
        remove_cell = convert_square_to_coordinates(self.remove_square)

        grid, turn = parse_fen_to_int_grid(old_fen)
        grid[from_cell[0]][from_cell[1]] = -1
        grid[remove_cell[0]][remove_cell[1]] = -1 # if regular capture will be overwritten, if en passant stays empty
        grid[to_cell[0]][to_cell[1]] = 6*turn+self.moving_piece
        
        return grid_to_fen(grid, 1-turn)


class Upgrade(ChessAction):
    """Represents a pawn promotion move (with or without capture)."""

    def __init__(self, from_square: str, to_square: str, promoted_piece: PieceType = PieceType.QUEEN, captured_piece: Optional[PieceType] = None):
        self.from_square = from_square
        self.to_square = to_square
        self.promoted_piece = promoted_piece
        self.captured_piece = captured_piece

    def execute_on_robot(self, robot: PlayingRobot) -> bool:
        return robot.upgrade(self.from_square, self.to_square, self.promoted_piece, self.captured_piece)

    def update_fen(self, old_fen: str) -> str:
        from_cell = convert_square_to_coordinates(self.from_square)
        to_cell = convert_square_to_coordinates(self.to_square)

        grid, turn = parse_fen_to_int_grid(old_fen)
        grid[from_cell[0]][from_cell[1]] = -1
        grid[to_cell[0]][to_cell[1]] = 6*turn+self.promoted_piece

        return grid_to_fen(grid, 1-turn)


class Castle(ChessAction):
    """Represents a castling move (kingside or queenside)."""

    def __init__(self, king_from: str, king_to: str, rook_from: str, rook_to: str):
        self.king_from = king_from
        self.king_to = king_to
        self.rook_from = rook_from
        self.rook_to = rook_to

    def execute_on_robot(self, robot: PlayingRobot) -> bool:
        return robot.castle(self.king_from, self.king_to, self.rook_from, self.rook_to)

    def update_fen(self, old_fen: str) -> str:
        king_from_cell = convert_square_to_coordinates(self.king_from)
        king_to_cell = convert_square_to_coordinates(self.king_to)
        rook_from_cell = convert_square_to_coordinates(self.rook_from)
        rook_to_cell = convert_square_to_coordinates(self.rook_to)

        grid, turn = parse_fen_to_int_grid(old_fen)
        grid[king_from_cell[0]][king_from_cell[1]] = -1
        grid[king_to_cell[0]][king_to_cell[1]] = 6 * turn + PieceType.KING
        grid[rook_from_cell[0]][rook_from_cell[1]] = -1
        grid[rook_to_cell[0]][rook_to_cell[1]] = 6 * turn + PieceType.ROOK

        return grid_to_fen(grid, 1-turn)


