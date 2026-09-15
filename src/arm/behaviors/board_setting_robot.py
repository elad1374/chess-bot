from abc import ABC, abstractmethod
import math
from common.typing import Pos
from common.utils import *
from src.arm.chessbot import RobotHardware
from src.arm.measurements import *
from common.enums_and_dicts import Orientation, ColoredPieceType, PieceType

class BoardSettingRobot(ABC):

    """
    Interface to handle movement of pieces during setting board
    Each move method returns the True if successfull, otherwise False
    """

    @abstractmethod
    def move_piece_to_platform(self, head_pos: Pos, base_pos: Pos, orientation) -> bool:
        pass

    @abstractmethod
    def move_from_platform_to_target(self, target: str, type: str) -> bool:
        pass




class BoardSettingArm(BoardSettingRobot):

    """
    Real UR5E arm class for setting board before game
    """

    def __init__(self, robot_hardware: RobotHardware):
        self.robot_hardware = robot_hardware

    def move_piece_to_platform(self, head_pos: Pos, base_pos: Pos, orientation: Orientation) -> bool:
        # translate to robot coordinates
        head_pos = self.robot_hardware.normalize_pos(head_pos)
        base_pos = self.robot_hardware.normalize_pos(base_pos)

        print(f"orientation: {orientation}, head: {head_pos}, base: {base_pos}")
        dx, dy, dz = [head_pos[i] - base_pos[i] for i in range(3)]
        drz = math.degrees(math.atan2(dx, dy))
        is_standing = (orientation == Orientation.STANDING)
        HEAD_BIAS = 0.6
        
        pickup_pos = weighted_avg(head_pos[:3], base_pos[:3], HEAD_BIAS)
        if is_standing:
            pickup_pos = [*pickup_pos[:2], self.robot_hardware.grip_height[PieceType.PAWN] + GRIP_RELEASE_HEIGHT, *self.robot_hardware.down_orientation] # always the height of the shortest piece
            if abs(head_pos[Y] - base_pos[Y]) > 0.015: # too far
                pickup_pos[Y] = base_pos[Y] - 0.010
                print("points are too far")
            if abs(head_pos[Y] - base_pos[Y]) < 0.01: # too close
                print("points are too close")
                pickup_pos[Y] = head_pos[Y]
        else:
            pickup_pos = [pickup_pos[X], pickup_pos[Y],self.robot_hardware.table_height+0.005, *self.robot_hardware.get_rotated_tcp_orientation(Rz=drz+180)]

        if self.robot_hardware.pose[Z] < self.robot_hardware.safe_height:
            self.robot_hardware.move_to(z=self.robot_hardware.safe_height)

        self.robot_hardware.set_gripper(HALF_OPENED, wait=False)
        self.robot_hardware.move_to(pickup_pos, z=self.robot_hardware.safe_height)
        self.robot_hardware.move_to(pickup_pos)
        self.robot_hardware.set_gripper(CLOSED)
        self.robot_hardware.move_to_safe_height()
        self.robot_hardware.move_to(cube_pose, z=self.robot_hardware.safe_height)

        dy_alignment = -0.002 if is_standing else -0.005
        if not is_standing:
            self.robot_hardware.move_to(orientation = self.robot_hardware.get_rotated_tcp_orientation(Rx=85))

        piece_height_worst_case = math.hypot(dx, dy, dz) * 1.2
        print(f"{dx=} {dy=} {dz=} {piece_height_worst_case=} {HEAD_BIAS=} {piece_height_worst_case*HEAD_BIAS=}")
        
        if is_standing:
            self.robot_hardware.move_to(z=cube_pose[Z], dy=dy_alignment, dz=self.robot_hardware.grip_height[PieceType.PAWN] + GRIP_RELEASE_HEIGHT - self.robot_hardware.floor_height)
        else:
            self.robot_hardware.move_to(z=cube_pose[Z], dy=dy_alignment, dz=piece_height_worst_case * HEAD_BIAS)

        self.robot_hardware.set_gripper(open_by=GRIP_RELEASE_OFFSET)

        self.robot_hardware.move_to(cube_pose,z=self.robot_hardware.sky_height)

        return True


    def move_from_platform_to_target(self, target: str, type: PieceType, orientation: Orientation) -> bool:
        if isinstance(type, ColoredPieceType):
            type = type.piece_type

        # grip from the cube   
        self.robot_hardware.set_gripper(HALF_OPENED, wait=False)
        self.robot_hardware.move_to(
            dx=-0.00,
            z=cube_pose[Z] - self.robot_hardware.floor_height + self.robot_hardware.grip_height[type],
            orientation =
                self.robot_hardware.get_rotated_tcp_orientation(Rz=90)
                if orientation == Orientation.LYING and type == PieceType.KNIGHT else None)
        self.robot_hardware.set_gripper(CLOSED) # grip the piece
        self.robot_hardware.move_to(dz=0.05) # raise the arm

        # put back on the chess board
        self.robot_hardware.move_to(
            self.robot_hardware.positions[target],
            z=self.robot_hardware.safe_height,
        )
        self.robot_hardware.move_to(z=self.robot_hardware.grip_height[type] + GRIP_RELEASE_HEIGHT)
        
        self.robot_hardware.set_gripper(open_by=GRIP_RELEASE_OFFSET)
        self.robot_hardware.move_to(z=self.robot_hardware.safe_height)
        
        self.robot_hardware.move_to(self.robot_hardware.start_position, z=self.robot_hardware.sky_height)
        self.robot_hardware.move_joint(BASE_EYAL, 1, 0.5) # align gripper

        return True


        
class BoardSettingMock(BoardSettingRobot):

    """
    Mock Class for BoardSettingRobot
    res determines if will fail or succeed
    """
    def __init__(self, res: bool = True):
        """
        res = false -> fails / true -> succeeds
        """
        self.res = res
    
    def move_piece_to_platform(self, head_pos: Pos, base_pos: Pos, orientation) -> bool:
        return self.res

    def move_from_platform_to_target(self, target: str, type: str) -> bool:
        return self.res
