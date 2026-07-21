"""Generate Chapter-1 background figure: threat chain + evidence decay.

Left panel: AIGC threat chain across the social-media dissemination pipeline,
annotated with the three lines of defense (generation-side alignment /
labels & metadata / end-of-chain third-party audit).

Right panel: measured evidence-decay pair from the degraded case
(BigGAN fake, fake_prob 0.9671 original -> 0.0180 after Facebook),
numbers from experiments/socialmedia/verified_results/case_manifest_extended.csv.

Style matches experiments/socialmedia/plot_case_evidence.py:
card background #F8F9FA, border #DEE2E6, Microsoft YaHei, editable SVG text.

Usage:
    python docs/figures/background/plot_threat_chain.py
Outputs docs/figures/background/background_threat_chain.{svg,pdf,png}
"""

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch
from PIL import Image

plt.rcParams["font.family"] = "sans-serif"
plt.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei", "Arial", "DejaVu Sans"]
plt.rcParams["axes.unicode_minus"] = False
plt.rcParams["svg.fonttype"] = "none"
plt.rcParams["pdf.fonttype"] = 42

ROOT = Path(__file__).resolve().parents[3]
OUT_DIR = Path(__file__).resolve().parent

CARD_BG = "#F8F9FA"
CARD_BORDER = "#DEE2E6"
TEXT_DARK = "#212529"
TEXT_MUTED = "#6C757D"
GREEN = "#198754"
RED = "#DC3545"
ORANGE = "#FD7E14"
BLUE = "#0D6EFD"

CASE_ORIGINAL = ROOT / "data/case_images/degraded_original.png"
CASE_FACEBOOK = ROOT / "data/case_images/degraded_facebook.jpg"


def _stage_card(ax, x, y, w, h, title, sub, border=CARD_BORDER, title_color=TEXT_DARK):
    ax.add_patch(
        FancyBboxPatch(
            (x, y), w, h,
            boxstyle="round,pad=0.012",
            facecolor=CARD_BG, edgecolor=border, linewidth=1.2,
            mutation_aspect=0.6, clip_on=False,
        )
    )
    ax.text(x + w / 2, y + h * 0.66, title, ha="center", va="center",
            fontsize=10.5, fontweight="bold", color=title_color)
    ax.text(x + w / 2, y + h * 0.30, sub, ha="center", va="center",
            fontsize=8.2, color=TEXT_MUTED)


def _arrow(ax, x0, x1, y, color=TEXT_MUTED):
    ax.add_patch(
        FancyArrowPatch((x0, y), (x1, y),
                        arrowstyle="-|>", mutation_scale=14,
                        linewidth=1.4, color=color)
    )


def _defense(ax, x, y, w, text, ok):
    color = GREEN if ok else RED
    tag = "√" if ok else "×"
    h = 0.15
    ax.add_patch(
        FancyBboxPatch(
            (x, y), w, h,
            boxstyle="round,pad=0.010",
            facecolor="white", edgecolor=color, linewidth=1.3,
            mutation_aspect=0.6, clip_on=False,
        )
    )
    ax.text(x + 0.016, y + h / 2, tag, ha="left", va="center",
            fontsize=10, fontweight="bold", color=color)
    ax.text(x + w / 2 + 0.012, y + h / 2, text, ha="center", va="center",
            fontsize=8.0, color=TEXT_DARK)


