"""Generate report-grade case evidence plates with interpretation boundaries.

#15-A deliverable: three classes of cases (stable / degraded / conflict) with
explanatory annotations and mandatory disclaimers that bboxes are engineering
evidence only, not pixel-precise ground truth.
"""

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

ROLES = ["stable", "degraded", "conflict"]
ROLE_LABELS = {
    "stable": "Stable",
    "degraded": "Degraded",
    "conflict": "Conflict",
}
ROLE_TITLES_CN = {
    "stable": "稳定案例 (Stable)",
    "degraded": "衰减案例 (Degraded)",
    "conflict": "冲突案例 (Conflict)",
}

VARIANT_LABELS = {
    "original": "Original",
    "facebook": "Facebook",
    "wechat": "WeChat",
    "weibo": "Weibo",
}

# Risk level colour hints for annotation
RISK_COLORS = {"low": "#4CAF50", "medium": "#FF9800", "high": "#F44336"}


def _save(fig, output_base):
    output_base = Path(output_base)
    output_base.parent.mkdir(parents=True, exist_ok=True)
    paths = []
    for extension, kwargs in (
        ("svg", {}),
        ("pdf", {}),
        ("png", {"dpi": 300}),
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


def _format_fp(val):
    """Format fake_prob consistently: 3 decimals for sub-0.1, 4 otherwise."""
    v = float(val)
    if v < 0.001:
        return f"{v:.4f}"
    elif v < 0.1:
        return f"{v:.4f}"
    else:
        return f"{v:.4f}"


def _annotation_text(record):
    """Build rich multi-line annotation from case record."""
    lines = []
    label = record.get("label", "")
    fp = _format_fp(record["fake_prob"])
    risk = _format_fp(record.get("risk_score", 0))
    risk_level = record.get("risk_level", "")
    bbox = record.get("bbox_count", "0")
    tamper = record.get("tamper_type", "")

    lines.append(f"label={label}  fake_prob={fp}")
    lines.append(f"risk={risk}({risk_level})  bbox={bbox}")
    lines.append(f"tamper_type={tamper}")

    return "\n".join(lines)


def generate_case_figure(rows, output_base, variants=None):
    """Render case evidence grid with interpretation boundaries.

    Parameters
    ----------
    rows : list[dict]
        Manifest rows with columns: role, variant, image_path, label,
        fake_prob, tamper_type, risk_score, risk_level, bbox_count.
    output_base : str or Path
        Output file path without extension.
    variants : list[str] or None
        Which variant columns to render.  Default: original, facebook, wechat, weibo.
    """
    if variants is None:
        variants = ["original", "facebook", "wechat", "weibo"]

    lookup = {(row["role"], row["variant"]): row for row in rows}

    n_roles = len(ROLES)
    n_variants = len(variants)

    # Tight layout: each cell ~2.2 x 2.0 inches
    fig_width = n_variants * 2.4 + 0.8
    fig_height = n_roles * 2.6 + 1.6  # extra for footer
    fig, axes = plt.subplots(
        n_roles, n_variants, figsize=(fig_width, fig_height),
        gridspec_kw={"hspace": 0.42, "wspace": 0.06,
                     "top": 0.94, "bottom": 0.20, "left": 0.12, "right": 0.98},
    )
    if n_roles == 1 and n_variants == 1:
        axes = [[axes]]
    elif n_roles == 1:
        axes = [axes]
    elif n_variants == 1:
        axes = [[ax] for ax in axes]

    for row_index, role in enumerate(ROLES):
        for col_index, variant in enumerate(variants):
            ax = axes[row_index][col_index]
            key = (role, variant)
            if key not in lookup:
                ax.text(0.5, 0.5, "N/A", transform=ax.transAxes,
                        ha="center", va="center", fontsize=10, color="#999")
                ax.set_xticks([])
                ax.set_yticks([])
                continue

            record = lookup[key]
            img_path = Path(record["image_path"])
            if img_path.exists():
                with Image.open(img_path) as img:
                    ax.imshow(img.convert("RGB"))
            else:
                ax.text(0.5, 0.5, f"missing:\n{img_path}", transform=ax.transAxes,
                        ha="center", va="center", fontsize=6, color="#999")

            ax.set_xticks([])
            ax.set_yticks([])
            for spine in ax.spines.values():
                spine.set_color("#B8B8B8")
                spine.set_linewidth(0.6)

            # Rich annotation below
            ann = _annotation_text(record)
            ax.text(0.5, -0.18, ann, transform=ax.transAxes,
                    ha="center", va="top", fontsize=5.5,
                    fontfamily="monospace",
                    bbox=dict(boxstyle="round,pad=0.3", facecolor="#F5F5F5",
                              edgecolor="#DDD", alpha=0.9))

            # Variant header (top row)
            if row_index == 0:
                ax.text(
                    0.5, 1.03, VARIANT_LABELS.get(variant, variant),
                    transform=ax.transAxes, ha="center", va="bottom",
                    fontsize=9, fontweight="bold",
                )

            # Role label (leftmost column)
            if col_index == 0:
                ax.text(
                    -0.25, 0.5, ROLE_LABELS[role],
                    transform=ax.transAxes, ha="right", va="center",
                    rotation=90, fontsize=9, fontweight="bold",
                )

    # ---- Interpretation boundary footer ----
    footer = (
        "All values from case_summary.csv / case_classification/all.csv (real system output). "
        "bbox counts and tamper_type are engineering localization evidence only — "
        "NOT pixel-level ground truth. "
        "See experiments/localization/verified_results/ for pixel-level localization metrics."
    )
    fig.text(0.5, 0.015, footer, ha="center", va="bottom", fontsize=6.0,
             color="#666666", style="italic",
             bbox=dict(boxstyle="round,pad=0.4", facecolor="#FAFAFA",
                       edgecolor="#CCCCCC", alpha=0.85))

    return _save(fig, output_base)


def _read_rows(path):
    with Path(path).open(newline="", encoding="utf-8-sig") as handle:
        return list(csv.DictReader(handle))


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Plot social-media case evidence with interpretation boundaries"
    )
    parser.add_argument("--manifest", required=True,
                        help="CSV with columns: role, variant, image_path, label, "
                             "fake_prob, tamper_type, risk_score, risk_level, bbox_count")
    parser.add_argument("--output", required=True,
                        help="Output path without extension (svg/pdf/png auto)")
    parser.add_argument("--variants", default="original,facebook,wechat,weibo",
                        help="Comma-separated variant list (default: original,facebook,wechat,weibo)")
    args = parser.parse_args(argv)
    variants = [v.strip() for v in args.variants.split(",")]
    rows = _read_rows(args.manifest)
    for path in generate_case_figure(rows, args.output, variants=variants):
        print(path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
