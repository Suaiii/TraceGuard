# -*- coding: utf-8 -*-
"""
gen_figure_assets.py

用 matplotlib 渲染 TraceGuard 结构图所需的**原创**示意图素材（透明 PNG），
供 build_figures_pptx.py 嵌入。全部程序化生成、无任何外部/他人图像，可复现。

产物目录：docs/figures/system/assets/
  gradcam.png   Grad-CAM 热力图（真实平滑热力场 + 等高线）
  backbone.png  去全局池化骨干架构（特征层堆叠 + 2304→256 瓶颈）
  mkmmd.png     MK-MMD 域对齐散点（源/目标双分布靠拢）
  bbox.png      篡改定位（抽象图像 + 四象限 + 红框 + 掩膜）
  gauge.png     风险量表（半环 低/中/高 + 指针）
  bars.png      五维风险柱状
  icon_upload/check/api/gpu/panel/review/report.png  Web 流程小图标（线性）
"""
import os
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle, FancyArrow, Wedge, Circle, Polygon, FancyBboxPatch, Ellipse

OUT = r"E:\aNB\TECH\AI竞赛\docs\figures\system\assets"
os.makedirs(OUT, exist_ok=True)

INK = "#2A2A2A"
MUTE = "#666666"


def save(fig, name, pad=0.02):
    fig.savefig(os.path.join(OUT, name), transparent=True,
                bbox_inches="tight", pad_inches=pad, dpi=300)
    plt.close(fig)


# ---------------------------------------------------------------- gradcam
def gen_gradcam():
    fig, ax = plt.subplots(figsize=(2.3, 2.3), dpi=300)
    n = 220
    x = np.linspace(-3, 3, n)
    X, Y = np.meshgrid(x, x)
    Z = (np.exp(-((X - 0.7) ** 2 + (Y + 0.5) ** 2) / 1.1)
         + 0.7 * np.exp(-((X + 1.2) ** 2 + (Y - 1.0) ** 2) / 0.55)
         + 0.25 * np.exp(-((X + 0.2) ** 2 + (Y + 1.6) ** 2) / 0.9))
    Z = Z / Z.max()
    ax.imshow(np.full_like(Z, 0.9), cmap="gray", vmin=0, vmax=1)
    ax.imshow(Z, cmap="turbo", alpha=0.88, interpolation="bilinear")
    ax.contour(Z, levels=6, colors="white", linewidths=0.5, alpha=0.45)
    ax.set_xticks([]); ax.set_yticks([])
    for s in ax.spines.values():
        s.set_edgecolor("#888"); s.set_linewidth(1.4)
    save(fig, "gradcam.png")


