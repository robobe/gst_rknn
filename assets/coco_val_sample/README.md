# COCO val2017 evaluation sample

`tools/fetch_coco_val_sample.py` creates a deterministic 200-image subset
(seed `20260912`) and COCO-format annotation file. Images, annotations, and
benchmark output are local evaluation assets and are intentionally ignored by
Git. Run `./scripts/deploy.sh assets` to copy the subset to the Radxa.
