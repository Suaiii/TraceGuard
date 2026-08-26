# TraceGuard 测试报告

## 1. 报告概述

### 1.1 测试对象

本报告针对 TraceGuard:面向社交媒体网络传播的 可解释 AIGC 图像取证平台进行测试。系统以单张 RGB 图像为最小输入，输出全局真伪判断、伪造概率、Grad-CAM 热力图、局部可疑区域、风险等级及面向审核人员的解释信息。测试对象包括 MambaOut-Small 检测器、MK-MMD 跨域适配模块、热力图生成、局部区域分析、风险融合、Web 工作台、FastAPI 接口、命令行和批量分析入口。

### 1.2 测试目的

测试从五个方面验证平台主张：

1. 检查代码、接口合同和主要处理链路是否能够稳定运行；
2. 评估检测器在多生成器、多来源和传播扰动条件下的真伪判断表现；
3. 检查热力图与局部框是否能够作为可解释证据输出，并测量其与合成标注区域的重叠程度；
4. 验证风险融合与审核分流策略是否能够减少低伪造概率样本的漏检；
5. 验证用户是否能够通过 Web/API/CLI 完成“输入图像—检测—证据—风险—报告”的闭环。

本报告只将具有数据来源、实验条件、指标定义和结果文件支撑的结果写成已验证结论。尚未完成的多来源定位、裁剪扰动、长时稳定性和大规模并发测试不作为本报告的完成结果。

### 1.3 测试结论摘要

平台代码与接口曾在 191 项冻结基线中全部通过；本次针对当前工作区重新收集到 216 项测试，实测 213 项通过、3 项失败。失败项为 2 项批量 CLI 帮助子进程超出 15 秒，以及 1 项提交包装测试因缺少预期的 `output/doc` 构建目录而失败，均未表现为模型指标或 API 响应错误。跨域检测实验在 8 个生成器、每个生成器 1000 张真实图像和 1000 张生成图像的平衡集合上完成；启用 MK-MMD 的平均准确率为 79.68%，未启用时为 74.60%。在公开的 Facebook 派生 GenImage 子集上，零样本生成器识别总体 Fake Recall 为 98.00%，但该集合仅包含 fake 图像，不能替代完整二分类测试。

传播扰动测试显示，JPEG 压缩和截图模拟会明显降低 Fake Recall；Resize-0.5x 的 fake 保持率升高并不构成鲁棒性证据，因为同条件真图假阳率由 1.50% 升至 17.50%。在 200 张 Facebook 派生平衡校准集的 60/40 留出评价中，风险等级大于等于 medium 的策略在留出集上取得 F1=0.9877、Recall=1.0000；该结果仅适用于当前来源、划分和固定权重。

局部定位测试的图像级检出率为 100%，但 CASIA v1 合成评价的 Clean FP Rate 也为 100%，AIGC 派生合成评价的 Avg IoU 为 0.0148、Pixel F1 为 0.0286。因此，当前局部框应解释为模型关注区域和审核线索，不应宣称为像素级、法庭级篡改定位。

## 2. 测试环境与版本

### 2.1 软件与硬件环境

平台验收使用本地 CUDA 环境完成，关键环境如下：

| 项目 | 测试值 |
|---|---|
| 操作系统 | Windows |
| Python | 3.10.20 |
| PyTorch | 2.5.1+cu121 |
| GPU | NVIDIA GeForce RTX 4060 Laptop GPU |
| 显存 | 8188 MiB |
| NVIDIA 驱动 | 580.97 |
| 检测权重 SHA-256 | `29F85CAFFA5FCE11C7F31A2FB29C4DC44F65782D5300064BC4F73ADB153B0474` |
| 平台烟测提交版本 | `ca754cb495e055ee689f3e26c5745e50a12a498d` |

自动化回归测试还覆盖无 GPU 的模块级路径，模型权重不进入 Git，运行时由配置或启动参数指定。

### 2.2 测试入口

测试与验收围绕同一 `ExplanationPipeline` 展开。Web 前端和 FastAPI 使用 `/api/v1/health`、`/api/v1/analyze` 等接口；CLI 使用 `run_test.py`；批量实验使用 `batch_analyze.py` 与 `experiments/` 下的评价脚本。前端不重新计算 `fake_prob` 或 `risk_score`，全局真伪判断统一来自 `Detector.predict()`。

