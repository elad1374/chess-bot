import pyzed.sl as sl
import numpy as np
import cv2

def main():

    zed = sl.Camera()

    init_params = sl.InitParameters()
    init_params.depth_mode = sl.DEPTH_MODE.ULTRA
    init_params.coordinate_units = sl.UNIT.MILLIMETER
    init_params.camera_resolution = sl.RESOLUTION.HD2K

    if zed.open(init_params) != sl.ERROR_CODE.SUCCESS:
        print("Failed to open camera")
        return

    brightness = 8  # Usually 0-8

    zed.set_camera_settings(
        sl.VIDEO_SETTINGS.BRIGHTNESS,
        brightness
    )

    runtime = sl.RuntimeParameters()

    image = sl.Mat()
    depth = sl.Mat()

    print("LIVE: press Q to quit")

    while True:

        if zed.grab(runtime) == sl.ERROR_CODE.SUCCESS:

            # ---------- RGB IMAGE ----------
            zed.retrieve_image(image, sl.VIEW.LEFT)
            img = image.get_data()
            img = cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)

            # ---------- DEPTH MAP (FAST + FULL RESOLUTION) ----------
            zed.retrieve_measure(depth, sl.MEASURE.DEPTH)
            depth_map = depth.get_data()

            # replace invalid values (important!)
            depth_map = np.nan_to_num(depth_map, nan=0.0, posinf=0.0, neginf=0.0)

            # normalize for display
            depth_vis = cv2.normalize(depth_map, None, 0, 255, cv2.NORM_MINMAX)
            depth_vis = depth_vis.astype(np.uint8)

            # optional: improve contrast visually
            depth_vis = cv2.applyColorMap(depth_vis, cv2.COLORMAP_JET)

            cv2.imshow("RGB", img)
            cv2.imshow("Depth", depth_vis)

        key = cv2.waitKey(1) & 0xFF
        if key == ord('q'):
            break

    zed.close()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    main()