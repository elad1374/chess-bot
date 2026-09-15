from typing import List, Any
from src.main.config import AppConfig

from src.perception.ZED.cameralib import Camera
from src.arm.chessbot import RobotHardware


class HardwareFactory:
    """Creates and manages shared hardware context instances."""

    def __init__(self, config: AppConfig):
        self.config = config
        self._camera: Camera = None
        self._robot_hw: RobotHardware = None
        self._hardware_resources: List[Any] = []

    def get_camera(self) -> Camera:
        """Returns shared Camera instance (unopened)."""
        if self._camera is None:
            self._camera = Camera()
            self._hardware_resources.append(self._camera)
        return self._camera

    def get_robot_hardware(self) -> RobotHardware:
        """Returns shared RobotHardware instance (unopened)."""
        if self._robot_hw is None:
            if self.config.robot.is_mock:
                print("[HardwareFactory] Using Mock Robot (No hardware loaded)")
                return None
            
            flip_status = self.config.game.white_player == "human"

            self._robot_hw = RobotHardware(
                robot_ip=self.config.robot.ip,
                base_tcp_port=self.config.robot.base_tcp_port,
                speed=self.config.robot.speed,
                acceleration=self.config.robot.acceleration,
                flip=flip_status
            )
            self._hardware_resources.append(self._robot_hw)
        return self._robot_hw

    def get_active_resources(self) -> List[Any]:
        """Returns all context-managed hardware items for ExitStack."""
        return [res for res in self._hardware_resources if res is not None]