## 3. 数据来源与测试设计

### 3.1 跨生成器检测

跨域主评价使用 8 个生成器：ADM、BigGAN、Glide、Midjourney、SD14、SD15、VQDM 和 Wukong。每个生成器包含 1000 张 real 与 1000 张 fake，生成器内为平衡二分类评价。实验比较启用 MK-MMD 与不启用 MK-MMD 两种设置，变量为跨域适配模块是否参与检测流程，其他评价口径保持一致。

### 3.2 零样本内容域评价

零样本评价使用 Facebook 派生 GenImage 公开子集，覆盖 9 个生成器，每个生成器 250 张，共 2250 张，当前汇总文件仅包含 fake 样本。实验目的为观察检测器从既有生成器域迁移到另一公开内容域后的识别能力，指标只报告 Fake Recall、平均 `fake_prob` 和传播变体保持率，不计算 Accuracy、Macro F1 或 ROC AUC。

### 3.3 传播扰动与平台传播链

确定性派生扰动实验从 8000 个 GenImage fake 样本生成 Original、JPEG-75、JPEG-50、Resize-0.5x 和 Screenshot 五种条件，共 40000 条预测，失败数为 0。另使用 1000 张真实图像对 Original 与 Resize-0.5x 做假阳对照。

社交媒体传播实验使用 8000 个 fake 样本，比较 Original、Facebook、WeChat 和 Weibo 的成对结果；平台内完整分类评价另使用每个平台 500 张 real 与 4500 张 fake。两种实验构成不同，平台分类指标不能替代成对传播保持率。

### 3.4 定位与风险评价

定位主评价使用 CASIA v1 的 40 张 tampered 与 10 张 clean 样本。篡改区域由固定随机种子 42 的程序从 Modified Tp 图像裁剪 patch 后粘贴到 Au 底图生成，粘贴区域作为像素级 Ground Truth。另使用 Facebook 派生 GenImage 合成 10 张 tampered 与 5 张 clean 样本，仅用于说明 AIGC 局部定位边界。

风险评价使用 Facebook 派生 GenImage 平衡集：100 张 real 与 100 张 fake，共 200 张；按 seed=42 进行 60/40 分层留出，120 张用于校准，80 张用于留出评价。风险评分由 `fake_prob`、热力图强度、可疑框数量、篡改分数等维度融合形成，不等同于 `fake_prob`。

## 4. 指标定义与判定规则

### 4.1 检测指标

- Accuracy：预测正确样本数除以总样本数；
- Real Recall：真实图像被判为 real 的比例；
- Fake Recall：生成图像被判为 fake 的比例；
- Macro F1：real/fake 两类 F1 的宏平均；
- ROC AUC：以模型概率排序衡量二分类区分能力。

仅包含 fake 样本的实验只报告 Fake Recall、平均 `fake_prob`、成对概率变化和保持率，避免从不完整标签构造完整二分类指标。

### 4.2 扰动指标

Fake Recall retention 定义为某一扰动条件 Fake Recall 与 Original Fake Recall 的比值。该指标必须与真图假阳对照联合解释；当扰动使模型对真图产生明显假阳时，保持率升高不能单独证明鲁棒性。

### 4.3 定位指标

- IoU = TP / (TP + FP + FN)；
- Dice/Pixel F1 = 2TP / (2TP + FP + FN)；
- Detection Rate：tampered 图像中产生至少一个局部框的比例；
- Clean FP Rate：clean 图像中产生至少一个局部框的比例。

定位默认工作点为热力图 percentile=90，并额外扫描 50、60、70、75、80、85、90、92、95、97 等阈值，观察阈值变化对重叠与误报的影响。

### 4.4 风险策略

策略 A 仅使用 `fake_prob > 0.5`；策略 B 使用 `risk_level >= medium`。对比指标为 Precision、Recall、F1、FN 和策略一致率。风险阈值校准只在 120 张校准集上选择，最终报告 80 张未参与选阈值的留出集结果。

## 5. 自动化回归与功能测试

### 5.1 覆盖范围

