#!/usr/bin/python3

import os
import time
import sys
import math
from io import TextIOBase
from collections.abc import Sequence

from typing_extensions import override
from rtde_control import RTDEControlInterface
from rtde_receive import RTDEReceiveInterface
import numpy as np
import cv2
import pyzed.sl as sl


ROOT_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from common.enums_and_dicts import *
from common.utils import *
from src.arm.hardware.robotiq_gripper import RobotiqGripper
from src.arm.measurements import *
from src.arm.hardware.abstract_robot_hardware import AbstractRobotHardware


clicked_point = None
point_cloud = sl.Mat()



def reset_gripper(robot_ip=ROBOT_IP, base_tcp_port=BASE_TCP_PORT):
    print("Reset arg detected: resetting and activating gripper...")
    g = None
    try:
        g = RobotiqGripper()
        g.connect(robot_ip, base_tcp_port)
        try:
            g._reset()
        except Exception as exc:
            print("Warning during gripper reset:", exc)
        try:
            g.activate()
        except Exception as exc:
            print("Warning during gripper activate:", exc)
        print("Gripper reset+activate completed.")
    except Exception as exc:
        print("Error communicating with gripper:", exc)
    finally:
        if g is not None:
            try:
                g.disconnect()
            except Exception:
                pass
    sys.exit(0)

def move_to_start_position():
    with RobotHardware(robot_ip=ROBOT_IP, base_tcp_port=BASE_TCP_PORT, A1=A1_, H8=H8_, start=False) as robot:
        robot.move_to(robot.start_position, z=robot.sky_height)
    sys.exit(0)

def grip_close():
    with RobotHardware(robot_ip=ROBOT_IP, base_tcp_port=BASE_TCP_PORT, A1=A1_, H8=H8_, start=False) as robot:
        robot.set_gripper(CLOSED)
    sys.exit(0)

def grip_open():
    with RobotHardware(robot_ip=ROBOT_IP, base_tcp_port=BASE_TCP_PORT, A1=A1_, H8=H8_, start=False) as robot:
        robot.set_gripper(OPENED)
    sys.exit(0)

def print_position():
    with RobotHardware(robot_ip=ROBOT_IP, base_tcp_port=BASE_TCP_PORT, A1=A1_, H8=H8_, start=False) as robot:
        print(robot.pose[:3])
    sys.exit(0)

def align_position():
    with RobotHardware(robot_ip=ROBOT_IP, base_tcp_port=BASE_TCP_PORT, A1=A1_, H8=H8_, start=False) as robot:
        robot.move_joint(BASE_EYAL, 1, 0.5)
    sys.exit(0)

def get_grip():
    with RobotHardware(robot_ip=ROBOT_IP, base_tcp_port=BASE_TCP_PORT, A1=A1_, H8=H8_, start=False) as robot:
        print(robot.get_gripper())
    sys.exit(0)

def print_joints():
    with RobotHardware(robot_ip=ROBOT_IP, base_tcp_port=BASE_TCP_PORT, A1=A1_, H8=H8_, start=False) as robot:
        print(list(robot.rtde_r.getActualQ()))
    sys.exit(0)





