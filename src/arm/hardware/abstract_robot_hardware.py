# The interface behind RobotHardware and MockRobotHardware

import os
from io import TextIOBase
from typing import Optional
from abc import ABC, abstractmethod
from scipy.spatial.transform import Rotation
from src.arm.measurements import *
from common.enums_and_dicts import *
from common.typing import Vector
from common.utils import *

class AbstractRobotHardware(ABC):
    speed: Optional[float]
    acceleration: Optional[float]
    step_right: Optional[Vector]
    step_up: Optional[Vector]
    positions: dict[str, Vector]
    grip_height: dict[PieceType, float]
    down_orientation: Optional[Vector]
    start_position: Optional[Vector]
    sky_height: Optional[float]
    safe_height: Optional[float]

    def __init__(self, log: TextIOBase = None):
        self.speed = None
        self.acceleration = None
        self.step_right = None
        self.step_up = None
        self.positions = {}
        self.grip_height = {}
        self.down_orientation = None
        self.start_position = None
        self.sky_height = None
        self.safe_height = None
        self.log = log or os.devnull


    # Abstract methods:

    @abstractmethod
    def __enter__(self):
        pass

    @abstractmethod
    def __exit__(self, exc_type, exc, tb):
        pass

    @property
    @abstractmethod
    def pose(self) -> Vector:
        pass

    @abstractmethod
    def move_raw(self, target_pose: Vector, speed: float, acceleration: float) -> None:
        pass

    @abstractmethod
    def move_joint(self, target_pose: Vector, speed: float, acceleration: float) -> None:
        pass

    @abstractmethod
    def get_gripper(self) -> int:
        pass

    @abstractmethod
    def set_gripper_raw(self, position: int, speed: int, force: int, wait: bool) -> None:
        pass


    # Extensions:

    # return a position moved right and up by the given number of centimeters, can also use negative numbers to move left and down
    # must before use the calibrate_board_positions function at least once to set the step_right and step_up values
    def move_on_chessboard(self, current_pos, right=0, up=0):
        position = current_pos.copy()
        position[X] += (self.step_right[X] / CELL_LENGTH) * right + (self.step_up[X] / CELL_LENGTH) * up
        position[Y] += (self.step_right[Y] / CELL_LENGTH) * right + (self.step_up[Y] / CELL_LENGTH) * up
        return position

    def normalize_pos(self, pos):
        if isinstance(pos, str):
            # Check if the string is a board square ('e4', sP3, ...)
            if pos in self.positions:
                return self.positions[pos]
            else:
                raise ValueError(f"Position '{pos}' not found in board or storage dictionaries")
            
        if not isinstance(pos, Sequence):
            raise Exception("expected a sequence")
        if not isinstance(pos, list):
            pos = list(map(float, pos))
        if len(pos) == 3:
            return pos + self.down_orientation
        elif len(pos) == 6:
            return pos
        else:
            raise Exception("bad length")

    # return a rotated version vector of curent position by tcp
    def get_rotated_tcp_orientation(self, base_orientation = None, Rx=0, Ry=0, Rz=0):
        if base_orientation is None:
            base_orientation = self.pose
        base_orientation = base_orientation[-3:] 
        rot_base = Rotation.from_rotvec(base_orientation)
        rot_local = Rotation.from_euler('xyz', [Rx, Ry, Rz], degrees=True)
        new_rot = rot_base * rot_local
        return  new_rot.as_rotvec().tolist()

    @staticmethod
    def modify_pose(pose, x=None, y=None, z=None, rx=None, ry=None, rz=None,
                    dx=None, dy=None, dz=None, drx=None, dry=None, drz=None):
        """Modify a pose with absolute and/or relative parameters.
        
        Absolute parameters (x, y, z, rx, ry, rz) set the coordinate directly.
        Relative parameters (dx, dy, dz, drx, dry, drz) add to the coordinate.
        If both absolute and relative are provided for the same coordinate, they are summed.
        """
        modified = pose.copy()

        # Process X coordinate (absolute and/or relative)
        if x is not None or dx is not None:
            value = pose[X]
            if x is not None:
                value = x
            if dx is not None:
                value += dx
            modified[X] = value
        
        # Process Y coordinate (absolute and/or relative)
        if y is not None or dy is not None:
            value = pose[Y]
            if y is not None:
                value = y
            if dy is not None:
                value += dy
            modified[Y] = value
        
        # Process Z coordinate (absolute and/or relative)
        if z is not None or dz is not None:
            value = pose[Z]
            if z is not None:
                value = z
            if dz is not None:
                value += dz
            modified[Z] = value
        
        # Process RX rotation (absolute and/or relative)
        if rx is not None or drx is not None:
            value = pose[RX]
            if rx is not None:
                value = rx
            if drx is not None:
                value += drx
            modified[RX] = value
        
        # Process RY rotation (absolute and/or relative)
        if ry is not None or dry is not None:
            value = pose[RY]
            if ry is not None:
                value = ry
            if dry is not None:
                value += dry
            modified[RY] = value
        
        # Process RZ rotation (absolute and/or relative)
        if rz is not None or drz is not None:
            value = pose[RZ]
            if rz is not None:
                value = rz
            if drz is not None:
                value += drz
            modified[RZ] = value
        
        return modified

    def calculate_target_pose(self, pose=None, x=None, y=None, z=None, rx=None, ry=None, rz=None, 
                              orientation = None, dx=None, dy=None, dz=None, drx=None, dry=None, drz=None):
        if pose is None:
            pose = self.pose

        # Handle orientation case
        if orientation is not None:
            # Check if any x, y, z are provided
            other_params = any(v is not None for v in (rx, ry, rz, drx, dry, drz))
            if other_params:
                raise ValueError("Cannot mix orientation with x, y, z parameters")
        
        # Use unified modify_pose for all position/rotation parameters
        target_pose = self.modify_pose(pose, x=x, y=y, z=z, rx=rx, ry=ry, rz=rz,
                                        dx=dx, dy=dy, dz=dz, drx=drx, dry=dry, drz=drz)
        
        if orientation is not None:
            target_pose[3:] = orientation

        return target_pose

    def move_to(self, pose=None, x=None, y=None, z=None, rx=None, ry=None, rz=None, orientation = None,
                dx=None, dy=None, dz=None, drx=None, dry=None, drz=None, speed = None, acceleration = None):
        """Move to a target pose. Accepts absolute, relative, or mixed arguments.
        
        Absolute parameters (x, y, z, rx, ry, rz) set the coordinate directly.
        Relative parameters (dx, dy, dz, drx, dry, drz) add to the current/given pose.
        Can also provide orientation directly or mix absolute and relative parameters.
        """
        if speed is None:
            speed = self.speed
        if acceleration is None:
            acceleration = self.acceleration
        target_pose = self.calculate_target_pose(pose=pose, x=x, y=y, z=z, rx=rx, ry=ry, rz=rz, orientation = orientation,
                                                dx=dx, dy=dy, dz=dz, drx=drx, dry=dry, drz=drz)
        self.move_raw(target_pose, speed, acceleration)
        return target_pose

    def set_gripper(self, position=None, close_by=None, open_by=None, speed=60, force=0, wait = True):
        if position is None and close_by is None and open_by is None:
            raise Exception("expected position or close_by or open_by")
        if position is None:
            position = self.get_gripper()
        if close_by is not None:
            position += close_by
        if open_by is not None:
            position -= open_by
        self.set_gripper_raw(position, speed, force, wait)

    def move_to_safe_height(self):
        self.move_to(z=self.safe_height)

    def mov_chess_piece(self, type: PieceType=None, start_pos=None, end_pos=None, speed=None, acceleration=None, rz_rotation_start=None, rz_rotation_end=None, move_to_start=True):
        if speed is None:
            speed = self.speed
        if acceleration is None:
            acceleration = self.acceleration
        if self.pose[Z] < self.safe_height:
            self.move_to(z=self.safe_height)

        # update chess board locations
        start_pos = self.normalize_pos(start_pos)
        end_pos = self.normalize_pos(end_pos)
        if rz_rotation_start is not None:
            start_pos[3:6] = self.get_rotated_tcp_orientation(start_pos,Rz=rz_rotation_start)
        if rz_rotation_end is not None:
            end_pos[3:6] = self.get_rotated_tcp_orientation(end_pos,Rz=rz_rotation_end)

        self.set_gripper(grip_size[type] - GRIP_RELEASE_OFFSET,wait=False) #  open the gripper

        # move to first spot
        self.move_to(start_pos, z=self.safe_height, speed=speed, acceleration=acceleration) 
        self.move_to(z=self.grip_height[type])

        self.set_gripper(CLOSED) # grip the piece

        # move to end spot
        self.move_to(start_pos, z=self.safe_height)
        self.move_to(end_pos, z=self.safe_height, speed=speed, acceleration=acceleration)
        self.move_to(z=self.grip_height[type] + GRIP_RELEASE_HEIGHT)
        
        self.set_gripper(open_by=GRIP_RELEASE_OFFSET, speed=10) # release the piece

        # return to start postion
        self.move_to(z=self.safe_height)
        if move_to_start:
            self.move_to(self.start_position, z=self.sky_height, speed=speed, acceleration=acceleration)
