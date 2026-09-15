import cv2
from common.utils import repo_path

def plot_detections(image_path, coord_file_path):
    """
    Reads an image and coordinate file, plots colored dots on the image,
    and displays it in a window without saving.
    """
    img = cv2.imread(image_path)
    if img is None:
        print(f"Error: Could not load image from '{image_path}'")
        return

    # Color definitions in BGR format
    # White pieces: White filled circle with a Black border
    # Black pieces: Red filled circle with a White border (for high visibility)
    with open(coord_file_path, "r") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue

            parts = line.split()
            if len(parts) < 3:
                continue

            label = parts[0].lower()
            x = int(float(parts[1]))
            y = int(float(parts[2]))

            if label == "white":
                cv2.circle(img, (x, y), 7, (255, 255, 255), -1)  # White fill
                cv2.circle(img, (x, y), 7, (0, 0, 0), 2)        # Black outline
            elif label == "black":
                cv2.circle(img, (x, y), 7, (0, 0, 255), -1)      # Red fill
                cv2.circle(img, (x, y), 7, (255, 255, 255), 2)  # White outline

    # Display image in pop-up window
    cv2.imshow("Piece Detections", img)
    print("Press any key in the image window to close it.")
    cv2.waitKey(0)
    cv2.destroyAllWindows()


# --- USAGE ---
if __name__ == "__main__":
    plot_detections(repo_path("src/perception/yolo/photos_game/00_20260817_220907_300.png"), repo_path("src/perception/yolo/predictions_game/00_20260817_220907_300.txt"))