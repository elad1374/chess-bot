import json
import os

class LabelingQualityError(Exception):
    pass

class LabelingQualityChecker:
    def __init__(self, allow_orphans: bool = False):
        # We check for orphans and keypoint completeness per bounding box.
        self.allow_orphans = allow_orphans
        self.required_keypoints = {"head", "base"}

    def check_file(self, file_path: str):
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")

        with open(file_path, 'r', encoding='utf-8') as f:
            tasks = json.load(f)

        total_errors = 0
        report = []
        total_images = len(tasks)

        print("--- Starting Label Quality Check ---\n")

        for task_idx, task in enumerate(tasks):
            task_id = task.get("id", f"Task_{task_idx}")
            image_name = task.get("data", {}).get("image", "Unknown Image")

            image_rect_count = 0

            for ann_idx, annotation in enumerate(task.get("annotations", [])):
                errors, rect_count = self._inspect_annotation_logic(annotation, task_id, image_name)
                image_rect_count += rect_count
                if errors:
                    total_errors += len(errors)
                    report.extend(errors)

            # Print rectangle count for the current image
            print(f"Image [{image_name}]: {image_rect_count} rectangle(s) found.")

        # Print total images processed
        print(f"\nTotal images processed: {total_images}")
        print("------------------------------------\n")

        if total_errors > 0:
            error_msg = f"Found {total_errors} labeling logic error(s):\n" + "\n".join(f"- {e}" for e in report)
            raise LabelingQualityError(error_msg)
        
        print("All labeling logic checks passed successfully! No annotation errors found.")

    def _inspect_annotation_logic(self, annotation: dict, task_id, image_name) -> tuple[list, int]:
        errors = []
        results = annotation.get("result", [])

        # ---------------------------------------------------------
        # 1. Categorize Annotation Regions
        # ---------------------------------------------------------
        regions_by_id = {}
        relations = []

        for item in results:
            if item.get("type") == "relation":
                relations.append(item)
            elif "id" in item:
                regions_by_id[item["id"]] = item

        # Separate bounding boxes and keypoints for easier iteration
        bboxes = {k: v for k, v in regions_by_id.items() if v.get("type") in ["rectanglelabels", "rectangle"]}
        keypoints = {k: v for k, v in regions_by_id.items() if v.get("type") == "keypointlabels"}

        # ---------------------------------------------------------
        # 2. Map Explicit Manual Relations
        # ---------------------------------------------------------
        explicit_parents = {}
        for rel in relations:
            from_id, to_id = rel.get("from_id"), rel.get("to_id")
            
            # Check if IDs exist
            if from_id not in regions_by_id or to_id not in regions_by_id:
                errors.append(f"[{image_name}] Broken Relation: Points to a missing ID ({from_id} -> {to_id})")
                continue

            # Map the relation: Keypoint -> Bounding Box
            if from_id in keypoints and to_id in bboxes:
                explicit_parents.setdefault(from_id, set()).add(to_id)
            elif to_id in keypoints and from_id in bboxes:
                explicit_parents.setdefault(to_id, set()).add(from_id)

        # ---------------------------------------------------------
        # 3. Determine Final Ownership (The Core Logic)
        # ---------------------------------------------------------
        final_owners = {}          # Maps keypoint_id -> set of bounding_box_ids
        parent_keypoint_labels = {} # Maps bounding_box_id -> list of keypoint labels owned

        for kp_id, kp_region in keypoints.items():
            # RULE 1: Explicit manual relation overrides everything
            if kp_id in explicit_parents and explicit_parents[kp_id]:
                final_owners[kp_id] = explicit_parents[kp_id]
            else:
                # RULE 2: Spatial inclusion (Fallback)
                kp_val = kp_region.get("value", {})
                kp_x, kp_y = kp_val.get("x"), kp_val.get("y")
                
                spatial_parents = set()
                if kp_x is not None and kp_y is not None:
                    # Check every bounding box to see if the point resides inside it
                    for box_id, box_region in bboxes.items():
                        box_val = box_region.get("value", {})
                        bx = box_val.get("x", 0)
                        by = box_val.get("y", 0)
                        bw = box_val.get("width", 0)
                        bh = box_val.get("height", 0)
                        
                        # Point resides in rectangle logic
                        if bx <= kp_x <= (bx + bw) and by <= kp_y <= (by + bh):
                            spatial_parents.add(box_id)
                            
                final_owners[kp_id] = spatial_parents

            # Map the resulting owner(s) to track labels per box (normalized to lowercase)
            kp_raw_labels = kp_region.get("value", {}).get("keypointlabels", ["unknown"])
            kp_labels = [label.strip().lower() for label in kp_raw_labels]
            
            for owner_id in final_owners[kp_id]:
                parent_keypoint_labels.setdefault(owner_id, []).extend(kp_labels)

        # ---------------------------------------------------------
        # 4. Run Quality Checks on the Final Ownership Structure
        # ---------------------------------------------------------
        
        # --- A. KEYPOINT-LEVEL CHECKS ---
        for kp_id, owners in final_owners.items():
            label_str = keypoints[kp_id].get("value", {}).get("keypointlabels", ["Unknown"])[0]

            # MULTI-OWNER ERROR
            if len(owners) > 1:
                errors.append(
                    f"[{image_name}] MULTI-OWNER ERROR: Keypoint '{label_str}' (ID: {kp_id}) "
                    f"is owned by {len(owners)} bounding boxes: {list(owners)}"
                )

            # ORPHAN ERROR
            elif len(owners) == 0 and not self.allow_orphans:
                errors.append(
                    f"[{image_name}] ORPHAN ERROR: Keypoint '{label_str}' (ID: {kp_id}) "
                    f"has no manual relation and resides outside all bounding boxes."
                )

        # --- B. BOUNDING BOX-LEVEL CHECKS ---
        for box_id in bboxes.keys():
            kp_label_list = parent_keypoint_labels.get(box_id, [])

            # 1. DUPLICATE KEYPOINT CHECK
            seen = set()
            duplicates = set()
            for label in kp_label_list:
                if label in seen:
                    duplicates.add(label)
                seen.add(label)

            if duplicates:
                errors.append(
                    f"[{image_name}] DUPLICATE KEYPOINT: Bounding box '{box_id}' "
                    f"owns multiple keypoints with the exact same label(s): {list(duplicates)}"
                )

            # 2. MISSING REQUIRED KEYPOINTS CHECK (NEW)
            attached_set = set(kp_label_list)
            missing = self.required_keypoints - attached_set
            if missing:
                errors.append(
                    f"[{image_name}] INCOMPLETE BOX: Bounding box '{box_id}' "
                    f"is missing required keypoint(s): {sorted(list(missing))}"
                )

        # Return errors along with total bounding box count found
        return errors, len(bboxes)

if __name__ == "__main__":
    checker = LabelingQualityChecker()

    try:
        checker.check_file("/home/checkmate/Documents/chess-bot/ZED/zed_board_images_3/daniel_labels_2.json")
    except LabelingQualityError as e:
        print(e)