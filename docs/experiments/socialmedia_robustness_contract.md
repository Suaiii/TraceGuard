# 社交媒体传播鲁棒性实验合同

状态：`completed`
冻结日期：2026-07-13  
负责人：朱羿帅（实验基础设施、系统集成、证据归档与报告合稿）

## User Value

验证 TraceGuard 在社交媒体传播链末端接收到重编码图像时，是否仍能维持可复核的 AIGC 审核能力，并量化传播导致的检测置信度与检出能力变化。

## Current Evidence

- 当前权重：`best.pth`，SHA-256 为 `29F85CAFFA5FCE11C7F31A2FB29C4DC44F65782D5300064BC4F73ADB153B0474`。
- GenImage 原图包含 ADM、BigGAN、Glide、Midjourney、SD14、SD15、VQDM、Wukong 各 1000 张，共 8000 张 fake 图像。
- Facebook、WeChat、Weibo 传播后 GenImage 各有 8000 张有效图像；排除 `.ipynb_checkpoints` 后，三平台均与原图实现 8000/8000 文件主名配对。
- 三个平台分别包含一个 `test_eachfake_500_real500` 归档，每个归档有 5000 张图像，可用于平台内完整分类评价；正式运行前必须验证文件名标签规则与类别计数。
- 15 个社交媒体内层 ZIP 已逐条完整读取，未发现读取错误。

## Scope

1. 直接从 ZIP 条目流式读取图片，不复制第二份解压图像。
2. 由 `Detector` 统一产生 `label` 与 `fake_prob`，实验脚本不得重新定义模型判断。
3. 对 GenImage 执行 Original/Facebook/WeChat/Weibo 成对推理。
4. 对三个 `test_eachfake_500_real500` 平台归档执行分类评价。
5. 保存逐样本原始预测、失败记录、运行元数据、平台汇总和生成器汇总。
6. 仅将完成完整性校验的数字提升为报告结论。

## Out of Scope

- 不重新训练模型，不修改 MK-MMD 训练目标。
- 不把社交媒体数据作为训练集或阈值调参集。
- 不把 GenImage fake-only 成对实验写成完整二分类 Accuracy、F1 或 AUC 实验。
- 不代替张潇补写缺失的消融原始表、训练脚本或 baseline 结果。
- 不代替贺杰宣称 CASIA 定位指标、热力图定量价值或风险融合校准已经完成。

## Affected Modules

- `detection/inference_api.py`：新增保持单图语义不变的批量推理入口。
- `experiments/socialmedia/evaluate.py`：归档读取、配对、推理、断点续跑、指标和结果归档。
- `tests/test_detection_batch.py`：批量推理合同测试。
- `tests/test_socialmedia_evaluate.py`：数据过滤、配对、标签和指标测试。
- `reports/TraceGuard.md`：只接收已验证结果。

## Data Contract

### GenImage 成对原始结果

每行唯一键为 `(sample_id, variant)`：

```text
sample_id,dataset,generator,label,variant,archive_path,entry_path,
predicted_label,real_prob,fake_prob,checkpoint_sha256,elapsed_ms,status,error
```

其中 `label` 固定为 `fake`，`variant` 仅允许 `original`、`facebook`、`wechat`、`weibo`。

### 平台分类结果

每行唯一键为 `(platform, sample_id)`，标签必须从已经验证的文件命名规则解析。无法唯一判定 `real` 或 `fake` 的文件必须进入失败表，不能静默猜测。

## Metric Definitions

### Paired GenImage

按平台与生成器报告：

- `Fake Recall = TP_fake / N_fake`。
- `Mean Fake Probability`：该条件下 `fake_prob` 的算术平均值。
- `Probability Delta = mean(fake_prob_platform - fake_prob_original)`，按相同 `sample_id` 成对计算。
- `Recall Retention = FakeRecall_platform / FakeRecall_original`；原图 Fake Recall 为 0 时记为不可定义，不填 0 或无穷大。
- 同时报告样本数、失败数和配对完整率。

