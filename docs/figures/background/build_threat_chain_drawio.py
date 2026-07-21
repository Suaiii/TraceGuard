"""Build background_threat_chain_drawio_v1.drawio (Chapter-1 background figure).

Visual language matches docs/figures/system/system_architecture_drawio_v1.drawio:
canvas #F8FAFC / #CBD5E1, rounded pastel cards with saturated borders,
Microsoft YaHei, no in-figure title (队长要求：图内标题全删).

Case images are embedded as base64 data URIs so the .drawio is self-contained.
Numbers come from experiments/socialmedia/verified_results/case_manifest_extended.csv
(degraded case, BigGAN, fake_prob 0.9671 -> 0.0180 after Facebook).

Usage: python docs/figures/background/build_threat_chain_drawio.py
Then export with draw.io CLI (see README).
"""

import base64
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent / "background_threat_chain_drawio_v1.drawio"

IMG_A = ROOT / "data/case_images/degraded_original.png"
IMG_B = ROOT / "data/case_images/degraded_facebook.jpg"

YAHEI = "fontFamily=Microsoft YaHei;"
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


def txt(cid, x, y, w, h, value, size=14, color="#0F172A", align="center"):
    style = (
        f"text;strokeColor=none;fillColor=none;align={align};verticalAlign=middle;"
        f"whiteSpace=wrap;html=1;fontColor={color};{YAHEI}fontSize={size};spacing=0;"
    )
    cell(cid, style, x, y, w, h, value)


# ── canvas ────────────────────────────────────────────────────
cell("canvas_bg", "rounded=0;whiteSpace=wrap;html=1;fillColor=#F8FAFC;strokeColor=#CBD5E1;strokeWidth=1;", 20, 20, 1560, 600)

# ── threat chain: four stage cards ────────────────────────────
CARD = "rounded=1;arcSize=10;whiteSpace=wrap;html=1;strokeWidth=2;shadow=0;" + YAHEI
stages = [
    ("st1", 70, "#F2EEFA", "#7C6AB0", "AIGC 图像生成",
     "超监管内容可绕过&lt;br&gt;生成端安全对齐"),
    ("st2", 310, "#E0F2FE", "#0284C7", "社交平台发布",
     "附显式标识&lt;br&gt;与元数据"),
    ("st3", 550, "#FFF9DE", "#D8B84E", "平台处理",
     "转码 · 压缩&lt;br&gt;截图转存"),
    ("st4", 790, "#EEF2F6", "#64748B", "传播后「裸图」",
     "标识与元数据&lt;br&gt;被系统性剥离"),
]
for cid, x, fill, stroke, title, sub in stages:
    cell(cid, CARD + f"fillColor={fill};strokeColor={stroke};", x, 170, 200, 140)
    txt(cid + "_t", x + 10, 190, 180, 44, f"&lt;b&gt;{title}&lt;/b&gt;", size=17)
    txt(cid + "_s", x + 10, 240, 180, 50, sub, size=13, color="#64748B")

ARROW = ("edgeStyle=orthogonalEdgeStyle;rounded=0;html=1;strokeColor=#475569;"
         "strokeWidth=2.5;endArrow=blockThin;endFill=1;")
for i in (1, 2, 3):
    edge(f"ar{i}", f"st{i}", f"st{i+1}", ARROW + "exitX=1;exitY=0.5;entryX=0;entryY=0.5;")

# ── threat banner above end of chain ──────────────────────────
cell("threats", CARD + "fillColor=#FEE2E2;strokeColor=#DC2626;dashed=0;", 640, 60, 350, 56,
     "&lt;b&gt;假新闻配图 · 舆情误导 · 电子证据污染&lt;/b&gt;")
cells[-1] = cells[-1].replace('style="rounded=1', 'style="fontColor=#B91C1C;fontSize=15;align=center;verticalAlign=middle;rounded=1')
edge("ar_threat", "st4", "threats",
     "edgeStyle=orthogonalEdgeStyle;rounded=0;html=1;strokeColor=#DC2626;strokeWidth=2;"
     "endArrow=blockThin;endFill=1;exitX=0.5;exitY=0;entryX=0.5;entryY=1;")

# ── three lines of defense ────────────────────────────────────
DEF = ("rounded=1;arcSize=12;whiteSpace=wrap;html=1;fillColor=#FFFFFF;strokeWidth=2;"
       "align=center;verticalAlign=middle;" + YAHEI)
cell("d1", DEF + "strokeColor=#DC2626;fontSize=13;fontColor=#0F172A;", 50, 390, 240, 70,
     "&lt;b&gt;第一道防线：生成端对齐&lt;/b&gt;&lt;br&gt;"
     "&lt;font color=&quot;#DC2626&quot;&gt;× 可被超监管内容绕过&lt;/font&gt;")
