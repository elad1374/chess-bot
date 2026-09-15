


from src.perception.yolo.processing.fen_translator import AdvancedToFenTranslator, BinaryToFenTranslator
from src.perception.yolo.vision_inference.board_pieces_detector import *
from src.perception.yolo.processing.human_interpreter import *

if __name__ == "__main__":
    test1_path = "C:/Users/m1478/Downloads/test_trans/detections.txt"
    test2_path = "C:/Users/m1478/Downloads/test_trans/flipped.txt"
    test3_path = "C:/Users/m1478/Downloads/test_trans/binary_detections.txt"
    test4_path = "C:/Users/m1478/Downloads/test_trans/binary_flipped.txt"
    test5_path = "C:/Users/m1478/OneDrive/Документы/CS_Degree/Y3B/Robotics Workshop/chess-bot/corners.json"

    FEN_TO_PATH = [
        ("8/8/8/4p3/8/8/4Q3/8 w - - 0 1", "C:/Users/m1478/Downloads/test_trans/regular_e2e4.txt"),
        ("8/8/8/R7/3Q4/8/8/8 b - - 0 1", "C:/Users/m1478/Downloads/test_trans/blocking_d4a4.txt"),
        ("8/8/8/R7/r2Q4/8/8/8 w - - 0 1", "C:/Users/m1478/Downloads/test_trans/capturing_d4a4.txt"),
        ("8/8/8/8/3R2r1/3Q4/8/8 b - - 0 1", "C:/Users/m1478/Downloads/test_trans/capturing_blocked_g4d4.txt"),
        ("8/8/8/8/3R4/8/8/3Q4 w - - 0 1", "C:/Users/m1478/Downloads/test_trans/blocked_d4d2.txt"),
        ("8/8/8/8/8/8/8/R3K3 w KQkq - 0 1", "C:/Users/m1478/Downloads/test_trans/castle_e1c1.txt"),
        # Flipped
        ("8/8/8/8/3K4/6R1/8/8 w KQkq - 0 1", "C:/Users/m1478/Downloads/test_trans/flipped_moving_blocked_g3d3.txt"),
        ("8/8/8/8/3K4/6R1/8/8 w KQkq - 0 1", "C:/Users/m1478/Downloads/test_trans/flipped_moving_blockes_d4g4.txt"),
        ("8/8/8/8/3K4/3n2R1/8/8 w KQkq - 0 1", "C:/Users/m1478/Downloads/test_trans/flipped_capturing_blocked_g3d3.txt"),
        ("8/8/8/8/3K2n1/6R1/8/8 w KQkq - 0 1", "C:/Users/m1478/Downloads/test_trans/flipped_capturing_blockes_d4g4.txt")

        ]
    mock_detector = MockBoardDetector()
    binary_translator = BinaryToFenTranslator(flip = True)
    controller = HumanMoveController(mock_detector, binary_translator, mock_detector)

    fen, path = FEN_TO_PATH[6] ##change here index
    board = chess.Board(fen)
    move = binary_translator.translate_to_move(board, path)
    print(move)





