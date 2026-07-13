# TraceGuard Devlog

更新时间：2026-07-14
技术封版目标：2026-07-20

## 使用规则

- 本文件记录当前已验证进展、阻塞项、下一步任务和负责人。
- 每次 `git fetch`、`git pull`、切换分支或开始新任务后，先阅读本文件，再读取任务相关代码、配置、测试和实验资产。
- 本文件仅仅提供工作导航，不替代 Git 历史、GitHub Issue、实验 CSV、测试输出或接口合同。
- 完成任务、合并 PR、替换权重、更新实验结果或改变下一步优先级后，在同一工作中更新本文件。
- 条目按时间倒序排列。未经当前资产验证的结果必须标记为“待复核”，不得写成已完成事实。

## 当前状态

### 已完成并进入 `main`

- Web、FastAPI、CLI 和批量分析入口已经形成单图审核闭环。
- `Detector.predict()` 是 `label` 与 `fake_prob` 的唯一权威来源。
- 已实现 Stage2 14x14 Grad-CAM、patch + feature 局部定位、五维风险融合、中文解释和 HTML 报告。
- 启动程序会依次查找 `checkpoints/best.pth` 与根目录 `best.pth`。
- 已建立数据、模型和交付物库存清单。
- `reports/TraceGuard.md` 已作为多人协作报告工作源进入 Git。
- 张潇已提交跨 8 个生成器的平衡盲测结果与复现说明，见 `REPRODUCIBILITY.md` 和 `eval_results.csv`。

### 当前实验基线

| 项目 | 当前记录 | 证据 | 解释边界 |
|---|---:|---|---|
| 8 生成器平均 Accuracy | 79.68% | `eval_results.csv` | 平衡测试集上的宏观平均，不代表所有社交传播条件 |
| BigGAN Accuracy | 97.35% | `eval_results.csv` | 1000 real + 1000 fake |
| BigGAN Fake Recall | 94.90% | `eval_results.csv` | README 中“BigGAN 检出率 94.9%”的正式口径 |
| Real Recall | 99.80% | `eval_results.csv` | 当前 8 组测试使用同一源域 real 子集 |
| GenImage Facebook Fake Recall | 21.675% | `experiments/socialmedia/verified_results/paired_summary_all.csv` | 8000 个 fake-only 成对样本，不是完整二分类 Accuracy |
| GenImage WeChat Fake Recall | 48.1875% | `experiments/socialmedia/verified_results/paired_summary_all.csv` | 相对 Original 59.55%，保持率 80.919% |
| GenImage Weibo Fake Recall | 47.5125% | `experiments/socialmedia/verified_results/paired_summary_all.csv` | 相对 Original 59.55%，保持率 79.786% |
| 三平台分类 Accuracy | 92.50%–92.64% | `experiments/socialmedia/verified_results/classification_summary.csv` | 每平台 500 real + 4500 fake，类别不平衡且无 Original 对应版本 |
| 跨域提升 17%+ | 待补直接证据 | `REPRODUCIBILITY.md` 指向尚未入库的 `实验数据表.md` | 在消融原始表入库前不得作为已复核结论 |

### 当前主要缺口

- GenImage 的 Original/Facebook/WeChat/Weibo 8000 组成对推理、性能保持率分析、两张汇总图和三类典型案例均已完成。
- AIGCDetectBenchmark、AIGIBench、Chameleon 和 `test_eachfake_500_real500` 的传播后数据已就绪，但对应原始版本尚未定位，暂时不能计算成对性能保持率。
- 尚未完成 JPEG、缩放、裁剪和截图转存的系统鲁棒性实验。
- 尚未完成更多独立来源上的风险权重与 low/medium/high 阈值复核；Facebook 派生平衡集的 60/40 留出校准已完成。
- 尚未完成更多来源的可解释与局部定位定量评价；Facebook 派生 AIGC 边界评价已完成。
- `REPRODUCIBILITY.md` 中的 `train.py`、`eval.py`、`实验数据表.md` 和数据目录当前未全部进入本仓库，完整复现链仍需核对。
- 报告已完成当前证据范围内的图表、引用、实验分析和官方 Word 工作稿；最终封版仍等待更多算法原始证据与封面字段。
- 原创性声明已按官方模板预填作品名并完成视觉核查；签名、盖章和学校提交负责人仍需确认。
- 已完成 Facebook 派生 AIGC 平衡集的 60/40 分层留出风险校准，以及 10 tampered + 5 clean 的像素级定位边界评价；结果仅支持当前来源的候选阈值和局限性说明。
- 已集成贺杰的定位/风险评价基础设施，修正 CLI 重型导入、案例 manifest BOM 和案例冲突方向判定；全量测试更新为 179 项。

