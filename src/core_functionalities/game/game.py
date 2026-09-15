import chess
from .player import Player
from src.arm.state.perception_state import PerceptionState

DEFAULT_STARTING_FEN = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"

class Game:
    def __init__(self, white_player: Player, black_player: Player, fen: str = DEFAULT_STARTING_FEN):
        self.players = [black_player, white_player]
        self.init_fen: str = fen
        self.turn: int = self._extract_turn_from_fen(fen) # 1 for white, 0 for black
        self.is_running: bool = False
        self.board: chess.Board = chess.Board(self.init_fen.strip())
        PerceptionState().set_latest_board(board=self.board)

    def set_fen(self, fen:str):
        self.init_fen = fen.strip()
        self.board = chess.Board(self.init_fen)
        
    def _extract_turn_from_fen(self, fen_string: str) -> int:
        """
        Extracts active turn from FEN string:
        Returns 1 for White ('w'), 0 for Black ('b').
        """
        parts = fen_string.split()
        if len(parts) > 1 and parts[1].lower() == 'w':
            return 1
        return 0

    def start_game(self):
        """Starts the game loop or marks the game as active."""
        self.is_running = True
        current_turn_name = "White" if self.turn == 1 else "Black"
        print(f"Game started! Initial FEN: {self.init_fen}")
        print(f"Active turn: {current_turn_name} ({self.turn})")
        while self.is_running:
            if self.board.is_checkmate():
                # The side to move is checkmated, so the other side wins
                winner = not self.board.turn
                print("Checkmate!")
                print("Winner:", "White" if winner == chess.WHITE else "Black")
                break

            elif self.board.is_stalemate():
                print("Stalemate! Draw.")
                break

            cur_player = self.players[self.turn]
            cur_player.make_move(self.board)
            self.turn = 1 - self.turn


    def stop_game(self):
        """Stops the game loop or marks the game as inactive."""
        self.is_running = False
        print("Game stopped.")