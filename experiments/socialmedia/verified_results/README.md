# 社交媒体传播鲁棒性已验证汇总

冻结日期：2026-07-13

本目录只保存可进入 Git 的小型汇总。逐样本原始预测保存在本地 `results/socialmedia/`，受 `.gitignore` 保护；原始文件的 SHA-256 固定在 `provenance.json`。

## 结果文件

- `paired_summary_all.csv`：8000 个 GenImage fake 样本在 Original、Facebook、WeChat、Weibo 下的总体成对结果。
- `paired_summary_by_generator.csv`：上述结果按 8 个生成器拆分。
- `classification_summary.csv`：三个平台各 500 real + 4500 fake 的平台内完整分类指标。
- `case_summary.csv`：稳定、传播退化和全局/局部证据冲突三类代表样本的完整流水线结果。
- `provenance.json`：权重、数据归档、原始预测和汇总文件的版本证据。

## 口径边界

GenImage 成对集仅仅包含 fake 图像，因此只报告 Fake Recall、平均 `fake_prob`、成对概率变化和 Fake Recall 保持率。不得从该数据计算完整二分类 Accuracy、Macro F1 或 ROC AUC。

平台分类集包含 real 与 fake，可报告完整分类指标，但当前没有对应的 Original 版本，因此不得计算其 Original-to-platform 性能保持率。

两个实验的数据来源与构成不同，不能把平台分类 Accuracy 作为 GenImage 成对传播实验的替代结论。

案例表仅仅用于解释已测量的系统行为，不构成局部定位精度验证。`bbox_count` 和 `tamper_type` 必须与后续 CASIA 等带标注数据上的 IoU、Dice、Pixel F1 分开解释。
