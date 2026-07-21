"""Build background_threat_chain_drawio_v2.drawio (Chapter-1 background figure).

视觉语言参照《AIGC 的伪造媒体内容检测与安全防御申报材料》背景概述页的排版范式
（贯穿式阶段箭头 + 阶段胶囊配色递进 + 白底橙描边内容卡 + 右侧红框数据卡 +
红色关键词强调），但全部内容、数据与配图均为本作品自产：

- 不复制该 PPT 的任何图片素材（第三方/网络来源，版权与身份红线）。
- 不出现实验室、导师、团队等身份措辞。
- 案例图取自本仓库 data/case_images/，数值取自
  experiments/socialmedia/verified_results/case_manifest_extended.csv
  （degraded 案例，BigGAN，fake_prob 0.9671 -> 0.0180 after Facebook）。
- 图内不放报告标题与高层结论句（队长要求）。

Usage: E:\\aNB\\envs\\traceguard\\python.exe docs/figures/background/build_threat_chain_drawio.py
Then export with draw.io CLI (see README).
"""

import base64
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent / "background_threat_chain_drawio_v2.drawio"

IMG_A = ROOT / "data/case_images/degraded_original.png"
IMG_B = ROOT / "data/case_images/degraded_facebook.jpg"

YAHEI = "fontFamily=Microsoft YaHei;"

# ── 取自参考版式的配色 ────────────────────────────────
TAN = "#CFC6AE"        # 贯穿箭头
BEIGE = "#F2EFE6"      # 前段阶段胶囊（威胁尚未加剧）
CYAN = "#4CBEF2"       # 第三阶段（对抗加剧）
NAVY = "#17376B"       # 末段阶段（威胁最重）
ORANGE = "#E29B3C"     # 内容卡描边
RED = "#C00000"        # 关键词/失效强调
BLUE = "#1F4E9C"       # 数据卡标题
GREEN = "#2E7D32"      # 本作品/有效
INK = "#1A1A1A"
GRAY = "#808080"

cells = []


def cell(cid, style, x, y, w, h, value=""):
    cells.append(
        f'<mxCell id="{cid}" parent="1" style="{style}" value="{value}" vertex="1">'
        f'<mxGeometry height="{h}" width="{w}" x="{x}" y="{y}" as="geometry"/></mxCell>'
    )


def edge(cid, src, dst, style):
    cells.append(
        f'<mxCell id="{cid}" parent="1" style="{style}" edge="1" source="{src}" target="{dst}">'
        f'<mxGeometry relative="1" as="geometry"/></mxCell>'
    )


def txt(cid, x, y, w, h, value, size=14, color=INK, align="center", bold=False):
    v = f"&lt;b&gt;{value}&lt;/b&gt;" if bold else value
    style = (
        f"text;strokeColor=none;fillColor=none;align={align};verticalAlign=middle;"
        f"whiteSpace=wrap;html=1;fontColor={color};{YAHEI}fontSize={size};spacing=0;"
    )
    cell(cid, style, x, y, w, h, v)


# 注意：这些串最终落在 mxCell 的 value="..." 属性里，属性用双引号定界，
# 因此 HTML 属性的引号必须写成 &quot;，否则 XML 属性会被提前截断（整张图后半段丢失）。
def red(s):
    return f"&lt;font color=&quot;{RED}&quot;&gt;{s}&lt;/font&gt;"


def blue(s):
    return f"&lt;font color=&quot;{BLUE}&quot;&gt;{s}&lt;/font&gt;"


# ── 版面纵向锚点（收紧上下留白）────────────────────────
CAP_Y = 90     # 阶段胶囊
CARD_Y = 158   # 阶段内容卡
BAR_Y = 322    # 三道防线条
HARM_Y = 432   # 现实危害行
EV_Y = 71      # 右侧数据卡

# ── 画布 ──────────────────────────────────────────────
cell("bg", "rounded=0;whiteSpace=wrap;html=1;fillColor=#FFFFFF;strokeColor=#D6D6D6;strokeWidth=1;",
     20, 20, 1560, 490)

