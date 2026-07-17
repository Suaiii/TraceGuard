"""Generate bbox overlay images for case evidence figures.

One-shot batch script: runs TamperDetector on all 12 case images (3 cases × 4 platforms)
and saves the bbox_image (original + red bounding boxes) for use in case figures.

Usage:
    python experiments/socialmedia/generate_bbox_overlays.py
"""

import os
import sys
from pathlib import Path

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from detection.inference_api import Detector
from explanation.localization import TamperDetector


CASE_IMAGES_DIR = Path("data/case_images")
OUTPUT_DIR = Path("data/case_images/bbox")

# All 12 images defined in case_manifest_extended.csv
IMAGES = [
    # stable
    ("stable", "original", "stable_original.png"),
    ("stable", "facebook", "stable_facebook.jpg"),
    ("stable", "wechat", "stable_wechat.jpg"),
    ("stable", "weibo", "stable_weibo.jpg"),
    # degraded
    ("degraded", "original", "degraded_original.png"),
    ("degraded", "facebook", "degraded_facebook.jpg"),
    ("degraded", "wechat", "degraded_wechat.jpg"),
    ("degraded", "weibo", "degraded_weibo.jpg"),
    # conflict
    ("conflict", "original", "conflict_original.png"),
    ("conflict", "facebook", "conflict_facebook.jpg"),
    ("conflict", "wechat", "conflict_wechat.jpg"),
    ("conflict", "weibo", "conflict_weibo.jpg"),
]


def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    print("Loading detector...")
    detector = Detector(checkpoint_path="checkpoints/best.pth", device="cuda")

    print("Initializing TamperDetector...")
    localizer = TamperDetector(detector)

    for role, variant, filename in IMAGES:
        input_path = CASE_IMAGES_DIR / filename
        if not input_path.exists():
            print(f"  SKIP (missing): {input_path}")
            continue

        out_name = f"{role}_{variant}_bbox.png"
        out_path = OUTPUT_DIR / out_name

        if out_path.exists():
            print(f"  SKIP (exists): {out_path}")
            continue

        print(f"  Processing: {filename} → {out_name}")
        result = localizer.detect(str(input_path))
        bbox_img = result["bbox_image"]
        bbox_img.save(str(out_path))
        print(f"    bboxes: {len(result['bbox_list'])}, elapsed: {result['elapsed_ms']:.0f}ms")

    print(f"Done. Outputs in {OUTPUT_DIR}/")


if __name__ == "__main__":
    main()