自动化测试覆盖配置加载、检测器推理接口、批量检测、热力图、局部定位、风险评分、文本解释、管线合同、API schema、FastAPI 路由、CLI、报告导出、可视化、Windows 启动器和提交包检查。重点合同包括：

1. `label` 与 `fake_prob` 只由全局检测入口产生；
2. 局部定位可以输出证据，但不得覆盖全局真伪判断；
3. 风险分数与 `fake_prob` 分开保留；
4. 单图与批量响应的字段、类型和错误结构保持一致；
5. LLM 不可用或返回空内容时，报告能够降级到非空模板文本；
6. Windows 启动器能够传递参数并检查权重路径。

### 5.2 结果

历史冻结自动化基线为 191/191 通过；本次当前工作区全量复测为 216 项，213 项通过、3 项失败。具体失败如下：

- `tests/test_cli.py::TestBatchCLI::test_batch_help`：`python -m explanation.batch --help` 在 15 秒测试时限内未返回；
- `tests/test_cli.py::TestBatchCLI::test_batch_config_flag`：同一批量 CLI 子进程超时；
- `tests/test_submission_package_script.py::test_submission_package_contains_runtime_allowlist_only`：提交包装脚本预期的 `output/doc` 目录不存在。

前两项属于当前批量 CLI 启动耗时或子进程环境问题，第三项属于构建产物目录未准备的问题；三项均不应被表述为 216/216 通过。该结果证明大部分代码合同和已覆盖的行为路径满足预期，但不替代跨数据集模型泛化、长时间稳定性或真实业务压力测试。

### 5.3 功能验收

Web/API 闭环检查包括健康检查、首页工作台、真实图片上传、单图分析、结果展示和证据切换。验收观察到：

- `/api/v1/health` 返回 HTTP 200 且 `model_loaded=true`；
- `/api/v1/analyze` 对真实测试图片返回 HTTP 200；
- 页面能够显示 `label`、`fake_prob`、`risk_level`、局部框和证据图；
- 一个样例同时保留 `label=real` 与 `tamper_type=local_tamper`，说明前端未使用局部定位结果覆盖全局判断；
- 1440×1000 桌面视口和 390×844 窄屏视口均完成上传、分析、结论与证据切换检查，控制台无错误。

## 6. 跨域检测性能测试

### 6.1 MK-MMD 消融结果

| 设置 | 平均 Accuracy | 结果解释 |
|---|---:|---|
| 不启用 MK-MMD | 74.60% | 作为无跨域适配模块的对照 |
| 启用 MK-MMD | 79.68% | 在当前 8 个生成器、固定权重和固定划分上提高 5.08 个百分点 |

启用 MK-MMD 后，各生成器结果如下：

| 生成器 | Accuracy | Real Recall | Fake Recall |
|---|---:|---:|---:|
| ADM | 68.40% | 99.80% | 37.00% |
| BigGAN | 97.35% | 99.80% | 94.90% |
| Glide | 86.35% | 99.80% | 72.90% |
| Midjourney | 74.50% | 99.80% | 49.20% |
| SD14 | 86.15% | 99.80% | 72.50% |
| SD15 | 86.45% | 99.80% | 73.10% |
| VQDM | 56.50% | 99.80% | 13.20% |
| Wukong | 81.70% | 99.80% | 63.60% |

结果显示，当前模型对真实图像的识别较稳定，但不同生成器之间 Fake Recall 差异明显，VQDM 和 ADM 是主要困难域。因此，79.68% 只能作为该实验构成下的平均结果，不能直接写成对所有生成器、所有来源的泛化性能。

## 7. 零样本与传播扰动测试

### 7.1 公开子集零样本结果

在 2250 张 fake 图像上，Original Fake Recall 为 98.00%，JPEG-75 为 19.38%，JPEG-50 为 12.00%，Resize-0.5x 为 99.07%，Screenshot 为 55.69%。该结果支持“检测器在当前公开内容域上具有较强零样本识别能力”的有限主张，但不包含 real 样本，不能推导完整分类准确率或真实图假阳率。

### 7.2 确定性扰动结果