# ── 贯穿式阶段箭头（先画，压在卡片下层）────────────────
cell("arrow_shaft", f"rounded=0;whiteSpace=wrap;html=1;fillColor={TAN};strokeColor=none;",
     58, 118, 950, 38)
cell("arrow_head", f"shape=triangle;direction=east;whiteSpace=wrap;html=1;fillColor={TAN};strokeColor=none;",
     1006, 100, 44, 74)

# ── 四阶段：胶囊标签 + 白底橙描边内容卡 ────────────────
CAP = ("rounded=1;absoluteArcSize=1;arcSize=14;whiteSpace=wrap;html=1;strokeColor=none;"
       "align=center;verticalAlign=middle;" + YAHEI)
CARD = ("rounded=1;absoluteArcSize=1;arcSize=16;whiteSpace=wrap;html=1;fillColor=#FFFFFF;"
        f"strokeColor={ORANGE};strokeWidth=2;align=center;verticalAlign=top;" + YAHEI)

stages = [
    ("s1", 60, BEIGE, INK, "① AIGC 图像生成",
     ["生成端安全对齐", red("超监管内容可绕过")]),
    ("s2", 305, BEIGE, INK, "② 社交平台发布",
     ["附显式标识", "与生成元数据"]),
    ("s3", 550, CYAN, INK, "③ 平台转码压缩",
     ["转码 · 有损压缩", "截图转存"]),
    ("s4", 795, NAVY, "#FFFFFF", "④ 传播后「裸图」",
     [red("标识与元数据"), red("被系统性剥离")]),
]

for cid, x, fill, fc, title, lines in stages:
    cell(cid + "_cap", CAP + f"fillColor={fill};fontColor={fc};fontSize=17;fontStyle=1;",
         x, CAP_Y, 225, 54, title)
    cell(cid + "_card", CARD, x, CARD_Y, 225, 118)
    for i, ln in enumerate(lines):
        txt(f"{cid}_l{i}", x + 12, CARD_Y + 24 + i * 34, 201, 30, ln, size=14)

# ── 三道防线：按覆盖的阶段跨列对齐 ─────────────────────
BAR = ("rounded=1;absoluteArcSize=1;arcSize=14;whiteSpace=wrap;html=1;fillColor=#FFFFFF;"
       "strokeWidth=2;align=center;verticalAlign=middle;" + YAHEI + "fontSize=14;")

cell("d1", BAR + f"strokeColor={RED};fontColor={INK};", 60, BAR_Y, 225, 84,
     "&lt;b&gt;第一道防线&lt;/b&gt;&lt;br&gt;生成端安全对齐&lt;br&gt;" + red("&lt;b&gt;× 被超监管内容绕过&lt;/b&gt;"))
cell("d2", BAR + f"strokeColor={RED};fontColor={INK};", 305, BAR_Y, 470, 84,
     "&lt;b&gt;第二道防线&lt;/b&gt;&lt;br&gt;显式标识与生成元数据&lt;br&gt;" + red("&lt;b&gt;× 传播中被系统性剥离&lt;/b&gt;"))
cell("d3", BAR + f"strokeColor={GREEN};fillColor=#F1F8F1;fontColor={INK};", 795, BAR_Y, 255, 84,
     "&lt;b&gt;第三道防线&lt;/b&gt;&lt;br&gt;传播后第三方审核&lt;br&gt;"
     f"&lt;font color=&quot;{GREEN}&quot;&gt;&lt;b&gt;√ 本作品 TraceGuard&lt;/b&gt;&lt;/font&gt;")

# 虚线须垂直：entryX 按“阶段卡中心落在防线条上的相对位置”算，
# 否则跨列的第二道防线会拉出一条斜线。
DASH = "endArrow=none;dashed=1;html=1;strokeWidth=1.5;exitX=0.5;exitY=1;entryY=0;"
edge("dl1", "s1_card", "d1", DASH + f"strokeColor={RED};entryX=0.5;")
edge("dl2a", "s2_card", "d2", DASH + f"strokeColor={RED};entryX=0.24;")
edge("dl2b", "s3_card", "d2", DASH + f"strokeColor={RED};entryX=0.76;")
edge("dl3", "s4_card", "d3", DASH + f"strokeColor={GREEN};entryX=0.44;")

