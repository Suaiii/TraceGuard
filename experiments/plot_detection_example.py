"""Generate a compact implementation example from real pipeline outputs."""

import argparse
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from PIL import Image


plt.rcParams["font.family"] = "sans-serif"
plt.rcParams["font.sans-serif"] = ["Microsoft YaHei", "Noto Sans SC", "Arial", "DejaVu Sans"]
plt.rcParams["svg.fonttype"] = "none"
plt.rcParams["pdf.fonttype"] = 42
plt.rcParams["font.size"] = 7


def _save(fig, output_base):
    output_base = Path(output_base)
    output_base.parent.mkdir(parents=True, exist_ok=True)
    paths = []
    for extension, kwargs in (
        ("svg", {}),
        ("pdf", {}),
        ("png", {"dpi": 300}),
        ("tiff", {"dpi": 600}),
    ):
        path = output_base.with_suffix(f".{extension}")
        fig.savefig(path, bbox_inches="tight", facecolor="white", **kwargs)
        if extension == "svg":
            svg = path.read_text(encoding="utf-8")
            path.write_text("\n".join(line.rstrip() for line in svg.splitlines()) + "\n", encoding="utf-8")
        paths.append(path)
    plt.close(fig)
    return paths


def generate_detection_example(original, overlay, bbox, output_base):
    """Render original, Grad-CAM overlay, and localization evidence side by side."""
    sources = [original, overlay, bbox]
    labels = ["Original", "Grad-CAM overlay", "Suspicious regions"]
    fig, axes = plt.subplots(1, 3, figsize=(6.3, 2.25))
    for index, (ax, source, label) in enumerate(zip(axes, sources, labels)):
        with Image.open(source) as image:
            ax.imshow(image.convert("RGB"))
        ax.set_xticks([])
        ax.set_yticks([])
        for spine in ax.spines.values():
            spine.set_color("#A8A8A8")
            spine.set_linewidth(0.6)
        ax.text(
            -0.04,
            1.02,
            chr(ord("a") + index),
            transform=ax.transAxes,
            ha="left",
            va="bottom",
            fontsize=8,
            fontweight="bold",
        )
        ax.text(0.5, -0.06, label, transform=ax.transAxes, ha="center", va="top", fontsize=7)
    fig.subplots_adjust(left=0.02, right=0.99, bottom=0.12, top=0.98, wspace=0.09)
    return _save(fig, output_base)


def main():
    parser = argparse.ArgumentParser(description="Plot a TraceGuard detection example")
    parser.add_argument("--original", required=True)
    parser.add_argument("--overlay", required=True)
    parser.add_argument("--bbox", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    for path in generate_detection_example(args.original, args.overlay, args.bbox, args.output):
        print(path)


if __name__ == "__main__":
    main()
