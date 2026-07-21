"""Build the two Chapter-1 background figures (draw.io sources).

产出两张图（2026-07-21 队长要求：原来一张 1600 宽的横图压进 A4 页宽后字号只剩约 4pt，
根本看不清；拆成两张，并按论证逻辑分工）：

  1) background_threat_chain_drawio_v3.drawio  → 图 1.1 威胁链路与三道防线（论证：为何需要第三道防线）
  2) background_evidence_decay_drawio_v1.drawio → 图 1.2 同图传播前后检测输出对比（证据：实测衰减）

版面尺寸的硬约束：正文 textwidth = 21 - 2.86 - 2.59 = 15.55cm。图按 \\linewidth 排版时
  实际字号(mm) = fontSize × 155.5 / canvas_width
故画布宽度必须压到 760~960 单位，正文字号取 20 左右才能落在 9~11pt 的可读区间。
（旧版 1600 宽 + fontSize 14 → 约 3.9pt，不可读。）

视觉语言参照《AIGC 的伪造媒体内容检测与安全防御申报材料》背景概述页的排版范式
（贯穿式阶段箭头 + 阶段胶囊配色递进 + 白底橙描边内容卡 + 红框数据卡 + 红色关键词强调），
但只借版式不借素材：不复制该 PPT 任何图片（第三方/网络来源，版权与身份红线），
不出现实验室、导师、团队等身份措辞。案例图与数值均为本作品自产。

Usage: E:\\aNB\\envs\\traceguard\\python.exe docs/figures/background/build_threat_chain_drawio.py
Then export with draw.io CLI (see README).
"""

import base64
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = Path(__file__).resolve().parents[3]

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
GRAY = "#767676"


class Doc:
    """收集 mxCell 的容器；一个 Doc 对应一张图。"""

    def __init__(self, name, page_w, page_h):
        self.cells = []
        self.name = name
        self.page_w = page_w
        self.page_h = page_h

    def cell(self, cid, style, x, y, w, h, value=""):
        self.cells.append(
            f'<mxCell id="{cid}" parent="1" style="{style}" value="{value}" vertex="1">'
            f'<mxGeometry height="{h}" width="{w}" x="{x}" y="{y}" as="geometry"/></mxCell>'
        )

    def edge(self, cid, src, dst, style):
        self.cells.append(
            f'<mxCell id="{cid}" parent="1" style="{style}" edge="1" source="{src}" target="{dst}">'
            f'<mxGeometry relative="1" as="geometry"/></mxCell>'
        )

    def txt(self, cid, x, y, w, h, value, size=20, color=INK, align="center", bold=False):
        v = f"&lt;b&gt;{value}&lt;/b&gt;" if bold else value
        self.cell(cid,
                  f"text;strokeColor=none;fillColor=none;align={align};verticalAlign=middle;"
                  f"whiteSpace=wrap;html=1;fontColor={color};{YAHEI}fontSize={size};spacing=0;",
                  x, y, w, h, v)

    def write(self, path, diagram_id):
        xml = (
            '<?xml version="1.0" encoding="UTF-8"?>\n'
            f'<mxfile host="Electron" version="30.3.6">\n'
            f'  <diagram id="{diagram_id}" name="{self.name}">\n'
            f'<mxGraphModel dx="800" dy="600" grid="1" gridSize="10" page="1" '
            f'pageWidth="{self.page_w}" pageHeight="{self.page_h}">'
            "<root>"
            '<mxCell id="0"/><mxCell id="1" parent="0"/>'
            + "".join(self.cells)
            + "</root></mxGraphModel>\n  </diagram>\n</mxfile>\n"
        )
        path.write_text(xml, encoding="utf-8")
        print("wrote", path.name, len(xml), "bytes")