| 条件 | 样本数 | Fake Recall | 平均 fake_prob | 相对 Original 保持率 |
|---|---:|---:|---:|---:|
| Original | 8000 | 59.54% | 0.5909 | 100.00% |
| JPEG-75 | 8000 | 9.91% | 0.1749 | 16.65% |
| JPEG-50 | 8000 | 2.34% | 0.1164 | 3.93% |
| Resize-0.5x | 8000 | 82.13% | 0.7628 | 137.94% |
| Screenshot | 8000 | 24.39% | 0.2978 | 40.96% |

40000 条预测均完成且无失败。JPEG 和 Screenshot 结果表明传播处理会造成明显证据衰减。Resize-0.5x 的保持率高于 100% 不能解释为抗缩放能力：1000 张真图的假阳率同时由 Original 的 1.50% 升至 Resize-0.5x 的 17.50%，约为 11.7 倍，且观察到 160 个 real→fake 单向翻转、没有相反翻转，说明该结果更符合重采样偏置。

### 7.3 社交媒体传播链结果

| 条件 | 成对 fake 样本数 | Fake Recall | 平均 fake_prob | 相对 Original 保持率 |
|---|---:|---:|---:|---:|
| Original | 8000 | 59.55% | 0.5909 | 100.00% |
| Facebook | 8000 | 21.68% | 0.2747 | 36.40% |
| WeChat | 8000 | 48.19% | 0.4952 | 80.92% |
| Weibo | 8000 | 47.51% | 0.4919 | 79.79% |

平台内完整分类评价中，Facebook、WeChat、Weibo 的 Accuracy 分别为 92.64%、92.50% 和 92.60%，Macro F1 分别为 0.8428、0.8401 和 0.8424，ROC AUC 分别为 0.9929、0.9929 和 0.9930。平台成对实验与平台内分类实验数据构成不同，不能互相替代。

## 8. 局部证据与定位测试

### 8.1 CASIA v1 主评价

在 40 张 tampered 与 10 张 clean 的程序合成评价上，默认 percentile=90 的结果为：

| 指标 | 结果 |
|---|---:|
| Avg IoU | 0.107 |
| Avg Dice / Pixel F1 | 0.177 |
| Avg Precision | 0.145 |
| Avg Recall | 0.242 |
| Detection Rate | 100% |
| Clean FP Rate | 100% |
| Clean Avg Bbox Count | 7.9 |

percentile=80 时 Dice 达到 0.191，percentile=85 时 IoU 达到 0.113，但阈值选择仍然依赖当前数据构成，不能跨数据集外推。

### 8.2 AIGC 派生边界评价

在 10 张 tampered 与 5 张 clean 的 Facebook 派生 GenImage 合成评价上，Avg IoU 为 0.0148，Pixel F1 为 0.0286，Detection Rate 为 100%，Clean FP Rate 为 100%，clean 平均局部框数量为 9.8。

两个定位评价共同表明：局部模块能够产生稳定的图像级关注区域，但当前输出与像素级篡改掩膜的重叠较低，clean 样本也会产生局部框。当前热力图和 bbox 的适当定位是“解释模型关注位置、辅助人工复核”，而不是“确认真实篡改边界”。

## 9. 风险融合与审核分流测试

### 9.1 策略对比

在 200 张平衡集上，策略 A 为 `fake_prob > 0.5`，策略 B 为 `risk_level >= medium`：

| 指标 | 策略 A | 策略 B |
|---|---:|---:|
| Precision | 0.9785 | 0.9083 |
| Recall | 0.9100 | 0.9900 |
| F1 | 0.9430 | 0.9474 |
| FN | 9 | 1 |
| 与另一策略总体一致率 | — | 92.00% |

策略 B 多捕获 16 个策略 A 会漏掉的样本。这些样本平均 `fake_prob=0.2935`，但平均局部框数量为 8.0，平均 `risk_score=0.3970`，说明局部证据和多维风险融合可以将部分低伪造概率样本升级为人工复核对象。

### 9.2 留出集评价

在 60/40 分层留出设置下，120 张用于校准，80 张用于留出评价：

| 分流边界 | Precision | Recall | F1 | TP | FP | FN | TN |
|---|---:|---:|---:|---:|---:|---:|---:|
| review，threshold=0.3947 | 0.9756 | 1.0000 | 0.9877 | 40 | 1 | 0 | 39 |
| high，threshold=0.4232 | 1.0000 | 1.0000 | 1.0000 | 40 | 0 | 0 | 40 |

