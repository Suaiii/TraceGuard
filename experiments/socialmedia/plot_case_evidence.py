"""Generate a report-grade case plate from measured pipeline evidence."""

import argparse
import csv
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from PIL import Image


plt.rcParams["font.family"] = "sans-serif"
plt.rcParams["font.sans-serif"] = ["Arial", "DejaVu Sans", "Liberation Sans"]
plt.rcParams["svg.fonttype"] = "none"
plt.rcParams["pdf.fonttype"] = 42
plt.rcParams["font.size"] = 7


ROLES = ["stable", "degraded", "conflict"]
VARIANTS = ["original", "facebook"]
ROLE_LABELS = {
    "stable": "Stable",
    "degraded": "Degraded",
    "conflict": "Conflict",
}
VARIANT_LABELS = {"original": "Original", "facebook": "Facebook"}


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
            path.write_text(
                "\n".join(line.rstrip() for line in svg.splitlines()) + "\n",
                encoding="utf-8",
            )
        paths.append(path)
    plt.close(fig)
    return paths


def generate_case_figure(rows, output_base):
    """Render Original/Facebook evidence for stable, degraded, and conflict cases."""
    lookup = {(row["role"], row["variant"]): row for row in rows}
    missing = [
        (role, variant)
        for role in ROLES
        for variant in VARIANTS
        if (role, variant) not in lookup
    ]
    if missing:
        raise ValueError(f"missing case evidence rows: {missing}")

    fig, axes = plt.subplots(3, 2, figsize=(6.3, 6.6))
    for row_index, role in enumerate(ROLES):
        for column_index, variant in enumerate(VARIANTS):
            ax = axes[row_index, column_index]
            record = lookup[(role, variant)]
            with Image.open(record["image_path"]) as image:
                ax.imshow(image.convert("RGB"))
            ax.set_xticks([])
            ax.set_yticks([])
            for spine in ax.spines.values():
                spine.set_color("#B8B8B8")
                spine.set_linewidth(0.6)
            label = record.get("label", "")
            probability = float(record["fake_prob"])
            evidence = record.get("tamper_type", "")
            annotation = f"label={label} | fake probability={probability:.3f}"
            if role == "conflict":
                annotation += f"\nlocal evidence={evidence}"
            ax.text(0.5, -0.055, annotation, transform=ax.transAxes, ha="center", va="top")
            if row_index == 0:
                ax.text(
                    0.5,
                    1.025,
                    VARIANT_LABELS[variant],
                    transform=ax.transAxes,
                    ha="center",
                    va="bottom",
                    fontsize=8,
                    fontweight="bold",
                )
            if column_index == 0:
                ax.text(
                    -0.08,
                    0.5,
                    ROLE_LABELS[role],
                    transform=ax.transAxes,
                    ha="right",
                    va="center",
                    rotation=90,
                    fontsize=8,
                    fontweight="bold",
                )
    fig.subplots_adjust(left=0.10, right=0.99, bottom=0.06, top=0.96, hspace=0.30, wspace=0.10)
    return _save(fig, output_base)


def _read_rows(path):
    with Path(path).open(newline="", encoding="utf-8-sig") as handle:
        return list(csv.DictReader(handle))


def main(argv=None):
    parser = argparse.ArgumentParser(description="Plot verified social-media case evidence")
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args(argv)
    for path in generate_case_figure(_read_rows(args.manifest), args.output):
        print(path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