class RobotHardware(AbstractRobotHardware):
    def __init__(self, robot_ip=ROBOT_IP, base_tcp_port=BASE_TCP_PORT, speed=0.5, acceleration=0.5, A1 = A1_, H8 = H8_, flip=False, log: TextIOBase = None, start=False):
        super().__init__(log=log)
        self.robot_ip = robot_ip
        self.base_tcp_port = base_tcp_port
        self.speed = speed
        self.acceleration = acceleration
        self.rtde_c = None
        self.rtde_r = None
        self.gripper = None
        self.A1 = A1 
        self.H8 = H8 
        self.floor_height = 0
        self.sky_height = 0
        self.safe_height = 0.15
        self.grip_height = {}
        self.table_height = 0
        self.flip = flip
        self.start = start

    @override
    def __enter__(self):
        self.rtde_c = RTDEControlInterface(self.robot_ip)
        self.rtde_r = RTDEReceiveInterface(self.robot_ip)
        self.gripper = RobotiqGripper()

        self.gripper.connect(self.robot_ip, self.base_tcp_port)

        time.sleep(0.1)

        if self.flip:
            self.A1, self.H8 = self.H8, self.A1

        self.calibrate_board_positions(self.A1, self.H8, flip=self.flip)
        self.create_physical_storage_positions(flip=self.flip)
        

        if not self.gripper.is_active():
            self.gripper.activate()
        return self

    def calibrate_board_positions(self, a1=None, h8=None, flip=False):

        if a1 is None or h8 is None:
            raise Exception("error with a1 and h8 set values")
        dx = h8[X] - a1[X]
        dy = h8[Y] - a1[Y]
        h1 = [a1[X] + (dx + dy) / 2.0, a1[Y] + (dy - dx) / 2.0]

        self.step_right = [(h1[X] - a1[X]) / 7.0, (h1[Y] - a1[Y]) / 7.0]
        self.step_up = [-self.step_right[Y], self.step_right[X]]

        # orientations
        rad = math.atan2(h8[1] - a1[1], h8[0] - a1[0])
        rad = math.degrees(rad)
        extra_angle = 0 if flip else 180
        self.down_orientation = self.get_rotated_tcp_orientation([0, np.pi, 0], Rz=rad-45+extra_angle)

        self.floor_height = (h8[Z] + a1[Z]) / 2 + 0.0015 # offset
        self.table_height = self.floor_height + OFFSET_TO_TABLE_HEIGHT

        self.sky_height = self.floor_height + 0.3
        self.safe_height = 0.15 + self.floor_height

        # pieces grip heights
        self.grip_height[PieceType.QUEEN] = self.floor_height + 0.04
        self.grip_height[PieceType.PAWN] = self.floor_height + 0.025
        self.grip_height[PieceType.KING] = self.floor_height + 0.04
        self.grip_height[PieceType.ROOK] = self.floor_height + 0.025 
        self.grip_height[PieceType.KNIGHT] = self.floor_height + 0.03
        self.grip_height[PieceType.BISHOP] = self.floor_height + 0.03

        # boards positions
        tmp_pos = [a1[X], a1[Y]]
        for row in range(1, 9):
            for col in "abcdefgh":
                square = f"{col}{row}"
                self.positions[square] = tmp_pos + [self.floor_height] + self.down_orientation
                tmp_pos = self.move_on_chessboard(tmp_pos, right=CELL_LENGTH, up=0)
            tmp_pos = self.move_on_chessboard(tmp_pos, right=-8*CELL_LENGTH, up=CELL_LENGTH)
        if not flip:
            self.start_position = self.move_on_chessboard(self.positions['h5'], right = CELL_LENGTH/2, up = -CELL_LENGTH/2)
        else:
            self.start_position = self.move_on_chessboard(self.positions['a4'], right = -CELL_LENGTH/2, up = CELL_LENGTH/2)
        self.start_position[Z] = self.sky_height   

        if self.start:
            self.move_to(self.start_position)
        
    @override
    def __exit__(self, exc_type, exc_value, traceback):
        try:
            if self.rtde_c is not None:
                self.rtde_c.stopScript()
        except Exception:
            pass
        try:
            if self.gripper is not None:
                self.gripper.disconnect()
        except Exception:
            pass
        try:
            if self.rtde_c is not None:
                self.rtde_c.disconnect()
        except Exception:
            pass
        try:
            if self.rtde_r is not None:
                self.rtde_r.disconnect()
        except Exception:
            pass

    @property
    @override
    def pose(self):
        return self.rtde_r.getActualTCPPose()

    @override
    def move_raw(self, target_pose, speed, acceleration):
        self.rtde_c.moveL(target_pose, speed, acceleration)

    @override
    def move_joint(self, target_pose, speed, acceleration):
        self.rtde_c.moveJ(target_pose, speed, acceleration)

    @override
    def set_gripper_raw(self, position, speed, force, wait):
        if wait:
            self.gripper.move_and_wait_for_pos(position, speed, force)
        else:
            self.gripper.move(position, speed, force)

    @override
    def get_gripper(self):
        return self.gripper.get_current_position()

    def create_physical_storage_positions(self, storage_start = None, flip=False):
        
        if storage_start == None:
            if not flip:
                storage_start = self.move_on_chessboard(self.positions['h8'], right=0.4*CELL_LENGTH, up=2.5*CELL_LENGTH)
            else:
                storage_start = self.move_on_chessboard(self.positions['a1'], right=-0.4*CELL_LENGTH, up=-2.5*CELL_LENGTH)

        STORAGE_WIDTH = 5.3
        STORAGE_HEIGHT = 5

        direction = -1 if not flip else 1

        tmp_pos = storage_start
        for i in range(1,5):
        
            if i == 1: # add special black pieces
                for type in "rnbqk":
                    self.positions[f's{type}1'] = [tmp_pos[X] ,tmp_pos[Y], self.table_height] + self.down_orientation
                    tmp_pos = self.move_on_chessboard(tmp_pos, right=direction*STORAGE_WIDTH, up=0)
                for type in "bnr":
                    self.positions[f's{type}2'] = [tmp_pos[X] ,tmp_pos[Y], self.table_height] + self.down_orientation
                    tmp_pos = self.move_on_chessboard(tmp_pos, right=direction*STORAGE_WIDTH, up=0)

            elif i == 4: # add special white pieces
                for type in "RNBQK":
                    self.positions[f's{type}1'] = [tmp_pos[X] ,tmp_pos[Y], self.table_height] + self.down_orientation
                    tmp_pos = self.move_on_chessboard(tmp_pos, right=direction*STORAGE_WIDTH, up=0)
                for type in "BNR":
                    self.positions[f's{type}2'] = [tmp_pos[X] ,tmp_pos[Y], self.table_height] + self.down_orientation
                    tmp_pos = self.move_on_chessboard(tmp_pos, right=direction*STORAGE_WIDTH, up=0)

            elif i == 2: # add regular black pieces
                for counter in range(1,9):
                    self.positions[f'sp{counter}'] = [tmp_pos[X] ,tmp_pos[Y], self.table_height] + self.down_orientation
                    tmp_pos = self.move_on_chessboard(tmp_pos, right=direction*STORAGE_WIDTH, up=0)

            else: # i == 3 # add regular white pieces
                for counter in range(1,9):
                    self.positions[f'sP{counter}'] = [tmp_pos[X] ,tmp_pos[Y], self.table_height] + self.down_orientation
                    tmp_pos = self.move_on_chessboard(tmp_pos, right=direction*STORAGE_WIDTH, up=0)

            # next line        
            tmp_pos = self.move_on_chessboard(tmp_pos, right=-1*direction*8*STORAGE_WIDTH, up=-1*direction*STORAGE_HEIGHT)

    def camera_vector_to_robot_vector(self, camera_vector):
        R, t = estimate_transform(camera_points, robot_points)
        return list(map(float, R @ camera_vector + t)) + self.down_orientation


