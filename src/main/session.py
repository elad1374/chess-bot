from contextlib import ExitStack
from typing import List, Any, Optional
from .config import AppConfig
from src.core_functionalities.game.game import Game
from factories.board_setup_factory import BoardSetupService
from src.perception.yolo.processing.human_interpreter import HumanMoveController


class ChessSession:
    """Manages the full lifecycle from hardware context opening to teardown."""

    def __init__(
        self, 
        config: AppConfig, 
        hardware_resources: List[Any],
        game: Game,
        board_setup_service: Optional[BoardSetupService] = None,
        initial_board_detector: Optional[HumanMoveController] = None
    ):
        self.config = config
        self.hardware_resources = hardware_resources
        self.game = game
        self.board_setup_service = board_setup_service
        self.initial_board_detector = initial_board_detector
        self._exit_stack = ExitStack()

    def run(self):
        try:
            print("\n=== MOUNTING HARDWARE ===")
            # Entering the context
            for res in self.hardware_resources:
                if hasattr(res, "__enter__"):
                    self._exit_stack.enter_context(res)
            print("[Session] All hardware connected and ready.")

            # Optional Pre-game setup phase
            if self.config.game.run_board_setup and self.board_setup_service:
                print("\n=== STAGE 1: BOARD SETUP ===")
                self.board_setup_service.setup_board()

            # Optional Pre-game board detection
            if (not self.config.game.run_board_setup) and self.config.game.run_initial_detection and self.initial_board_detector:
                print("\n=== STAGE 1.5: BOARD DETECTION ===")
                fen = self.initial_board_detector.detect_initial_board() #can have turn as argument
                print(f"Detected FEN: {fen}")
                correct = input("Is the FEN correct (yes/no): ")
                if correct=="no":
                    fen = input("Input your real FEN: ")
                self.game.set_fen(fen)
                


            # Gameplay phase
            print("\n=== STAGE 2: CHESS GAME ===")
            self.game.start_game()

        finally:
            print("\n=== UNMOUNTING HARDWARE ===")
            self._exit_stack.close()
            print("[Session] Hardware successfully safely unmounted.")