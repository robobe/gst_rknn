#!/usr/bin/env python3
"""Download a reproducible, labeled COCO 2017 train or validation subset."""

import argparse
import json
import random
import shutil
import tempfile
import zipfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from time import sleep
from urllib.request import urlopen, urlretrieve


ROOT = Path(__file__).resolve().parents[1]
ANNOTATIONS = "http://images.cocodataset.org/annotations/annotations_trainval2017.zip"
COUNT, SEED = 200, 20260912


def download(output, image):
    target = output / "images" / image["file_name"]
    if target.exists(): return
    for attempt in range(3):
        try:
            urlretrieve(image["coco_url"], target)
            return
        except OSError:
            target.unlink(missing_ok=True)
            if attempt == 2: raise
            sleep(attempt + 1)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--split", choices=("train", "val"), default="val")
    parser.add_argument("--count", type=int, default=COUNT)
    parser.add_argument("--seed", type=int, default=SEED)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    output = args.output or ROOT / "assets" / f"coco_{args.split}_sample"
    annotation_name = f"instances_{args.split}2017.json"
    output.joinpath("images").mkdir(parents=True, exist_ok=True)
    print(f"reading {ANNOTATIONS}")
    with tempfile.NamedTemporaryFile() as archive:
        with urlopen(ANNOTATIONS) as response: shutil.copyfileobj(response, archive)
        with zipfile.ZipFile(archive).open(f"annotations/{annotation_name}") as source: data = json.load(source)
    ids = sorted({item["image_id"] for item in data["annotations"] if not item.get("iscrowd", 0)})
    if args.count > len(ids): parser.error(f"count {args.count} exceeds {len(ids)} labeled images")
    selected_ids = set(random.Random(args.seed).sample(ids, args.count))
    images = [item for item in data["images"] if item["id"] in selected_ids]
    subset = {"info": {"description": f"COCO {args.split}2017 sample, seed {args.seed}"}, "licenses": data["licenses"],
              "images": images, "annotations": [item for item in data["annotations"] if item["image_id"] in selected_ids],
              "categories": data["categories"]}
    (output / "annotations.json").write_text(json.dumps(subset))
    with ThreadPoolExecutor(max_workers=8) as pool:
        list(pool.map(lambda image: download(output, image), images))
    (output / "calibration.txt").write_text("\n".join(str((output / "images" / image["file_name"]).resolve()) for image in images) + "\n")
    print(f"downloaded {len(images)} images to {output}")


if __name__ == "__main__": main()
