import chess
from abc import ABC, abstractmethod
import json
import cv2
import numpy as np
from common.enums_and_dicts import *
from common.utils import *


CORNERS_FILE = repo_path("corners.json")


class Translator(ABC):

    def __init__(self, flip: bool):
            self.flip = flip # If the buttom side (camera's prespective) is black need to flip to get correct FEN notation. 

    def _debug_boards(self, matrices):
        for mat in matrices:
            for row in mat:
                print(row)
            print("\n")

    def _get_non_capture_moves(self, board: chess.Board, square: str):
        """ Returns list of chess.Move"""
        square = chess.parse_square(square)

        moves = []

        for move in board.legal_moves:
            if move.from_square == square and not board.is_capture(move):
                moves.append(move)

        return moves

    def _get_warp_matrix(self, corners, target_size=800):
        src_pts = np.array(corners, dtype="float32")
        dst_pts = np.float32([
            [0, 0],
            [target_size - 1, 0],
            [target_size - 1, target_size - 1],
            [0, target_size - 1]
        ])
        return cv2.getPerspectiveTransform(src_pts, dst_pts)
        
    def _get_grid_position(self, x, y, matrix, target_size=800):
        """Transforms image (x, y) coordinates into grid (row, col) indices."""
        pt = np.array([[[x, y]]], dtype=np.float32)
        warped_pt = cv2.perspectiveTransform(pt, matrix)
        wx, wy = warped_pt[0][0]
        
        square_size = target_size / 8.0
        col = int(wx // square_size)
        row = int(wy // square_size)
        # Captured pieces outside the grid bounds 
        if not (0 <= row <= 7 and 0 <= col <= 7):
            return -1, -1

        if self.flip:
            row = 7 - row
            col = 7 - col
        return row, col

    def _create_detected_grid(self, detections_file, corners_file, target_size=800):
        """
        Creates an 8x8 color occupancy grid.
        Values: -1 = empty, others based on class or color
        """
        with open(corners_file, "r") as f:
            corners = json.load(f)

        matrix = self._get_warp_matrix(corners, target_size=target_size)
        
        # Initialize all 64 squares as -1 (empty)
        color_grid = [[-1 for _ in range(8)] for _ in range(8)]

        with open(detections_file, "r") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                
                parts = line.split()
                if len(parts) < 3:
                    continue
                
                label = parts[0].lower()  #class
                x = float(parts[1])
                y = float(parts[2])
                color_val = self._get_label_num(label)
                if color_val is not None:
                    row, col = self._get_grid_position(x, y, matrix, target_size=target_size)
                    if row>=0 and col>=0:
                        color_grid[row][col] = color_val

        return color_grid

    @abstractmethod    
    def _get_label_num(self, label:str) -> int:
        return -1

    @abstractmethod
    def translate_to_fen(self, old_fen: str, detections_file: str) -> str:
        """
        Given an old FEN and a labels file, translates the detected pieces into a new FEN string.
        """
        pass

    @abstractmethod
    def translate_to_move(self, board: chess.Board, detections_file: str):
        """
        Given an old board and a labels file, translates the detected pieces into a move UCI string.
        """
        pass 

class AdvancedToFenTranslator(Translator):

    def __init__(self, flip: bool = False):
        super().__init__(flip)

    def _get_label_num(self, label:str) -> int:
        return CLASS_TO_INT.get(label)

    def translate_to_fen(self, old_fen: str, detections_file: str) -> str:
        """
        Generates a new FEN string based on the old FEN and detected colors.
        """
        active_turn = -1
        old_board_grid = []
        detected_color_grid = self._create_detected_grid(detections_file, CORNERS_FILE)
        if len(old_fen)==1:
            # this is the case where we initialize a board and the old_fen becomes indicator of turn
            active_turn = 1 if old_fen=="w" else 0
        self._debug_boards([old_board_grid, detected_color_grid])
        return grid_to_fen(detected_color_grid, active_turn)
    
    
    def translate_to_move(self, board: chess.Board, detections_file: str) -> str:
        return ""

    def detect_promotion(self, detections_file: str, sqr: str) -> str:
        """
        Looks at the sqr of the board from detections_file outputs the class of the piece at that square. 
        """
        detected_color_grid = self._create_detected_grid(detections_file, CORNERS_FILE)
        target_cell = convert_square_to_coordinates(sqr)
        cell_class = detected_color_grid[target_cell[0]][target_cell[1]]
        if cell_class<0 or cell_class in [1,3,7,9]: # class == empty, pawn or king 
            return ""
        else:
            return INT_TO_FEN[cell_class].lower()

def create_advaced_translator(tranlator: Translator)->AdvancedToFenTranslator:
    return AdvancedToFenTranslator(flip=tranlator.flip)

class BinaryToFenTranslator(Translator):

    def __init__(self, flip: bool = False):
        super().__init__(flip)

    def _get_label_num(self, label:str) -> int:
        res =  COLOR_TO_INT.get(label)
        return res

    def translate_to_fen(self, old_fen: str, detections_file: str) -> str:
        """
        Generates a new FEN string based on the old FEN and detected colors.
        """
        old_board_grid, active_turn = parse_fen_to_int_grid(old_fen)
        detected_color_grid = self._create_detected_grid(detections_file, CORNERS_FILE)
        self._debug_boards([old_board_grid, detected_color_grid])

        moved_source=[]
        moved_target=[]
        captured=[]

        for row in range(8):
            for col in range(8):
                old_piece = old_board_grid[row][col]
                old_piece_type = get_color(old_piece)
                new_piece_type = detected_color_grid[row][col]

                if old_piece_type == new_piece_type:
                    continue  # No change in piece type
                elif old_piece_type == -1 and new_piece_type != -1:
                    # moved here
                    moved_target.append((row, col))
                elif old_piece_type != -1 and new_piece_type == -1:
                    # moved from here
                    moved_source.append((row, col))
                elif old_piece_type != -1 and new_piece_type != -1 and old_piece_type != new_piece_type:
                    # captured here
                    print(f"Captured piece at ({row}, {col}): old_piece_type={old_piece_type}, new_piece_type={new_piece_type}")
                    captured.append((row, col))

        print(f"Moved Source: {moved_source}, Moved Target: {moved_target}, Captured: {captured}")
        if len(captured) > 0:
            # Handle capture: Move the piece from moved_source to captured square
            capturing_piece = old_board_grid[moved_source[0][0]][moved_source[0][1]]
            old_board_grid[moved_source[0][0]][moved_source[0][1]] = -1
            old_board_grid[captured[0][0]][captured[0][1]] = capturing_piece
        elif len(moved_source) == 1 and len(moved_target) == 1:
            # Handle normal move: Move the piece from moved_source to moved_target
            moving_piece = old_board_grid[moved_source[0][0]][moved_source[0][1]]
            old_board_grid[moved_source[0][0]][moved_source[0][1]] = -1
            old_board_grid[moved_target[0][0]][moved_target[0][1]] = moving_piece
        elif len(moved_source) == 2 and len(moved_target) == 2:
            # Handle castling: Move the king and rook to their new positions
            king_source = None
            rook_source = None
            king_target = None
            rook_target = None

            distance_from_mid_source_0 = abs(moved_source[0][1] - 4) 
            distance_from_mid_source_1 = abs(moved_source[1][1] - 4) 
            distance_from_mid_target_0 = abs(moved_target[0][1] - 4) 
            distance_from_mid_target_1 = abs(moved_target[1][1] - 4) 

            if distance_from_mid_source_0 < distance_from_mid_source_1:
                king_source = moved_source[0]
                rook_source = moved_source[1]
            else:
                king_source = moved_source[1]
                rook_source = moved_source[0]
            if distance_from_mid_target_0 > distance_from_mid_target_1:
                king_target = moved_target[0]
                rook_target = moved_target[1]
            else:
                king_target = moved_target[1]
                rook_target = moved_target[0]
            
            king_piece = old_board_grid[king_source[0]][king_source[1]]
            rook_piece = old_board_grid[rook_source[0]][rook_source[1]]
            old_board_grid[king_source[0]][king_source[1]] = -1
            old_board_grid[rook_source[0]][rook_source[1]] = -1
            old_board_grid[king_target[0]][king_target[1]] = king_piece
            old_board_grid[rook_target[0]][rook_target[1]] = rook_piece
        elif len(moved_source) == 2 and len(moved_target) == 1:
            source0_label = old_board_grid[moved_source[0][0]][moved_source[0][1]]
            source1_label = old_board_grid[moved_source[1][0]][moved_source[1][1]]
            if sorted([source0_label, source1_label]) == [3, 9]:  # one black pawn and one white pawn
                # Handle en passant: Move the pawn from moved_source to moved_target and remove the captured pawn
                for source in moved_source:
                    old_board_grid[source[0]][source[1]] = -1  # Clear both source squares
                old_board_grid[moved_target[0][0]][moved_target[0][1]] = 3+active_turn*6  # Set the moving pawn in the target square
            else:
                print("Error: Unexpected move scenario.")
            
        else:
            print("Error: Unexpected move scenario.")

        return grid_to_fen(old_board_grid, 1-active_turn)
    

    def translate_to_move(self, board: chess.Board, detections_file: str) -> str:
        """
        Given an old board and a labels file, translates the detected pieces into a move UCI string.
        """
        old_board_grid, active_turn = parse_board_to_int_grid(board)
        detected_color_grid = self._create_detected_grid(detections_file, CORNERS_FILE)
        self._debug_boards([old_board_grid, detected_color_grid])
        # White is always at the buttom. If flipped the camera is from above so the blocker has less row value
        # Otherwise the camera at bottum and blocker's row is higher 
        blocker_offset = -1 if self.flip else 1
        moved_source=[]
        moved_target=[]
        captured=[]

        for row in range(8):
            for col in range(8):
                old_piece = old_board_grid[row][col]
                old_piece_type = get_color(old_piece)
                new_piece_type = detected_color_grid[row][col]

                if old_piece_type == new_piece_type:
                    continue  # No change in piece type
                elif old_piece_type == -1 and new_piece_type != -1:
                    # moved here
                    moved_target.append((row, col))
                elif old_piece_type != -1 and new_piece_type == -1:
                    # moved from here
                    moved_source.append((row, col))
                elif old_piece_type != -1 and new_piece_type != -1 and old_piece_type != new_piece_type:
                    # captured here
                    print(f"Captured piece at ({row}, {col}): old_piece_type={old_piece_type}, new_piece_type={new_piece_type}")
                    captured.append((row, col))

        print(f"Moved Source: {moved_source}, Moved Target: {moved_target}, Captured: {captured}")
        source_sqr = ""
        target_sqr = ""
        promotion = ""
        if len(captured) == 1 and len(moved_source)==1:
            # Handle regular capture: 
            capturing_piece = old_board_grid[moved_source[0][0]][moved_source[0][1]]
            source_sqr = convert_coordinates_to_square(moved_source[0][0], moved_source[0][1])
            target_sqr = convert_coordinates_to_square(captured[0][0], captured[0][1])
            if (capturing_piece==3 and captured[0][0] == 7) or (capturing_piece==6 and captured[0][0] == 0):
                promotion = "_"

        elif len(captured) == 1 and len(moved_source)==2:
            # Handle capture where moving piece blocks
            true_source = None
            blocked_source = None
            for source in moved_source:
                if source[1]==captured[0][1] and source[0]+blocker_offset==captured[0][0]:
                    blocked_source = source
                else:
                    true_source = source
            blocked_sqr = convert_coordinates_to_square(blocked_source[0], blocked_source[1])
            source_sqr = convert_coordinates_to_square(true_source[0], true_source[1])
            target_sqr = convert_coordinates_to_square(captured[0][0], captured[0][1])
            print(f"The square: {blocked_sqr} is blocked from the camera")

        elif len(captured) == 0 and len(moved_source)==2 and len(moved_target) == 0:
            # Handle capture where moving piece is blockd
            true_source = None
            captured_cell = None
            capturing_piece = -1
            for source in moved_source:
                piece_class = old_board_grid[source[0]][source[1]]
                if get_color(piece_class)==active_turn:
                    true_source = source
                    capturing_piece = piece_class
                else:
                    captured_cell = source
            source_sqr = convert_coordinates_to_square(true_source[0], true_source[1])
            target_sqr = convert_coordinates_to_square(captured_cell[0], captured_cell[1])
            print(f"The square: {target_sqr} is blocked from the camera")            
            if (capturing_piece==3 and captured_cell[0] == 7) or (capturing_piece==6 and captured_cell[0] == 0):
                promotion = "_"

        elif len(moved_source) == 1 and len(moved_target) == 1:
            # Handle normal move: 
            moving_piece = old_board_grid[moved_source[0][0]][moved_source[0][1]]
            source_sqr = convert_coordinates_to_square(moved_source[0][0], moved_source[0][1])
            target_sqr = convert_coordinates_to_square(moved_target[0][0], moved_target[0][1])    
            if (moving_piece==3 and moved_target[0][0] == 7) or (moving_piece==6 and moved_target[0][0] == 0):
                promotion = "_"

        elif len(moved_source)==1 and len(moved_target)==0 and len(captured) == 0:
            # Handle moveing where moving piece is blocked
            source_sqr = convert_coordinates_to_square(moved_source[0][0], moved_source[0][1])
            moves = self._get_non_capture_moves( board, source_sqr)
            filtered_targets = []
            for move in moves:
                possible_target = move.uci()[2:4]
                target_cell = convert_square_to_coordinates(possible_target)
                blocker_row = target_cell[0]+blocker_offset
                if blocker_row>7 or blocker_row<0:
                    continue
                blocker_col = target_cell[1]
                if(old_board_grid[blocker_row][blocker_col] in [1,4,7,10]): #blocker is big piece
                    filtered_targets.append(possible_target)
            if len(filtered_targets)==1:
                target_sqr = filtered_targets[0]
                print(f"The square: {target_sqr} is blocked from the camera")
            elif len(filtered_targets)>1:
                print(f"Some square(s) are blocked from the camera, ambigous move")
                return ""
            else:
                print("Error: Unexpected move scenario.")
                return ""

                    
        elif len(moved_source) == 2 and len(moved_target) == 2:
            # Handle castling: Move the king and rook to their new positions
            king_source = None
            king_target = None

            distance_from_mid_source_0 = abs(moved_source[0][1] - 4) 
            distance_from_mid_source_1 = abs(moved_source[1][1] - 4) 
            distance_from_mid_target_0 = abs(moved_target[0][1] - 4) 
            distance_from_mid_target_1 = abs(moved_target[1][1] - 4) 

            if distance_from_mid_source_0 < distance_from_mid_source_1:
                king_source = moved_source[0]
            else:
                king_source = moved_source[1]
            if distance_from_mid_target_0 > distance_from_mid_target_1:
                king_target = moved_target[0]
            else:
                king_target = moved_target[1]
            
            king_piece = old_board_grid[king_source[0]][king_source[1]]
            rook_piece = king_piece + 3
            
            source_sqr = convert_coordinates_to_square(king_source[0], king_source[1])
            target_sqr = convert_coordinates_to_square(king_target[0], king_target[1])  
            
        elif len(moved_source) == 2 and len(moved_target) == 1:
            source0_label = old_board_grid[moved_source[0][0]][moved_source[0][1]]
            source1_label = old_board_grid[moved_source[1][0]][moved_source[1][1]]
            if sorted([source0_label, source1_label]) == [3, 9]:  # one black pawn and one white pawn
                # Handle en passant: 
                capturer_source = moved_source[0] if moved_source[1][1]==moved_target[0][1] else moved_source[1] #the capturer iff not on the same column as target
                capturer_target = moved_target[0]
                source_sqr = convert_coordinates_to_square(capturer_source[0], capturer_source[1])
                target_sqr = convert_coordinates_to_square(capturer_target[0], capturer_target[1])                  
            else:
                # Handle moving but moving piece blocks
                true_source = None
                blocked_source = None
                for source in moved_source:
                    if source[1]==moved_target[0][1] and source[0]+blocker_offset==moved_target[0][0]:
                        blocked_source = source
                    else:
                        true_source = source
                blocked_sqr = convert_coordinates_to_square(blocked_source[0], blocked_source[1])
                source_sqr = convert_coordinates_to_square(true_source[0], true_source[1])
                target_sqr = convert_coordinates_to_square(moved_target[0][0], moved_target[0][1])
                print(f"The square: {blocked_sqr} is blocked from the camera")
            
        else:
            print("Error: Unexpected move scenario.")

        return source_sqr+target_sqr+promotion