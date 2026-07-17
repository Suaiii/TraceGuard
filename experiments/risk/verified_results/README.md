# 风险等级校准已验证汇总

冻结日期：2026-07-13（provenance 于 2026-07-17 补齐）

本目录只保存可进入 Git 的小型汇总。逐样本原始预测保存在本地 `results/risk/`，受 `.gitignore` 保护；原始文件的 SHA-256 固定在 `provenance.json`。

## 结果文件

- `facebook_balanced_200_summary.json`：Facebook 派生 GenImage 平衡子集（100 real + 100 fake = 200 张）的五维风险融合评估——fake_prob 与 risk_score 分布、risk_level 分布、策略 A（仅 fake_prob > 0.5）vs 策略 B（risk_level ≥ medium）对比、b_only 样本特征、60/40 分层留出校准（seed=42）的 PR 曲线与 holdout 评价。
- `facebook_balanced_200_conflict_cases.csv`：策略 A 与策略 B 判定分歧的逐样本记录，含 fake_prob、risk_score、risk_level、bbox_count、tamper_type。
- `provenance.json`：权重、数据来源、原始预测和汇总文件的版本证据。

## 口径边界

### 策略对比（A vs B）

策略 A（仅 `fake_prob > 0.5`）与策略 B（`risk_level ≥ medium`）的对比基于 Facebook 派生 GenImage 平衡子集 200 张的 60/40 分层留出校准。关键数字：

| 指标 | 策略 A | 策略 B |
|------|--------|--------|
| Precision | 0.979 | 0.908 |
| Recall | 0.910 | **0.990** |
| F1 | 0.943 | 0.947 |
| 漏检 (FN) | 9 | **1** |

- 策略 B 多捕获了 16 个策略 A 会漏掉的样本（`b_only_count=16`）。
- 这 16 个样本的特征：`mean_fake_prob=0.294`（低于 0.5 阈值），但 `mean_bbox_count=8.0`（局部证据丰富），`mean_risk_score=0.397`。
- 策略 A 与 B 的总体一致率为 92%，分歧集中在 fake_prob 偏低的样本上。

**不得将上述阈值（low < 0.35、medium 0.35–0.70、high > 0.70）外推到其他数据集、平台或传播条件。** 该校准仅为单一来源（Facebook 派生 GenImage 200 张）的候选阈值，不代表跨数据集泛化。

### holdout 评价

- 60/40 分层留出（seed=42）：120 张校准、80 张留出。阈值仅在 120 张校准集上选择，报告指标来自未参与选阈值的 80 张留出集。
- review 边界（threshold=0.3947）：留出 F1=0.9877、Precision=0.9756、Recall=1.0。
- high 边界（threshold=0.4232）：留出 F1=1.0、Precision=1.0、Recall=1.0。

**该留出评价仅证明在当前 200 张样本内未过拟合，不代表真实部署中的泛化性能。**

### conflict_cases.csv

该文件记录策略 A 与 B 判定不一致的所有样本。**该文件仅含 fake_prob 偏低但风险/bbox 异于典型的样本，不代表整体分布。**

### 风险阈值来源

当前系统使用的三分位阈值（low < 0.35, medium 0.35–0.70, high > 0.70）来自 `explanation/risk/scorer.py` 的硬编码，不是从校准数据自动导出的。`facebook_balanced_200_summary.json` 中同时给出了 `equal_frequency`（等频）与 `calibrated`（基于 PR 曲线）的备选阈值，仅供对比参考，**未替换系统默认值**。

## 与报告的关系

本目录的策略对比数据（b_only_count=16 及其特征）已用于 `docs/narrative_risk_escalation.md`（#17-P4）的证据 2 段落。报告 3.5（风险等级校准与审核分流）应引用本目录的汇总数字，并在引用时注明阈值不可跨数据集外推的边界。

## 来源与缺口

- 数据来源：Facebook 派生 GenImage 平衡子集，经 `experiments/synthetic_dataset.py` 从 `results/socialmedia/platform_benchmark/raw_predictions.csv` 按 seed=42 抽取 100 real + 100 fake。
- 风险评分由 `explanation/risk/scorer.py`（五维融合：fake_prob、heatmap_max、heatmap_mean、bbox_count、tamper_score_mean）计算，权重为默认均匀权重。
- `random_seed`：校准 split 使用 seed=42；数据采样使用 seed=42。
- `source_image_archive_sha256`：待补——原始图像未随材料交付为独立归档。
- `raw_per_sample_predictions`：留本地 `results/risk/risk_pipeline_outputs.csv`（gitignored），SHA-256 见 `provenance.json`。
- 校准集仅 200 张、单一平台来源（Facebook），**不得声称阈值在更多来源或更大规模上有效**。