# 注意：以下串最终落在 mxCell 的 value="..." 属性里，属性用双引号定界，
# 因此内嵌 HTML 的引号必须写成 &quot;，否则 XML 属性会被提前截断（整张图后半段丢失）。
def color_span(s, c, bold=False):
    inner = f"&lt;b&gt;{s}&lt;/b&gt;" if bold else s
    return f"&lt;font color=&quot;{c}&quot;&gt;{inner}&lt;/font&gt;"


# ══════════════════════════════════════════════════════
# 图 1.1  威胁链路与三道防线
# ══════════════════════════════════════════════════════
a = Doc("图1.1 威胁链路与三道防线", 1000, 500)

a.cell("bg", "rounded=0;whiteSpace=wrap;html=1;fillColor=#FFFFFF;strokeColor=#D6D6D6;strokeWidth=1;",
       20, 20, 960, 450)

# 贯穿式阶段箭头（先画，压在胶囊下层）
a.cell("shaft", f"rounded=0;whiteSpace=wrap;html=1;fillColor={TAN};strokeColor=none;",
       30, 92, 900, 32)
a.cell("head", f"shape=triangle;direction=east;whiteSpace=wrap;html=1;fillColor={TAN};strokeColor=none;",
       928, 76, 44, 64)

CAP = ("rounded=1;absoluteArcSize=1;arcSize=14;whiteSpace=wrap;html=1;strokeColor=none;"
       "align=center;verticalAlign=middle;fontSize=23;fontStyle=1;" + YAHEI)
CARD = ("rounded=1;absoluteArcSize=1;arcSize=16;whiteSpace=wrap;html=1;fillColor=#FFFFFF;"
        f"strokeColor={ORANGE};strokeWidth=2;" + YAHEI)

# 阶段列：x 起点、胶囊底色、胶囊字色、标题、卡内两行
stages = [
    ("s1", 20, BEIGE, INK, "① AIGC 图像生成",
     ["生成端安全对齐", color_span("超监管内容可绕过", RED)]),
    ("s2", 250, BEIGE, INK, "② 社交平台发布",
     ["附显式标识", "与生成元数据"]),
    ("s3", 480, CYAN, INK, "③ 平台转码压缩",
     ["转码 · 有损压缩", "截图转存"]),
    ("s4", 710, NAVY, "#FFFFFF", "④ 传播后裸图",
     [color_span("标识与元数据", RED), color_span("被系统性剥离", RED)]),
]
for cid, x, fill, fc, title, lines in stages:
    a.cell(cid + "_cap", CAP + f"fillColor={fill};fontColor={fc};", x, 64, 210, 52, title)
    a.cell(cid + "_card", CARD, x, 128, 210, 110)
    for i, ln in enumerate(lines):
        a.txt(f"{cid}_l{i}", x + 10, 150 + i * 36, 190, 32, ln, size=20)

# 三道防线：按覆盖的阶段跨列对齐（第二道跨阶段②③）
BAR = ("rounded=1;absoluteArcSize=1;arcSize=14;whiteSpace=wrap;html=1;fillColor=#FFFFFF;"
       "strokeWidth=2;align=center;verticalAlign=middle;fontSize=19;" + YAHEI)
a.cell("d1", BAR + f"strokeColor={RED};fontColor={INK};", 20, 278, 210, 104,
       "&lt;b&gt;第一道防线&lt;/b&gt;&lt;br&gt;生成端安全对齐&lt;br&gt;"
       + color_span("× 被超监管内容绕过", RED, bold=True))
a.cell("d2", BAR + f"strokeColor={RED};fontColor={INK};", 250, 278, 440, 104,
       "&lt;b&gt;第二道防线&lt;/b&gt;&lt;br&gt;显式标识与生成元数据&lt;br&gt;"
       + color_span("× 传播中被系统性剥离", RED, bold=True))
a.cell("d3", BAR + f"strokeColor={GREEN};fillColor=#F1F8F1;fontColor={INK};", 710, 278, 210, 104,
       "&lt;b&gt;第三道防线&lt;/b&gt;&lt;br&gt;传播后第三方审核&lt;br&gt;"
       + color_span("√ 本作品 TraceGuard", GREEN, bold=True))

