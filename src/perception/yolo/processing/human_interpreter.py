import chess
from ..vision_inference.board_pieces_detector import BoardPiecesDetector, AbsBoardDetector
from .fen_translator import *
from src.arm.state.storage_manager import StorageManager
from common.utils import convert_fen_char_to_type_and_color
from collections import Counter
from src.arm.state.perception_state import PerceptionState
from typing import Optional

class HumanMoveController:
    """
    Coordinates between the vision system (BoardPiecesDetector) and state translation (Translator)
    to compute updated board after a human player makes a move.
    """

    def __init__(self, yolo_model: AbsBoardDetector, translator: Optional[Translator] = None, advanced_model: AbsBoardDetector = None):
        self.yolo_model: AbsBoardDetector = yolo_model
        # Default to BinaryToFenTranslator if none is supplied
        self.translator: Translator = translator or BinaryToFenTranslator()
        self.promotion_model: AbsBoardDetector = advanced_model
        self.promotion_translator: AdvancedToFenTranslator = create_advaced_translator(tranlator=self.translator)
        self.storage = StorageManager() # Singleton

    def detect_initial_board(self, turn = "w",  image_path: Optional[str] = None) -> str:
        detections_file = self.yolo_model.predict(image_path=image_path)
        PerceptionState().set_latest_detections(detections_file)
        fen = self.translator.translate_to_fen("", detections_file)
        ##TODO: sync storage
        return fen


    def update_fen(self, board: chess.Board, image_path: Optional[str] = None) -> str:
        """
        Captures/processes an image, runs detection, updates storage, and translates the detected 
        pieces into an updated FEN string.

        :param board: The previous game board.
        :param image_path: Optional static image path for testing/debugging.
        :return: Updated FEN string.
        """
        old_fen = board.fen()
        detections_file = self.yolo_model.predict(image_path=image_path)
        PerceptionState().set_latest_detections(detections_file)
        print("####### ABOUT TO TRANSLATE MOVE#######")
        move_str = self.translator.translate_to_move(board, detections_file)
        if move_str=="":
            move_str = input("The translator wasn't able to understand the move. Input your move (UCI): ")
        elif move_str[-1]=='_':
            full_detections_file = self.yolo_model.predict(image_path=image_path)
            promoted = self.promotion_translator.detect_promotion(full_detections_file, move_str[2:4])
            if promoted=="":
                promoted = input("The yolo model wasn't able to detect promotion. Input your piece (q, n, b, r): ")
            move_str = move_str[0:4]+promoted
        print(f"Human Move: {move_str}")
        chess_move =  chess.Move.from_uci(move_str)
        board.push(chess_move)
        new_fen = board.fen()
        self._sync_storage(old_fen, new_fen)
        return new_fen

    def _sync_storage(self, old_fen: str, current_fen: str):

        if not old_fen or not current_fen:
            return

        old_board = old_fen.split()[0]
        new_board = current_fen.split()[0]

        old_counts = Counter(c for c in old_board if c.isalpha())
        new_counts = Counter(c for c in new_board if c.isalpha())

        # check for missing pieces
        for char, old_count in old_counts.items():
            new_count = new_counts.get(char, 0)
            if old_count > new_count:
                missing_qty = old_count - new_count
                piece_type, color = convert_fen_char_to_type_and_color(char)
                for _ in range(missing_qty):
                    self.storage.register_human_capture(piece_type, color) 
                    #print(f"[Robot Memory] Human captured {color} {piece_type.name}. Storage memory updated.")

        # check for new pieces
        for char, new_count in new_counts.items():
            old_count = old_counts.get(char, 0)
            if new_count > old_count:
                added_qty = new_count - old_count
                piece_type, color = convert_fen_char_to_type_and_color(char)
                for _ in range(added_qty):
                    self.storage.register_human_promotion(piece_type, color) 
                    #print(f"[Robot Memory] Human promoted to {color} {piece_type.name}. Storage memory updated.")