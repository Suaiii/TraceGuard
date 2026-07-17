# 跨域平衡盲测已验证汇总

冻结日期：2026-07-13（MK-MMD 消融两臂与逐样本预测于 2026-07-17 补入）

本目录只保存可进入 Git 的小型汇总。该实验的逐样本原始预测未随材料交付，当前不在本仓库；`provenance.json` 只能锚定汇总文件本身与权重，复现链缺口见下文。

## 结果文件

- `eval_results.csv`：8 个生成器（ADM、BigGAN、Glide、Midjourney、SD14、SD15、VQDM、Wukong）各 1000 real + 1000 fake 的平衡盲测表，含 Accuracy、Real Recall、Fake Recall 及 Average 行。**MK-MMD 消融的 `+MK-MMD` 臂。**
- `eval_results_no_mmd.csv`：同一消融的 `无 MMD` 臂（MambaOut only，不含 MK-MMD），生成器与样本量构成与上表一致。
- `genimage_original_fakeprob.csv`：GenImage original 条件下 8000 个 fake 样本的逐图 `fake_prob`。**按 §12.1 约定，逐样本预测本不应入库**，应放本地 `results/<线>/`（gitignored）——该文件已由队友公开推送至远端，故暂时保留入库，**是否移出待队长决定**。
- `provenance.json`：权重与汇总文件的版本证据，以及当前已知的来源与缺口。

## 口径边界

### 平衡盲测表

该表是 8 组各自平衡（1000 real + 1000 fake）的盲测结果。`Average` 行的 79.68% 是八个生成器 Accuracy 的宏观平均，只代表平衡测试集上的静态口径，不代表任何社交传播条件下的表现，也不得作为平台整体准确率对外表述。

八个生成器的 Fake Recall 均值为 59.55%，与 `experiments/socialmedia/verified_results/paired_summary_all.csv` 中 original 条件的 Fake Recall 0.5955 逐位一致。这是本实验与社交媒体成对传播实验之间的交叉校验点：它证明成对实验的 original 臂与本盲测表出自同一权重且样本构成一致，因此传播退化幅度可以相对 original 直接解读。引用该一致性时只能表述为两个实验的口径互证，不得表述为独立复现。

`Real_Recall%` 在八组中恒为 99.80%，因为当前 8 组测试共用同一源域 real 子集，不是八次独立的真图评测。

`experiments/perturbation/verified_results/` 的 original 臂为另一次独立推理，记录值为 59.5375%，与本表的 59.55% 存在 VQDM 单样本差异，两者不得互相改写或混用。

### MK-MMD 消融对比

两臂逐生成器 Fake Recall（%）：

| 生成器 | 无 MMD | +MK-MMD | 提升 |
|---|---:|---:|---:|
| ADM | 25.30 | 37.00 | +11.70 |
| BigGAN | 73.26 | 94.90 | +21.64 |
| Glide | 65.70 | 72.90 | +7.20 |
| Midjourney | 43.70 | 49.20 | +5.50 |
| SD14 | 63.90 | 72.50 | +8.60 |
| SD15 | 65.66 | 73.10 | +7.44 |
| VQDM | 8.90 | 13.20 | +4.30 |
| Wukong | 50.33 | 63.60 | +13.27 |

两臂汇总：

| 指标 | 无 MMD | +MK-MMD | 绝对提升 | 相对提升 |
|---|---:|---:|---:|---:|
| Fake Recall 均值 | 49.5938% | 59.5500% | +9.96 pp | **+20.08%** |
| Accuracy 均值 | 74.5950% | 79.6750% | +5.08 pp | +6.81% |

**「跨域提升 17%+」的口径限制（引用前必读）。** 报告中「跨域提升 17%+」这一说法，**只在「Fake Recall 相对提升」这一个口径下成立**（+20.08%）。绝对提升仅 +9.96 pp、Accuracy 相对提升仅 +6.81%，**这两个口径都够不到 17%**。引用该数字时必须同时标明**指标**与**口径**（绝对 pp 还是相对 %），**不得裸写「提升 17%+」**。

建议表述：

> MK-MMD 使八生成器平均 Fake Recall 从 49.59% 提升至 59.55%（相对提升 20.1%）。

MK-MMD 在全部 8 个生成器上均为正向贡献，这是该消融当前可支持的最强定性结论。

**两臂不是同一权重的消融开关。** 两臂的 `Real_Recall` 不同（无 MMD 为 99.6%，+MK-MMD 为 99.8%），说明这是**两次独立训练**，而不是在同一组权重上开关 MK-MMD 分支。因此两臂差值中混入了训练随机性，当前证据无法把差值全部归因于 MK-MMD 本身。引用时不得表述为「控制变量消融」。

**列名口径差异。** `eval_results_no_mmd.csv` 的表头为 `Accuracy,Real_Recall,Fake_Recall`（无 `%` 后缀），`eval_results.csv` 为 `Accuracy%,Real_Recall%,Fake_Recall%`。两表数值同为百分数口径，合并读取时需注意表头不一致。

### 逐样本预测表

`genimage_original_fakeprob.csv` 为 8000 行逐图 `fake_prob`（`sample_id`、`condition=Original`、`fake_prob`、`ground_truth=fake`），仅含 fake 样本，因此**不得由该表计算 Accuracy、Macro F1 或 ROC AUC**。该表按 §12.1 属于逐样本原始预测，归宿应为本地 `results/`（gitignored），当前入库仅因已公开推送，不构成对该约定的例外。

## 来源与缺口

`eval_results.csv` 由张潇（GitHub 账号 `zx973`）于 2026-07-13 提交（commit `af22fee`），同批提交 `REPRODUCIBILITY.md`。

`eval_results_no_mmd.csv` 与 `genimage_original_fakeprob.csv` 由张潇（`zx973`）于 2026-07-17 推送，推送时 §12.1 `verified_results` 约定尚未确立，原始位置分别为仓库根目录与 `experiments/detection/`，现已归位至本目录。

以下字段当前缺失，如实记录，不得推断或补写：

- 训练配置与超参数：`REPRODUCIBILITY.md` 给出命令示例，但对应的 `train.py`、`eval.py` 未进入本仓库。
- 数据划分依据：real 子集与各生成器 fake 子集的来源目录、划分方式和去重口径未提供。
- 随机种子：未提供。
- 逐样本原始预测（平衡盲测两臂）：未提供，因此两臂盲测表无法用哈希锚定到原始预测。`genimage_original_fakeprob.csv` 只覆盖 GenImage original 条件的 fake 侧，不能替代两臂盲测的原始预测。

MK-MMD 消融特有的缺口：

- **`eval_results_no_mmd.csv` 没有对应的 checkpoint**：无权重文件、无 SHA-256。`eval_results.csv` 对应权重 sha256 为 `29F85CAFFA5FCE11C7F31A2FB29C4DC44F65782D5300064BC4F73ADB153B0474`，但 no-MMD 那次训练的权重不在手上，该臂无法复算。
- **两次训练是否共享同一数据划分未说明**：`Real_Recall` 不同已证明是两次独立训练，但是否复用同一 85:15 划分与同一 real 子集，交付材料未交代。
- **产出该消融表的脚本未提供**，随机种子未提供。

按 Issue #14 验收标准（每项正式结果需具备数据来源、划分、配置、命令、原始 CSV、指标定义、解释边界与复现记录），该消融当前**仅到「原始表」一项**，复现链未闭合。

在上述缺口补齐前，本目录的表只能作为已提交记录引用，不构成可独立复现的结论。
