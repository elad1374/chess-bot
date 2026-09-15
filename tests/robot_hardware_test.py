from sys import stdout
from common.enums_and_dicts import PieceType
from src.arm.hardware.abstract_robot_hardware import AbstractRobotHardware
from src.arm.hardware.mock_robot_hardware import MockRobotHardware

if __name__ == "__main__":
    with MockRobotHardware(log=stdout) as hw:
        hw.mov_chess_piece(PieceType.PAWN, "a1", "b2")
