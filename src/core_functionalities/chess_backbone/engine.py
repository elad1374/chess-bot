import chess
import chess.engine
import argparse
from common.exceptions import EngineNoMove
from pathlib import Path

ENGINE_PATH = (
    Path(__file__).resolve().parent
    / "stockfish"
    / "stockfish-ubuntu-x86-64-avx2"
)
ENGINE_PATH = "/usr/games/stockfish" # TODO check for permenant path in linux

class ChessEngine:
    
    def _engine_make_move(self, board: chess.Board, engine_path=ENGINE_PATH) -> str:
        """
        Uses real chess engine to decide on move based on current board FEN string
        Returns move in UCI format e.g "e2e4", "e7e8q"
        """
        # Open the engine, find the move, and safely close the engine
        with chess.engine.SimpleEngine.popen_uci(engine_path) as engine:
            # --- -------------------------
            print("FEN sent to Stockfish:", board.fen())
            if not board.is_valid():
                print("WARNING: The board is logically invalid!")
                print("Reason:", board.status())
            # -----------------------------
            result = engine.play(board, chess.engine.Limit(time=0.1))
            if result.move:
                return result.move.uci()
            else: 
                raise EngineNoMove()
            
        return ""

    def choose_move(self, board: chess.Board, engine_path=ENGINE_PATH) -> str:
        return self._engine_make_move(board, engine_path=engine_path)


    def choose_move_fen(self, fen: str, engine_path=ENGINE_PATH) -> str:

        # Handle cases where only the board layout is provided
        try:
            board = chess.Board(fen.strip())
        except ValueError:
            board = chess.Board(fen.strip() + " w - - 0 1")

        return self._engine_make_move(board, engine_path=engine_path)



if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Get the optimal chess move from a FEN string")
    parser.add_argument("--test", action="store_true", help="Run the test suite")
    parser.add_argument("--fen", type=str, help="Pass a FEN string to get the optimal move")
    
    args = parser.parse_args()

    # If a FEN is passed directly via terminal
    if args.fen:
        best_move = ChessEngine.choose_move_fen(args.fen)
        print(best_move)
        
    # If the --test flag is passed
    elif args.test:
        test_cases = [
            {
                "name": "Standard Starting Position",
                "fen": "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1",
                "expected": None # No strict expectation, just needs a valid move
            },
            {
                "name": "Mate in 1 (White to move)",
                "fen": "r1bqkbnr/pppp1ppp/2n5/4p3/2B1P3/5Q2/PPPP1PPP/RNB1K1NR w KQkq - 4 4",
                "expected": "f3f7" # Scholar's mate
            },
            {
                "name": "Mate in 1 (Black to move)",
                "fen": "4r1k1/5ppp/8/8/8/8/5PPP/6K1 b - - 0 1",
                "expected": "e8e1" # Back rank mate
            },
            {
                "name": "Board-only FEN (Tests the ValueError fallback)",
                "fen": "rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR",
                "expected": None # No strict expectation, but should not crash
            }
        ]

        print("--- Running Chess Engine Test Suite ---\n")
        
        passed = 0
        engine = ChessEngine()

        for i, test in enumerate(test_cases, 1):
            print(f"Test {i}: {test['name']}")
            print(f"FEN: {test['fen']}")
            
            try:
                move = engine.choose_move_fen(test['fen'])
                print(f"Engine played: {move}")
                
                if test['expected']:
                    if move == test['expected']:
                        print("Result: PASS (Found expected move)")
                        passed += 1
                    else:
                        print(f"Result: FAIL (Expected {test['expected']})")
                else:
                    if move:
                        print("Result: PASS (Generated a valid move)")
                        passed += 1
                    else:
                        print("Result: FAIL (No move generated)")
            except Exception as e:
                print(f"Result: FAIL (Exception occurred: {e})")
                
            print("-" * 40)
            
        print(f"Tests Completed: {passed}/{len(test_cases)} Passed")

    else:
        # If no arguments are passed, show the help menu
        parser.print_help()