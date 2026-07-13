"""Generate report-grade TraceGuard architecture and Web workflow figures."""

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch


plt.rcParams["font.family"] = "sans-serif"
plt.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei", "Arial", "DejaVu Sans"]
plt.rcParams["svg.fonttype"] = "none"
plt.rcParams["pdf.fonttype"] = 42
plt.rcParams["font.size"] = 7


COLORS = {
    "input": (0.91, 0.95, 0.93),
    "entry": (0.90, 0.94, 0.98),
    "pipeline": (0.98, 0.94, 0.84),
    "global": (0.90, 0.95, 0.91),
    "explain": (0.89, 0.94, 0.97),
    "local": (0.98, 0.91, 0.89),
    "fusion": (0.95, 0.92, 0.97),
    "output": (0.93, 0.93, 0.93),
}


def _box(ax, xy, width, height, text, color, edge="#505050", fontsize=7):
    patch = FancyBboxPatch(
        xy,
        width,
        height,
        boxstyle="round,pad=0.012,rounding_size=0.012",
        linewidth=0.8,
        edgecolor=edge,
        facecolor=color,
    )
    ax.add_patch(patch)
    ax.text(
        xy[0] + width / 2,
        xy[1] + height / 2,
        text,
        ha="center",
        va="center",
        fontsize=fontsize,
        linespacing=1.3,
    )
    return patch


def _arrow(ax, start, end, color="#555555", style="-"):
    arrow = FancyArrowPatch(
        start,
        end,
        arrowstyle="-|>",
        mutation_scale=9,
        linewidth=0.8,
        linestyle=style,
        color=color,
        shrinkA=2,
        shrinkB=2,
    )
    ax.add_patch(arrow)


def _canvas(figsize):
    fig, ax = plt.subplots(figsize=figsize)
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")
    return fig, ax


def _architecture_figure():
    fig, ax = _canvas((6.3, 4.1))
    _box(ax, (0.03, 0.42), 0.13, 0.16, "RGB 图像\n单一用户输入", COLORS["input"])
    _box(ax, (0.21, 0.39), 0.15, 0.22, "Web 工作台\nFastAPI\nCLI / 批量", COLORS["entry"])
    _box(ax, (0.41, 0.39), 0.16, 0.22, "Explanation\nPipeline\n统一编排", COLORS["pipeline"])

    _box(ax, (0.62, 0.72), 0.18, 0.14, "Detector.predict()\nlabel + fake_prob", COLORS["global"], edge="#26734D")
    _box(ax, (0.62, 0.49), 0.18, 0.14, "Detector.get_heatmap()\nGrad-CAM", COLORS["explain"], edge="#31769B")
    _box(ax, (0.62, 0.26), 0.18, 0.14, "TamperDetector\nmask + bbox\ntamper_type", COLORS["local"], edge="#A64B45", fontsize=6.2)
    _box(ax, (0.62, 0.05), 0.18, 0.12, "RiskScorer + TextExplainer\nrisk + explanation", COLORS["fusion"], edge="#72558C", fontsize=5.8)

    _box(ax, (0.84, 0.36), 0.13, 0.28, "AnalysisResponse\n\n全局判断\n局部证据\n融合结论", COLORS["output"])

    _arrow(ax, (0.16, 0.50), (0.21, 0.50))
    _arrow(ax, (0.36, 0.50), (0.41, 0.50))
    _arrow(ax, (0.57, 0.53), (0.62, 0.79), color="#26734D")
    _arrow(ax, (0.57, 0.51), (0.62, 0.56), color="#31769B")
    _arrow(ax, (0.57, 0.47), (0.62, 0.33), color="#A64B45")
    _arrow(ax, (0.57, 0.44), (0.62, 0.11), color="#72558C")
    _arrow(ax, (0.80, 0.79), (0.84, 0.57), color="#26734D")
    _arrow(ax, (0.80, 0.56), (0.84, 0.53), color="#31769B")
    _arrow(ax, (0.80, 0.33), (0.84, 0.47), color="#A64B45")
    _arrow(ax, (0.80, 0.11), (0.88, 0.36), color="#72558C")

    ax.text(0.71, 0.89, "唯一真伪判定来源", ha="center", va="bottom", color="#26734D", fontsize=6.5)
    ax.text(0.49, 0.33, "并行证据分支", ha="center", va="top", color="#666666", fontsize=6.5)
    fig.subplots_adjust(left=0.01, right=0.99, bottom=0.02, top=0.98)
    return fig


def _workflow_figure():
    fig, ax = _canvas((6.3, 2.6))
    boxes = [
        (0.02, "上传 RGB 图像", "input"),
        (0.18, "格式校验\n读取预览", "entry"),
        (0.34, "POST /api/v1/\nanalyze", "pipeline"),
        (0.52, "统一流水线\nGPU 推理", "global"),
        (0.68, "结论与证据\n同步渲染", "explain"),
        (0.84, "人工复核\n导出报告", "fusion"),
    ]
    y, width, height = 0.48, 0.13, 0.24
    for index, (x, text, color_key) in enumerate(boxes):
        _box(ax, (x, y), width, height, text, COLORS[color_key])
        if index < len(boxes) - 1:
            _arrow(ax, (x + width, y + height / 2), (boxes[index + 1][0], y + height / 2))

    ax.text(0.085, 0.34, "empty / invalid", ha="center", va="top", fontsize=6.5, color="#777777")
    ax.text(0.405, 0.34, "loading / API error", ha="center", va="top", fontsize=6.5, color="#777777")
    ax.text(0.745, 0.34, "label 与 tamper_type 分栏", ha="center", va="top", fontsize=6.5, color="#777777")
    ax.plot([0.085, 0.085], [0.46, 0.37], color="#999999", linewidth=0.7, linestyle="--")
    ax.plot([0.405, 0.405], [0.46, 0.37], color="#999999", linewidth=0.7, linestyle="--")
    ax.plot([0.745, 0.745], [0.46, 0.37], color="#999999", linewidth=0.7, linestyle="--")
    fig.subplots_adjust(left=0.01, right=0.99, bottom=0.05, top=0.95)
    return fig


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


def generate_system_figures(output_dir):
    output_dir = Path(output_dir)
    generated = []
    generated.extend(_save(_architecture_figure(), output_dir / "system_architecture"))
    generated.extend(_save(_workflow_figure(), output_dir / "web_workflow"))
    return generated


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Generate TraceGuard system figures")
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    for path in generate_system_figures(args.output):
        print(path)


if __name__ == "__main__":
    main()
