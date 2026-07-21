# 第一章背景图（威胁链路与证据衰减）

## Core conclusion

AIGC 图像威胁沿「生成 → 发布 → 平台处理 → 传播后裸图」链路形成；生成端对齐（第一道防线）可被超监管内容绕过，标识与元数据（第二道防线）在传播中被系统性剥离，故需传播后第三方审核（第三道防线，本作品）。（2026-07-21 队长定名：全文弃用"传播链末端"，标题用共识词"社交媒体传播场景"，正文精确概念用"传播后裸图"。）右侧以实测衰减案例佐证：同图经 Facebook 传播后伪造概率 0.9671 → 0.0180。

## Figure contract

- **正式版为 Draw.io 工作流**（与图 2-1 同一套流程与视觉语言：浅底 #F8FAFC、粉彩填充+饱和描边圆角卡片、微软雅黑、图内无大标题）。
  - 可编辑源：`background_threat_chain_drawio_v1.drawio`（案例图像以 base64 内嵌，自包含）。
  - 源文件由 `build_threat_chain_drawio.py` 生成；手工在 draw.io 里微调后可直接覆盖保存 .drawio，无需回改脚本。
  - 导出命令（注意：draw.io 单实例，导出前先关闭已开的 draw.io 窗口，否则静默不写出）：
    `draw.io.exe -x -f png -s 2 -o background_threat_chain.png background_threat_chain_drawio_v1.drawio`
    （pdf 加 `--crop`；svg 同理。exe 位于 `C:\Users\ZHUyi\AppData\Local\Programs\draw.io\`。）
- 旧 matplotlib 版脚本 `plot_threat_chain.py` 已被 Draw.io 版取代，仅留档不再维护。
- Source data：右侧案例图像 `data/case_images/degraded_original.png` 与 `degraded_facebook.jpg`（128×128）；数值来源 `experiments/socialmedia/verified_results/case_manifest_extended.csv`（degraded 案例，BigGAN，genimage:biggan:316_biggan_00143）。
- 左侧示意链路仅表达概念；所有实测数字只出现在右侧证据卡内。
- Statistics：固定测试集、固定权重的一次确定性推理；不绘制误差条或置信区间，图内脚注注明。
- 未使用任何外部网图 / 第三方仓库示例图（版权与来源不可控）；未使用超监管图像（红线：不打开/显示/导出）。
- Export：`.drawio` 可编辑主格式；PNG(2x)/PDF(crop)/SVG 为报告兼容格式；LaTeX 引用 `background_threat_chain.pdf`。

## Visual QA

- 逐卡片核对：四阶段卡、威胁横幅、三道防线框、证据卡均无裁剪/重叠；连线方向正确。
- √/× 以文字呈现且红/绿同时依赖文字标签，不仅靠颜色。
- 图内无报告标题或高层结论句；证据卡脚注含确定性推理免责句。