留出集结果支持当前 200 张单一来源样本内的候选审核分流逻辑；它不支持将阈值推广到其他数据集、平台或传播条件。生产默认阈值仍由当前风险模块管理，校准结果未自动替换生产配置。

## 10. 平台运行与短时烟测

平台烟测向本地 `/api/v1/analyze` 端点发送同一精选测试图像 12 次，并发度为 3，超时时间为 60 秒。结果如下：

| 指标 | 结果 |
|---|---:|
| 成功请求 | 12/12 |
| 成功率 | 100% |
| 总耗时 | 3.588 秒 |
| 吞吐 | 3.345 requests/s |
| 最小延迟 | 0.445 秒 |
| 中位延迟 | 0.520 秒 |
| P95 延迟 | 2.075 秒 |
| 最大延迟 | 2.075 秒 |
| HTTP 状态 | 200 |

该测试证明单机、单图、短时条件下 API 能够连续返回符合合同的结果。由于请求使用同一图像且运行时间较短，不能据此推导饱和容量、多用户并发、长时稳定性或线上 SLA。

## 11. 缺陷、风险与限制

### 11.1 已识别的限制

1. 跨生成器结果受数据来源、固定权重和测试划分影响，难例生成器之间存在显著差异；
2. JPEG、缩放和截图只覆盖当前派生算子，真实平台压缩链路仍可能存在未测变体；
3. Resize-0.5x 的高 Fake Recall 与真图假阳上升同时出现，不能作为鲁棒性结论；
4. 定位模块在当前合成数据上 Clean FP Rate 为 100%，不支持像素级精确定位；
5. 风险阈值校准仅覆盖 Facebook 派生 200 张样本，不能外推到更多来源；
6. 平台仅完成短时单机烟测，尚未完成长时、饱和容量和多输入并发测试；
7. 当前尚未形成更大规模、多来源的热力图相似度和定位定量评价；
8. 裁剪扰动尚未形成正式冻结结果。

### 11.2 测试结论边界

本报告支持的核心结论是：TraceGuard 已经形成可运行的图像安全审核闭环，能够在固定实验构成下完成全局检测、局部证据生成、风险分流和报告输出；跨域适配、零样本识别和风险融合具有当前数据范围内的实验证据；传播退化和局部定位误报能够被系统测量并显式呈现。

本报告不支持以下结论：系统在所有生成器和所有传播平台上均保持高准确率；局部 bbox 等同于真实篡改边界；风险阈值适用于所有数据集；短时烟测等同于生产容量或长期稳定性；任何单一实验数字等同于正式比赛成绩。

## 12. 复现与证据索引

入库证据的唯一归宿为 `experiments/*/verified_results/`。各目录中的 `README.md` 说明结果口径边界，`provenance.json` 固定权重、数据归档、逐样本原始预测和汇总文件的哈希关系。

| 测试线 | 报告级证据 |
|---|---|
| 跨域检测 | `experiments/crossdomain/verified_results/eval_results.csv`、`eval_results_no_mmd.csv` |
| 零样本公开子集 | `experiments/eximage/verified_results/zeroshot_summary_all.csv`、`zeroshot_summary_by_generator.csv` |
| 确定性扰动 | `experiments/perturbation/verified_results/perturb_full_summary_all.csv`、`real_fp_summary_all.csv` |
| 社交媒体传播 | `experiments/socialmedia/verified_results/paired_summary_all.csv`、`classification_summary.csv`、`case_summary.csv` |
| 定位评价 | `experiments/localization/verified_results/aigc_synthetic_15_summary.json`、阈值扫描 CSV |
| 风险校准 | `experiments/risk/verified_results/facebook_balanced_200_summary.json` |
| 平台烟测 | `experiments/platform/verified_results/runtime_smoke_summary.json` |

建议复现命令：

```powershell
python -m pytest tests -q
python server.py --device cuda
python run_test.py --input-dir tests/fixtures --output case_study
python batch_analyze.py --input-dir tests/BigGAN --output batch_results --csv batch_results/results.csv
```

其中大规模数据评价需要先按库存文件补齐外部数据集；若仅进行代码回归和精选样例验收，可使用仓库内 `tests/fixtures/`。

---

报告版本：v1.1

报告日期：2026 年 8 月 26 日