######################## zed camera #########################
def estimate_transform(camera_points, robot_points):
    """
    camera_points: Nx3 numpy array
    robot_points:  Nx3 numpy array

    Returns:
        R (3x3 rotation matrix)
        t (3-vector translation)
    """

    assert camera_points.shape == robot_points.shape
    assert camera_points.shape[1] == 3

    # Centroids
    centroid_cam = np.mean(camera_points, axis=0)
    centroid_robot = np.mean(robot_points, axis=0)

    # Center points
    cam_centered = camera_points - centroid_cam
    robot_centered = robot_points - centroid_robot

    # Covariance matrix
    H = cam_centered.T @ robot_centered

    # SVD
    U, S, Vt = np.linalg.svd(H)

    R = Vt.T @ U.T

    # Reflection correction
    if np.linalg.det(R) < 0:
        Vt[-1, :] *= -1
        R = Vt.T @ U.T

    t = centroid_robot - R @ centroid_cam

    return R, t

def mouse_callback(event, x, y, flags, param):
    global clicked_point

    if event == cv2.EVENT_LBUTTONDOWN:
            clicked_point = (x, y)

# Returns base, head
def get_base_and_head_camera_points() -> tuple[Vector, Vector]:
    global clicked_point, point_cloud
    base_point = None
    head_point = None

    # Create camera
    zed = sl.Camera()
    init_params = sl.InitParameters()
    init_params.depth_mode = sl.DEPTH_MODE.ULTRA
    init_params.coordinate_units = sl.UNIT.METER
    init_params.camera_resolution = sl.RESOLUTION.HD2K

    if zed.open(init_params) != sl.ERROR_CODE.SUCCESS:
        print("Failed to open ZED")
        return

    image = sl.Mat()
    runtime_params = sl.RuntimeParameters()
    cv2.namedWindow("ZED")
    cv2.setMouseCallback("ZED", mouse_callback)

    while head_point==None:
        if zed.grab(runtime_params) == sl.ERROR_CODE.SUCCESS:
            # Left image
            zed.retrieve_image(image, sl.VIEW.LEFT)
            # Point cloud
            zed.retrieve_measure(
                point_cloud,
                sl.MEASURE.XYZ
            )
            frame = image.get_data()
            if clicked_point is not None:
                x, y = clicked_point
                err, point3d = point_cloud.get_value(x, y)
                if err == sl.ERROR_CODE.SUCCESS:
                    X_, Y_, Z_ = point3d[:3]
                    if np.isfinite(X_) and np.isfinite(Y_) and np.isfinite(Z_):
                        print(f"Pixel ({x}, {y})")
                        print(f"3D point: X={X_:.3f}, Y={Y_:.3f}, Z={Z_:.3f} meters")
                        if(base_point is None):
                            base_point = [X_, Y_, Z_]
                            print(f"base_point is set")
                        else:
                            head_point = [X_, Y_, Z_]
                            print(f"head_point is set")
                    else:
                        print("Invalid depth at this pixel")

                clicked_point = None
            cv2.imshow("ZED", frame)
        key = cv2.waitKey(1)

        if key == 27:  # ESC
            break

    zed.close()
    cv2.destroyAllWindows()

    return base_point, head_point