# ── 威胁后果条（阶段链下游的现实危害）──────────────────
txt("harm", 60, HARM_Y, 990, 34,
    "现实危害：" + red("&lt;b&gt;假新闻配图&lt;/b&gt;") + " · " + red("&lt;b&gt;舆情误导&lt;/b&gt;")
    + " · " + red("&lt;b&gt;电子证据污染&lt;/b&gt;"),
    size=16, align="center")

# ── 右侧红框数据卡（照参考版式的数据卡样式）────────────
cell("ev", "rounded=1;absoluteArcSize=1;arcSize=16;whiteSpace=wrap;html=1;fillColor=#FFFFFF;"
     f"strokeColor={RED};strokeWidth=2;", 1090, EV_Y, 460, 424)

txt("ev_h", 1110, EV_Y + 20, 420, 30, "同图传播前后 · 检测证据衰减（实测）", size=17, color=BLUE, bold=True)
txt("ev_s", 1110, EV_Y + 52, 420, 24, "BigGAN 伪造样本 · 固定权重一次确定性推理", size=12, color=GRAY)

b64a = base64.b64encode(IMG_A.read_bytes()).decode()
b64b = base64.b64encode(IMG_B.read_bytes()).decode()
IMGSTYLE = "shape=image;imageAspect=1;verticalLabelPosition=bottom;verticalAlign=top;"
cell("img_a", IMGSTYLE + f"image=data:image/png,{b64a};", 1122, EV_Y + 90, 150, 150)
cell("img_b", IMGSTYLE + f"image=data:image/jpeg,{b64b};", 1358, EV_Y + 90, 150, 150)
edge("ar_ev", "img_a", "img_b",
     f"html=1;strokeColor={ORANGE};strokeWidth=3;endArrow=blockThin;endFill=1;"
     "exitX=1;exitY=0.5;entryX=0;entryY=0.5;")

txt("ca1", 1122, EV_Y + 246, 150, 24, "Original", size=14, bold=True)
txt("cb1", 1358, EV_Y + 246, 150, 24, "经 Facebook 传播后", size=14, bold=True)
txt("ca2", 1112, EV_Y + 274, 170, 44, "&lt;b&gt;0.9671&lt;/b&gt;", size=30, color=RED)
txt("cb2", 1348, EV_Y + 274, 170, 44, "&lt;b&gt;0.0180&lt;/b&gt;", size=30, color=RED)
txt("ca3", 1122, EV_Y + 320, 150, 24, "伪造概率 · 判定：伪", size=12, color=GRAY)
txt("cb3", 1348, EV_Y + 320, 170, 24, "伪造概率 · 判定：真", size=12, color=GRAY)
txt("cb4", 1348, EV_Y + 342, 170, 24, "（证据不足 → 转人工）", size=12, color=GREEN)

txt("ev_f", 1110, EV_Y + 380, 420, 32,
    "数据来源：case_manifest_extended.csv&lt;br&gt;单次确定性推理，不代表跨随机种子置信区间",
    size=11, color=GRAY)

xml = (
    '<?xml version="1.0" encoding="UTF-8"?>\n'
    '<mxfile host="Electron" version="30.3.6">\n'
    '  <diagram id="threat-chain-v2" name="第一章背景图：威胁链路与证据衰减">\n'
    '<mxGraphModel dx="800" dy="600" grid="1" gridSize="10" page="1" pageWidth="1600" pageHeight="530">'
    "<root>"
    '<mxCell id="0"/><mxCell id="1" parent="0"/>'
    + "".join(cells)
    + "</root></mxGraphModel>\n  </diagram>\n</mxfile>\n"
)
OUT.write_text(xml, encoding="utf-8")
print("wrote", OUT, len(xml), "bytes")
