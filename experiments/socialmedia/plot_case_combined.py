"""Generate a polished, academic-grade combined case-evidence figure (#15-A).

Three case cards (stable / degraded / conflict) stacked vertically.
Design spec:
- Card background (#F8F9FA) with subtle #DEE2E6 border, rounded corners
- Horizontal badge (colored dot + Chinese + English italic) in top-left
- Bold Arial platform headers centered above images
- Plain-text data annotations: labels muted (#ADB5BD), values bold (#212529)
- Modern narrative box: Auto-wrapped #FFF3CD fill, tightly following annotations
- Single #6C757D footnote at bottom, 8.5pt on pure white background
"""

import argparse
import csv
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch
import numpy as np
from PIL import Image

# ── Font & style ──────────────────────────────────────────────
plt.rcParams["font.family"] = "sans-serif"
plt.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei", "Arial", "DejaVu Sans"]
plt.rcParams["axes.unicode_minus"] = False
plt.rcParams["svg.fonttype"] = "none"
plt.rcParams["pdf.fonttype"] = 42

# ── Constants ─────────────────────────────────────────────────
ROLES = ["stable", "degraded", "conflict"]
ROLE_LABELS_CN = {"stable": "稳定案例", "degraded": "衰减案例", "conflict": "冲突案例"}
ROLE_LABELS_EN = {"stable": "Stable", "degraded": "Degraded", "conflict": "Conflict"}
ROLE_BADGE_COLORS = {
    "stable": "#198754",
    "degraded": "#DC3545",
    "conflict": "#FD7E14",
}

VARIANT_LABELS = {
    "original": "Original", "facebook": "Facebook",
    "wechat": "WeChat", "weibo": "Weibo",
}

ROLE_NARRATIVES = {
    "stable": (
        "【行为】传播前后伪造概率维持 0.99+，风险等级保持「中」，"
        "判定始终为「伪」。证据充分且一致——系统稳定放行，不引入额外不确定性。"
    ),
    "degraded": (
        "【行为】原始图像伪造概率 0.967 → Facebook 传播后骤降至 0.018，"
        "判定由「伪」翻转为「真」，风险等级从「中」降至「低」，可疑区域归零。\n"
        "【关键】系统并未静默改判为真，而是同步降低置信度并触发转人工——"
        "证据不足时宁可转人工，不以低证据状态做出高置信判定。"
    ),
    "conflict": (
        "【行为】四平台伪造概率均远低于 0.5，全局判定为「真」，"
        "但局部模块持续检出 1 处可疑区域（篡改类型=局部篡改）。\n"
        "【关键】系统保留全局与局部的证据分歧，不强行取一路覆盖另一路，转人工鉴定。"
    ),
}

_LABEL_CN = {"fake": "伪", "real": "真"}
_RISK_LEVEL_CN = {"low": "低", "medium": "中", "high": "高"}
_TAMPER_CN = {
    "full_aigc_hotspots": "全图AIGC热点",
    "local_tamper": "局部篡改",
    "confirmed_real": "确认真实",
}

FOOTNOTE_TEXT = (
    "数据来源：case_summary.csv / case_classification/all.csv（真实系统输出）。"
    "可疑区域计数与篡改类型为工程定位证据，不等同于像素级真值标注。"
    "像素级定位指标见 experiments/localization/verified_results/。"
)


# ── Helpers ───────────────────────────────────────────────────
def _format_fp(val):
    return f"{float(val):.4f}"


def _annotation_lines(record):
    label = record.get("label", "")
    label_cn = _LABEL_CN.get(label, label)
    fp = _format_fp(record["fake_prob"])
    risk = _format_fp(record.get("risk_score", 0))
    risk_level = record.get("risk_level", "")
    risk_level_cn = _RISK_LEVEL_CN.get(risk_level, risk_level)
    bbox = record.get("bbox_count", "0")
    tamper = record.get("tamper_type", "")
    tamper_cn = _TAMPER_CN.get(tamper, tamper)
    return [
        ("判定", f"{label_cn}", "伪造概率", f"{fp}"),
        ("风险分", f"{risk}({risk_level_cn})", "可疑区域", f"{bbox}"),
        ("篡改类型", f"{tamper_cn}", None, None),
    ]


