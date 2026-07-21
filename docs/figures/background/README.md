# 第一章背景图（威胁链路与证据衰减）

## Core conclusion

AIGC 图像威胁沿「AIGC 图像生成 → 社交平台发布 → 平台转码压缩 → 传播后裸图」链路逐级加重；生成端对齐（第一道防线）可被超监管内容绕过，显式标识与生成元数据（第二道防线）在传播中被系统性剥离，故需传播后第三方审核（第三道防线，本作品）。右侧以实测衰减案例佐证：同图经 Facebook 传播后伪造概率 0.9671 → 0.0180。

（2026-07-21 队长定名：全文弃用「传播链末端」，标题用共识词「社交媒体传播场景」，正文精确概念用「传播后裸图」。）

## Figure contract

- **正式版为 Draw.io 工作流**。可编辑源：`background_threat_chain_drawio_v2.drawio`（案例图像以 base64 内嵌，自包含），由 `build_threat_chain_drawio.py` 生成；在 draw.io 里手工微调后可直接覆盖保存 .drawio，无需回改脚本。
- 导出命令（注意：draw.io 单实例，导出前先关闭已开的 draw.io 窗口，否则静默不写出）：
  `draw.io.exe -x -f png -s 2 -o background_threat_chain.png background_threat_chain_drawio_v2.drawio`
  （pdf 加 `--crop`；svg 同理。exe 位于 `C:\Users\ZHUyi\AppData\Local\Programs\draw.io\`。）
- **v2 视觉语言（2026-07-21 重做）**：参照《AIGC 的伪造媒体内容检测与安全防御申报材料》背景概述页的排版范式——贯穿式阶段大箭头（#CFC6AE）压在阶段胶囊下层、阶段胶囊配色随威胁递进加重（米 #F2EFE6 → 米 → 亮蓝 #4CBEF2 → 深藏蓝 #17376B）、白底橙描边内容卡（#E29B3C）、右侧红框实测数据卡（红边 #C00000 + 蓝标题 #1F4E9C + 大号红数字）、关键词红色强调。微软雅黑，图内无报告标题与高层结论句。
- **只借版式，不借素材**：未复制该 PPT 的任何图片（第三方/网络来源，版权与身份红线）；图中不出现实验室、导师、团队等身份措辞。
- 未使用任何外部网图 / 第三方仓库示例图；未使用超监管图像（红线：不打开/显示/导出）。
- Source data：右侧案例图像 `data/case_images/degraded_original.png` 与 `degraded_facebook.jpg`（128×128）；数值来源 `experiments/socialmedia/verified_results/case_manifest_extended.csv`（degraded 案例，BigGAN，genimage:biggan:316_biggan_00143）。
- 左侧示意链路仅表达概念；所有实测数字只出现在右侧证据卡内。
- Statistics：固定测试集、固定权重的一次确定性推理；不绘制误差条或置信区间，图内脚注注明。
- Export：`.drawio` 可编辑主格式；PNG(2x)/PDF(crop)/SVG 为报告兼容格式；LaTeX 引用 `background_threat_chain.pdf`。
- 已删除的旧件（git 历史可查）：`background_threat_chain_drawio_v1.drawio`（v1 浅底粉彩版，队长评价过于素净）、`plot_threat_chain.py`（最初的 matplotlib 版）。

## 踩过的坑

- **mxCell 的 `value="..."` 属性内不能出现裸双引号**：内嵌 HTML 的 `<font color="#C00000">` 必须写成 `&quot;`，否则 XML 属性被提前截断，导出图从该处起整段丢失（首次导出只画出了第一个阶段）。
- 跨列的防线条要让虚线保持垂直，需按「阶段卡中心落在防线条上的相对位置」显式设 `entryX`，不能一律用 0.5。
- 圆角用百分比会随尺寸变形，统一 `absoluteArcSize=1;arcSize=<px>`。

## Visual QA

- 逐卡片核对：四阶段胶囊与内容卡、三道防线条、现实危害行、右侧数据卡均无裁剪/重叠；贯穿箭头压在胶囊下层、箭头头部不被遮挡。
- 三条虚线垂直落到对应防线条（第二道防线跨阶段②③，挂两条线）。
- √/× 以文字呈现且红/绿同时依赖文字标签，不仅靠颜色。
- 图内无报告标题或高层结论句；证据卡脚注含确定性推理免责句。
