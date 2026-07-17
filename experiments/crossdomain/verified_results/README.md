# 跨域平衡盲测已验证汇总

冻结日期：2026-07-13

本目录只保存可进入 Git 的小型汇总。该实验的逐样本原始预测未随材料交付，当前不在本仓库；`provenance.json` 只能锚定汇总文件本身与权重，复现链缺口见下文。

## 结果文件

- `eval_results.csv`：8 个生成器（ADM、BigGAN、Glide、Midjourney、SD14、SD15、VQDM、Wukong）各 1000 real + 1000 fake 的平衡盲测表，含 Accuracy、Real Recall、Fake Recall 及 Average 行。
- `provenance.json`：权重与汇总文件的版本证据，以及当前已知的来源与缺口。

## 口径边界

该表是 8 组各自平衡（1000 real + 1000 fake）的盲测结果。`Average` 行的 79.68% 是八个生成器 Accuracy 的宏观平均，只代表平衡测试集上的静态口径，不代表任何社交传播条件下的表现，也不得作为平台整体准确率对外表述。

八个生成器的 Fake Recall 均值为 59.55%，与 `experiments/socialmedia/verified_results/paired_summary_all.csv` 中 original 条件的 Fake Recall 0.5955 逐位一致。这是本实验与社交媒体成对传播实验之间的交叉校验点：它证明成对实验的 original 臂与本盲测表出自同一权重且样本构成一致，因此传播退化幅度可以相对 original 直接解读。引用该一致性时只能表述为两个实验的口径互证，不得表述为独立复现。

`Real_Recall%` 在八组中恒为 99.80%，因为当前 8 组测试共用同一源域 real 子集，不是八次独立的真图评测。

`experiments/perturbation/verified_results/` 的 original 臂为另一次独立推理，记录值为 59.5375%，与本表的 59.55% 存在 VQDM 单样本差异，两者不得互相改写或混用。

## 来源与缺口

本表由张潇（GitHub 账号 `zx973`）于 2026-07-13 提交（commit `af22fee`），同批提交 `REPRODUCIBILITY.md`。

以下字段当前缺失，如实记录，不得推断或补写：

- 训练配置与超参数：`REPRODUCIBILITY.md` 给出命令示例，但对应的 `train.py`、`eval.py` 未进入本仓库。
- 数据划分依据：real 子集与各生成器 fake 子集的来源目录、划分方式和去重口径未提供。
- 随机种子：未提供。
- 逐样本原始预测：未提供，因此本表无法用哈希锚定到原始预测。

在上述缺口补齐前，本表只能作为已提交记录引用，不构成可独立复现的结论。