def _save(fig, output_base):
    output_base = Path(output_base)
    output_base.parent.mkdir(parents=True, exist_ok=True)
    paths = []

    for ext, kw in (("png", {"dpi": 300}), ("svg", {}), ("pdf", {})):
        p = output_base.with_suffix(f".{ext}")
        fig.savefig(p, bbox_inches="tight", facecolor="white", pad_inches=0.15, **kw)
        if ext == "svg":
            svg = p.read_text(encoding="utf-8")
            p.write_text(
                "\n".join(line.rstrip() for line in svg.splitlines()) + "\n",
                encoding="utf-8",
            )
        paths.append(p)

    plt.close(fig)
    return paths


# ── Main drawing ──────────────────────────────────────────────
def generate_combined_figure(rows, output_base, variants=None):
    plt.close("all")
    
    variants = variants or ["original", "facebook", "wechat", "weibo"]
    lookup = {(row["role"], row["variant"]): row for row in rows}

    n_roles = len(ROLES)
    n_vars = len(variants)

    fig_width = n_vars * 3.1 + 1.5    
    fig_height = n_roles * 5.0 + 1.5   # 稍微拉高整体画布，配合大行距
    fig = plt.figure(figsize=(fig_width, fig_height), facecolor="white")
    fig.clf()

    from matplotlib import gridspec
    gs = gridspec.GridSpec(
        n_roles, n_vars, figure=fig,
        hspace=0.75, wspace=0.15,  # 核心修改：大幅拉大行距（0.55 -> 0.75），彻底隔离上下文
        top=0.96, bottom=0.15, left=0.08, right=0.96
    )

    # ── 2. 渲染图片子图 ──────────────────────────────────
    all_axes = []
    for ri in range(n_roles):
        row_axes = []
        for ci in range(n_vars):
            ax = fig.add_subplot(gs[ri, ci])
            row_axes.append(ax)
        all_axes.append(row_axes)

    for ri, role in enumerate(ROLES):
        for ci, variant in enumerate(variants):
            ax = all_axes[ri][ci]
            key = (role, variant)
            if key not in lookup:
                ax.text(0.5, 0.5, "N/A", transform=ax.transAxes, ha="center", va="center", color="#999")
                ax.set_axis_off()
                continue

            record = lookup[key]
            img_path = Path(record["image_path"])
            if img_path.exists():
                with Image.open(img_path) as img:
                    ax.imshow(img.convert("RGB"))
            else:
                ax.text(0.5, 0.5, f"Missing:\n{img_path.name}", transform=ax.transAxes,
                        ha="center", va="center", fontsize=8, color="#999")

            ax.set_xticks([])
            ax.set_yticks([])
            for spine in ax.spines.values():
                spine.set_visible(False)
            ax.set_zorder(10)

    fig.canvas.draw()

    # ── 3. 动态卡片与自适应叙事框渲染 ───────────────────────
    for ri, role in enumerate(ROLES):
        fb = all_axes[ri][0].get_position()
        lb = all_axes[ri][-1].get_position()

        # 精确计算行内各元素坐标
        labels_relative_bottom = -0.22
        labels_absolute_bottom = fb.y0 + labels_relative_bottom * fb.height

        narrative = ROLE_NARRATIVES.get(role, "")
        if narrative:
            narr_height = 0.035 if "\n" in narrative else 0.024
            narr_top = labels_absolute_bottom - 0.005
            narr_bottom = narr_top - narr_height
        else:
            narr_bottom = labels_absolute_bottom - 0.010

        card_left = fb.x0 - 0.04
        card_right = lb.x1 + 0.04
        card_top = fb.y1 + 0.03       # 稍微收紧上边缘，不越界
        card_bottom = narr_bottom - 0.010 # 紧凑底部，留出充足的白色行间距

        # 绘制浅灰色大卡片背景框
        card = FancyBboxPatch(
            (card_left, card_bottom), card_right - card_left, card_top - card_bottom,
            boxstyle="round,pad=0.01",
            facecolor="#F8F9FA", edgecolor="#DEE2E6", linewidth=0.8,
            transform=fig.transFigure, zorder=-1,
        )
        fig.patches.append(card)

        # ── 顶层小徽章 ──
        badge_color = ROLE_BADGE_COLORS[role]
        bx = card_left + 0.02
        by = card_top - 0.012
        fig.text(bx, by, "●", fontsize=9, color=badge_color, ha="left", va="center", transform=fig.transFigure, zorder=3)
        fig.text(bx + 0.012, by, ROLE_LABELS_CN[role], fontsize=11, fontweight="bold", color="#212529", ha="left", va="center", transform=fig.transFigure, zorder=3)
        #fig.text(bx + 0.095, by, f"({ROLE_LABELS_EN[role]})", fontsize=9, style="italic", color="#6C757D", ha="left", va="center", transform=fig.transFigure, zorder=3)

        # ── 平台标题与数据标签 ──
        for ci, variant in enumerate(variants):
            ax = all_axes[ri][ci]
            ax.text(0.5, 1.06, VARIANT_LABELS.get(variant, variant), fontsize=13, fontweight="bold",
                    fontfamily="Arial", color="#212529", ha="center", va="bottom", transform=ax.transAxes, zorder=3)

            key = (role, variant)
            if key not in lookup: continue
            ann_lines = _annotation_lines(lookup[key])

            start_y = -0.10
            y_space = 0.06
            for li, (lbl1, val1, lbl2, val2) in enumerate(ann_lines):
                cur_y = start_y - li * y_space
                ax.text(0.28, cur_y, f"{lbl1} =", fontsize=7.5, color="#ADB5BD", ha="right", va="center", transform=ax.transAxes, zorder=3)
                ax.text(0.31, cur_y, val1, fontsize=7.5, fontweight="bold", color="#212529", ha="left", va="center", transform=ax.transAxes, zorder=3)
                if lbl2 is not None:
                    ax.text(0.80, cur_y, f"{lbl2} =", fontsize=7.5, color="#ADB5BD", ha="right", va="center", transform=ax.transAxes, zorder=3)
                    ax.text(0.83, cur_y, val2, fontsize=7.5, fontweight="bold", color="#212529", ha="left", va="center", transform=ax.transAxes, zorder=3)

        # ── 黄色叙事框 ──
        if narrative:
            fig.text(
                card_left + 0.04, 
                narr_bottom + narr_height / 2, 
                narrative,
                fontsize=8.5, 
                color="#495057", 
                ha="left", 
                va="center", 
                linespacing=1.4,
                transform=fig.transFigure, 
                zorder=3,
                bbox=dict(
                    boxstyle="round,pad=0.4", 
                    facecolor="#FFF3CD", 
                    edgecolor="#FFC107", 
                    linewidth=0.6
                )
            )

    # ── 4. 全局底部页脚（Footnote - 纯大白底） ────────────────────────
    fig.text(
        0.5, 0.020, FOOTNOTE_TEXT,
        fontsize=8.5, color="#6C757D", style="italic",
        ha="center", va="bottom", transform=fig.transFigure, zorder=5,
    )

    return _save(fig, output_base)


def _read_rows(path):
    with Path(path).open(newline="", encoding="utf-8-sig") as handle:
        return list(csv.DictReader(handle))


def main(argv=None):
    parser = argparse.ArgumentParser(description="Generate polished combined case-evidence figure")
    parser.add_argument("--manifest", required=True, help="CSV manifest")
    parser.add_argument("--output", required=True, help="Output path without extension")
    parser.add_argument("--variants", default="original,facebook,wechat,weibo", help="Comma-separated variant list")
    args = parser.parse_args(argv)
    variants = [v.strip() for v in args.variants.split(",")]
    rows = _read_rows(args.manifest)
    for path in generate_combined_figure(rows, args.output, variants=variants):
        print(path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())