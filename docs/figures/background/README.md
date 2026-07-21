# 第一章背景图（两张）

## Core conclusion

- **图 1.1 威胁链路与三道防线**（论证）：AIGC 图像威胁沿「AIGC 图像生成 → 社交平台发布 → 平台转码压缩 → 传播后裸图」逐级加重；生成端对齐（第一道防线）可被超监管内容绕过，显式标识与生成元数据（第二道防线）在传播中被系统性剥离，故需传播后第三方审核（第三道防线，本作品）。
- **图 1.2 同图传播前后检测输出对比**（证据）：同一 BigGAN 伪造图像经 Facebook 传播后，伪造概率 0.9671 → 0.0180，判定被完全翻转。

（2026-07-21 队长定名：全文弃用「传播链末端」，标题用共识词「社交媒体传播场景」，正文精确概念用「传播后裸图」。）

## 为什么是两张图（重要，改图前先读）

原先是一张 1600 单位宽的横图（链路 + 证据卡并排）。按 `\linewidth` 排进 A4 正文后**字号只剩约 4pt，完全不可读**，且横图挤占版面。2026-07-21 拆为两张，并按论证逻辑分工：图 1.1 讲"为什么需要第三道防线"，图 1.2 给"证据衰减实测"。

**画布宽度是硬约束**。正文 textwidth = 21 − 2.86 − 2.59 = 15.55cm，图按 `\linewidth` 排版时：

```
实际字号(mm) = fontSize × 155.5 / canvas_width
```

要落在 9~11pt（3.2~3.9mm）的可读区间，画布宽度必须压到 **760~1000 单位**，正文字号取 **20 左右**。旧版 1600 宽 + fontSize 14 → 3.9pt，不可读。**新增或改图时务必按此式先算一遍。**

当前：图 1.1 画布 1000×500（`\linewidth`），图 1.2 画布 800×570（`0.9\linewidth`）。

## Figure contract

- 可编辑源（draw.io，案例图 base64 内嵌、自包含），均由 `build_threat_chain_drawio.py` 一次生成两张：
  - `background_threat_chain_drawio_v3.drawio` → `background_threat_chain.{pdf,png,svg}`
  - `background_evidence_decay_drawio_v1.drawio` → `background_evidence_decay.{pdf,png,svg}`
  - 在 draw.io 里手工微调后可直接覆盖保存 .drawio，无需回改脚本。
- 导出命令（注意：draw.io 单实例，导出前先关闭已开的 draw.io 窗口，否则静默不写出）：
  `draw.io.exe -x -f png -s 2 -o background_threat_chain.png background_threat_chain_drawio_v3.drawio`
  （pdf 加 `--crop`；svg 同理。exe 位于 `C:\Users\ZHUyi\AppData\Local\Programs\draw.io\`。）
- **视觉语言**参照《AIGC 的伪造媒体内容检测与安全防御申报材料》背景概述页的排版范式：贯穿式阶段大箭头（#CFC6AE）压在阶段胶囊下层、胶囊配色随威胁递进加重（米 #F2EFE6 → 米 → 亮蓝 #4CBEF2 → 深藏蓝 #17376B）、白底橙描边内容卡（#E29B3C）、红框数据卡（红边 #C00000 + 蓝标题 #1F4E9C + 大号红数字）、关键词红色强调。微软雅黑。
- **只借版式，不借素材**：未复制该 PPT 的任何图片（第三方/网络来源，版权与身份红线）；图中不出现实验室、导师、团队等身份措辞。
- 未使用任何外部网图 / 第三方仓库示例图；未使用超监管图像（红线：不打开/显示/导出）。
- Source data：案例图像 `data/case_images/degraded_original.png` 与 `degraded_facebook.jpg`（128×128）；数值来源 `experiments/socialmedia/verified_results/case_manifest_extended.csv`（degraded 案例，BigGAN，genimage:biggan:316_biggan_00143）。
- 图 1.1 为概念示意，不含任何实测数字；所有实测数字只出现在图 1.2。
- Statistics：固定测试集、固定权重的一次确定性推理；不绘制误差条或置信区间，图内脚注注明。
- Export：`.drawio` 为可编辑主格式；PNG(2x)/PDF(crop)/SVG 为报告兼容格式；LaTeX 引用两个 `.pdf`。
- 已删除的旧件（git 历史可查）：`background_threat_chain_drawio_v1.drawio`（浅底粉彩版）、`background_threat_chain_drawio_v2.drawio`（1600 宽合并横版，字太小）、`plot_threat_chain.py`（最初的 matplotlib 版）。

## 踩过的坑

- **mxCell 的 `value="..."` 属性内不能出现裸双引号**：内嵌 HTML 的 `<font color="#C00000">` 必须写成 `&quot;`，否则 XML 属性被提前截断，导出图从该处起整段丢失（曾经只画出了第一个阶段）。
- **画布越宽，正文里的字越小**。见上方公式；不要为了"信息放得下"而加宽画布。
- 跨列的防线条要让虚线保持垂直，需按「阶段卡中心落在防线条上的相对位置」显式设 `entryX`，不能一律用 0.5。
- 圆角用百分比会随尺寸变形，统一 `absoluteArcSize=1;arcSize=<px>`。

## Visual QA

- 编译进正文后目视核对字号：阶段标题与正文 caption 相当，卡内文字不小于约 9pt。
- 逐卡片核对：四阶段胶囊与内容卡、三道防线条、现实危害行无裁剪/重叠；贯穿箭头压在胶囊下层且箭头头部不被遮挡。
- 三条虚线垂直落到对应防线条（第二道防线跨阶段②③，挂两条线）。
- √/× 以文字呈现且红/绿同时依赖文字标签，不仅靠颜色。
- 图内无报告标题或高层结论句；图 1.2 脚注含确定性推理免责句。
