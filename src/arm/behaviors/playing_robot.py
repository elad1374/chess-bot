from abc import ABC, abstractmethod
from typing import Optional
from common.enums_and_dicts import *
from src.arm.chessbot import *
from src.arm.state.storage_manager import StorageManager
import math
from src.arm.state.perception_state import PerceptionState

class PlayingRobot(ABC):

    """
    Interface to handle moving pieces according to command during game
    Each move method returns the True if successfull, otherwise False
    """

    @abstractmethod
    def move(self, from_square: str, to_square: str, piece: PieceType) -> bool:
        pass

    @abstractmethod
    def capture(self, from_square: str, to_square: str, remove_square: str, moving_piece: PieceType, captured_piece: PieceType) -> bool:
        pass

    @abstractmethod
    def castle(self, king_from_square: str, king_to_square: str, rook_from_square: str, rook_to_square: str) -> bool: 
        pass

    @abstractmethod
    def upgrade(self, from_square: str, to_square: str, promoted_piece: PieceType = PieceType.QUEEN, captured_piece: Optional[PieceType] = None) -> bool:
        pass



  
        



class PlayingArm(PlayingRobot):

    """
    Real UR5E arm class for playing
    """

    def __init__(self, robot_hardware: RobotHardware, human_color: str, robot_color: str):
        self.robot_hardware = robot_hardware
        self.human_color = human_color
        self.robot_color = robot_color
        self.storage = StorageManager() # call Singleton
    
    def _move_piece(self, type=None, start_pos=None, end_pos=None, speed=None, acceleration=None, rz_rotation_start=None, rz_rotation_end=None, move_to_start=True):
        """
        Private method for moving a piece, using the hardware class
        """
        robot = self.robot_hardware

        if speed is None:
            speed = robot.speed
        if acceleration is None:
            acceleration = robot.acceleration

        # --- APPLY HEIGHT SAFTEY ---
        if robot.pose[Z] < robot.safe_height:
            robot.move_to(z=robot.safe_height)
        
        path_is_clear = self.is_path_clear(start_pos, end_pos, type) 
        
        # --- GET PHYSICAL POSITIONS ---
        start_pos = robot.normalize_pos(start_pos)
        end_pos = robot.normalize_pos(end_pos)
        if rz_rotation_start is not None:
            start_pos[3:6] = robot.get_rotated_tcp_orientation(start_pos,Rz=rz_rotation_start)
        if rz_rotation_end is not None:
            end_pos[3:6] = robot.get_rotated_tcp_orientation(end_pos,Rz=rz_rotation_end)

        robot.set_gripper(grip_size[type] - GRIP_RELEASE_OFFSET,wait=False) #  open the gripper
        
        # --- PICKUP FROM BOARD ---
        robot.move_to(start_pos, z=robot.safe_height, speed=speed, acceleration=acceleration) 
        robot.move_to(z=robot.grip_height[type])
        robot.set_gripper(CLOSED) 

        if path_is_clear:
            robot.move_to(z=robot.grip_height[type]+0.01)
        else:
            robot.move_to(z=robot.safe_height)
        
        # --- PLACE ON BOARD ---
        if path_is_clear:
            robot.move_to(end_pos, z=robot.grip_height[type]+0.01, speed=speed, acceleration=acceleration)
        else:
            robot.move_to(end_pos, z=robot.safe_height, speed=speed, acceleration=acceleration)
        
        robot.move_to(z=robot.grip_height[type] + GRIP_RELEASE_HEIGHT)
        robot.set_gripper(robot.get_gripper() - GRIP_RELEASE_OFFSET) # release the piece
        robot.move_to(z=robot.safe_height)
        
        if move_to_start:
            robot.move_to(robot.start_position, z=robot.sky_height, speed=speed, acceleration=acceleration)


    def is_path_clear(self, start_pos_name, end_pos_name, piece_type):
        """
        Checks if the trajectory between start and end squares is completely empty.
        Returns True if clear (can hover low), False if blocked (must fly high).
        """
        # 1. Knights always fly high to avoid knocking pieces during their jump
        if piece_type == PieceType.KNIGHT:
            return False
            
        perception = PerceptionState()
        board = perception.get_latest_board()
        
        # 2. Convert standard names (e.g., 'e2') to 0-7 indices
        start_col = ord(start_pos_name.lower()[0]) - ord('a')
        start_row = int(start_pos_name[1]) - 1
        
        end_col = ord(end_pos_name.lower()[0]) - ord('a')
        end_row = int(end_pos_name[1]) - 1
        
        # 3. Determine the step direction (-1, 0, or 1) for rows and columns
        step_col = 0 if end_col == start_col else (1 if end_col > start_col else -1)
        step_row = 0 if end_row == start_row else (1 if end_row > start_row else -1)
        
        # Safety check: if it's not a valid straight or diagonal line, fly high
        is_diagonal = (step_col != 0 and step_row != 0)
        if step_col != 0 and step_row != 0 and abs(end_col - start_col) != abs(end_row - start_row):
            return False 
            
        # 4. Traverse the squares strictly BETWEEN start and end
        cur_col = start_col + step_col
        cur_row = start_row + step_row
        
        while (cur_col, cur_row) != (end_col, end_row):
            # Check primary square
            sq_index = cur_row * 8 + cur_col
            if board.piece_at(sq_index) is not None:
                return False 
                
            # Check side neighbors for diagonal moves
            if is_diagonal:
                neighbor_col1 = cur_col - step_col
                neighbor_row1 = cur_row
                if 0 <= neighbor_col1 <= 7 and 0 <= neighbor_row1 <= 7:
                    if board.piece_at(neighbor_row1 * 8 + neighbor_col1) is not None:
                        return False
                        
                neighbor_col2 = cur_col
                neighbor_row2 = cur_row - step_row
                if 0 <= neighbor_col2 <= 7 and 0 <= neighbor_row2 <= 7:
                    if board.piece_at(neighbor_row2 * 8 + neighbor_col2) is not None:
                        return False

            cur_col += step_col
            cur_row += step_row

        # 5. HARDENED FIX: Check the immediate side neighbors of the DESTINATION square for diagonal moves
        if is_diagonal:
            # Check adjacent columns/rows right next to the target landing square
            target_neighbors = [
                (end_col - step_col, end_row),
                (end_col, end_row - step_row)
            ]
            for n_col, n_row in target_neighbors:
                if 0 <= n_col <= 7 and 0 <= n_row <= 7:
                    if board.piece_at(n_row * 8 + n_col) is not None:
                        return False
            
        # If all checks pass, the path and landing clearance are safe
        return True

    def _remove_piece(self, type: PieceType, start_pos, end_pos = None, rz_start = None, speed=None, move_to_start=True):
        """
        Private method for remove a piece, using the hardware class
        """
        robot = self.robot_hardware

        if speed is None:
            speed = robot.speed

        # --- GET PHYSICAL POSITIONS ---
        start_pos = robot.normalize_pos(start_pos)
        end_pos = robot.normalize_pos(end_pos)

        if rz_start is not None:
            end_pos[3:6] = robot.get_rotated_tcp_orientation(end_pos, Rz=rz_start)

        # --- APPLY HEIGHT SAFTEY ---
        if robot.pose[Z] < robot.safe_height:
            robot.move_to(z=robot.safe_height)

        robot.set_gripper(grip_size[type] - GRIP_RELEASE_OFFSET,wait=False) #  open the gripper

        # --- PICKUP FROM BOARD ---
        robot.move_to(start_pos, z=robot.safe_height, speed=speed)
        robot.move_to(z=robot.grip_height[type])
        robot.set_gripper(CLOSED)
        robot.move_to(z=robot.safe_height)

        # --- PLACE IN STORAGE ---
        robot.move_to(end_pos, z=robot.safe_height, speed=speed)
        robot.move_to(z=robot.grip_height[type] + 0.002)
        robot.set_gripper(open_by=GRIP_RELEASE_OFFSET)
        robot.move_to(z=robot.safe_height)

        if move_to_start:
            robot.move_to(robot.start_position, z=robot.sky_height, speed=speed)

    def _bring_on_board(self, type: PieceType, end_pos, start_pos=None, rz_end=None, speed=None, move_to_start=True):
        """
        Private method for bringing a piece onto the board from off-board storage/graveyard
        (e.g., for pawn promotions).
        """
        robot = self.robot_hardware

        if speed is None:
            speed = robot.speed

        # --- GET PHYSICAL POSITIONS ---
        start_pos = robot.normalize_pos(start_pos)
        end_pos = robot.normalize_pos(end_pos)

        if rz_end is not None:
            end_pos[3:6] = robot.get_rotated_tcp_orientation(end_pos, Rz=rz_end)

        # --- APPLY HEIGHT SAFTEY ---
        if robot.pose[Z] < robot.safe_height:
            robot.move_to(z=robot.safe_height)

        robot.set_gripper(grip_size[type] - GRIP_RELEASE_OFFSET, wait=False)  #  open the gripper

        # --- PICKUP FROM STORAGE ---
        robot.move_to(start_pos, z=robot.safe_height, speed=speed)
        robot.move_to(z=robot.grip_height[type] + OFFSET_TO_TABLE_HEIGHT)
        robot.set_gripper(CLOSED)
        robot.move_to(z=robot.safe_height)

        # --- PLACE ON BOARD ---
        robot.move_to(end_pos, z=robot.safe_height, speed=speed)
        robot.move_to(z=robot.grip_height[type] + GRIP_RELEASE_HEIGHT)
        robot.set_gripper(open_by=GRIP_RELEASE_OFFSET)
        robot.move_to(z=robot.safe_height)

        # --- RETURN TO SAFE POSITION ---
        if move_to_start:
            robot.move_to(robot.start_position, z=robot.sky_height, speed=speed)


    # return true if pos is on board
    def _is_on_board(self, pos: str) -> bool:
        if pos is None or not pos:
            return False
        return len(pos) == 2 and pos[0] in "abcdefgh" and pos[1] in "12345678"

    # general movement of robot
    # examples
    # "e3" -> "b6" : from square -> square
    # "sP2" -> "b6" : from storage -> square
    # "e3" -> "sP2" : from square -> storage
    def _execute_movement(self, piece: PieceType, start_pos: Optional[str] = None, end_pos: Optional[str] = None, move_to_start: bool = True):
        start_on_board = self._is_on_board(start_pos)
        end_on_board = self._is_on_board(end_pos)

        if start_on_board and end_on_board:                                              # from square -> square
            self._move_piece(piece, start_pos, end_pos, speed=0.5 ,move_to_start=move_to_start)
        elif start_on_board and not end_on_board:                                        # from square -> storage
            self._remove_piece(piece, start_pos, end_pos, speed=0.5, move_to_start=move_to_start)
        elif not start_on_board and end_on_board:                                        # from storage -> square
            self._bring_on_board(piece, end_pos, start_pos, speed=0.5, move_to_start=move_to_start)
        else:
            raise Exception("Invalid square/borad coordinations provided")



    def move(self, from_square: str, to_square: str, piece: PieceType) -> bool:
        try:
            print(f"Moving {piece} from {from_square} to {to_square}")
            self._execute_movement(piece, start_pos=from_square, end_pos=to_square) # move
            return True
        except Exception as e:
            print(f"[Robot] Move failed: {type(e).__name__}: {e}")
            return False

    def capture(self, from_square: str, to_square: str, remove_square: str, moving_piece: PieceType, captured_piece: PieceType) -> bool:
        try:
            storage_pos = self.storage.get_slot_for_robot_capture(captured_piece, self.human_color)
            self._execute_movement(captured_piece, remove_square, storage_pos, move_to_start=False) # remove
            self._execute_movement(moving_piece, from_square, to_square)                            # move
            return True
        except Exception as e:
            print(f"[Robot] Capture failed: {type(e).__name__}: {e}")
            return False

    def castle(self, king_from_square: str, king_to_square: str, rook_from_square: str, rook_to_square: str) -> bool: 
        try:
            self._execute_movement(PieceType.KING, king_from_square, king_to_square, move_to_start=False) # move
            self._execute_movement(PieceType.ROOK, rook_from_square, rook_to_square)                      # move
            return True
        except Exception as e:
            print(f"[Robot] Castle failed: {type(e).__name__}: {e}")
            return False

    def upgrade(self, from_square: str, to_square: str, promoted_piece: PieceType = PieceType.QUEEN, captured_piece: Optional[PieceType] = None) -> bool:
        try:
            if captured_piece is not None: 
                storage_pos = self.storage.get_slot_for_robot_capture(captured_piece, self.human_color)
                self._execute_movement(captured_piece, to_square, storage_pos, move_to_start=False)   # remove
            storage_pos = self.storage.get_slot_for_robot_capture(PieceType.PAWN, self.robot_color)
            self._execute_movement(PieceType.PAWN, from_square, storage_pos, move_to_start=False)     # remove
            storage_pos = self.storage.get_slot_for_robot_promotion(promoted_piece, self.robot_color)
            self._execute_movement(promoted_piece, storage_pos, to_square)                            # get
            return True
        except Exception as e:
            print(f"[Robot] Upgrade failed: {type(e).__name__}: {e}")
            return False        



        
class PlayingMock(PlayingRobot):

    """
    Mock Class for PlayingRobot
    res determines if will fail or succeed
    """
    def __init__(self, res: bool = True):
        """
        res = false -> fails / true -> succeeds
        """
        self.res = res
    
    def move(self, from_square: str, to_square: str, piece: PieceType) -> bool:
        return self.res

    def capture(self, from_square: str, to_square: str, remove_square: str, moving_piece: PieceType, captured_piece: PieceType) -> bool:
        return self.res

    def castle(self, king_from_square: str, king_to_square: str, rook_from_square: str, rook_to_square: str) -> bool: 
        return self.res

    def upgrade(self, from_square: str, to_square: str, promoted_piece: PieceType = PieceType.QUEEN, captured_piece: Optional[PieceType] = None) -> bool:
        return self.res