def get_12_camera_points():
    global clicked_point, point_cloud
    points = []

    zed = sl.Camera()
    init_params = sl.InitParameters()
    init_params.depth_mode = sl.DEPTH_MODE.ULTRA
    init_params.coordinate_units = sl.UNIT.METER
    init_params.camera_resolution = sl.RESOLUTION.HD2K

    if zed.open(init_params) != sl.ERROR_CODE.SUCCESS:
        print("Failed to open ZED")
        return []

    image = sl.Mat()
    runtime_params = sl.RuntimeParameters()

    cv2.namedWindow("ZED")
    cv2.setMouseCallback("ZED", mouse_callback)

    while len(points) < 12:
        if zed.grab(runtime_params) == sl.ERROR_CODE.SUCCESS:
            zed.retrieve_image(image, sl.VIEW.LEFT)
            zed.retrieve_measure(point_cloud, sl.MEASURE.XYZ)
            frame = image.get_data()

            if clicked_point is not None:
                x, y = clicked_point
                err, point3d = point_cloud.get_value(x, y)
                if err == sl.ERROR_CODE.SUCCESS:
                    X_, Y_, Z_ = point3d[:3]
                    if np.isfinite(X_) and np.isfinite(Y_) and np.isfinite(Z_):
                        points.append([float(X_), float(Y_), float(Z_)])
                        print(f"Captured point #{len(points) - 1}: X={X_:.3f}, Y={Y_:.3f}, Z={Z_:.3f} meters")
                    else:
                        print("Invalid depth at this pixel")

                clicked_point = None

            cv2.imshow("ZED", frame)

        key = cv2.waitKey(1)
        if key == 27:  # ESC
            break

    zed.close()
    cv2.destroyAllWindows()

    print("camera_points = np.array([")
    for i, point in enumerate(points):
        print(f"    [{point[0]:.17f}, {point[1]:.17f}, {point[2]:.17f}],  # {i}")
    print("])")

    return points

def get_head_camera_point():
    global clicked_point, point_cloud
    base_point = None
    head_point = None

    # Create camera
    zed = sl.Camera()
    init_params = sl.InitParameters()
    init_params.depth_mode = sl.DEPTH_MODE.ULTRA
    init_params.coordinate_units = sl.UNIT.METER
    init_params.camera_resolution = sl.RESOLUTION.HD2K

    if zed.open(init_params) != sl.ERROR_CODE.SUCCESS:
        print("Failed to open ZED")
        return

    image = sl.Mat()
    runtime_params = sl.RuntimeParameters()

    cv2.namedWindow("ZED")
    cv2.setMouseCallback("ZED", mouse_callback)

    while head_point==None:
        if zed.grab(runtime_params) == sl.ERROR_CODE.SUCCESS:
            # Left image
            zed.retrieve_image(image, sl.VIEW.LEFT)
            # Point cloud
            zed.retrieve_measure(
                point_cloud,
                sl.MEASURE.XYZ
            )
            frame = image.get_data()
            if clicked_point is not None:
                x, y = clicked_point
                err, point3d = point_cloud.get_value(x, y)
                if err == sl.ERROR_CODE.SUCCESS:
                    X_, Y_, Z_ = point3d[:3]
                    if np.isfinite(X_) and np.isfinite(Y_) and np.isfinite(Z_):
                       head_point = [X_, Y_, Z_] 
                    else:
                        print("Invalid depth at this pixel")

                clicked_point = None
            cv2.imshow("ZED", frame)
        key = cv2.waitKey(1)

        if key == 27:  # ESC
            break

    zed.close()
    cv2.destroyAllWindows()

    R, t = estimate_transform(camera_points, robot_points)
    head_robot = R @ head_point + t

    return head_robot.tolist()
      
        
if __name__ == "__main__":
    if len(sys.argv) > 1:
        command = sys.argv[1].lower()

        if command == "reset":
            reset_gripper()
        elif command == "start":
            move_to_start_position()
        elif command == "print":
            print_position()
        elif command == "close":
            grip_close()
        elif command == "open":
            grip_open()
        elif command == "align":
            align_position()
        elif command == "grip":
            get_grip()
        elif command == "joints":
            print_joints()
   