# ---------------------------------------------------------------- backbone
def gen_backbone():
    fig, ax = plt.subplots(figsize=(4.6, 2.1), dpi=300)
    ax.set_xlim(0, 11.5); ax.set_ylim(0, 5); ax.axis("off")

    def slab(cx, cy, w, h, depth, color, edge="#5A4A82"):
        # 3D 特征块：正面矩形 + 顶面/右面平行四边形
        ax.add_patch(Rectangle((cx, cy), w, h, facecolor=color,
                               edgecolor=edge, linewidth=1.1, zorder=3))
        ax.add_patch(Polygon([(cx, cy + h), (cx + depth, cy + h + depth * 0.9),
                              (cx + w + depth, cy + h + depth * 0.9),
                              (cx + w, cy + h)], closed=True,
                             facecolor=color, edgecolor=edge, linewidth=1.0,
                             alpha=0.75, zorder=2))
        ax.add_patch(Polygon([(cx + w, cy), (cx + w + depth, cy + depth * 0.9),
                              (cx + w + depth, cy + h + depth * 0.9),
                              (cx + w, cy + h)], closed=True,
                             facecolor=color, edgecolor=edge, linewidth=1.0,
                             alpha=0.55, zorder=2))

    # 输入图像
    ax.add_patch(Rectangle((0.1, 1.7), 1.3, 1.3, facecolor="#DCEBF7",
                           edgecolor="#888", linewidth=1.2, zorder=3))
    ax.add_patch(Polygon([(0.35, 1.95), (0.75, 2.55), (1.15, 1.95)],
                         closed=True, facecolor="#7FB06E", edgecolor="none", zorder=4))
    ax.add_patch(Circle((1.05, 2.6), 0.13, facecolor="#F6C74B", edgecolor="none", zorder=4))

    # 特征层堆叠（空间变小、通道变多）
    cols = ["#CDBCEA", "#BCA7E0", "#A98FD3", "#9678C6"]
    specs = [(2.0, 1.35, 1.1, 1.1, 0.32),
             (3.7, 1.55, 0.85, 0.9, 0.30),
             (5.15, 1.75, 0.62, 0.7, 0.26),
             (6.35, 1.9, 0.45, 0.5, 0.22)]
    for (cx, cy, w, h, d), c in zip(specs, cols):
        slab(cx, cy, w, h, d, c)

    # 瓶颈条 2304 -> 256（去全局池化）
    ax.add_patch(Rectangle((7.5, 1.55), 0.32, 1.4, facecolor="#C7B8E2",
                           edgecolor="#5A4A82", linewidth=1.1, zorder=3))
    ax.add_patch(Rectangle((8.9, 2.0), 0.3, 0.55, facecolor="#B6D5AA",
                           edgecolor="#4B7A3D", linewidth=1.1, zorder=3))
    ax.annotate("", xy=(8.9, 2.27), xytext=(7.82, 2.25),
                arrowprops=dict(arrowstyle="-|>", color=INK, lw=1.4))
    ax.text(7.66, 1.3, "2304", ha="center", va="top", fontsize=8, color=MUTE)
    ax.text(9.05, 1.75, "256", ha="center", va="top", fontsize=8, color=MUTE)

    # 输出 logits
    ax.add_patch(Rectangle((9.9, 1.9), 0.9, 0.75, facecolor="#EFE7D0",
                           edgecolor="#888", linewidth=1.0, zorder=3))
    ax.text(10.35, 2.27, "Real/\nFake", ha="center", va="center", fontsize=7.5, color=INK)

    # 主箭头
    for x0, x1, y in [(1.45, 1.95, 2.35), (9.25, 9.85, 2.28)]:
        ax.annotate("", xy=(x1, y), xytext=(x0, y),
                    arrowprops=dict(arrowstyle="-|>", color=INK, lw=1.3))
    save(fig, "backbone.png")


# ---------------------------------------------------------------- mkmmd
def gen_mkmmd():
    rng = np.random.RandomState(7)
    fig, ax = plt.subplots(figsize=(2.6, 2.1), dpi=300)
    ax.set_xlim(0, 10); ax.set_ylim(0, 8); ax.axis("off")
    # 源域（蓝）与目标域（橙），对齐后仍有小残差
    src = rng.multivariate_normal([4.2, 4.3], [[1.1, 0.3], [0.3, 0.9]], 26)
    tgt = rng.multivariate_normal([5.4, 3.7], [[1.0, -0.2], [-0.2, 1.0]], 26)
    ax.scatter(src[:, 0], src[:, 1], s=26, c="#6C8ED6", edgecolors="white",
               linewidths=0.4, zorder=3, label="源域")
    ax.scatter(tgt[:, 0], tgt[:, 1], s=26, c="#E39B6C", edgecolors="white",
               linewidths=0.4, zorder=3, label="目标域")
    for c, col in [([4.2, 4.3], "#3E6ABF"), ([5.4, 3.7], "#C97B44")]:
        ax.add_patch(Ellipse(c, 3.4, 2.7, edgecolor=col, facecolor="none",
                             linestyle="--", linewidth=1.3, alpha=0.8, zorder=2))
    ax.annotate("", xy=(5.0, 4.0), xytext=(4.6, 4.0),
                arrowprops=dict(arrowstyle="<|-|>", color=INK, lw=1.4))
    ax.text(4.8, 6.6, "MMD ↓  分布对齐", ha="center", fontsize=9.5,
            color=INK, fontfamily="Microsoft YaHei")
    save(fig, "mkmmd.png")


