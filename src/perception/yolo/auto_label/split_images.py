import os
import shutil
import random
from pathlib import Path

def split_dataset(
    dataset_dir: str, 
    train_ratio: float = 0.8, 
    seed: int = 42, 
    move_files: bool = False
):
    """
    Splits a dataset with matching images and labels into train and val sets.

    :param dataset_dir: Path to directory containing 'images' and 'labels' folders.
    :param train_ratio: Fraction of data for training (default 0.8 for 80/20 split).
    :param seed: Random seed for reproducible shuffling.
    :param move_files: If True, moves files. If False, copies files (safer).
    """
    dataset_path = Path(dataset_dir)
    images_dir = dataset_path / "images"
    labels_dir = dataset_path / "labels"

    if not images_dir.exists() or not labels_dir.exists():
        raise FileNotFoundError(
            f"Expected directory structure not found! Ensure '{dataset_dir}' "
            f"contains both 'images' and 'labels' folders."
        )

    # Allowed image formats
    valid_extensions = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}

    # Step 1: Pair images with their matching .txt label files
    pairs = []
    unmatched_images = 0

    for img_path in images_dir.iterdir():
        # Only process image files (ignores subdirectories like 'train'/'val')
        if img_path.is_file() and img_path.suffix.lower() in valid_extensions:
            stem = img_path.stem
            label_path = labels_dir / f"{stem}.txt"

            if label_path.exists():
                pairs.append((img_path, label_path))
            else:
                unmatched_images += 1
                print(f"Warning: Image '{img_path.name}' has no matching label file.")

    if not pairs:
        print("Error: No matching image-label pairs found!")
        return

    print(f"Found {len(pairs)} matching image-label pairs.")
    if unmatched_images > 0:
        print(f"Skipped {unmatched_images} unmatched image(s).\n")

    # Step 2: Shuffle pairs deterministically
    random.seed(seed)
    random.shuffle(pairs)

    # Step 3: Calculate 80/20 split index
    split_idx = int(len(pairs) * train_ratio)
    train_pairs = pairs[:split_idx]
    val_pairs = pairs[split_idx:]

    # Step 4: Create target destination subdirectories
    dirs = {
        "train_img": images_dir / "train",
        "val_img": images_dir / "val",
        "train_lbl": labels_dir / "train",
        "val_lbl": labels_dir / "val",
    }

    for target_dir in dirs.values():
        target_dir.mkdir(parents=True, exist_ok=True)

    # Step 5: Transfer files (copy or move)
    action_fn = shutil.move if move_files else shutil.copy2
    action_str = "Moving" if move_files else "Copying"

    print(f"{action_str} {len(train_pairs)} pairs to 'train' and {len(val_pairs)} pairs to 'val'...")

    for img_path, lbl_path in train_pairs:
        action_fn(img_path, dirs["train_img"] / img_path.name)
        action_fn(lbl_path, dirs["train_lbl"] / lbl_path.name)

    for img_path, lbl_path in val_pairs:
        action_fn(img_path, dirs["val_img"] / img_path.name)
        action_fn(lbl_path, dirs["val_lbl"] / lbl_path.name)

    print("\n--- Dataset Split Complete ---")
    print(f"Train set: {len(train_pairs)} items ({train_ratio*100:.0f}%)")
    print(f"Val set:   {len(val_pairs)} items ({(1-train_ratio)*100:.0f}%)")


if __name__ == "__main__":
    # Path to the directory containing 'images' and 'labels'
    DATASET_PATH = "/home/checkmate/Downloads/data_set_carton"

    split_dataset(
        dataset_dir=DATASET_PATH,
        train_ratio=0.8,   # 80% train, 20% val
        seed=42,           # Keep seed for reproducible splits
        move_files=False   # Set to True if you want to move instead of copy
    )