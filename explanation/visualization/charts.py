"""
可视化图表生成 — 基于 matplotlib 的图表工具

提供:
  - radar_chart():      五维度风险雷达图
  - risk_gauge():       风险等级仪表条
  - batch_summary():    批量处理汇总图 (2×2 子图)

全部返回 PIL.Image，可直接嵌入 HTML 报告或保存为 PNG。
"""

import io
import numpy as np
from PIL import Image

# 非交互后端 (headless safe)
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.font_manager import FontProperties

# ==============================================================================
# 中文字体检测
# ==============================================================================

def _get_cjk_font():
    """检测可用的中文字体，回退到默认"""
    from matplotlib.font_manager import fontManager

    # 在所有已安装字体中搜索 CJK 字体
    cjk_keywords = [
        'Microsoft YaHei', 'SimHei', 'SimSun', 'KaiTi', 'STSong',
        'PingFang SC', 'Heiti SC', 'STHeiti',
        'WenQuanYi', 'Noto Sans CJK', 'Droid Sans Fallback',
    ]

    for f in fontManager.ttflist:
        for kw in cjk_keywords:
            if kw.lower() in f.name.lower():
                fp = FontProperties(family=f.name)
                return fp

    return None


_CJK_FONT = _get_cjk_font()

# 全局设置中文字体 (解决 legend/title 等 fallback 问题)
if _CJK_FONT:
    import matplotlib.pyplot as plt
    plt.rcParams['font.family'] = _CJK_FONT.get_name()
    # 负号显示修复
    plt.rcParams['axes.unicode_minus'] = False

# 维度标签 (中文 / 英文回退)
if _CJK_FONT:
    DIM_LABELS = ['检测置信度', '伪影强度', '篡改面积', '区域数量', '一致性']
    LABEL_PIE = ['AIGC伪造', '真实']
    LABEL_RISK = ['低风险', '中风险', '高风险']
else:
    DIM_LABELS = ['Fake Prob', 'Artifact\nIntensity', 'Tamper\nArea', 'Region\nCount', 'Consistency']
    LABEL_PIE = ['Fake', 'Real']
    LABEL_RISK = ['Low', 'Medium', 'High']

# ==============================================================================
# 颜色常量
# ==============================================================================

RISK_COLORS = {
    'low':    '#4CAF50',   # 绿
    'medium': '#FF9800',   # 橙
    'high':   '#F44336',   # 红
}

CHART_BG = '#FAFAFA'
RADAR_FILL = '#42A5F5'
RADAR_EDGE = '#1E88E5'
GRID_COLOR = '#BDBDBD'


# ==============================================================================
# 1. 五维度雷达图
# ==============================================================================

def radar_chart(dimension_scores: dict,
                size: tuple = (480, 480),
                title: str = None) -> Image.Image:
    """
    生成五维度风险雷达图。

    Args:
        dimension_scores: {'fake_prob': 0.039, 'artifact_intensity': 0.875, ...}
        size: 输出尺寸 (W, H)
        title: 图表标题，默认自动生成

    Returns:
        PIL.Image — RGBA 雷达图
    """
    labels = DIM_LABELS
    keys = ['fake_prob', 'artifact_intensity', 'tamper_area', 'region_count', 'consistency']
    values = [dimension_scores.get(k, 0) for k in keys]

    n = len(labels)
    angles = np.linspace(0, 2 * np.pi, n, endpoint=False).tolist()
    angles += angles[:1]  # 闭合
    values_closed = values + values[:1]

    # 创建极坐标图
    fig, ax = plt.subplots(figsize=(size[0] / 100, size[1] / 100),
                           subplot_kw={'projection': 'polar'},
                           facecolor=CHART_BG)
    fig.patch.set_alpha(0)

    # 绘制五边形网格
    ax.set_theta_offset(np.pi / 2)
    ax.set_theta_direction(-1)
    ax.set_xticks(angles[:-1])

    if _CJK_FONT:
        ax.set_xticklabels(labels, fontproperties=_CJK_FONT, fontsize=11)
    else:
        ax.set_xticklabels(labels, fontsize=10)

    # Y轴: 0.0 ~ 1.0
    ax.set_ylim(0, 1)
    ax.set_yticks([0.2, 0.4, 0.6, 0.8, 1.0])
    ax.set_yticklabels(['0.2', '0.4', '0.6', '0.8', '1.0'], fontsize=8, color='#757575')
    ax.yaxis.grid(True, color=GRID_COLOR, linestyle='--', linewidth=0.5)

    # 填充区域
    ax.fill(angles, values_closed, alpha=0.25, color=RADAR_FILL, linewidth=0)
    ax.plot(angles, values_closed, color=RADAR_EDGE, linewidth=2, marker='o',
            markersize=6, markerfacecolor='white', markeredgecolor=RADAR_EDGE, markeredgewidth=2)

    # 标注各点数值
    for angle, val in zip(angles[:-1], values):
        ha = 'center'
        offset = 0.12
        ax.annotate(
            f'{val:.3f}',
            xy=(angle, val),
            xytext=(angle, val + offset),
            fontsize=9, ha=ha,
            color='#424242',
        )

    # 标题
    if title is None:
        title = 'Risk Dimension Analysis' if not _CJK_FONT else '风险维度分析'
    if _CJK_FONT:
        ax.set_title(title, fontproperties=_CJK_FONT, fontsize=14, fontweight='bold', pad=20)
    else:
        ax.set_title(title, fontsize=14, fontweight='bold', pad=20)

    # 外圈美化
    ax.spines['polar'].set_visible(False)
    ax.set_rlabel_position(30)

    plt.tight_layout()

    # → PIL.Image
    buf = io.BytesIO()
    fig.savefig(buf, format='png', dpi=100, bbox_inches='tight',
                facecolor=fig.get_facecolor(), edgecolor='none')
    plt.close(fig)
    buf.seek(0)
    return Image.open(buf).convert('RGBA')


