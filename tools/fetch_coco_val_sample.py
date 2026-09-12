#!/usr/bin/env python3
"""Download a reproducible, labeled 200-image COCO 2017 validation subset."""

import json
import random
import shutil
import tempfile
import zipfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from urllib.request import urlopen, urlretrieve


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "assets" / "coco_val_sample"
ANNOTATIONS = "http://images.cocodataset.org/annotations/annotations_trainval2017.zip"
COUNT, SEED = 200, 20260912


def download(image):
    target = OUTPUT / "images" / image["file_name"]
    if not target.exists(): urlretrieve(image["coco_url"], target)


def main():
    OUTPUT.joinpath("images").mkdir(parents=True, exist_ok=True)
    print(f"reading {ANNOTATIONS}")
    with tempfile.NamedTemporaryFile() as archive:
        with urlopen(ANNOTATIONS) as response: shutil.copyfileobj(response, archive)
        with zipfile.ZipFile(archive).open("annotations/instances_val2017.json") as source: data = json.load(source)
    ids = sorted({item["image_id"] for item in data["annotations"] if not item.get("iscrowd", 0)})
    selected_ids = set(random.Random(SEED).sample(ids, COUNT))
    images = [item for item in data["images"] if item["id"] in selected_ids]
    subset = {"info": {"description": f"COCO val2017 sample, seed {SEED}"}, "licenses": data["licenses"],
              "images": images, "annotations": [item for item in data["annotations"] if item["image_id"] in selected_ids],
              "categories": data["categories"]}
    (OUTPUT / "annotations.json").write_text(json.dumps(subset))
    with ThreadPoolExecutor(max_workers=8) as pool: list(pool.map(download, images))
    print(f"downloaded {len(images)} images to {OUTPUT}")


if __name__ == "__main__": main()
