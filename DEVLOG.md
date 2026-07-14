# TraceGuard Devlog

更新时间：2026-07-14
技术封版目标：2026-07-20

## 使用规则

- 本文件记录当前已验证进展、阻塞项、下一步任务和负责人。
- 每次 `git fetch`、`git pull`、切换分支或开始新任务后，先阅读本文件，再读取任务相关代码、配置、测试和实验资产。
- 本文件仅仅提供工作导航，不替代 Git 历史、GitHub Issue、实验 CSV、测试输出或接口合同。
- 完成任务、合并 PR、替换权重、更新实验结果或改变下一步优先级后，在同一工作中更新本文件。
- 条目按时间倒序排列。未经当前资产验证的结果必须标记为“待复核”，不得写成已完成事实。

## 当前研究方向与关注点（2026-07-14 更新，队友请先读本节）

**研究方向（已定稿）**：TraceGuard 面向社交媒体传播链末端的可解释 AIGC 图像审核。2026-07-14 起在原「社交媒体压缩鲁棒性」主线上叠加「超监管高危内容」应用场景，按 **L1 档**执行——报告以第三人称引用公开文献叙述超监管威胁（L0 叙事已并入主稿 1.1/1.2/1.3/4.1，参考文献加 \[9\]），并用自研检测器做零样本 + 传播扰动的边界评测。**绝不接入外部模型/权重/代码复现（B 档，取消资格风险）。** ExImage 数据到位放弃线 2026-07-16 24:00，未到位则退回纯 L0，不影响封版。

**当前状态一句话**：派生扰动实验流水线已落地并跑完 GenImage 全量；报告结构性硬伤已清；等三人补齐可追溯的原始证据。

- 派生扰动实验（JPEG-75/50、Resize-0.5x、截图模拟）已由 `experiments/socialmedia/perturb.py` + `evaluate.py paired-derived` 落地，跑完 GenImage 全量 8000×5（40000 预测 0 失败，见下方基线表与本文最新条目）。**此项原列为张潇待办，现已由集成侧完成，张潇无需重做。**
- resize50 反常 recall 升高**已定性（P3 真图假阳检查完成，output/perturb_real_fp/）**：1000 张真图 FP 从 1.50%→17.50%（约 11.7x），mean fake_prob +155.6%，160 例 real→fake 单向翻转、0 例反向，证明是重采样偏置——resize50 不分真假地整体抬高 fake 预测，那 137.9% 的 fake-recall 是虚高、**不是鲁棒性证据**（结论写入报告 3.3.2 解释边界；#16）。
- 报告主稿结构性硬伤已修、各章字数达标；第一章/第四章扩写目前仅为草稿（`docs/report_draft_ch1_ch4_2026-07-14.md`），**待队长审阅后才并入主稿**。

**三人当前关注点（可执行清单见对应 GitHub Issue）**：
- 张潇 → **#14**：跨域「提升 17%+」消融原始表；AIGCDetectBenchmark/AIGIBench/Chameleon/test_eachfake_500_real500 四套测试集的**传播前原始版本**（对齐 stem 以解锁大规模成对保持率）；`REPRODUCIBILITY.md` 完整复现链。
- 贺杰 → **#15**：定位/可解释与风险阈值在**更多独立来源**上的复评；真实篡改案例的标注依据、指标、baseline 与局限。
- 朱羿帅 → **#16**：冻结的全量扰动结果写入报告 3.3.2；resize50 真图假阳检查；ch1/ch4 草稿并入；07-20 封版同步与匿名化复核。

封版 2026-07-20，提交 2026-08-02。红线：报告/答辩禁现「实验室/导师/同组工作」等身份措辞；ExImage 与 ExDA 权重不进 Git、不进提交包。

## 当前状态

### 2026-07-14 - 超监管方向按 L1 落地，扰动实验流水线跑通