# 虚线须垂直：entryX 按“阶段卡中心落在防线条上的相对位置”算，
# 否则跨列的第二道防线会拉出斜线。
DASH = "endArrow=none;dashed=1;html=1;strokeWidth=1.5;exitX=0.5;exitY=1;entryY=0;"
a.edge("dl1", "s1_card", "d1", DASH + f"strokeColor={RED};entryX=0.5;")
a.edge("dl2a", "s2_card", "d2", DASH + f"strokeColor={RED};entryX=0.239;")
a.edge("dl2b", "s3_card", "d2", DASH + f"strokeColor={RED};entryX=0.761;")
a.edge("dl3", "s4_card", "d3", DASH + f"strokeColor={GREEN};entryX=0.5;")

a.txt("harm", 20, 404, 900, 36,
      "现实危害：" + color_span("假新闻配图", RED, bold=True) + " · "
      + color_span("舆情误导", RED, bold=True) + " · "
      + color_span("电子证据污染", RED, bold=True),
      size=21)

a.write(HERE / "background_threat_chain_drawio_v3.drawio", "threat-chain-v3")


# ══════════════════════════════════════════════════════
# 图 1.2  同图传播前后检测输出对比（实测）
# ══════════════════════════════════════════════════════
b = Doc("图1.2 同图传播前后检测输出对比", 800, 570)

b.cell("bg", "rounded=1;absoluteArcSize=1;arcSize=16;whiteSpace=wrap;html=1;fillColor=#FFFFFF;"
       f"strokeColor={RED};strokeWidth=2;", 20, 20, 760, 520)

b.txt("h", 40, 44, 720, 34, "同一伪造图像 · 传播前后的检测输出对比", size=24, color=BLUE, bold=True)
b.txt("s", 40, 82, 720, 26, "BigGAN 伪造样本 · 固定权重的一次确定性推理", size=17, color=GRAY)

b64a = base64.b64encode(IMG_A.read_bytes()).decode()
b64b = base64.b64encode(IMG_B.read_bytes()).decode()
IMGSTYLE = "shape=image;imageAspect=1;verticalLabelPosition=bottom;verticalAlign=top;"
b.cell("img_a", IMGSTYLE + f"image=data:image/png,{b64a};", 150, 120, 200, 200)
b.cell("img_b", IMGSTYLE + f"image=data:image/jpeg,{b64b};", 450, 120, 200, 200)
b.edge("ar", "img_a", "img_b",
       f"html=1;strokeColor={ORANGE};strokeWidth=4;endArrow=blockThin;endFill=1;"
       "exitX=1;exitY=0.5;entryX=0;entryY=0.5;")
b.txt("ar_l", 350, 186, 100, 26, "经 Facebook&lt;br&gt;传播", size=15, color=GRAY)

b.txt("la", 130, 332, 240, 30, "Original（原始）", size=20, bold=True)
b.txt("lb", 430, 332, 240, 30, "Facebook 传播后", size=20, bold=True)
b.txt("na", 130, 366, 240, 54, "0.9671", size=40, color=RED, bold=True)
b.txt("nb", 430, 366, 240, 54, "0.0180", size=40, color=RED, bold=True)
b.txt("ja", 130, 424, 240, 28, "伪造概率 · 判定：伪", size=18, color=INK)
b.txt("jb", 430, 424, 240, 28, "伪造概率 · 判定：真", size=18, color=INK)
b.txt("jb2", 430, 452, 240, 28, "（证据不足 → 转人工）", size=18, color=GREEN)

b.txt("foot", 40, 492, 720, 40,
      "数据来源：case_manifest_extended.csv（degraded 案例）&lt;br&gt;"
      "单次确定性推理，不代表跨随机种子置信区间",
      size=15, color=GRAY)

b.write(HERE / "background_evidence_decay_drawio_v1.drawio", "evidence-decay-v1")
