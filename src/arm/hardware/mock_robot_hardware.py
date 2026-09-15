try:
    from typing import override, Optional
except:
    override = lambda f: f

from math import atan2, pi
from io import TextIOBase
from .abstract_robot_hardware import AbstractRobotHardware
from src.arm.measurements import *
from common.utils import *

class MockRobotHardware(AbstractRobotHardware):
    _pose: Vector
    _gripper: int
    log: TextIOBase
    friendly_pose_names: dict[Vector, str]

    def __init__(self, log: TextIOBase = None):
        super().__init__(log=log)
        self.speed = 0.01
        self.acceleration = 0.01
        self._pose = [0.1, 0.2, 0.3, 0.4, 0.5, 0.6]
        self._gripper = 123
        self.log = log
        self.friendly_pose_names = {}

    @override
    def __enter__(self):
        self.step_right = [1.0, 0]
        self.step_up = [0, 1.0]

        a1 = [-0.3, 0.4, 0.5]
        h8 = [0.3, -0.4, 0.5]

        dx = h8[X] - a1[X]
        dy = h8[Y] - a1[Y]
        h1 = [a1[X] + (dx + dy) / 2.0, a1[Y] + (dy - dx) / 2.0]

        self.step_right = [(h1[X] - a1[X]) / 7.0, (h1[Y] - a1[Y]) / 7.0]
        self.step_up = [-self.step_right[Y], self.step_right[X]]

        # Different constants than in the real chessbot.
        rad = atan2(h8[1] - a1[1], h8[0] - a1[0])
        self.down_orientation = [0, pi, rad-pi/4 + pi]
        self.floor_height = (h8[Z] + a1[Z]) / 2 + 0.1
        self.sky_height = self.floor_height + 0.5

        tmp_pos = [a1[X], a1[Y]]
        for row in range(1, 9):
            for col in "abcdefgh":
                square = f"{col}{row}"
                self.positions[square] = tmp_pos + [self.floor_height] + self.down_orientation
                tmp_pos = self.move_on_chessboard(tmp_pos, right=CELL_LENGTH, up=0)
            tmp_pos = self.move_on_chessboard(tmp_pos, right=-8*CELL_LENGTH, up=CELL_LENGTH)

        self.start_position = self.move_on_chessboard(self.positions['h5'], right = CELL_LENGTH/2, up = CELL_LENGTH/2)

        self.start_position[Z] = self.sky_height

        self.grip_height[PieceType.QUEEN] = self.floor_height + 0.01
        self.grip_height[PieceType.PAWN] = self.floor_height + 0.02
        self.grip_height[PieceType.KING] = self.floor_height + 0.03
        self.grip_height[PieceType.ROOK] = self.floor_height + 0.04
        self.grip_height[PieceType.KNIGHT] = self.floor_height + 0.05
        self.grip_height[PieceType.BISHOP] = self.floor_height + 0.06

        self.safe_height = self.floor_height + 0.2
        self.table_height = self.floor_height + OFFSET_TO_TABLE_HEIGHT

        storage_start = self.move_on_chessboard(self.positions['h8'], right=0.4*CELL_LENGTH, up=2.5*CELL_LENGTH)
        for type in "PNBRQKpnbrqk":
            for i in range(1, 9):
                self.positions[f's{type}{i}'] = storage_start

        self.friendly_pose_names[tuple(self.start_position)] = "start_position"
        self.friendly_pose_names[tuple(cube_pose)] = "cube_pose"
        for k, v in self.positions.items():
            self.friendly_pose_names[tuple(v)] = k

        print("enter", file=self.log)
        print("initial pose:", self._pose, file=self.log)
        print("initial grippr:", self._gripper, file=self.log)
        return self

    @override
    def __exit__(self, exc_type, exc, tb):
        print("exit", file=self.log)

    def get_friendly_pose_name(self, pose: Vector) -> str:
        for other_pose, name in self.friendly_pose_names.items():
            if is_close(other_pose[:2], pose[:2]):
                dz = (pose[2] - other_pose[2]) * 100
                return f"{dz:.1f} cm above {name}"
        nearest_pose, name = min(
            self.friendly_pose_names.items(),
            key = lambda kv: distance(kv[0][:3], pose[:3])
        )
        if is_close(nearest_pose, pose):
            return name
        return f"nearest to {name}"

    @property
    @override
    def pose(self):
        return self._pose

    @override
    def move_raw(self, target_pose, speed, acceleration):
        assert isinstance(target_pose, Sequence)
        assert len(target_pose) == 6
        assert all(isinstance(x, int | float) for x in target_pose)
        assert isinstance(speed, int | float)
        assert isinstance(acceleration, int | float)

        self._pose = target_pose
        name = self.get_friendly_pose_name(self._pose)
        print(f"move to {self._pose} ({name})", file=self.log)

    @override
    def move_joint(self, target_pose, speed, acceleration):
        assert isinstance(target_pose, Sequence)
        assert len(target_pose) == 6
        assert all(isinstance(x, int | float) for x in target_pose)
        assert isinstance(speed, int | float)
        assert isinstance(acceleration, int | float)

        print("warning: ignoring move_joint method call", file=self.log)

    @override
    def get_gripper(self):
        return self._gripper

    @override
    def set_gripper_raw(self, position, speed, force, wait):
        assert isinstance(position, int)
        assert 0 <= position <= 255
        assert isinstance(speed, int)
        assert isinstance(force, int)

        self._gripper = position
        if wait:
            print("set gripper to", self._gripper, "and wait", file=self.log)
        else:
            print("set gripper to", self._gripper, file=self.log)
