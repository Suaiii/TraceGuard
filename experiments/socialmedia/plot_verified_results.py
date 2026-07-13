"""Generate report-grade figures from verified social-media summaries."""

import argparse
import csv
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.colors import LinearSegmentedColormap
import numpy as np


plt.rcParams["font.family"] = "sans-serif"
plt.rcParams["font.sans-serif"] = ["Arial", "DejaVu Sans", "Liberation Sans"]
plt.rcParams["svg.fonttype"] = "none"
plt.rcParams["pdf.fonttype"] = 42
plt.rcParams["ps.fonttype"] = 42
plt.rcParams["font.size"] = 7
plt.rcParams["axes.linewidth"] = 0.8
plt.rcParams["axes.spines.right"] = False
plt.rcParams["axes.spines.top"] = False
plt.rcParams["legend.frameon"] = False


VARIANTS = ["original", "facebook", "wechat", "weibo"]
PLATFORMS = ["facebook", "wechat", "weibo"]
DISPLAY = {
    "original": "Original",
    "facebook": "Facebook",
    "wechat": "WeChat",
    "weibo": "Weibo",
}
COLORS = {
    "original": "#4D4D4D",
    "facebook": "#B64342",
    "wechat": "#42949E",
    "weibo": "#3775BA",
}


def _read_csv(path):
    with Path(path).open(newline="", encoding="utf-8-sig") as handle:
        return list(csv.DictReader(handle))


def build_figure_data(source_dir):
    source_dir = Path(source_dir)
    overall_rows = _read_csv(source_dir / "paired_summary_all.csv")
    generator_rows = _read_csv(source_dir / "paired_summary_by_generator.csv")
    overall = {row["variant"]: row for row in overall_rows}
    if set(overall) != set(VARIANTS):
        raise ValueError("paired_summary_all.csv must contain all four variants")

    generators = sorted({row["scope"] for row in generator_rows}, key=str.casefold)
    generator_lookup = {
        (row["scope"], row["variant"]): row
        for row in generator_rows
    }
    retention_matrix = np.array([
        [float(generator_lookup[(generator, platform)]["recall_retention"]) for platform in PLATFORMS]
        for generator in generators
    ])
    original_recall_by_generator = {
        generator: float(generator_lookup[(generator, "original")]["fake_recall"])
        for generator in generators
    }
    return {
        "variants": list(VARIANTS),
        "platforms": list(PLATFORMS),
        "generators": generators,
        "original_recall_by_generator": original_recall_by_generator,
        "fake_recall": np.array([float(overall[variant]["fake_recall"]) for variant in VARIANTS]),
        "mean_probability_delta": np.array([
            float(overall[variant]["mean_probability_delta"]) for variant in VARIANTS
        ]),
        "retention_matrix": retention_matrix,
    }


def _panel_label(ax, label):
    ax.text(
        -0.12,
        1.04,
        label,
        transform=ax.transAxes,
        fontsize=8,
        fontweight="bold",
        ha="left",
        va="bottom",
    )


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
        paths.append(path)
    plt.close(fig)
    return paths


