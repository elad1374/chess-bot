#!/usr/bin/env python3

# Usage: python3 daniel_autolink.py <input_file.json> <output_file.json>
#
# Automatically adds the missing relations between rectangles and points (head and base) in the JSON.
# Prints a warning if it can't infer some relations automatically.
#
# I'm not 100% sure this script works - if you use it, please import the resulting JSON back to label studio and verify.
# - Daniel

from sys import argv
import json
from itertools import chain

in_file, out_file = argv[1:3]
with open(in_file) as f:
    data = json.load(f)

for record in data:
    annotations = record["annotations"]
    for annotation in annotations:
        result = annotation["result"]

        id_dict = {
            x["id"]: x
            for x in result
            if "id" in x
        }

        heads = {}
        bases = {}
        rect_parts = {"Head": heads, "Base": bases}
        unlinked = {}

        keypoints = {item["id"]: item for item in result if item["type"] == "keypointlabels"}
        rectangles = {item["id"]: item for item in result if item["type"] == "rectanglelabels"}
        relations = [item for item in result if item["type"] == "relation"]

        for rel in relations:
            f = id_dict[rel["from_id"]]
            t = id_dict[rel["to_id"]]
            assert {f["type"], t["type"]} == {"keypointlabels", "rectanglelabels"}
            keypoint, rectangle = sorted([f, t], key=lambda x: x["type"])
            (label,) = keypoint["value"]["keypointlabels"]
            rect_parts[label][rectangle["id"]] = keypoint["id"]

        unlinked = {
            id
            for id in keypoints
            if id not in heads.values()
            and id not in bases.values()
        }

        should_repeat = True
        while should_repeat:
            should_repeat = False
            for id in unlinked.copy():
                kp = keypoints[id]
                (label,) = kp["value"]["keypointlabels"]
                x = kp["value"]["x"]
                y = kp["value"]["y"]
                inside = {
                    rect_id
                    for rect_id, rect in rectangles.items()
                    if rect_id not in rect_parts[label]
                    if (
                        x1 := rect["value"]["x"],
                        y1 := rect["value"]["y"],
                        w1 := rect["value"]["width"],
                        h1 := rect["value"]["height"],
                    )
                    if x1 <= x <= x1 + w1
                    if y1 <= y <= y1 + h1
                }
                if len(inside) == 1:
                    (rect_id,) = inside
                    rect_parts[label][rect_id] = id
                    unlinked.remove(id)
                    should_repeat = True

        if len(unlinked) != 0:
            print(f'''Warning: {len(unlinked)} ambiguous relations in {record["data"]["image"]} - couldn't infer automatically''')

        relations_needed = [
            {
                "from_id": point_id,
                "to_id": rect_id,
                "type": "relation",
                "direction": "right",
            }
            for rect_id, point_id in chain(heads.items(), bases.items())
        ]
        for rel in relations:
            relations_needed.remove(rel)
        result += relations_needed

with open(out_file, "w") as f:
    json.dump(data, f)