# ==============================================================================
# 2. 风险等级仪表条
# ==============================================================================

def risk_gauge(risk_score: float, risk_level: str,
               size: tuple = (600, 180),
               title: str = None) -> Image.Image:
    """
    生成风险等级仪表条 (横向分段条形图)。

    Args:
        risk_score: 综合风险分 (0~1)
        risk_level: low | medium | high
        size: 输出尺寸 (W, H)
        title: 图表标题

    Returns:
        PIL.Image
    """
    fig, ax = plt.subplots(figsize=(size[0] / 100, size[1] / 100),
                           facecolor=CHART_BG)
    fig.patch.set_alpha(0)

    # 绘制三段背景条
    segments = [
        (0.0, 0.35, RISK_COLORS['low'], LABEL_RISK[0]),
        (0.35, 0.70, RISK_COLORS['medium'], LABEL_RISK[1]),
        (0.70, 1.00, RISK_COLORS['high'], LABEL_RISK[2]),
    ]

    bar_height = 0.35
    y_center = 0.5

    for start, end, color, label in segments:
        width = end - start
        ax.barh(y_center, width, height=bar_height, left=start,
                color=color, alpha=0.4, edgecolor='white', linewidth=1.5)
        # 文字标签
        mid = start + width / 2
        ax.text(mid, y_center, label, ha='center', va='center',
                fontsize=11, fontweight='bold', color=color,
                fontproperties=_CJK_FONT)

    # 当前分数指示线
    ax.axvline(x=risk_score, ymin=0.15, ymax=0.85,
               color='#212121', linewidth=3, zorder=10)
    # 分数标注圆点
    ax.plot(risk_score, y_center, 'o', color='white', markersize=14,
            markeredgecolor='#212121', markeredgewidth=2.5, zorder=11)
    ax.text(risk_score, y_center + 0.22,
            f'{risk_score:.2f}',
            ha='center', va='bottom',
            fontsize=13, fontweight='bold', color='#212121')

    # 风险等级标签
    level_colors = {
        'low': RISK_COLORS['low'],
        'medium': RISK_COLORS['medium'],
        'high': RISK_COLORS['high'],
    }
    level_text = {'low': '低风险', 'medium': '中风险', 'high': '高风险'} if _CJK_FONT else \
                 {'low': 'Low Risk', 'medium': 'Medium Risk', 'high': 'High Risk'}
    level_color = level_colors.get(risk_level, '#212121')

    ax.text(0.5, 0.85, level_text.get(risk_level, risk_level),
            ha='center', va='center',
            fontsize=16, fontweight='bold', color=level_color,
            transform=ax.transAxes,
            fontproperties=_CJK_FONT)

    # 美化
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.set_xticks([0, 0.25, 0.5, 0.75, 1.0])
    ax.set_xticklabels(['0', '0.25', '0.5', '0.75', '1.0'], fontsize=9, color='#757575')
    ax.set_yticks([])
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.spines['left'].set_visible(False)
    ax.spines['bottom'].set_color('#E0E0E0')

    if title is None:
        title = '风险分数' if _CJK_FONT else 'Risk Score'
    if _CJK_FONT:
        ax.set_title(title, fontproperties=_CJK_FONT, fontsize=14, fontweight='bold')
    else:
        ax.set_title(title, fontsize=14, fontweight='bold')

    plt.tight_layout()

    buf = io.BytesIO()
    fig.savefig(buf, format='png', dpi=100, bbox_inches='tight',
                facecolor=fig.get_facecolor(), edgecolor='none')
    plt.close(fig)
    buf.seek(0)
    return Image.open(buf).convert('RGBA')


