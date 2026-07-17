# 传播扰动鲁棒性已验证汇总

冻结日期：2026-07-14

本目录只保存可进入 Git 的小型汇总。逐样本原始预测保存在本地 `results/perturbation/`，受 `.gitignore` 保护；原始文件的 SHA-256 固定在 `provenance.json`。

## 结果文件

- `perturb_full_summary_all.csv`：8000 个 GenImage fake 样本在 original、jpeg75、jpeg50、resize50、screenshot 五种确定性派生条件下的总体成对结果（40000 条预测，0 失败）。
- `perturb_full_summary_by_generator.csv`：上述结果按 8 个生成器拆分。
- `real_fp_summary_all.csv`：1000 张 `dataset/Real` 真图在 original 与 resize50 下的假阳检查总体结果（2000 条预测，0 失败）。
- `real_fp_summary_by_generator.csv`：上述真图假阳检查的按生成器拆分表；该集合全部为真图，`scope` 列固定为 `unknown`，不构成生成器维度结论。
- `provenance.json`：权重、源归档、派生归档、原始预测和汇总文件的版本证据。

## 口径边界

`perturb_full` 派生集仅仅包含 fake 图像，因此只报告 Fake Recall、平均 `fake_prob`、成对概率变化和 Fake Recall 保持率。不得从该数据计算完整二分类 Accuracy、Macro F1 或 ROC AUC。

resize50 的 Fake Recall 保持率 137.9% 不是鲁棒性证据。按生成器拆分显示 resize50 把所有生成器的 recall 拉到 0.834–0.891 的窄区间，与其 original recall 无关：VQDM 由 0.131 升到 0.834（6.37 倍），而 original 表现最好的 BigGAN 由 0.949 反降到 0.846（0.89 倍）。该现象指向“降采样再放大”被模型读成伪造痕迹的重采样偏置。`real_fp_summary_all.csv` 的真图假阳检查给出定性依据：1000 张真图的假阳率由 1.5% 升到 17.5%（约 11.7 倍）。resize50 的保持率必须与该真图假阳检查配合解读，不得单独引用为模型抗缩放能力。

真图假阳检查只覆盖 original 与 resize50 两种条件，不能外推到 jpeg75、jpeg50 和 screenshot；这三种条件当前没有对应的真图假阳基线。

本实验与 `experiments/socialmedia/verified_results/` 的成对传播实验数据构成不同，不可互相替代。前者是本地确定性派生的压缩与缩放算子，后者是三个真实平台的实际传播链；两者的 original 臂虽然同源于 GenImage 8000 样本，但分别独立推理，本目录记录的 original Fake Recall 为 59.5375%，社交媒体成对实验记录的 original Fake Recall 为 59.55%，差异来自 VQDM 单个样本（0.131 与 0.132），两者均为各自实验的既有记录，不得互相改写或混用。

`perturb_pilot`（200 样本试点）为试点性质，不进入本目录，也不得与全量口径混用。
