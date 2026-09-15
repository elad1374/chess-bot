from typing import Optional
from common.enums_and_dicts import PieceType
from common.utils import convert_type_and_color_to_fen_char

class StorageManager:
    _instance = None

    def __new__(cls, *args, **kwargs):
        # Singleton 
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            
            # Inventory management tracking pieces off the board
            cls._instance.storage_state = {
                'sP': 0, 'sp': 0,   
                'sR': 0, 'sr': 0,
                'sN': 0, 'sn': 0,   
                'sB': 0, 'sb': 0,
                'sQ': 0, 'sq': 0,
                'sK': 0, 'sk': 0
            }
        return cls._instance

    # ==============================================================
    # Synchronization functions for human moves (Memory update only)
    # ==============================================================
    
    def register_human_capture(self, type: PieceType, color: str):
        """
        Updates the inventory state when a human captures a piece and places it in storage.
        """
        fen_char = convert_type_and_color_to_fen_char(type, color)
        self.storage_state[f"s{fen_char}"] += 1 

        #self.print_state()  # Optional: Print the updated state for debugging

    def register_human_promotion(self, type: PieceType, color: str):
        """
        Updates the inventory state when a human takes a piece from storage for a promotion.
        """
        fen_char = convert_type_and_color_to_fen_char(type, color)
        self.storage_state[f"s{fen_char}"] -= 1 

        #self.print_state()  # Optional: Print the updated state for debugging

    # ==============================================================
    # Movement functions for robot moves
    # ==============================================================

    def get_slot_for_robot_capture(self, type: PieceType, color: str) -> str:
        """
        Updates the inventory when the robot captures a piece, 
        and returns the exact slot name the robotic arm should move to.
        """
        fen_char = convert_type_and_color_to_fen_char(type, color)
        self.storage_state[f"s{fen_char}"] += 1 
        index = self.storage_state[f"s{fen_char}"]
        
        #self.print_state()  # Optional: Print the updated state for debugging

        return f"s{fen_char}{index}"
        
    def get_slot_for_robot_promotion(self, type: PieceType, color: str) -> str:
        """
        Returns the exact slot name from which the robot should take a piece for promotion, 
        and updates the inventory state accordingly.
        """
        fen_char = convert_type_and_color_to_fen_char(type, color)
        index = self.storage_state[f"s{fen_char}"]
        
        if index <= 0:
            raise Exception(f"No {fen_char} in storage to remove!")
            
        slot_name = f"s{fen_char}{index}"
        self.storage_state[f"s{fen_char}"] -= 1 

        #self.print_state()  # Optional: Print the updated state for debugging

        return slot_name

    def calibrate_storage_from_fen(self, fen_string: str):
        """
        Calculates missing pieces on the board relative to a standard starting position
        and calibrates the storage inventory state accordingly.
        """
        # Standard starting counts for each chess piece
        initial_counts = {
            'P': 8, 'R': 2, 'N': 2, 'B': 2, 'Q': 1, 'K': 1,
            'p': 8, 'r': 2, 'n': 2, 'b': 2, 'q': 1, 'k': 1
        }

        # Count actual pieces on the board
        board_part = fen_string.split()[0]
        board_counts = {char: 0 for char in initial_counts.keys()}

        for char in board_part:
            if char in board_counts:
                board_counts[char] += 1

        # Reset and populate storage_state based on missing pieces
        for char, max_count in initial_counts.items():
            missing_count = max(0, max_count - board_counts[char])
            self.storage_state[f"s{char}"] = missing_count

        print("\n[Storage Calibrated From FEN]")
        self.print_state()

    def print_state(self):
        print("\n" + "="*30)
        print("📦 CURRENT STORAGE STATE")
        print("="*30)
        
        white_pieces = {k: v for k, v in self.storage_state.items() if k[1].isupper()}
        black_pieces = {k: v for k, v in self.storage_state.items() if k[1].islower()}
        
        print(f"White off-board: {white_pieces}")
        print(f"Black off-board: {black_pieces}")
        print("="*30 + "\n")