- 导师提议"社交媒体压缩 × 超监管"经评审后按 L1 方案执行：报告第一章/第四章已并入超监管威胁叙事（第三人称引用），参考文献新增 \[9\]（ExDA, ACM MM'25, DOI 10.1145/3746027.3755434）。红线：不接入 ExDA 模型/权重，ExImage 数据不进 Git 与提交包，报告与答辩禁止出现"实验室/导师"等身份措辞。
- `reports/TraceGuard.md` 完成结构性修复：2.2.4 补 REST 字段表；2.5 改为已实现口径并与 2.4.5 对齐；两处 LaTeX 公式缺陷修复（转 Word 前置条件）；3.2 指标定义压缩；3.4 定位边界数字改为表 3.4，原平台验收表改号表 3.5；分散免责句收编为 3.5 末尾"结果解释边界"。各章 CJK 字数经脚本核查：544→759 / 3817→3927 / 2224→**1998（上限 2000）** / 501→557 / 307，全部达标。
- 新增 `experiments/socialmedia/perturb.py`：JPEG-75/JPEG-50/Resize-0.5x/截图模拟四种确定性派生（固定 ZIP 时间戳，字节级可复现），输出与 `expand_pair_manifest` 兼容的宽表 manifest。`evaluate.py` 新增 `paired-derived` 子命令，成对汇总的变体列表参数化（默认值不变，向后兼容）。新增 `tests/test_socialmedia_perturb.py` 11 项；除 4 个已知环境缺依赖模块外全量 181 项通过（总可收集 190 项）。
- GenImage 200 样本试点（每生成器 25 张，同一 29F85 权重，1000 次预测 0 失败）：original Fake Recall 74.0%；jpeg75 12.0%（保持率 16.2%）；jpeg50 0.5%（0.7%）；resize50 88.5%（119.6%，**反升现象待解释，疑与模型依赖高频特征有关**）；screenshot 32.0%（43.2%）。JPEG 量化是证据破坏主因，与 Facebook 传播退化互证。结果在 `output/perturb_pilot/`（试点性质，未进 verified_results）。
- 全量 8000 样本 × 5 条件流水线**已跑完**（8 生成器各 1000 张，40000 次预测 0 失败，冻结于 `output/perturb_full/`，各派生 ZIP 与源 ZIP 的 SHA-256 记于 `run_metadata.json`）。全量口径 original Fake Recall 59.5%；jpeg75 9.9%（保持率 **16.6%**）；jpeg50 2.3%（**3.9%**）；resize50 82.1%（**137.9%，反升复现**）；screenshot 24.4%（41.0%）。JPEG 量化仍是证据破坏主因，结论在全量上稳固。**resize50 反升机理已定位**：by-generator 显示它把所有生成器 recall 拉到 ~0.83-0.89 与原始 recall 无关（VQDM 0.131→0.834 达 6.37x，BigGAN 0.949→0.846 反降到 0.89x），指向"降采样再放大"被读成伪造的重采样偏置，**必须用 `dataset/Real` 做真图假阳检查才能定性**（见 Issue、报告 3.3.2 待写）。该实验同时覆盖并替代张潇待交付的 JPEG/Resize/Screenshot 派生扰动项。
- ExImage.zip（12.1GB，Google Drive）下载触发配额限制，间歇重试累计到 1.72GB 后，**朱羿帅确认可不依赖 Google Drive 从其他渠道获取 ExImage，重试守护已停止**；断点文件 `dataset/eximage/ExImage.zip*.part` 保留可续传。放弃线不变：7-16 24:00 前数据未到位则退回 L0 纯叙事，不影响封版。拿到数据后执行命令见 `docs/report_guidance_2026-07-14.md` 第五节（perturb 派生 + paired-derived 推理，两条命令）。
- 第一章扩写/第四章对账/摘要重排的草稿在 `docs/report_draft_ch1_ch4_2026-07-14.md`，待队长审阅后并入主稿；完整报告指导在 `docs/report_guidance_2026-07-14.md`。
- 已知环境性问题（非回归）：`tests/test_windows_launcher.py` 在控制台代码页 65001（UTF-8）+ 中文工作目录下失败（cmd 相对路径 bat 解析缺陷），常规 GBK 控制台不受影响。

### 2026-07-14 - 正式交接入口已建立

