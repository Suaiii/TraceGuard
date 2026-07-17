# 社交媒体实验图形合同与 QA

## Core conclusion

传播退化具有平台差异和生成器差异：Facebook 对当前 GenImage 检测证据破坏最强，WeChat 与 Weibo 的总体 Fake Recall 保持率约为 80%。

## Figure contract

- Archetype：quantitative grid。
- Backend：Python，matplotlib；未使用 R 或其他绘图后端。
- Source data：`experiments/socialmedia/verified_results/paired_summary_all.csv` 与 `paired_summary_by_generator.csv`。
- Overall figure：Fake Recall 与成对平均 `fake_prob` 变化，固定 GenImage fake 样本 `n=8000`。
- Generator heatmap：8 个生成器 × 3 个平台；行标签同时显示 Original Fake Recall。
- Case evidence (`socialmedia_case_evidence.*`)：三类已测量样本的 Original/Facebook 区域标注图；数值来源为 `case_manifest_extended.csv`。
- Case evidence full (`socialmedia_case_evidence_full.*`)：三类样本 × 四平台 (Original/Facebook/WeChat/Weibo) 完整对比图；每格标注 label、fake_prob、risk_score(risk_level)、bbox_count、tamper_type。底部附解释边界声明。生成脚本同上，`--variants original,facebook,wechat,weibo`。
- Case evidence per-type (`socialmedia_case_{stable,degraded,conflict}.*`)：**#15-A 三类案例图**，每种案例独立一张，均为 1×4（四平台并排），便于报告逐案例详细展示。生成脚本同上，`--roles stable` / `--roles degraded` / `--roles conflict`。
- 案例解释与高危处置叙事：见 `docs/narrative_risk_escalation.md`（#17-P4 交付物）。
- Statistics：固定测试集、固定权重的一次确定性推理；没有跨随机种子或重复采样，因此不绘制误差条或置信区间。
- Export：SVG 为可编辑主格式，PDF 与 PNG 为报告兼容格式，600 dpi TIFF 保存在本地 `output/figures/socialmedia/`。

## Visual QA

- SVG 保留 `<text>` 节点，文字可编辑。
- 轴标签、数值标注、面板标签和色标无重叠。
- 图内未放置报告标题、长副标题或高层结论。
- 色彩同时依赖文字数值和位置编码，不仅仅依赖红/绿色差异。
- 热图加入 Original Fake Recall，避免以较高相对保持率掩盖低绝对基线。
- 总体图与热图由 `experiments/socialmedia/plot_verified_results.py` 生成，案例图由 `experiments/socialmedia/plot_case_evidence.py` 生成。
