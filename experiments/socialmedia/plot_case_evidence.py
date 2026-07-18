"""Generate report-grade case evidence plates — academic premium style.

#15-A deliverable: three classes of cases (stable / degraded / conflict) with
explanatory annotations and mandatory disclaimers that bboxes are engineering
evidence only, not pixel-precise ground truth.

Visual style matches plot_case_combined.py:
- Card background (#F8F9FA) with subtle #DEE2E6 border
- Horizontal badge (colored dot + Chinese + English italic)
- Bold Arial platform headers
- Plain-text data annotations: muted labels (#ADB5BD), values bold (#212529)
- Narrative box with #FFF3CD fill and #FFC107 border
- No footnote (generated per-case, unlike the combined figure)
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

plt.rcParams["font.family"] = "sans-serif"
plt.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei", "Arial", "DejaVu Sans"]
plt.rcParams["axes.unicode_minus"] = False
plt.rcParams["svg.fonttype"] = "none"
plt.rcParams["pdf.fonttype"] = 42

ROLES = ["stable", "degraded", "conflict"]
ROLE_LABELS_CN = {"stable": "稳定案例", "degraded": "衰减案例", "conflict": "冲突案例"}
ROLE_LABELS_EN = {"stable": "Stable", "degraded": "Degraded", "conflict": "Conflict"}
ROLE_BADGE_COLORS = {
    "stable": "#198754",
    "degraded": "#DC3545",
    "conflict": "#FD7E14",
}

VARIANT_LABELS = {
    "original": "Original",
    "facebook": "Facebook",
    "wechat": "WeChat",
    "weibo": "Weibo",
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


# ── Helpers ───────────────────────────────────────────────────
def _format_fp(val):
    return f"{float(val):.4f}"


def _annotation_lines(record):
    """Return structured annotation lines: (label, value, label2, value2) tuples."""
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
        fig.savefig(p, bbox_inches="tight", facecolor="white", pad_inches=0.20, **kw)
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
def generate_case_figure(rows, output_base, variants=None, roles=None):
    """Render case evidence figure with academic premium card style.

    Parameters
    ----------
    rows : list[dict]
        Manifest rows with columns: role, variant, image_path, label,
        fake_prob, tamper_type, risk_score, risk_level, bbox_count.
    output_base : str or Path
        Output file path without extension.
    variants : list[str] or None
        Which variant columns to render.  Default: original, facebook, wechat, weibo.
    roles : list[str] or None
        Which roles to render.  Default: all — stable, degraded, conflict.
    """
    plt.close("all")

    if variants is None:
        variants = ["original", "facebook", "wechat", "weibo"]
    if roles is None:
        roles = list(ROLES)

    lookup = {(row["role"], row["variant"]): row for row in rows}

    n_roles = len(roles)
    n_vars = len(variants)

    # ── Layout ──────────────────────────────────────────────
    fig_width = n_vars * 3.1 + 1.5
    fig_height = n_roles * 4.7 + 1.2
    fig = plt.figure(figsize=(fig_width, fig_height), facecolor="white")

    from matplotlib import gridspec
    gs = gridspec.GridSpec(
        n_roles, n_vars, figure=fig,
        hspace=0.55, wspace=0.15,
        top=0.92, bottom=0.06, left=0.08, right=0.96,
    )

    # ── Render image subplots ───────────────────────────────
    all_axes = []
    for ri in range(n_roles):
        row_axes = []
        for ci in range(n_vars):
            ax = fig.add_subplot(gs[ri, ci])
            row_axes.append(ax)
        all_axes.append(row_axes)

    for ri, role in enumerate(roles):
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

    # ── Card backgrounds, badges, annotations, narratives ───
    for ri, role in enumerate(roles):
        fb = all_axes[ri][0].get_position()
        lb = all_axes[ri][-1].get_position()

        # Calculate card boundaries
        card_left = fb.x0 - 0.04
        card_right = lb.x1 + 0.04
        card_top = fb.y1 + 0.1

        # Annotation / narrative area
        narrative = ROLE_NARRATIVES.get(role, "")
        labels_relative_bottom = -0.22
        labels_absolute_bottom = fb.y0 + labels_relative_bottom * fb.height

        if narrative:
            narr_height = 0.038 if "\n" in narrative else 0.026
            # 叙事框顶部必须在标注文字底部之下，预留足够间距
            narr_top = labels_absolute_bottom - 0.04
            narr_bottom = narr_top - narr_height
        else:
            narr_bottom = labels_absolute_bottom - 0.02

        if ri == n_roles - 1:
            card_bottom = max(0.07, narr_bottom - 0.025)
        else:
            card_bottom = narr_bottom - 0.025

        # Card background
        card = FancyBboxPatch(
            (card_left, card_bottom), card_right - card_left, card_top - card_bottom,
            boxstyle="round,pad=0.01",
            facecolor="#F8F9FA", edgecolor="#DEE2E6", linewidth=0.8,
            transform=fig.transFigure, zorder=-1,
        )
        fig.patches.append(card)

        # ── Badge（卡片上方，独占一行） ──────────────────────
        badge_color = ROLE_BADGE_COLORS[role]
        bx = card_left + 0.02
        by = card_top - 0.05
        fig.text(bx, by, "●", fontsize=12, color=badge_color, ha="left", va="center",
                 transform=fig.transFigure, zorder=3)
        fig.text(bx + 0.015, by, ROLE_LABELS_CN[role], fontsize=16, fontweight="bold",
                 color="#212529", ha="left", va="center", transform=fig.transFigure, zorder=3)

        # ── Platform headers + data annotations ─────────────
        for ci, variant in enumerate(variants):
            ax = all_axes[ri][ci]
            ax.text(0.5, 1.06, VARIANT_LABELS.get(variant, variant), fontsize=13,
                    fontweight="bold", fontfamily="Arial", color="#212529",
                    ha="center", va="bottom", transform=ax.transAxes, zorder=3)

            key = (role, variant)
            if key not in lookup:
                continue
            ann_lines = _annotation_lines(lookup[key])

            start_y = -0.10
            y_space = 0.06
            for li, (lbl1, val1, lbl2, val2) in enumerate(ann_lines):
                cur_y = start_y - li * y_space
                ax.text(0.42, cur_y, f"{lbl1} =", fontsize=7.5, color="#ADB5BD",
                        ha="right", va="center", transform=ax.transAxes, zorder=3)
                ax.text(0.45, cur_y, val1, fontsize=7.5, fontweight="bold",
                        color="#212529", ha="left", va="center", transform=ax.transAxes, zorder=3)
                if lbl2 is not None:
                    ax.text(0.80, cur_y, f"{lbl2} =", fontsize=7.5, color="#ADB5BD",
                            ha="right", va="center", transform=ax.transAxes, zorder=3)
                    ax.text(0.83, cur_y, val2, fontsize=7.5, fontweight="bold",
                            color="#212529", ha="left", va="center", transform=ax.transAxes, zorder=3)

        # ── Narrative box ────────────────────────────────────
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
                    linewidth=0.6,
                ),
            )

    return _save(fig, output_base)


# ── CLI ───────────────────────────────────────────────────────
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
    parser.add_argument("--roles", default=None,
                        help="Comma-separated role filter (default: all — stable,degraded,conflict)")
    args = parser.parse_args(argv)
    variants = [v.strip() for v in args.variants.split(",")]
    roles = None
    if args.roles:
        requested = set(r.strip() for r in args.roles.split(","))
        roles = [r for r in ROLES if r in requested]
    rows = _read_rows(args.manifest)
    for path in generate_case_figure(rows, args.output, variants=variants, roles=roles):
        print(path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