### Platform Classification Benchmark

按平台报告：

- Accuracy。
- Macro F1，即 real 与 fake 两类 F1 的算术平均值。
- ROC AUC，以 `fake_prob` 为正类分数。
- Real Recall。
- Fake Recall。
- 类别数量与失败数量。

当前缺少 `test_eachfake_500_real500` 的 Original 对应归档，因此不得计算这组完整分类指标的 Original-to-platform 性能保持率。

## Acceptance Criteria

1. GenImage 产生 32000 个唯一 `(sample_id, variant)` 预测键。
2. 8000 个 `sample_id` 均有四个传播条件，八个生成器各 1000 个。
3. 三个平台分类归档的全部有效图片均得到预测或明确失败记录。
4. 所有概率为有限数且位于 `[0, 1]`。
5. 输出记录权重 SHA-256、数据包路径与哈希、Python/PyTorch/CUDA 版本、命令、设备和时间。
6. 任一缺失、重复、读取失败或推理失败都会使运行状态保持 `incomplete`。
7. 报告数字可回溯到逐样本 CSV 和运行元数据。

## Verified Results

- GenImage 成对实验完成 32000 个预测键，0 失败；8000 个 `sample_id` 均包含 Original、Facebook、WeChat、Weibo 四个版本。
- Original、Facebook、WeChat、Weibo 的总体 Fake Recall 分别为 59.55%、21.675%、48.1875%、47.5125%。
- 相对 Original，Facebook、WeChat、Weibo 的 Fake Recall 保持率分别为 36.398%、80.919%、79.786%。
- 相对 Original，三个平台的平均 `fake_prob` 成对变化分别为 -0.3162、-0.0957、-0.0990。
- 三个平台分类集各有 500 real 与 4500 fake。Facebook、WeChat、Weibo 的 Accuracy 分别为 92.64%、92.50%、92.60%，Macro F1 分别为 84.28%、84.01%、84.24%，ROC AUC 分别为 99.29%、99.29%、99.30%。
- GenImage Original 的八生成器 Fake Recall 与 `experiments/crossdomain/verified_results/eval_results.csv` 逐项一致。
- 已验证汇总与来源哈希见 `experiments/socialmedia/verified_results/`。

上述两个实验的数据构成不同。平台分类结果不能替代 GenImage 成对传播结果，也不能用于声称 Facebook 对所有数据都没有显著影响。

## Validation Commands

```powershell
E:\anaconda\envs\traceguard\python.exe -m pytest tests -q
E:\anaconda\envs\traceguard\python.exe -m experiments.socialmedia.evaluate validate `
  --manifest dataset/socialmedia/manifests/genimage_socialmedia_pairs.csv
E:\anaconda\envs\traceguard\python.exe -m experiments.socialmedia.evaluate paired-genimage `
  --manifest dataset/socialmedia/manifests/genimage_socialmedia_pairs.csv `
  --checkpoint best.pth --device cuda --batch-size 32 `
  --output results/socialmedia/paired_genimage
```

## Asset / Report Impact

- 数据、逐样本输出和浏览器产物保持 ignored。
- 代码、测试、实验合同、复现命令、汇总表和报告级图表进入明确的版本管理路径。
- 图表使用 Word 题注系统；图内不放大标题、长副标题或报告式结论。

## Risks and Rollback

- GPU 显存不足：只降低 batch size，不改变预处理、权重或阈值。
- 中途停止：使用唯一键断点续跑，不删除已完成行。
- 数据标签含糊：停止该归档评价并保留失败清单，不推测标签。
- 结果异常：保留原始 CSV 和运行元数据，撤回报告结论而不是覆盖原始结果。
- 代码回退：批量接口和实验模块由独立提交承载，可单独回退，不影响现有 Web/API/CLI。