# ---------------------------------------------------------------- bbox
def gen_bbox():
    rng = np.random.RandomState(3)
    fig, ax = plt.subplots(figsize=(2.3, 2.3), dpi=300)
    ax.set_xlim(0, 10); ax.set_ylim(0, 10); ax.axis("off")
    # 抽象“图像”底：柔和分块
    base = rng.rand(8, 8)
    ax.imshow(base, extent=(0, 10, 0, 10), cmap="Pastel1", alpha=0.7,
              interpolation="bilinear", zorder=1)
    ax.add_patch(Rectangle((0, 0), 10, 10, facecolor="none",
                           edgecolor="#888", linewidth=1.4, zorder=4))
    # 四象限虚线
    ax.plot([5, 5], [0, 10], "--", color=MUTE, linewidth=0.9, zorder=3)
    ax.plot([0, 10], [5, 5], "--", color=MUTE, linewidth=0.9, zorder=3)
    # 篡改掩膜（右下）+ 红框
    ax.add_patch(Ellipse((6.9, 3.0), 3.0, 2.4, facecolor="#C62E24",
                         alpha=0.28, edgecolor="none", zorder=3))
    ax.add_patch(Rectangle((5.4, 1.6), 3.1, 2.9, facecolor="none",
                           edgecolor="#C0392B", linewidth=2.4, zorder=5))
    save(fig, "bbox.png")


# ---------------------------------------------------------------- gauge
def gen_gauge():
    fig, ax = plt.subplots(figsize=(2.6, 1.6), dpi=300)
    ax.set_xlim(-1.2, 1.2); ax.set_ylim(-0.15, 1.25); ax.axis("off"); ax.set_aspect("equal")
    ax.add_patch(Wedge((0, 0), 1.0, 120, 180, width=0.34, facecolor="#B6D5AA"))
    ax.add_patch(Wedge((0, 0), 1.0, 60, 120, width=0.34, facecolor="#ECDD9A"))
    ax.add_patch(Wedge((0, 0), 1.0, 0, 60, width=0.34, facecolor="#E89A8A"))
    ang = np.deg2rad(34)  # 指向 high 段
    ax.annotate("", xy=(0.82 * np.cos(ang), 0.82 * np.sin(ang)), xytext=(0, 0),
                arrowprops=dict(arrowstyle="-|>", color=INK, lw=2.4))
    ax.add_patch(Circle((0, 0), 0.07, facecolor=INK))
    save(fig, "gauge.png")


# ---------------------------------------------------------------- bars
def gen_bars():
    fig, ax = plt.subplots(figsize=(2.5, 1.9), dpi=300)
    vals = [0.55, 0.92, 0.42, 0.78, 0.6]
    cols = ["#C7B8E2", "#F1C69B", "#A9D3D6", "#B6D5AA", "#ECDD9A"]
    ax.bar(range(5), vals, color=cols, edgecolor="#888", linewidth=0.8, width=0.68)
    ax.set_ylim(0, 1.05); ax.axis("off")
    ax.plot([-0.5, 4.5], [0, 0], color=MUTE, linewidth=1.2)
    save(fig, "bars.png")


# ---------------------------------------------------------------- slide2 icons
def _icon_ax():
    fig, ax = plt.subplots(figsize=(1.0, 1.0), dpi=300)
    ax.set_xlim(0, 10); ax.set_ylim(0, 10); ax.axis("off"); ax.set_aspect("equal")
    return fig, ax

