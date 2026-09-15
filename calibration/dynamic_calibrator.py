import sys
import time
from src.arm.chessbot import *

if __name__ == "__main__":
    if len(sys.argv) > 1:
        command = sys.argv[1].lower()

        if command == "test":
            with RobotHardware(robot_ip=ROBOT_IP, base_tcp_port=BASE_TCP_PORT, A1=A1_, H8=H8_, speed=0.1, flip=True) as robot:
                print("Managed to connect to arm")
                robot.move_to(robot.normalize_pos(get_head_camera_point()))    
                time.sleep(5)
                robot.move_to(robot.start_position)

        elif command == "robot":
            with RobotHardware(robot_ip=ROBOT_IP, base_tcp_port=BASE_TCP_PORT, A1=A1_, H8=H8_, speed=0.1, flip=True) as robot:
                print("Managed to connect to arm")
                for i in range(4):
                    robot.move_to(z=robot.safe_height)
                    robot.move_to(robot_points[i].tolist() + robot.down_orientation)
                    time.sleep(1)
                robot.move_to(robot.start_position)

        elif command == "camera":
            get_12_camera_points()