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
plt.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei", "Arial", "DejaVu Sans"]
plt.rcParams["axes.unicode_minus"] = False
plt.rcParams["svg.fonttype"] = "none"
plt.rcParams["pdf.fonttype"] = 42

ROLES = ["stable", "degraded", "conflict"]
ROLE_LABELS = {
    "stable": "稳定案例",
    "degraded": "衰减案例",
    "conflict": "冲突案例",
}
ROLE_TITLES_CN = {
    "stable": "稳定案例 (Stable)",
    "degraded": "衰减案例 (Degraded)",
    "conflict": "冲突案例 (Conflict)",
}

# ---- Case-level behavioral narratives (#15-A) ----
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

VARIANT_LABELS = {
    "original": "Original",
    "facebook": "Facebook",
    "wechat": "WeChat",
    "weibo": "Weibo",
}

# Risk level colour hints for annotation
RISK_COLORS = {"low": "#4CAF50", "medium": "#FF9800", "high": "#F44336"}

# ---- Chinese translations for annotation values ----
_LABEL_CN = {"fake": "伪", "real": "真"}
_RISK_LEVEL_CN = {"low": "低", "medium": "中", "high": "高"}
_TAMPER_CN = {
    "full_aigc_hotspots": "全图AIGC热点",
    "local_tamper": "局部篡改",
    "confirmed_real": "确认真实",
}


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
    """Build rich multi-line Chinese annotation from case record."""
    lines = []
    label = record.get("label", "")
    label_cn = _LABEL_CN.get(label, label)
    fp = _format_fp(record["fake_prob"])
    risk = _format_fp(record.get("risk_score", 0))
    risk_level = record.get("risk_level", "")
    risk_level_cn = _RISK_LEVEL_CN.get(risk_level, risk_level)
    bbox = record.get("bbox_count", "0")
    tamper = record.get("tamper_type", "")
    tamper_cn = _TAMPER_CN.get(tamper, tamper)

    lines.append(f"判定={label_cn}  伪造概率={fp}")
    lines.append(f"风险分={risk}({risk_level_cn})  可疑区域={bbox}")
    lines.append(f"篡改类型={tamper_cn}")

    return "\n".join(lines)


def generate_case_figure(rows, output_base, variants=None, roles=None):
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
    roles : list[str] or None
        Which roles to render.  Default: all — stable, degraded, conflict.
    """
    if variants is None:
        variants = ["original", "facebook", "wechat", "weibo"]
    if roles is None:
        roles = list(ROLES)

    lookup = {(row["role"], row["variant"]): row for row in rows}

    n_roles = len(roles)
    n_variants = len(variants)

    # When showing a single role, add narrative box below the image row
    single_role = n_roles == 1
    narrative_extra = 0.7 if single_role else 0.0
    narrative_y = 0.13 if single_role else 0.105
    footer_bottom = 0.04 if single_role else 0.015

    # Tight layout: each cell ~2.2 x 2.0 inches
    fig_width = n_variants * 2.4 + 0.8
    fig_height = n_roles * 2.6 + 1.6 + narrative_extra
    fig, axes = plt.subplots(
        n_roles, n_variants, figsize=(fig_width, fig_height),
        gridspec_kw={"hspace": 0.42, "wspace": 0.06,
                     "top": 0.94, "bottom": 0.22, "left": 0.08, "right": 0.98},
    )
    if n_roles == 1 and n_variants == 1:
        axes = [[axes]]
    elif n_roles == 1:
        axes = [axes]
    elif n_variants == 1:
        axes = [[ax] for ax in axes]

    for row_index, role in enumerate(roles):
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
                    fontfamily="Microsoft YaHei",
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
                    -0.12, 0.5, ROLE_LABELS[role],
                    transform=ax.transAxes, ha="right", va="center",
                    rotation=90, fontsize=9, fontweight="bold",
                )

    # ---- Case-level behavioral narrative (single-role only) ----
    if single_role:
        narrative = ROLE_NARRATIVES.get(roles[0], "")
        if narrative:
            fig.text(
                0.5, narrative_y, narrative,
                ha="center", va="center", fontsize=7.0,
                fontfamily="Microsoft YaHei", color="#222222",
                bbox=dict(boxstyle="round,pad=0.5", facecolor="#FFF8E1",
                          edgecolor="#FF9800", alpha=0.95, linewidth=1.2),
            )

    # ---- Interpretation boundary footer ----
    footer = (
        "数据来源：case_summary.csv / case_classification/all.csv（真实系统输出）。"
        "可疑区域计数与篡改类型为工程定位证据，不等同于像素级真值标注。"
        "像素级定位指标见 experiments/localization/verified_results/。"
    )
    fig.text(0.5, footer_bottom, footer, ha="center", va="bottom", fontsize=6.5,
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
