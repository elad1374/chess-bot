try:
    import pyzed.sl as sl
except ImportError:
    sl = None
import cv2
import os
from math import hypot
from datetime import datetime
import numpy as np
from common.typing import Vector

# Folder where images will be saved (inside project)
SAVE_DIR = "zed_setting_images_2"


class Camera:
    def __init__(self, brightness: int = None):
        self.zed = sl.Camera()
        self.init_params = sl.InitParameters()
        self.init_params.camera_resolution = sl.RESOLUTION.HD2K
        self.init_params.depth_mode = sl.DEPTH_MODE.ULTRA
        self.init_params.coordinate_units = sl.UNIT.METER
        self.init_params.camera_fps = 15
        self.brightness = brightness #0-8
        self.clicked_point = None

    def mouse_callback(self, event, x, y, flags, param):
        if event == cv2.EVENT_LBUTTONDOWN:
            self.clicked_point = (x, y)
            print(f"Clicked point: {self.clicked_point}")
        
    def _take_photo(self, image_mat):
        """
        Private method, ZED takes the actual photo
        """
        if self.zed.grab() != sl.ERROR_CODE.SUCCESS:
            raise RuntimeError("Failed to grab image from ZED camera.")

        self.zed.retrieve_image(image_mat, sl.VIEW.LEFT)

        # Convert BGRA -> BGR
        frame = image_mat.get_data()    
        frame = cv2.cvtColor(frame, cv2.COLOR_BGRA2BGR)
        return frame

    def _save_photo(self, output_dir:str, frame) -> str:
        """
        Private method, Saves photo at the specified dir
        """
        piece_type = "00"
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:-3]
        image_path = os.path.join(output_dir, f"{piece_type}_{timestamp}.png")

        if not cv2.imwrite(image_path, frame):
            raise RuntimeError(f"Failed to save image to {image_path}")
        print(f"Saved {image_path}")

        return os.path.abspath(image_path)

    def _crop_frame(
    self,
    frame,
    x: int,
    y: int,
    width: int,
    height: int,
    ):
        """
        Private method. Returns a cropped copy of the frame.
        """

        img_h, img_w = frame.shape[:2]

        x = max(0, min(x, img_w - 1))
        y = max(0, min(y, img_h - 1))
        width = min(width, img_w - x)
        height = min(height, img_h - y)

        return frame[y:y + height, x:x + width].copy()

    def take_photo(self, output_dir: str) -> str:
        """
        Takes a single photo with the ZED camera, saves it in output_dir,
        and returns the full path to the saved image.
        """
        os.makedirs(output_dir, exist_ok=True)

        image_mat = sl.Mat()

        frame = self._take_photo(image_mat)
        file_path = self._save_photo(output_dir, frame)
        return file_path



    
    def shoot_many(self, output_dir):
        os.makedirs(output_dir, exist_ok=True)

        image_mat = sl.Mat()

        print("Press ENTER to save an image.")
        print("Press 'q' to quit.")


        while True:
            frame = self._take_photo(image_mat)

            cv2.imshow("ZED Camera", frame)

            key = cv2.waitKey(1) & 0xFF

            # ENTER saves image
            if key == 13:
                self._save_photo(output_dir, frame)

            # q quits
            elif key == ord('q'):
                break

    def capture_and_crop(
        self,
        output_path: str,
        x: int,
        y: int,
        width: int,
        height: int,
    ) -> bool:
        """
        Shows a live preview.
        Press ENTER to save the cropped image.
        Press q to quit without saving.
        """
        cropped_path = output_path + "_cropped"
        os.makedirs(output_path, exist_ok=True)
        os.makedirs(cropped_path, exist_ok=True)

        image_mat = sl.Mat()

        print("Press ENTER to save the cropped image.")
        print("Press 'q' to quit.")

        while True:
            frame = self._take_photo(image_mat)

            cv2.imshow("ZED Camera", frame)

            key = cv2.waitKey(1) & 0xFF

            if key == 13:
                img_h, img_w = frame.shape[:2]

                x0 = max(0, min(x, img_w - 1))
                y0 = max(0, min(y, img_h - 1))
                w = min(width, img_w - x0)
                h = min(height, img_h - y0)

                cropped = frame[y0:y0 + h, x0:x0 + w]

                #self._save_photo(output_path, frame)
                self._save_photo(cropped_path, cropped)

            elif key == ord("q"):
                return False

    def get_two_points(self):
        point_cloud = sl.Mat()
        base_point = None
        head_point = None

        image = sl.Mat()
        runtime_params = sl.RuntimeParameters()
        cv2.namedWindow("ZED")
        cv2.setMouseCallback("ZED", self.mouse_callback)

        while head_point==None:
            if self.zed.grab(runtime_params) == sl.ERROR_CODE.SUCCESS:
                # Left image
                self.zed.retrieve_image(image, sl.VIEW.LEFT)
                # Point cloud
                self.zed.retrieve_measure(
                    point_cloud,
                    sl.MEASURE.XYZ
                )
                frame = image.get_data()
                if self.clicked_point is not None:
                    x, y = self.clicked_point
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

                    self.clicked_point = None
                cv2.imshow("ZED", frame)
            key = cv2.waitKey(1)

            if key == 27:  # ESC
                break
        return  head_point, base_point

    def last_image_get_xyz(self, x: float, y: float) -> Vector:
        """
        In the last image captured, try to find the 3D point corresponding to (x, y).
        Failing that, try to find the nearest point (x+dx, y+dy) that can be converted to a 3D point
        (with |dx| <= 5, |dy| <= 5).
        Failing that too, raise an error.
        """

        point_cloud = sl.Mat()
        err = self.zed.retrieve_measure(
            point_cloud,
            sl.MEASURE.XYZ
        )
        if err != sl.ERROR_CODE.SUCCESS:
            raise Exception("failed to retrieve point cloud")

        max_d = 5
        nearby_points = [
            (x + dx, y + dy)
            for dx in range(-max_d, max_d + 1)
            for dy in range(-max_d, max_d + 1)
        ]
        nearby_points.sort(key=lambda p: hypot(p[0] - x, p[1] - y))

        for (nearby_x, nearby_y) in nearby_points:
            err, point3d = point_cloud.get_value(nearby_x, nearby_y)
            if err != sl.ERROR_CODE.SUCCESS:
                raise Exception("Failed to get 3D point")

            point3d = tuple(point3d[:3])
            if all(np.isfinite(coord) for coord in point3d):
                print((x, y), (nearby_x, nearby_y), point3d)
                return point3d

        raise Exception(f"Invalid depth at pixel ({x}, {y})")

    def __enter__(self):
        status = self.zed.open(self.init_params)
        if status != sl.ERROR_CODE.SUCCESS:
            raise Exception(f"Failed to open camera: {status}")
        
        if self.brightness is not None:
            self.zed.set_camera_settings(sl.VIDEO_SETTINGS.BRIGHTNESS, self.brightness)

        # Let auto exposure stabilize
        for _ in range(30):
            self.zed.grab()

        return self
    
    def __exit__(self, *_):
        cv2.destroyAllWindows()
        self.zed.close()
