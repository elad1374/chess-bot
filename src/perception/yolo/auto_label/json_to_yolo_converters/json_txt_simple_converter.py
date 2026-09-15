import json
import os

class ConversionError(Exception):
    pass

class LabelStudioToYOLOPoseConverter:
    def __init__(self, output_dir: str = "./yolo_pose_labels"):
        self.output_dir = output_dir

        # Class mapping: lying => 0, standing => 1
        self.class_map = {
            "lying": 0,
            "standing": 1
        }

        # Keypoint order: 1st = head, 2nd = base
        self.kp_order = ["head", "base"]

    def convert_file(self, json_path: str):
        if not os.path.exists(json_path):
            raise FileNotFoundError(f"File not found: {json_path}")

        with open(json_path, 'r', encoding='utf-8') as f:
            tasks = json.load(f)

        print(f"--- Starting YOLO Pose Conversion & Export ---\n")

        total_errors = 0
        error_report = []
        converted_tasks = []  # Stores tuple of (txt_filename, yolo_lines)

        for task_idx, task in enumerate(tasks):
            image_path = task.get("data", {}).get("image", f"img_{task_idx}.jpg")
            
            # Extract raw image filename without paths or URL parameters
            raw_image_filename = os.path.basename(image_path).split("?")[0]
            raw_name_no_ext = os.path.splitext(raw_image_filename)[0]

            # Drop hash/UUID prefix up to 'img_'
            if "img_" in raw_name_no_ext:
                clean_name = raw_name_no_ext[raw_name_no_ext.find("img_"):]
            else:
                clean_name = raw_name_no_ext

            txt_filename = f"{clean_name}.txt"

            # Strict check: Ensure target filename starts with 'img_'
            if not txt_filename.startswith("img_"):
                total_errors += 1
                error_report.append(
                    f"[{raw_image_filename}] Invalid Filename: Target filename '{txt_filename}' "
                    f"does not start with 'img_'."
                )

            task_yolo_lines = []

            for annotation in task.get("annotations", []):
                lines, errors = self._process_annotation(annotation, raw_image_filename)
                task_yolo_lines.extend(lines)
                if errors:
                    total_errors += len(errors)
                    error_report.extend(errors)

            converted_tasks.append((txt_filename, task_yolo_lines))

        # -----------------------------------------------------------
        # DECISION POINT: Raise error notice if issues were found
        # -----------------------------------------------------------
        if total_errors > 0:
            error_msg = f"Found {total_errors} conversion error(s) / validation issue(s):\n" + "\n".join(f"- {e}" for e in error_report)
            raise ConversionError(error_msg)

        # -----------------------------------------------------------
        # EXPORT PHASE: Write files ONLY if all checks pass cleanly
        # -----------------------------------------------------------
        os.makedirs(self.output_dir, exist_ok=True)
        for txt_filename, lines in converted_tasks:
            out_txt_path = os.path.join(self.output_dir, txt_filename)
            with open(out_txt_path, 'w', encoding='utf-8') as f_out:
                f_out.write("\n".join(lines))
            print(f"Exported {txt_filename} ({len(lines)} objects)")

        print(f"\nSuccessfully generated {len(converted_tasks)} YOLO Pose label file(s) in '{self.output_dir}'!")

    def _process_annotation(self, annotation: dict, image_name: str) -> tuple[list[str], list[str]]:
        errors = []
        results = annotation.get("result", [])
        regions_by_id = {}
        relations = []

        for item in results:
            if item.get("type") == "relation":
                relations.append(item)
            elif "id" in item:
                regions_by_id[item["id"]] = item

        bboxes = {k: v for k, v in regions_by_id.items() if v.get("type") in ["rectanglelabels", "rectangle"]}
        keypoints = {k: v for k, v in regions_by_id.items() if v.get("type") == "keypointlabels"}

        # Map explicit manual relations
        explicit_parents = {}
        for rel in relations:
            from_id, to_id = rel.get("from_id"), rel.get("to_id")
            if from_id in keypoints and to_id in bboxes:
                explicit_parents.setdefault(from_id, set()).add(to_id)
            elif to_id in keypoints and from_id in bboxes:
                explicit_parents.setdefault(to_id, set()).add(from_id)

        # Map box_id -> dict of keypoints { 'head': (x, y), 'base': (x, y) }
        box_keypoints = {box_id: {} for box_id in bboxes.keys()}

        for kp_id, kp_region in keypoints.items():
            kp_val = kp_region.get("value", {})
            kp_x, kp_y = kp_val.get("x"), kp_val.get("y")
            kp_labels = kp_val.get("keypointlabels", [])
            kp_name = kp_labels[0].strip().lower() if kp_labels else "unknown"

            if kp_x is None or kp_y is None:
                continue

            # Determine parent box(es)
            if kp_id in explicit_parents and explicit_parents[kp_id]:
                parents = explicit_parents[kp_id]
            else:
                # Spatial inclusion fallback
                parents = set()
                for box_id, box_region in bboxes.items():
                    box_val = box_region.get("value", {})
                    bx, by = box_val.get("x", 0), box_val.get("y", 0)
                    bw, bh = box_val.get("width", 0), box_val.get("height", 0)
                    if bx <= kp_x <= (bx + bw) and by <= kp_y <= (by + bh):
                        parents.add(box_id)

            for parent_id in parents:
                if parent_id in box_keypoints:
                    box_keypoints[parent_id][kp_name] = (kp_x, kp_y)

        # Build YOLO lines and validate completeness
        yolo_lines = []
        for box_id, box_region in bboxes.items():
            box_val = box_region.get("value", {})

            # 1. Determine & Validate Class ID
            class_labels = box_val.get("rectanglelabels", [])
            class_name = class_labels[0].strip().lower() if class_labels else ""
            
            if class_name not in self.class_map:
                errors.append(f"[{image_name}] Bounding box '{box_id}' has unrecognized class '{class_name}'. Expected 'lying' or 'standing'.")
                class_id = 0
            else:
                class_id = self.class_map[class_name]

            # 2. Compute normalized bounding box (x_center, y_center, width, height)
            bx, by = box_val.get("x", 0), box_val.get("y", 0)
            bw, bh = box_val.get("width", 0), box_val.get("height", 0)

            x_center = (bx + (bw / 2.0)) / 100.0
            y_center = (by + (bh / 2.0)) / 100.0
            w_norm = bw / 100.0
            h_norm = bh / 100.0

            # 3. Format keypoints (head first, then base)
            kp_tokens = []
            attached_kps = box_keypoints.get(box_id, {})

            for kp_type in self.kp_order:  # ['head', 'base']
                if kp_type in attached_kps:
                    kx, ky = attached_kps[kp_type]
                    kp_tokens.extend([f"{kx / 100.0:.6f}", f"{ky / 100.0:.6f}", "2"])
                else:
                    errors.append(f"[{image_name}] Bounding box '{box_id}' ({class_name}) is missing required keypoint '{kp_type}'.")

            line = f"{class_id} {x_center:.6f} {y_center:.6f} {w_norm:.6f} {h_norm:.6f} " + " ".join(kp_tokens)
            yolo_lines.append(line)

        return yolo_lines, errors

if __name__ == "__main__":
    converter = LabelStudioToYOLOPoseConverter(output_dir="/home/checkmate/Downloads/data_set_carton/labels")
    
    try:
        converter.convert_file("/home/checkmate/Documents/chess-bot/ZED/zed_board_images_3/daniel_labels_2.json")
    except ConversionError as e:
        print(e)