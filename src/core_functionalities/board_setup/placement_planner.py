from common.utils import parse_fen_to_int_grid, convert_coordinates_to_square
from common.enums_and_dicts import INT_TO_FEN, ColoredPieceType

class PlacementPlanner():
    """Given desired FEN string and piece computes the target placement for piece"""

    def __init__(self, fen: str):
        self.piece_target_stack_array = None
        self.grave_yard_counter_array = [1]*12 #counter for off board pieces, number represents the next grave yard cell for piece
        self.total_count = 0 #count of pieces to be set on board
        self._fen_to_targets(fen)

    def _fen_to_targets(self, fen:str):
        self.piece_target_stack_array = [[] for _ in range(12)]
        int_grid, _ = parse_fen_to_int_grid(fen)
        for row in range(8):
            for col in range(8):
                piece_type = int_grid[row][col]
                if piece_type >= 0:
                    self.total_count+=1
                    self.piece_target_stack_array[piece_type].append(convert_coordinates_to_square(row, col))


    def get_total_count(self)->int:
        return self.total_count

    def get_targer_for_piece(self, colored_piece: ColoredPieceType) -> str: 
        int_class = int(colored_piece)
        piece_targe_arr = self.piece_target_stack_array[int_class]
        if len(piece_targe_arr)>0:
            return piece_targe_arr.pop()
        cell = self.grave_yard_counter_array[int_class]
        self.grave_yard_counter_array[colored_piece]+=1
        return "s"+INT_TO_FEN[int_class]+str(cell)
        

    def get_grave_yard(self):
        return self.grave_yard_counter_array    
