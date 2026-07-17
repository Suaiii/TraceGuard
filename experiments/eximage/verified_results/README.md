# 公开 ExImage 超监管零样本已验证汇总

冻结日期：2026-07-17

本目录只保存可进入 Git 的小型汇总。子集 ZIP、派生 ZIP 与逐样本原始预测保存在本地
`dataset/eximage_public_subset/` 与 `output/eximage_zeroshot_public/`，均受 `.gitignore`
保护；原始文件的 SHA-256 固定在 `provenance.json`。

## 结果文件

- `zeroshot_summary_all.csv`：2250 个公开 ExImage fake 样本在 original、jpeg75、jpeg50、resize50、screenshot 五种条件下的总体成对结果。
- `zeroshot_summary_by_generator.csv`：上述结果按 9 个生成器拆分。
- `subset_counts.csv`：子集构成，含各生成器 `test/` 可用张数与实际抽取张数。
- `provenance.json`：权重、公开源归档、子集、派生归档、原始预测与本目录汇总文件的版本证据。

## 数据来源与子集口径

数据取自**公开释出的 ExImage**（ExDA 论文配套数据集），通过 ExDA 官方 README 给出的
Google Drive 公开链接下载（file id `1s2JYbZyMe-SzWjkja9tlZFrzIJiFhwI-`，无需登录）。

**子集由本作品自建。** 公开物未提供官方划分（其 `dataset_paths.py` 未随仓库发布），
因此「自建子集」是唯一准确的表述，**不得声称使用了原论文的划分**，也不得把本结果与原论文
报告的数字直接比较。抽样过程完全确定：对每个生成器 `test/` 划分内的条目名排序后，用固定种子
`seed=42` 的 `random.Random` 抽取 250 张，脚本为 `experiments/eximage/build_public_subset.py`，
确定性由 `tests/test_eximage_public_subset.py` 覆盖。

### 公开包实测结构（路径字符串扫描，未解码任何图像）

公开包内 9 个生成器各一个嵌套 ZIP，仅含 `train/` 与 `test/` 两个划分，无第三种划分：

| 划分 | 条目数 |
|---|---|
| `train/` | 28800（每生成器 3200） |
| `test/` | 6805（每生成器 800，LatentDM 仅 405） |
| 合计 | 35605 |

抽样只取 `test/`。LatentDM 的 `test/` 只有 405 张，仍足够抽满 250 张，因此**本次 9 个生成器
全部达到 250 张目标，无一短缺**。

全库 35605 个条目中存在 **75 个字节级重复**（按 `(crc32, 未压缩大小)` 判定，去重后 35530）：
CycleGAN 27、Midjourney 36、SD14 12。本子集的 2250 张经核验 **crc32 两两互不相同，无重复样本**。

## 口径边界

**公开包不含 real 图像**——对全库 35605 个条目路径做关键字扫描，`real`/`0_real`/`nature` 命中数为 **0**，
且划分目录只有 `train/` 与 `test/`，实测确认。因此本实验
**只报 Fake Recall、平均 `fake_prob`、成对概率变化和 Fake Recall 保持率**，
**不得计算 Accuracy、Macro F1、ROC AUC 或假阳率**。任何需要 real 样本的指标在本数据上都不成立。

本实验仅以固定权重零样本评价，**不生成、不训练、不优化任何高危内容**。

生成器构成与 GenImage 不同（无 VQDM、ADM 难例），因此结果**仅支持「识别能力可跨内容域迁移」
的方向性结论**，不得写成普适检测能力。

派生扰动（jpeg75、jpeg50、resize50、screenshot）是本地确定性模拟，**不是真实平台传播链**，
不能替代 `experiments/socialmedia/` 的 Facebook/WeChat/Weibo 实测结论；两者构成不同，不可互换。

## 与旧结果 `output/eximage_zeroshot/` 的关系

旧结果报告的 **98.84% 总体 Fake Recall 与 1.4% 真图假阳率** 建立在**公开 (js) + 非公开 (db) 混合集**上：
其 2250 张 fake 按文件名中缀完美二分，`js` 1152 张字节级存在于公开 ExImage 中，
`db` 1098 张在公开包中命中数为 0（以 ZIP 中央目录的 `(crc32, 未压缩大小)` 比对确认，未解码任何图像）。
旧结果的 500 张 real 亦不来自公开包。

本目录为**纯公开数据重跑**，样本集合与旧结果不同（仅在 `js` 部分部分重叠，且抽样种子与划分均不同）。
**两者数字不可混用、不可相互替代、不可并列为同一实验的不同版本。** 旧结果保留于
`output/eximage_zeroshot/` 仅作对比留档，其数字不得在声称「数据来自公开文献」的语境下使用。
