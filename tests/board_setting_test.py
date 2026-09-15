from sys import stdout
from common.utils import PieceType
from common.enums_and_dicts import Orientation
from src.arm.hardware.mock_robot_hardware import MockRobotHardware
from src.arm.chessbot import RobotHardware
from src.arm.behaviors.board_setting_robot import BoardSettingArm


if __name__ == "__main__":
    with RobotHardware() as hw:
        robot = BoardSettingArm(hw)
        base = hw.positions["a5"]
        head = base.copy()
        head[2] += 0.1
        robot.move_piece_to_platform(head, base, Orientation.STANDING)
        robot.move_from_platform_to_target("a6", PieceType.QUEEN)