- GitHub Issue #12（`封版交接：补齐张潇与贺杰实验材料`）已创建，作为技术封版前的材料交接清单。
- 当前开发分支为 `codex/socialmedia-robustness`；本地已完成 `origin/main` 合并及队友定位/风险代码的本地集成，待通过 draft PR 交接到远端审阅。
- **尚未收到张潇的材料**：跨域方法“提升 17%+”对应的消融原始 CSV、实验配置和结果来源；JPEG/Resize/Crop/Screenshot 派生扰动的固定样本、参数、命令和指标；`REPRODUCIBILITY.md` 引用的实际训练脚本、评测脚本和完整数据目录。
- **尚未收到贺杰的材料**：更多独立来源上的定位与可解释分支定量评价；真实篡改案例的标注依据、数据来源、指标定义、baseline、结果和局限；更多独立来源上的风险权重及 low/medium/high 阈值校准、独立验证集和旧值对比。
- 当前已完成的 Facebook 派生校准、定位边界评价和社交媒体传播实验仅仅代表当前证据范围，不能替代上述待交付材料。

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
- ~~尚未完成 JPEG、缩放、裁剪和截图转存的系统鲁棒性实验。~~ **已完成**：`perturb.py` 派生 + GenImage 全量 8000×5 成对推理已冻结于 `output/perturb_full/`（0 失败）；resize50 反常升高待真图假阳检查（#16）。
- 尚未完成更多独立来源上的风险权重与 low/medium/high 阈值复核；Facebook 派生平衡集的 60/40 留出校准已完成。
- 尚未完成更多来源的可解释与局部定位定量评价；Facebook 派生 AIGC 边界评价已完成。
- `REPRODUCIBILITY.md` 中的 `train.py`、`eval.py`、`实验数据表.md` 和数据目录当前未全部进入本仓库，完整复现链仍需核对。
- 报告已完成当前证据范围内的图表、引用、实验分析和官方 Word 工作稿；最终封版仍等待更多算法原始证据与封面字段。
- 原创性声明已按官方模板预填作品名并完成视觉核查；签名、盖章和学校提交负责人仍需确认。
- 已完成 Facebook 派生 AIGC 平衡集的 60/40 分层留出风险校准，以及 10 tampered + 5 clean 的像素级定位边界评价；结果仅支持当前来源的候选阈值和局限性说明。
- 已集成贺杰的定位/风险评价基础设施，修正 CLI 重型导入、案例 manifest BOM 和案例冲突方向判定；全量测试更新为 179 项。

## 下一步任务

### P0：张潇，跨域检测与传播鲁棒性（详见 Issue #14）

- 核对 `REPRODUCIBILITY.md` 中训练/评测命令与本仓库实际脚本、目录是否一致。
- 补交“跨域提升 17%+”对应的消融原始表、实验配置和结果来源。
- 交付 AIGCDetectBenchmark/AIGIBench/Chameleon/test_eachfake_500_real500 四套测试集的**传播前原始版本**，`sample_id`/stem 与现有传播后版本对齐，以便把成对保持率协议扩展到真实跨域数据。
- ~~继续建立 JPEG、Resize、Screenshot 的派生配对~~ **已由集成侧完成（perturb.py + 全量 GenImage 实验），张潇无需重做**；如需在真实跨域数据上复用，仅需确认派生协议与检测器评测口径一致。
- 所有正式数字必须能追溯到 CSV、配置和命令。

### P0：贺杰，可解释证据与风险复核（详见 Issue #15）

- **已完成**：定位定量评价基础设施与风险阈值校准分析框架（分支 `codex/localization-eval-risk-calibration`）。
- **当前状态**：已使用现有 Facebook 派生 AIGC 数据完成边界评价与风险留出校准；更多独立来源仍等待张潇的扰动/消融材料。
- 使用与张潇相同的 `sample_id` 分析传播前后热力图、bbox、风险等级和证据一致性变化。
- 完成成功、证据衰减、证据冲突三类案例。
- 完成定位定量评价；Grad-CAM 仅仅表述为分类证据响应，不替代定位指标。—— **Facebook 派生 AIGC 边界评价已完成，更多来源待补。**
- 对比仅使用 `fake_prob` 与五维风险融合的审核效果，统计人工复核触发率。—— **Facebook 派生平衡集留出校准已完成，更多来源待补。**
- 输出可直接进入报告的案例图、结果表和局限说明。

### P0：朱羿帅，集成、报告与提交（详见 Issue #16）

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