def _overall_figure(data):
    fig, axes = plt.subplots(1, 2, figsize=(6.3, 2.8), gridspec_kw={"wspace": 0.38})

    recall_percent = data["fake_recall"] * 100
    x = np.arange(len(VARIANTS))
    bars = axes[0].bar(
        x,
        recall_percent,
        width=0.68,
        color=[COLORS[variant] for variant in VARIANTS],
        edgecolor="white",
        linewidth=0.6,
    )
    axes[0].set_xticks(x, [DISPLAY[variant] for variant in VARIANTS], rotation=20, ha="right")
    axes[0].set_ylabel("Fake recall (%)")
    axes[0].set_ylim(0, 70)
    axes[0].set_yticks(np.arange(0, 71, 10))
    axes[0].grid(axis="y", color="#D8D8D8", linewidth=0.5, alpha=0.65)
    axes[0].set_axisbelow(True)
    for bar, value in zip(bars, recall_percent):
        axes[0].text(
            bar.get_x() + bar.get_width() / 2,
            value + 1.3,
            f"{value:.1f}",
            ha="center",
            va="bottom",
            fontsize=6.5,
        )
    _panel_label(axes[0], "a")

    platform_deltas = data["mean_probability_delta"][1:]
    platform_x = np.arange(len(PLATFORMS))
    bars = axes[1].bar(
        platform_x,
        platform_deltas,
        width=0.68,
        color=[COLORS[platform] for platform in PLATFORMS],
        edgecolor="white",
        linewidth=0.6,
    )
    axes[1].axhline(0, color="#767676", linewidth=0.8)
    axes[1].set_xticks(
        platform_x,
        [DISPLAY[platform] for platform in PLATFORMS],
        rotation=20,
        ha="right",
    )
    axes[1].set_ylabel(r"Mean paired $\Delta$ fake probability")
    axes[1].set_ylim(-0.36, 0.02)
    axes[1].set_yticks(np.arange(-0.3, 0.01, 0.1))
    axes[1].grid(axis="y", color="#D8D8D8", linewidth=0.5, alpha=0.65)
    axes[1].set_axisbelow(True)
    for bar, value in zip(bars, platform_deltas):
        axes[1].text(
            bar.get_x() + bar.get_width() / 2,
            value - 0.012,
            f"{value:.3f}",
            ha="center",
            va="top",
            fontsize=6.5,
        )
    _panel_label(axes[1], "b")

    fig.subplots_adjust(left=0.10, right=0.99, bottom=0.25, top=0.93)
    return fig


def _heatmap_figure(data):
    cmap = LinearSegmentedColormap.from_list(
        "retention",
        ["#B64342", "#F6E8E5", "#DDF0EE", "#42949E"],
    )
    fig, ax = plt.subplots(figsize=(6.3, 3.7))
    matrix = data["retention_matrix"]
    image = ax.imshow(matrix, vmin=0, vmax=1, cmap=cmap, aspect="auto")
    ax.set_xticks(range(len(PLATFORMS)), [DISPLAY[platform] for platform in PLATFORMS])
    generator_labels = [
        f"{generator} ({data['original_recall_by_generator'][generator] * 100:.1f}%)"
        for generator in data["generators"]
    ]
    ax.set_yticks(range(len(generator_labels)), generator_labels)
    ax.set_xlabel("Propagation condition")
    ax.set_ylabel("Generator")
    for row in range(matrix.shape[0]):
        for column in range(matrix.shape[1]):
            value = matrix[row, column]
            color = "white" if value < 0.16 or value > 0.82 else "#272727"
            ax.text(
                column,
                row,
                f"{value * 100:.1f}%",
                ha="center",
                va="center",
                fontsize=6.5,
                color=color,
            )
    for spine in ax.spines.values():
        spine.set_visible(False)
    colorbar = fig.colorbar(image, ax=ax, fraction=0.04, pad=0.025)
    colorbar.set_label("Fake recall retention")
    colorbar.set_ticks([0, 0.25, 0.5, 0.75, 1.0])
    colorbar.set_ticklabels(["0%", "25%", "50%", "75%", "100%"])
    fig.subplots_adjust(left=0.16, right=0.90, bottom=0.14, top=0.98)
    return fig


def generate_figures(source_dir, output_dir):
    data = build_figure_data(source_dir)
    output_dir = Path(output_dir)
    generated = []
    generated.extend(_save(_overall_figure(data), output_dir / "socialmedia_overall"))
    generated.extend(_save(_heatmap_figure(data), output_dir / "socialmedia_generator_retention"))
    return generated


def main(argv=None):
    parser = argparse.ArgumentParser(description="Plot verified social-media robustness results")
    parser.add_argument("--source", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args(argv)
    for path in generate_figures(args.source, args.output):
        print(path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