# ==============================================================================
# 3. 批量处理汇总图 (2×2)
# ==============================================================================

def batch_summary(results: list,
                  size: tuple = (800, 640),
                  title: str = None) -> Image.Image:
    """
    生成批量处理汇总图 (2×2 子图布局):

    ┌─────────────┬─────────────┐
    │  label 饼图   │ risk 柱状图  │
    ├─────────────┼─────────────┤
    │ fake_prob    │ risk_score  │
    │   直方图      │   分布图     │
    └─────────────┴─────────────┘

    Args:
        results: pipeline.run() 结果列表 (每项含 label, fake_prob, risk_score, risk_level)
        size: 输出尺寸 (W, H)
        title: 总标题

    Returns:
        PIL.Image
    """
    if not results:
        # 空结果返回占位图
        return Image.new('RGBA', size, (250, 250, 250, 255))

    labels_list = [r.get('label', 'real') for r in results]
    fake_probs = [r.get('fake_prob', 0) for r in results]
    risk_scores = [r.get('risk_score', 0) for r in results]
    risk_levels = [r.get('risk_level', 'low') for r in results]

    fig, axes = plt.subplots(2, 2, figsize=(size[0] / 100, size[1] / 100),
                             facecolor=CHART_BG)
    fig.patch.set_alpha(0)

    # ---- 子图1: label 饼图 ----
    ax1 = axes[0, 0]
    fake_count = sum(1 for l in labels_list if l == 'fake')
    real_count = len(labels_list) - fake_count
    wedges, texts, autotexts = ax1.pie(
        [fake_count, real_count],
        labels=None,
        autopct='%1.1f%%',
        colors=['#F44336', '#4CAF50'],
        startangle=90,
        wedgeprops={'edgecolor': 'white', 'linewidth': 1.5},
        textprops={'fontsize': 11, 'fontweight': 'bold'},
    )
    # 图例
    legend_labels = ['AIGC伪造', '真实'] if _CJK_FONT else ['Fake', 'Real']
    ax1.legend(wedges, [
        f'{legend_labels[0]} ({fake_count})',
        f'{legend_labels[1]} ({real_count})',
    ], loc='lower center', fontsize=9)
    pie_title = '检测结果分布' if _CJK_FONT else 'Detection Distribution'
    if _CJK_FONT:
        ax1.set_title(pie_title, fontproperties=_CJK_FONT, fontsize=13, fontweight='bold')
    else:
        ax1.set_title(pie_title, fontsize=13, fontweight='bold')

    # ---- 子图2: risk_level 柱状图 ----
    ax2 = axes[0, 1]
    level_counts = {
        'low': sum(1 for l in risk_levels if l == 'low'),
        'medium': sum(1 for l in risk_levels if l == 'medium'),
        'high': sum(1 for l in risk_levels if l == 'high'),
    }
    bar_labels = LABEL_RISK
    bar_values = [level_counts[k] for k in ['low', 'medium', 'high']]
    bar_colors = [RISK_COLORS[k] for k in ['low', 'medium', 'high']]
    bars = ax2.bar(bar_labels, bar_values, color=bar_colors, alpha=0.75,
                   edgecolor='white', linewidth=1.5)
    for bar, val in zip(bars, bar_values):
        ax2.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.2,
                 str(val), ha='center', fontsize=11, fontweight='bold', color='#424242')
    bar_title = '风险等级分布' if _CJK_FONT else 'Risk Level Distribution'
    if _CJK_FONT:
        ax2.set_title(bar_title, fontproperties=_CJK_FONT, fontsize=13, fontweight='bold')
        ax2.set_xticks(range(len(bar_labels)))
        ax2.set_xticklabels(bar_labels, fontproperties=_CJK_FONT)
    else:
        ax2.set_title(bar_title, fontsize=13, fontweight='bold')
    ax2.spines['top'].set_visible(False)
    ax2.spines['right'].set_visible(False)
    ax2.spines['left'].set_color('#E0E0E0')
    ax2.spines['bottom'].set_color('#E0E0E0')
    ax2.tick_params(axis='y', colors='#757575')

    # ---- 子图3: fake_prob 直方图 ----
    ax3 = axes[1, 0]
    ax3.hist(fake_probs, bins=12, color='#42A5F5', alpha=0.75, edgecolor='white', linewidth=1.2)
    ax3.axvline(x=0.5, color='#F44336', linestyle='--', linewidth=1.5, label='阈值 0.5')
    hist_title = '伪造概率分布' if _CJK_FONT else 'Fake Probability Histogram'
    if _CJK_FONT:
        ax3.set_title(hist_title, fontproperties=_CJK_FONT, fontsize=13, fontweight='bold')
        ax3.set_xlabel('fake_prob', fontsize=10, color='#757575')
        ax3.set_ylabel('数量', fontproperties=_CJK_FONT, fontsize=10, color='#757575')
        ax3.legend(fontsize=8, prop=_CJK_FONT)
    else:
        ax3.set_title(hist_title, fontsize=13, fontweight='bold')
        ax3.set_xlabel('fake_prob', fontsize=10, color='#757575')
        ax3.set_ylabel('Count', fontsize=10, color='#757575')
        ax3.legend(fontsize=8)
    ax3.set_xlim(0, 1)
    ax3.spines['top'].set_visible(False)
    ax3.spines['right'].set_visible(False)
    ax3.spines['left'].set_color('#E0E0E0')
    ax3.spines['bottom'].set_color('#E0E0E0')
    ax3.tick_params(colors='#757575')

    # ---- 子图4: risk_score 箱线图 + 散点 ----
    ax4 = axes[1, 1]
    # 分段背景
    for lo, hi, color in [
        (0.0, 0.35, RISK_COLORS['low']),
        (0.35, 0.70, RISK_COLORS['medium']),
        (0.70, 1.0, RISK_COLORS['high']),
    ]:
        ax4.axvspan(lo, hi, alpha=0.08, color=color, linewidth=0)
    # 散点图
    y_positions = np.random.uniform(-0.15, 0.15, len(risk_scores))  # 抖动
    ax4.scatter(risk_scores, y_positions, alpha=0.6, color='#1E88E5',
                edgecolors='white', linewidth=0.5, s=40, zorder=5)
    ax4.set_ylim(-0.5, 0.5)
    ax4.set_yticks([])
    ax4.set_xlim(0, 1)
    ax4.set_xticks([0, 0.25, 0.5, 0.75, 1.0])
    ax4.set_xticklabels(['0', '0.25', '0.5', '0.75', '1.0'], fontsize=9, color='#757575')
    dist_title = '风险分数分布' if _CJK_FONT else 'Risk Score Distribution'
    if _CJK_FONT:
        ax4.set_title(dist_title, fontproperties=_CJK_FONT, fontsize=13, fontweight='bold')
        ax4.set_xlabel('risk_score', fontsize=10, color='#757575')
    else:
        ax4.set_title(dist_title, fontsize=13, fontweight='bold')
        ax4.set_xlabel('risk_score', fontsize=10, color='#757575')
    ax4.spines['top'].set_visible(False)
    ax4.spines['right'].set_visible(False)
    ax4.spines['left'].set_visible(False)
    ax4.spines['bottom'].set_color('#E0E0E0')
    ax4.tick_params(colors='#757575')
    # risk_level 图例
    from matplotlib.patches import Patch
    legend_elements = [
        Patch(facecolor=RISK_COLORS['low'], alpha=0.3, label=LABEL_RISK[0]),
        Patch(facecolor=RISK_COLORS['medium'], alpha=0.3, label=LABEL_RISK[1]),
        Patch(facecolor=RISK_COLORS['high'], alpha=0.3, label=LABEL_RISK[2]),
    ]
    if _CJK_FONT:
        ax4.legend(handles=legend_elements, fontsize=8, loc='upper right', prop=_CJK_FONT)
    else:
        ax4.legend(handles=legend_elements, fontsize=8, loc='upper right')

    # 总标题
    if title is None:
        title = f'TraceGuard 批量分析摘要 (n={len(results)})' if _CJK_FONT else \
                f'TraceGuard Batch Summary (n={len(results)})'
    if _CJK_FONT:
        fig.suptitle(title, fontproperties=_CJK_FONT, fontsize=16, fontweight='bold', y=1.02)
    else:
        fig.suptitle(title, fontsize=16, fontweight='bold', y=1.02)

    plt.tight_layout()

    buf = io.BytesIO()
    fig.savefig(buf, format='png', dpi=100, bbox_inches='tight',
                facecolor=fig.get_facecolor(), edgecolor='none')
    plt.close(fig)
    buf.seek(0)
    return Image.open(buf).convert('RGBA')


# ==============================================================================
# 便捷函数: 直接从 pipeline result 生成全部图表
# ==============================================================================

def all_charts(result: dict, batch_results: list = None) -> dict:
    """
    从 pipeline 结果一键生成所有可用图表。

    Args:
        result: 单图 pipeline.run() 输出
        batch_results: 批量结果列表 (可选)

    Returns:
        dict: {'radar': PIL.Image, 'gauge': PIL.Image, 'summary': PIL.Image|None}
    """
    charts = {}

    dims = result.get('dimension_scores', {})
    if dims:
        charts['radar'] = radar_chart(dims)

    risk_score = result.get('risk_score', 0)
    risk_level = result.get('risk_level', 'low')
    charts['gauge'] = risk_gauge(risk_score, risk_level)

    if batch_results:
        charts['summary'] = batch_summary(batch_results)
    else:
        charts['summary'] = None

    return charts