## 下一步任务

### P0：张潇，跨域检测与传播鲁棒性

- 核对 `REPRODUCIBILITY.md` 中训练/评测命令与本仓库实际脚本、目录是否一致。
- 补交“跨域提升 17%+”对应的消融原始表、实验配置和结果来源。
- 以已固定的 GenImage `sample_id` 运行 Original、Facebook、WeChat、Weibo 成对推理，并继续建立 JPEG、Resize、Screenshot 的派生配对。
- 输出各条件的 Accuracy、F1、AUC、Recall、性能下降量和性能保持率。
- 所有正式数字必须能追溯到 CSV、配置和命令。

### P0：贺杰，可解释证据与风险复核

- **已完成**：定位定量评价基础设施与风险阈值校准分析框架（分支 `codex/localization-eval-risk-calibration`）。
- **当前状态**：已使用现有 Facebook 派生 AIGC 数据完成边界评价与风险留出校准；更多独立来源仍等待张潇的扰动/消融材料。
- 使用与张潇相同的 `sample_id` 分析传播前后热力图、bbox、风险等级和证据一致性变化。
- 完成成功、证据衰减、证据冲突三类案例。
- 完成定位定量评价；Grad-CAM 仅仅表述为分类证据响应，不替代定位指标。—— **Facebook 派生 AIGC 边界评价已完成，更多来源待补。**
- 对比仅使用 `fake_prob` 与五维风险融合的审核效果，统计人工复核触发率。—— **Facebook 派生平衡集留出校准已完成，更多来源待补。**
- 输出可直接进入报告的案例图、结果表和局限说明。

### P0：朱羿帅，集成、报告与提交

- 维护本 devlog、接口一致性和 Git 工作边界。
- 将两位成员交付的实验结果转换为评审可读的实验逻辑与结论。
- 维护 `reports/TraceGuard.md`，最终统一同步到官方 Word 模板。
- 确认原创性声明签名、盖章和联络教师上传流程。
- 7 月 19 日冻结技术内容，7 月 20 日仅仅处理封版阻塞问题。

## 变更记录

### 2026-07-13 - 单机短时并发烟测完成

- 从未封版工作包启动 CUDA 服务，以固定样例向单图接口发送 12 个请求，并发度为 3；12/12 返回 200 且响应合同完整。
- 总耗时 3.588 秒，吞吐 3.345 请求/秒，中位延迟 0.520 秒，P95 2.075 秒；汇总、环境和哈希进入 `experiments/platform/verified_results/`。
- 该结果仅仅是短时单机烟测，不支持长期稳定性、饱和容量、多用户多输入或生产 SLA 主张。

### 2026-07-13 - 官方报告工作稿与签章材料完成

- `reports/TraceGuard.md` 已同步到官方作品报告模板，生成 25 页 Word/PDF 工作稿；10 个模板节、目录与动态页码、14 张图片、表格、公式和新增定位/校准证据页均完成结构审计与逐页视觉核查。
- DOCX 可访问性审计结果为 0 个高/中/低问题，模板原件保持不变；生成器和对应测试已纳入仓库。
- 原创性声明已使用官方模板预填作品名并完成单页渲染，手写签名、日期和教务公章保持为空。
- 已生成包含 Git 跟踪源码、Windows 启动入口、四份报告/声明材料和正式权重的未封版工作包；权重 SHA-256 与库存一致，从包内启动 CUDA 服务后健康接口返回 200、`model_loaded=true`。
- 当前报告仅仅等待张潇的消融/扰动原始材料、更多来源复核材料，以及团队邮箱、提交日期和线下签章上传信息。

### 2026-07-13 - 社交媒体传播鲁棒性正式实验完成

- 使用 SHA-256 为 `29F85...0474` 的 `best.pth`，在 RTX 4060、PyTorch 2.5.1+cu121 环境运行。
- GenImage 成对实验完成 32000 个唯一预测键，0 失败；Original 的八生成器 Fake Recall 与 `eval_results.csv` 逐项一致。
- 三个平台分类实验完成 15000 个唯一预测键，0 失败；每个平台包含 500 real 与 4500 fake。
- 小型汇总、指标边界和来源哈希已冻结到 `experiments/socialmedia/verified_results/`；逐样本原始预测继续保持 ignored。
- 结果显示不同数据构成下平台影响差异显著，报告必须并列解释，不得仅仅引用较高 Accuracy 回避 GenImage 的传播退化。

### 2026-07-13 - 全局判定与局部证据合同修复