LW = 2.2
def gen_icons():
    C = "#3A3A46"
    # upload
    fig, ax = _icon_ax()
    ax.add_patch(Rectangle((1.5, 1.2), 7, 4.6, fill=False, edgecolor=C, linewidth=LW))
    ax.annotate("", xy=(5, 9), xytext=(5, 4.2),
                arrowprops=dict(arrowstyle="-|>", color=C, lw=LW + 0.4))
    ax.plot([3.2, 5, 6.8], [6.6, 8.6, 6.6], color=C, lw=LW, solid_capstyle="round")
    save(fig, "icon_upload.png")
    # check (clipboard)
    fig, ax = _icon_ax()
    ax.add_patch(FancyBboxPatch((2, 1.3), 6, 7.4, boxstyle="round,pad=0.1,rounding_size=0.6",
                 fill=False, edgecolor=C, linewidth=LW))
    ax.add_patch(Rectangle((3.7, 8.0), 2.6, 1.2, facecolor=C, edgecolor=C))
    ax.plot([3.2, 4.5, 7.2], [4.6, 3.2, 6.2], color="#2E8B3D", lw=LW + 0.6,
            solid_capstyle="round", solid_joinstyle="round")
    save(fig, "icon_check.png")
    # api ( </> )
    fig, ax = _icon_ax()
    ax.plot([4, 1.6, 4], [8, 5, 2], color=C, lw=LW, solid_capstyle="round", solid_joinstyle="round")
    ax.plot([6, 8.4, 6], [8, 5, 2], color=C, lw=LW, solid_capstyle="round", solid_joinstyle="round")
    ax.plot([5.6, 4.4], [8.4, 1.6], color=C, lw=LW, solid_capstyle="round")
    save(fig, "icon_api.png")
    # gpu (chip)
    fig, ax = _icon_ax()
    ax.add_patch(Rectangle((2.6, 2.6), 4.8, 4.8, fill=False, edgecolor=C, linewidth=LW))
    ax.add_patch(Rectangle((3.9, 3.9), 2.2, 2.2, facecolor=C))
    for k in (3.6, 5.0, 6.4):
        ax.plot([k, k], [7.4, 8.6], color=C, lw=LW, solid_capstyle="round")
        ax.plot([k, k], [1.4, 2.6], color=C, lw=LW, solid_capstyle="round")
        ax.plot([7.4, 8.6], [k, k], color=C, lw=LW, solid_capstyle="round")
        ax.plot([1.4, 2.6], [k, k], color=C, lw=LW, solid_capstyle="round")
    save(fig, "icon_gpu.png")
    # panel (three columns)
    fig, ax = _icon_ax()
    for i, col in enumerate(["#B6D5AA", "#F1C69B", "#A9D3D6"]):
        ax.add_patch(Rectangle((1.3 + i * 2.7, 1.6), 2.1, 6.8, facecolor=col,
                     edgecolor=C, linewidth=1.6))
    save(fig, "icon_panel.png")
    # review (magnifier + check)
    fig, ax = _icon_ax()
    ax.add_patch(Circle((4.4, 5.6), 2.6, fill=False, edgecolor=C, linewidth=LW))
    ax.plot([6.3, 8.6], [3.7, 1.4], color=C, lw=LW + 0.8, solid_capstyle="round")
    ax.plot([3.2, 4.2, 5.8], [5.7, 4.6, 6.8], color="#2E8B3D", lw=LW,
            solid_capstyle="round", solid_joinstyle="round")
    save(fig, "icon_review.png")
    # report (document)
    fig, ax = _icon_ax()
    ax.add_patch(Polygon([(2.3, 1.2), (2.3, 8.8), (6.2, 8.8), (7.7, 7.3),
                         (7.7, 1.2)], closed=True, fill=False, edgecolor=C, linewidth=LW))
    ax.plot([6.2, 6.2, 7.7], [8.8, 7.3, 7.3], color=C, lw=LW, solid_joinstyle="round")
    for yy in (6.4, 5.3, 4.2, 3.1):
        ax.plot([3.4, 6.6], [yy, yy], color=MUTE, lw=1.6, solid_capstyle="round")
    save(fig, "icon_report.png")


if __name__ == "__main__":
    gen_gradcam(); gen_backbone(); gen_mkmmd(); gen_bbox()
    gen_gauge(); gen_bars(); gen_icons()
    print("assets written to", OUT)
    for f in sorted(os.listdir(OUT)):
        print("  ", f)
