#!/usr/bin/env python3
"""Render the NanoTrack V3 profile CSV as a compact SVG and guide table."""
import argparse
import csv
import tempfile
from pathlib import Path


START = "<!-- profile-results:start -->"
END = "<!-- profile-results:end -->"


def read_rows(path):
    with Path(path).open(newline="") as source:
        rows = list(csv.DictReader(source))
    required = {"profile", "median_fps", "mean_iou", "min_iou", "matched_frames", "timestamp_utc"}
    if not rows or set(rows[0]) != required:
        raise ValueError(f"{path} must contain {', '.join(sorted(required))}")
    for row in rows:
        for field in ("median_fps", "mean_iou", "min_iou"):
            row[field] = float(row[field])
        row["matched_frames"] = int(row["matched_frames"])
    return rows


def svg(rows):
    labels = [row["profile"] for row in rows]
    fps_max = max(row["median_fps"] for row in rows) * 1.1
    bars, texts = [], []
    for index, row in enumerate(rows):
        x = 70 + index * 105
        height = round(row["median_fps"] / fps_max * 210)
        bars.append(f'<rect x="{x}" y="{270-height}" width="54" height="{height}" fill="#2878b5"/>')
        texts.append(f'<text x="{x+27}" y="290" text-anchor="middle">{labels[index]}</text><text x="{x+27}" y="{262-height}" text-anchor="middle">{row["median_fps"]:.2f}</text>')
    quality = []
    for index, row in enumerate(rows):
        x = 455 + index * 105
        for offset, value, color in ((0, row["mean_iou"], "#3b9d5d"), (28, row["min_iou"], "#dd8b2e")):
            height = round(value * 210)
            quality.append(f'<rect x="{x+offset}" y="{270-height}" width="24" height="{height}" fill="{color}"/><text x="{x+offset+12}" y="{262-height}" text-anchor="middle">{value:.3f}</text>')
        quality.append(f'<text x="{x+26}" y="290" text-anchor="middle">{labels[index]}</text>')
    return """<svg xmlns="http://www.w3.org/2000/svg" width="800" height="330" viewBox="0 0 800 330">
<style>text{font:12px sans-serif;fill:#20242a}.title{font-weight:bold;font-size:16px}.axis{stroke:#69727d}</style>
<rect width="800" height="330" fill="white"/><text class="title" x="70" y="28">Tracker-only FPS (median, runs 2–5)</text><text class="title" x="455" y="28">Tracking IoU</text>
<line class="axis" x1="55" y1="270" x2="410" y2="270"/><line class="axis" x1="440" y1="270" x2="795" y2="270"/>
""" + "".join(bars + texts + quality) + """<rect x="455" y="305" width="12" height="12" fill="#3b9d5d"/><text x="472" y="316">mean IoU</text><rect x="555" y="305" width="12" height="12" fill="#dd8b2e"/><text x="572" y="316">minimum IoU</text></svg>\n"""


def table(rows):
    lines = [START, "| Profile | Median FPS | Mean IoU | Minimum IoU | Matched frames |", "| --- | ---: | ---: | ---: | ---: |"]
    lines += [f"| `{r['profile']}` | {r['median_fps']:.2f} | {r['mean_iou']:.4f} | {r['min_iou']:.4f} | {r['matched_frames']} |" for r in rows]
    lines += ["", "![NanoTrack V3 profile comparison](images/nanotracker-v3-profile-comparison.svg)", END]
    return "\n".join(lines)


def update_guide(path, content):
    guide = Path(path)
    text = guide.read_text()
    start, end = text.index(START), text.index(END) + len(END)
    guide.write_text(text[:start] + content + text[end:])


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("csv")
    parser.add_argument("--svg", required=True)
    parser.add_argument("--guide", required=True)
    parser.add_argument("--self-check", action="store_true")
    args = parser.parse_args()
    if args.self_check:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "results.csv"
            source.write_text("profile,median_fps,mean_iou,min_iou,matched_frames,timestamp_utc\nmixed,50,0.9,0.8,500,2026-01-01T00:00:00Z\n")
            guide = root / "guide.md"
            guide.write_text(START + "\nold\n" + END)
            rows = read_rows(source)
            (root / "chart.svg").write_text(svg(rows))
            update_guide(guide, table(rows))
            assert "mixed" in (root / "chart.svg").read_text()
            assert "50.00" in guide.read_text()
        return
    rows = read_rows(args.csv)
    Path(args.svg).write_text(svg(rows))
    update_guide(args.guide, table(rows))


if __name__ == "__main__":
    main()