- `label` 与 `fake_prob` 继续仅由 `Detector.predict()` 产生，局部定位不再将全局 `real` 改写为 `local_tamper`。
- API、Web、CLI、HTML 报告新增或同步 `tamper_type` 独立字段；证据冲突时保留两类输出并提示人工复核。
- `tests/test_pipeline.py::TestPipelineMock::test_low_fake_pipeline` 改用确定性定位结果，消除随机特征是否产生 bbox 导致的非确定性。
- 该修复、报告/提交工具、运行烟测工具、定位/风险评价工具与 Windows 启动入口已通过 179 项全量测试；真实 GPU API 返回 `label=real`、`tamper_type=local_tamper`，桌面和 390x844 窄屏浏览器上传闭环均通过，控制台 0 错误。

### 2026-07-13 - 社交媒体典型案例固定

- 从 32000 条成对预测中固定稳定、Facebook 退化和全局/局部证据冲突三类 `sample_id`，并对 12 个传播版本运行完整 ExplanationPipeline。
- 稳定案例的 Original/Facebook `fake_prob` 为 0.996/0.995；退化案例为 0.967/0.018；冲突案例在两种条件下均保留 `label=real` 与 `tamper_type=local_tamper`。
- 案例汇总进入 `experiments/socialmedia/verified_results/case_summary.csv`，报告级案例图进入 `docs/figures/socialmedia/`。
- 当前红框仅仅是工程解释证据，不是带像素级真值的定位精度结论。

### 2026-07-13 - 报告系统图完成

- 图 2-1 固定“单一输入、唯一全局判定来源、并行局部证据、融合输出”的真实代码关系。
- 图 2-2 使用实测样例展示原图、Grad-CAM 叠加图和可疑区域，明确解释证据不等同于像素级真值。
- 图 2-3 固定上传、校验、统一 API、GPU 推理、证据渲染、人工复核和报告导出流程。
- 三图均由 Python 工作流生成并完成 PNG 视觉核查，报告占位已替换。

### 2026-07-13 - 社交媒体数据完成本地准入核验

- Facebook、WeChat、Weibo 三个外层下载包已完成 SHA-256 登记，并解压得到 15 个内层测试集 ZIP。
- 15 个内层 ZIP 的全部条目已逐条完整读取，未发现读取错误；`.ipynb_checkpoints` 下的重复图片已标记为正式实验排除项。
- GenImage 原图与三个社交平台版本各有 8000 张有效图片，文件主名均唯一，8000 组 `sample_id` 全部完整配对。
- 本地生成 `dataset/socialmedia/manifests/archive_inventory.csv` 和 `genimage_socialmedia_pairs.csv`；两者当前受 `dataset/` 忽略规则保护，不进入 Git。
- 当前结论仅仅证明数据准入与配对完成，不代表传播鲁棒性指标已经产出。

### 2026-07-13 14:51 - 张潇跨域实验材料进入 `main`

- 提交：`af22feed3d0ce34c4a0287065ae2acccb664cbad`
- 作者：张潇 GitHub 账号 `zx973`
- 新增：`REPRODUCIBILITY.md`
- 新增：`eval_results.csv`
- 已确认：8 个生成器平衡盲测表、数据划分、训练配置和复现命令说明已提供。
- 待确认：复现命令引用的训练脚本、评测脚本、数据目录和消融原始表是否已在其他位置提供。

### 2026-07-13 — 贺杰：定位定量评价与风险阈值校准基础设施

- 分支：`codex/localization-eval-risk-calibration`
- 新增 `experiments/synthetic_dataset.py`：从给定 real/fake 图像目录生成带像素级 GT 掩膜的合成篡改图。
- 新增 `evaluate_localization.py`：TamperDetector 逐样本 IoU / Dice / Pixel F1 / Image Recall 评价 + 百分位阈值扫描。
- 新增 `calibrate_risk.py`：支持分层校准/留出评估、策略对比和有序风险边界选择。
- 当前正式 AIGC 结果：Facebook 派生平衡集 100 real + 100 fake，60/40 留出；review F1=0.9877，high F1=1.0。定位边界评价为 10 tampered + 5 clean，Avg IoU=0.0148、Pixel F1=0.0286、clean FP=100%。
- 新增 `classify_cases.py`：传播链案例自动分类；已用 3 个固定 `sample_id` 跑出 3 success、1 degradation、2 conflict_degraded、3 conflict。
- 已知待处理：`scorer.py` 中 risk_levels 硬编码, YAML `risk.levels` 不生效；`FeatureStatsAnalyzer` 方差方法对自然图像纹理也产高异常分。

### 2026-07-13 - 报告与工作区基线整理

- `reports/TraceGuard.md` 成为多人协作报告工作源。
- 启动路径、资产库存和工作区规范已经进入仓库。
- 当前工作重点从功能扩张切换为跨域/传播实验、风险校准、报告证据与 7 月 20 日技术封版。
