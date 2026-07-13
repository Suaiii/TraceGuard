# 社交媒体实验图形合同与 QA

## Core conclusion

传播退化具有平台差异和生成器差异：Facebook 对当前 GenImage 检测证据破坏最强，WeChat 与 Weibo 的总体 Fake Recall 保持率约为 80%。

## Figure contract

- Archetype：quantitative grid。
- Backend：Python，matplotlib；未使用 R 或其他绘图后端。
- Source data：`experiments/socialmedia/verified_results/paired_summary_all.csv` 与 `paired_summary_by_generator.csv`。
- Overall figure：Fake Recall 与成对平均 `fake_prob` 变化，固定 GenImage fake 样本 `n=8000`。
- Generator heatmap：8 个生成器 × 3 个平台；行标签同时显示 Original Fake Recall。
- Statistics：固定测试集、固定权重的一次确定性推理；没有跨随机种子或重复采样，因此不绘制误差条或置信区间。
- Export：SVG 为可编辑主格式，PDF 与 PNG 为报告兼容格式，600 dpi TIFF 保存在本地 `output/figures/socialmedia/`。

## Visual QA

- SVG 保留 `<text>` 节点，文字可编辑。
- 轴标签、数值标注、面板标签和色标无重叠。
- 图内未放置报告标题、长副标题或高层结论。
- 色彩同时依赖文字数值和位置编码，不仅仅依赖红/绿色差异。
- 热图加入 Original Fake Recall，避免以较高相对保持率掩盖低绝对基线。
- 所有图由同一 Python 脚本生成：`experiments/socialmedia/plot_verified_results.py`。
