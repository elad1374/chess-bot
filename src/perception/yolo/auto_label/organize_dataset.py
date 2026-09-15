import os
import sys
import shutil

def organize_dataset(target_dir):
    # Define classes in the exact order requested
    classes = [
        "black-bishop", "black-king", "black-knight", 
        "black-pawn", "black-queen", "black-rook",
        "white-bishop", "white-king", "white-knight", 
        "white-pawn", "white-queen", "white-rook"
    ]
    
    # Filter for standard image extensions to ignore hidden OS files
    valid_exts = ('.png', '.jpg', '.jpeg', '.bmp', '.tiff')
    
    # Retrieve all valid files and sort them alphanumerically
    files = [
        f for f in os.listdir(target_dir) 
        if os.path.isfile(os.path.join(target_dir, f)) and f.lower().endswith(valid_exts)
    ]
    files.sort()
    
    # Validate the strict 600 image constraint
    if len(files) != 600:
        print(f"Error: Expected exactly 600 image files, but found {len(files)}.")
        sys.exit(1)
        
    print(f"Found 600 images. Beginning sorting process...")
        
    # Iterate through the 12 classes and move files in batches of 50
    for i, class_name in enumerate(classes):
        class_dir = os.path.join(target_dir, class_name)
        
        # Create the subdirectory if it does not already exist
        os.makedirs(class_dir, exist_ok=True)
        
        # Calculate start and end indices for the current batch of 50
        start_idx = i * 50
        end_idx = start_idx + 50
        batch = files[start_idx:end_idx]
        
        # Move the files from the root directory to the class subdirectory
        for file_name in batch:
            src = os.path.join(target_dir, file_name)
            dst = os.path.join(class_dir, file_name)
            shutil.move(src, dst)
            
        print(f"[{i+1}/12] Moved 50 images to {class_name}/")
            
    print("Dataset organization complete. Directory is ready for PyTorch ImageFolder.")

if __name__ == "__main__":
    # Validate command-line arguments
    if len(sys.argv) != 2:
        print("Usage: python organize_dataset.py <directory_path>")
        sys.exit(1)
        
    target_directory = sys.argv[1]
    
    if not os.path.isdir(target_directory):
        print(f"Error: Directory '{target_directory}' does not exist.")
        sys.exit(1)
        
    organize_dataset(target_directory)