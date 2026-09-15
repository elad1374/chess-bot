import glob
import os

input_dir = "/home/checkmate/Downloads/data_set_board/labels/train"
output_dir = "/home/checkmate/Downloads/data_set_board/labels/train_binary"

os.makedirs(output_dir, exist_ok=True)

for txt_file in glob.glob(os.path.join(input_dir, "*.txt")):
    filename = os.path.basename(txt_file)
    output_file = os.path.join(output_dir, filename)

    with open(txt_file, "r") as fin, open(output_file, "w") as fout:
        for line in fin:
            parts = line.strip().split()

            if not parts:
                continue

            cls = int(parts[0])

            if 0 <= cls <= 5:
                parts[0] = "0"
            elif 6 <= cls <= 11:
                parts[0] = "1"
            else:
                print(f"Warning: unexpected class {cls} in {filename}")
                continue

            fout.write(" ".join(parts) + "\n")

print("Finished converting labels.")