def main():
    fig = plt.figure(figsize=(12.6, 4.9))

    # ── Left panel: threat chain ─────────────────────────────
    axl = fig.add_axes([0.015, 0.03, 0.60, 0.94])
    axl.set_xlim(0, 1)
    axl.set_ylim(0, 1)
    axl.axis("off")

    stages = [
        ("AIGC 图像生成", "超监管内容可绕过\n生成端安全对齐"),
        ("社交平台发布", "附显式标识\n与元数据"),
        ("平台处理", "转码 · 压缩\n截图转存"),
        ("传播链末端「裸图」", "标识与元数据\n被系统性剥离"),
    ]
    n = len(stages)
    w, h, gap = 0.195, 0.30, 0.038
    x0 = (1 - n * w - (n - 1) * gap) / 2
    y0 = 0.56
    for i, (title, sub) in enumerate(stages):
        x = x0 + i * (w + gap)
        _stage_card(axl, x, y0, w, h, title, sub)
        if i < n - 1:
            _arrow(axl, x + w + 0.004, x + w + gap - 0.004, y0 + h / 2)

    axl.text(0.5, 0.955, "假新闻配图 · 舆情误导 · 电子证据污染",
             ha="center", va="center", fontsize=10, fontweight="bold", color=RED)

    dw = 0.235
    c1 = x0 + w / 2
    c3 = x0 + 2 * (w + gap) + w / 2
    c4 = x0 + 3 * (w + gap) + w / 2
    _defense(axl, c1 - dw / 2, 0.28, dw, "第一道防线：生成端对齐\n（可被绕过）", ok=False)
    _defense(axl, c3 - dw / 2, 0.28, dw, "第二道防线：标识与元数据\n（传播中被剥离）", ok=False)
    _defense(axl, c4 - dw / 2, 0.06, dw, "第三道防线：末端第三方审核\n（本作品）", ok=True)
    for xi in (c1, c3):
        axl.plot([xi, xi], [0.28 + 0.15 + 0.012, y0 - 0.014], color=RED,
                 linewidth=0.9, linestyle=":", alpha=0.7, clip_on=False)
    axl.plot([c4, c4], [0.06 + 0.15 + 0.012, y0 - 0.014], color=GREEN,
             linewidth=0.9, linestyle=":", alpha=0.7, clip_on=False)

    # ── Right panel: measured evidence decay ─────────────────
    axr = fig.add_axes([0.635, 0.03, 0.355, 0.94])
    axr.set_xlim(0, 1)
    axr.set_ylim(0, 1)
    axr.axis("off")
    axr.add_patch(
        FancyBboxPatch((0.025, 0.03), 0.95, 0.94,
                       boxstyle="round,pad=0.012",
                       facecolor="white", edgecolor=CARD_BORDER,
                       linewidth=1.2, mutation_aspect=0.6, clip_on=False)
    )
    axr.text(0.5, 0.905, "同图传播前后：检测证据衰减（本作品实测）",
             ha="center", va="center", fontsize=10, fontweight="bold",
             color=TEXT_DARK)

    for (img_path, xc, plat, prob, verdict, vcolor) in [
        (CASE_ORIGINAL, 0.26, "Original", "0.9671", "判定：伪", RED),
        (CASE_FACEBOOK, 0.74, "Facebook 传播后", "0.0180", "判定：真（证据不足→转人工）", GREEN),
    ]:
        img = Image.open(img_path).convert("RGB")
        iw, ih = 0.38, 0.44
        ax_img = axr.inset_axes([xc - iw / 2, 0.36, iw, ih])
        ax_img.imshow(img)
        ax_img.set_xticks([])
        ax_img.set_yticks([])
        for s in ax_img.spines.values():
            s.set_color(CARD_BORDER)
        axr.text(xc, 0.29, plat, ha="center", va="center",
                 fontsize=9, fontweight="bold", color=TEXT_DARK)
        axr.text(xc, 0.20, f"伪造概率 {prob}", ha="center", va="center",
                 fontsize=9.5, color=TEXT_DARK)
        axr.text(xc, 0.115, verdict, ha="center", va="center",
                 fontsize=8.2, color=vcolor)

    _arrow(axr, 0.47, 0.53, 0.58, color=ORANGE)
    axr.text(0.5, 0.045,
             "BigGAN 伪造样本 · 数值来源 case_manifest_extended.csv · 一次确定性推理",
             ha="center", va="center", fontsize=7.2, color=TEXT_MUTED)

    for stem in ["background_threat_chain"]:
        fig.savefig(OUT_DIR / f"{stem}.svg", bbox_inches="tight")
        fig.savefig(OUT_DIR / f"{stem}.pdf", bbox_inches="tight")
        fig.savefig(OUT_DIR / f"{stem}.png", dpi=300, bbox_inches="tight")
    print("written to", OUT_DIR)


if __name__ == "__main__":
    main()