cell("d2", DEF + "strokeColor=#DC2626;fontSize=13;fontColor=#0F172A;", 530, 390, 240, 70,
     "&lt;b&gt;第二道防线：标识与元数据&lt;/b&gt;&lt;br&gt;"
     "&lt;font color=&quot;#DC2626&quot;&gt;× 传播中被系统性剥离&lt;/font&gt;")
cell("d3", DEF + "strokeColor=#15803D;fillColor=#EDF6E7;fontSize=13;fontColor=#0F172A;", 770, 500, 240, 70,
     "&lt;b&gt;第三道防线：传播后第三方审核&lt;/b&gt;&lt;br&gt;"
     "&lt;font color=&quot;#15803D&quot;&gt;√ 本作品 TraceGuard&lt;/font&gt;")
DASH_R = "endArrow=none;dashed=1;html=1;strokeColor=#DC2626;strokeWidth=1.5;"
DASH_G = "endArrow=none;dashed=1;html=1;strokeColor=#15803D;strokeWidth=1.5;"
edge("dl1", "st1", "d1", DASH_R + "exitX=0.5;exitY=1;entryX=0.5;entryY=0;")
edge("dl2", "st3", "d2", DASH_R + "exitX=0.5;exitY=1;entryX=0.5;entryY=0;")
edge("dl3", "st4", "d3", DASH_G + "exitX=0.5;exitY=1;entryX=0.5;entryY=0;")

# ── right panel: measured evidence decay ──────────────────────
cell("ev_group", CARD + "absoluteArcSize=1;arcSize=14;fillColor=#FFFFFF;strokeColor=#CBD5E1;", 1060, 60, 490, 530)
txt("ev_h", 1080, 80, 450, 40,
    "&lt;b&gt;同图传播前后 · 检测证据衰减（实测）&lt;/b&gt;", size=17)
txt("ev_sub", 1080, 118, 450, 26,
    "BigGAN 伪造样本 · 固定权重一次确定性推理", size=12, color="#64748B")

b64a = base64.b64encode(IMG_A.read_bytes()).decode()
b64b = base64.b64encode(IMG_B.read_bytes()).decode()
IMGSTYLE = "shape=image;imageAspect=1;verticalLabelPosition=bottom;verticalAlign=top;"
cell("img_a", IMGSTYLE + f"image=data:image/png,{b64a};", 1090, 170, 180, 180)
cell("img_b", IMGSTYLE + f"image=data:image/jpeg,{b64b};", 1340, 170, 180, 180)
edge("ar_ev", "img_a", "img_b",
     "html=1;strokeColor=#F59E0B;strokeWidth=3;endArrow=blockThin;endFill=1;"
     "exitX=1;exitY=0.5;entryX=0;entryY=0.5;")

txt("cap_a1", 1090, 360, 180, 28, "&lt;b&gt;Original&lt;/b&gt;", size=15)
txt("cap_a2", 1090, 390, 180, 28, "伪造概率 &lt;b&gt;0.9671&lt;/b&gt;", size=14)
txt("cap_a3", 1090, 418, 180, 26, "判定：伪", size=13, color="#DC2626")
txt("cap_b1", 1340, 360, 180, 28, "&lt;b&gt;Facebook 传播后&lt;/b&gt;", size=15)
txt("cap_b2", 1340, 390, 180, 28, "伪造概率 &lt;b&gt;0.0180&lt;/b&gt;", size=14)
txt("cap_b3", 1340, 418, 180, 40, "判定：真&lt;br&gt;（证据不足 → 转人工）", size=13, color="#15803D")

txt("ev_foot", 1080, 540, 450, 30,
    "数值来源 case_manifest_extended.csv · 不代表跨随机种子置信区间",
    size=11, color="#94A3B8")

xml = (
    '<?xml version="1.0" encoding="UTF-8"?>\n'
    '<mxfile host="Electron" version="30.3.6">\n'
    '  <diagram id="threat-chain" name="第一章背景图：威胁链路与证据衰减">\n'
    '<mxGraphModel dx="800" dy="600" grid="1" gridSize="10" page="1" pageWidth="1600" pageHeight="660">'
    "<root>"
    '<mxCell id="0"/><mxCell id="1" parent="0"/>'
    + "".join(cells)
    + "</root></mxGraphModel>\n  </diagram>\n</mxfile>\n"
)
OUT.write_text(xml, encoding="utf-8")
print("wrote", OUT, len(xml), "bytes")
