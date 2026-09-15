


from src.perception.yolo.processing.fen_translator import AdvancedToFenTranslator, BinaryToFenTranslator
from src.perception.yolo.vision_inference.board_pieces_detector import *
from src.perception.yolo.processing.human_interpreter import *

if __name__ == "__main__":
    detection_path = "C:/Users/m1478/Downloads/test_trans/detections.txt"
    flipped_path = "C:/Users/m1478/Downloads/test_trans/flipped.txt"
    binaty_detect_file = "C:/Users/m1478/Downloads/test_trans/binary_detections.txt"
    binary_flipped_path = "C:/Users/m1478/Downloads/test_trans/binary_flipped.txt"
    cornerns_path = "C:/Users/m1478/OneDrive/Документы/CS_Degree/Y3B/Robotics Workshop/chess-bot/corners.json"
    translator = AdvancedToFenTranslator()
    grid = translator._create_detected_grid(detection_path, cornerns_path)
    translator._debug_boards([grid]) 
    binaty_translator = BinaryToFenTranslator()
    bi_grid = binaty_translator._create_detected_grid(binaty_detect_file, cornerns_path)
    binaty_translator.flip = True
    bi_grid_flip = binaty_translator._create_detected_grid(binaty_detect_file, cornerns_path)
    binaty_translator._debug_boards([bi_grid, bi_grid_flip]) 

    ### Test Initial Detection ###
    mock_detector = MockBoardDetector()
    init_detector = HumanMoveController(mock_detector, translator)
    fen = init_detector.detect_initial_board("w", detection_path)
    print(fen)
    translator.flip = True
    flipped_fen = init_detector.detect_initial_board("w", flipped_path)
    print(flipped_fen)

    binary_translator = BinaryToFenTranslator()
    step_detector = HumanMoveController(mock_detector, binary_translator)
    board = chess.Board(fen)
    #new_fen = step_detector.update_fen(board, binaty_detect_file)
    #print(new_fen)
    fen = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR b - - 0 1"
    board = chess.Board(fen)
    binary_translator.flip = True
    new_fen = step_detector.update_fen(board, binary_flipped_path)
    print(new_fen)    





