from chess import Board
from .actions import *
from common.utils import *
class ActionFactory():
    """ Generates action provided the current boatd and move """

    def _parse_move(self, move: str) -> tuple[str, str, str | None]:
        """
        Parses a UCI move string into a tuple.
        
        Examples:
            "e2e4"  -> ("e2", "e4", None)
            "e7e8q" -> ("e7", "e8", "q")
        """
        move = move.strip().lower()
        
        if not (4 <= len(move) <= 5):
            raise ValueError(f"Invalid UCI move string format: '{move}'")
        
        from_sq = move[:2]
        to_sq = move[2:4]
        promotion = move[4] if len(move) == 5 else None
        
        return from_sq, to_sq, promotion


    def interpret_action(self, move: str, board: Board) -> ChessAction:
        from_sq, to_sq, promo_char = self._parse_move(move)
        from_r, from_c = convert_square_to_coordinates(from_sq)
        to_r, to_c = convert_square_to_coordinates(to_sq)
        grid, turn = parse_board_to_int_grid(board)
        for row in grid:
            print(row)
        print("\n")
        print(f"from: ({from_r, from_c}), to: ({to_r, to_c})")
        

        from_val = grid[from_r][from_c]
        to_val = grid[to_r][to_c]

        moving_piece = PieceType(from_val % 6)


        
        # PROMOTION (UPGRADE)
        if(promo_char != None):
            promoted_piece = convert_string_to_chessType(promo_char)
            captured_piece = PieceType(to_val % 6) if to_val != -1 else None
            return Upgrade(from_sq, to_sq, promoted_piece, captured_piece)

        # CASTLING
        # King moves 2 columns sideways (e.g., e1 to g1 or c1)
        if moving_piece == PieceType.KING and abs(from_c - to_c) == 2:
            is_kingside = to_c > from_c
            rook_from_c = 7 if is_kingside else 0
            rook_to_c = 5 if is_kingside else 3
            
            rook_from = convert_coordinates_to_square(from_r, rook_from_c)
            rook_to = convert_coordinates_to_square(from_r, rook_to_c)
            
            return Castle(from_sq, to_sq, rook_from, rook_to)

        # EN PASSANT CAPTURE
        # Pawn moves diagonally into an EMPTY square
        if moving_piece == PieceType.PAWN and from_c != to_c and to_val == -1:
            # Captured pawn is sitting on the same row as 'from' and same column as 'to'
            remove_sq = convert_coordinates_to_square(from_r, to_c)
            return Capture(
                from_square=from_sq,
                to_square=to_sq,
                remove_square=remove_sq,
                moving_piece=PieceType.PAWN,
                captured_piece=PieceType.PAWN
            )

        # REGULAR CAPTURE
        if to_val != -1:
            captured_piece = PieceType(to_val % 6)
            return Capture(
                from_square=from_sq,
                to_square=to_sq,
                remove_square=to_sq,
                moving_piece=moving_piece,
                captured_piece=captured_piece
            )

        # STANDARD MOVE
        return Move(from_sq, to_sq, moving_piece)
        