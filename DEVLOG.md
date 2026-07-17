# TraceGuard Devlog

更新时间：2026-07-17
技术封版目标：2026-07-20

## 使用规则

- 本文件记录当前已验证进展、阻塞项、下一步任务和负责人。
- 每次 `git fetch`、`git pull`、切换分支或开始新任务后，先阅读本文件，再读取任务相关代码、配置、测试和实验资产。
- 本文件仅仅提供工作导航，不替代 Git 历史、GitHub Issue、实验 CSV、测试输出或接口合同。
- 完成任务、合并 PR、替换权重、更新实验结果或改变下一步优先级后，在同一工作中更新本文件。
- 条目按时间倒序排列。未经当前资产验证的结果必须标记为“待复核”，不得写成已完成事实。

## 当前研究方向与关注点（2026-07-15 更新，队友请先读本节）

**研究方向（已定稿）**：TraceGuard 面向社交媒体传播链末端的可解释 AIGC 图像审核，叠加「超监管高危内容」应用场景，按 **L1 档**执行——报告第三人称引用公开文献 \[9\] 叙述超监管威胁，用自研检测器做零样本 + 传播扰动的边界评测。**绝不接入外部模型/权重/代码复现（B 档，取消资格风险）；ExImage/ExDA 权重与代码不进 Git、不进提交包、不接入系统。**

**★ 2026-07-15 叙事转向（队友务必知悉）**：报告改为**能力前置（capability-forward）**。此前草稿按实验顺序组织，最先出现的都是脆弱性数字（盲测 79.68%、Facebook recall 塌到 21.675%、定位精度低），导致「产品能力没凸显、像个偏弱检测器裹免责声明」。新叙事把**能力头牌**提到台前，**传播退化从"中心贡献"降级为"平台自诊断能力的背书"**：
- **能力头牌 = 零样本超监管识别力 + 可信平台**。开头先亮最硬的数字（超监管零样本 98.00% recall，纯公开子集；真图低误伤以通用盲测 Real Recall 99.80% 为准，见 07-17 纠偏条目），再讲差异化能力：证据退化时系统**自己知道并精准转人工、绝不静默改判**。
- 诚实局限（VQDM/ADM 难例、定位精度低、阈值不可外推）**一条不删、数据不动**，但从各节"主旋律"降为"边界脚注"，不再抢在能力主张前定调。红线不变。

**当前状态一句话**：能力前置主稿、真实图 2-2 和五章字数收口均已完成；`output/TraceGuard.docx` / `.pdf` 共 24 个物理页面，正文页码 1--21，逐页视觉核验无截断。五章可见汉字为 617/4022/1416/447/145，匿名禁词、裸路径、SHA、姓名邮箱和占位词扫描均为 0；全量测试 191/191 通过。提交包已改为运行白名单，内部协作与作者文件不再进入 `program/`。

- **超监管零样本实验已完成（P2，0 失败）**：fake 11250/11250 + real 1000/1000。零样本 9 生成器 Fake Recall 均匀落在 94.0%–100.0%、总体 **98.84%**，真图假阳仅 **1.4%**（高召回未牺牲真图判别）。传播扰动 jpeg75 保持率 18.2% / jpeg50 8.6% / resize50 100.7% / screenshot 55.5%——与通用内容同构脆弱、JPEG 仍是头号破坏面。已写入报告 3.3.4（表 3.6/3.7）。诚实边界：ExImage 生成器构成比 GenImage 易（无 VQDM/ADM 难例），绝对值不与 GenImage 逐项比，方向性结论"零样本识别可跨内容域迁移"稳健。
- 派生扰动实验（JPEG-75/50、Resize-0.5x、截图模拟）已由 `experiments/socialmedia/perturb.py` + `evaluate.py paired-derived` 跑完 GenImage 全量 8000×5（40000 预测 0 失败）。**原列张潇待办，已由集成侧完成，张潇无需重做。**
- resize50 反常升高**已定性**（P3 真图假阳检查，output/perturb_real_fp/）：1000 张真图 FP 1.50%→17.50%（约 11.7x），160 例 real→fake 单向翻转、0 例反向，证明是重采样偏置、**非鲁棒性证据**。结论写入报告 **3.3.3 / 表 3.4 †脚注 / 表 3.5**（注意：章节号已随重构变化，不再是旧稿的 3.3.2）。
- 候选重构稿已完成并**已替换主稿**：产品化清洗（0 开发痕迹，SHA/路径/版本串清零）、resize50 加 †脚注、表号重排为连续的 3.1–3.9、41 个原生 OMML 公式。`reports/TraceGuard.md` 现即最新重构稿，`output/TraceGuard.docx` 为最终 Word。
- **结构图已重做 v3（队长 07-15 两轮反馈已落实）**：新增 `scripts/gen_figure_assets.py` 用 matplotlib 渲染**全原创**示意图素材（`docs/figures/system/assets/`：gradcam 真热力图 / backbone 骨干架构图含 2304→256 瓶颈 / mkmmd 域对齐散点 / bbox 篡改定位 / gauge 风险量表 / bars 五维柱状 / 7 个 Web 流程线性图标），`build_figures_pptx.py` v3 嵌入这些图片。字号再放大（标题 34 / 容器标题 16–17 / 标签 13–15）；三张图都补上图像；Web 流程每步加图标。COM 渲染核验无重叠、红线全过。
  - **诚信红线已收口**：拒绝了"抠他人论文示意图补充"的做法。图 2-2 已使用固定 BigGAN 测试样例，经正式权重和 CUDA 端到端推理生成真实输入图、Stage2 Grad-CAM 叠加图和局部定位框；PPT 第 3 页、`detection_example.png` 与报告引用已同步，不再包含示意占位。
  - **07-15 补修（此前疏漏）**：v3 图先前只在独立 pptx 里，**从未导入报告实际引用的三个图文件**，docx 仍嵌 07-14 旧图（队长打开看到"图都没变"即此因）。已用 PowerPoint COM 将 slide1/2/3 导出 2560×1440 覆盖 `system_architecture.png / web_workflow.png / detection_example.png`，PIL 裁去外围留白，重建 docx，转 PDF 逐页核验三图到位。
  - **图内标题全删（队长要求）**：报告图不需自带标题，Word 图下方已有自动题注；`build_figures_pptx.py` 三处 `title_bar` 调用已移除，导出后裁剪。docx 现为 33 页。
**三人当前关注点（★ 已按 07-15 叙事转向重排优先级，可执行清单见对应 GitHub Issue）**：
- 张潇 → **#14**：⬆️**升级为头号**——跨域「提升 17%+」消融原始表（这是**跨域泛化能力证据**，正好支撑新叙事的能力头牌）。⬇️**降级为选做**——四套测试集传播前原图（它产出的是"更多退化证据"，恰是本轮要弱化的方向，不进封版必交清单，有余力再补）。`REPRODUCIBILITY.md` 复现链照旧要补。
- 贺杰 → **#15**：⬆️**升级为头号**——三类案例（稳定/衰减/冲突）做成**干净、低刺激的案例图 + 说明**，直观**演示"可信路由"在工作**（这是"可信平台"能力头牌的最佳证据，风险低）。⬇️**降级为选做**——多独立来源阈值校准（结果不确定且封版逼近，有余力再做）。真实篡改案例标注依据照旧要补。
- 朱羿帅 → **#16**：能力前置改写摘要/Ch1/Ch4 并替换主稿；图 2-2 真实检测证据已收口；维护 DEVLOG 与分工；超监管 3.3.4 已并入；07-20 封版匿名化复核。

封版 2026-07-20，提交 2026-08-02。红线：报告/答辩禁现「实验室/导师/同组工作」等身份措辞；报告匿名（无学校/院系/指导教师，封面邮箱中性）；ExImage 与 ExDA 权重/代码不进 Git、不进提交包、不接入系统；超监管只谈"评测自研检测器"，不声称生成/训练/优化；涉敏图只低刺激远景，绝不打开/显示/导出超监管图像。

## 当前状态

### 2026-07-17 - 超监管零样本数据来源纠偏：换纯公开子集，98.84%→98.00%，撤 1.4%

**背景**：#17 复核发现旧超监管实验（07-15 写入报告 3.3.4）的 2250 fake / 500 real 是**公开(js 中缀)+ 非公开(db 中缀)混合子集**，真图半区来自未公开的内部 ExImage-v2。按红线「不依赖未公开内部资源」，必须换成纯公开可复现数据。

- **crc32 独立复核（未解码任何图像，仅读 ZIP 中央目录）**：旧 `fake_subset.zip` 2250 张中，js 中缀 1152/1152 命中公开 ExImage.zip、db 中缀 0/1098 命中——证实旧集一半来自非公开数据。
- **纯公开重跑**：`experiments/eximage/build_public_subset.py`（seed=42 确定性抽样，9 生成器 × 250 = 2250 fake，各生成器 test/ 实为 800 张、LatentDM 仅 405，全部够抽、无重复 crc32）→ `evaluate.py paired-derived` 补全 5 变体 × 2250 = **11250 行，0 失败**（CPU，无可用 CUDA）。
- **新数字（纯公开、可复现、无来源争议）**：original 总体 Fake Recall **98.00%**（旧混合集 98.84%，仅 -0.84pp，`comparable=false` 不可混用）；逐生成器 92.4%–100.0%（MJ 92.4 最低，CycleGAN/Flux 100）。传播扰动保持率 jpeg75 **19.8%** / jpeg50 **12.2%** / resize50 **101.1%** / screenshot **56.8%**。
- **1.4% 真图假阳率已撤**：公开 ExImage 未释出 real 半区，本内容域假阳率无法在公开子集复现；报告改以通用八生成器盲测 Real Recall 99.80% 撑「真图低误伤」。
- **核心价值**：换纯公开数据后头牌数字毫发无损，且在**全新内容域独立复现「JPEG 量化是证据破坏主通道」**（98%→19%→12%，resize 近无损、截图居中）——从「补窟窿」变「添独立佐证」。
- **已落地**：报告 3.3.4 表 3.6/3.7 + 摘要/1.3/4.1/结论共 6+ 处数字全线更新并自洽；`experiments/eximage/verified_results/` 冻结（README 口径边界 + provenance.json 哈希锚点[已相对化绝对路径] + 3 份汇总 CSV），代码 + test（11 项全绿）入库，**无数据无权重无图片**。commit `2ac53f9`，已 push。数据/权重/output 全 gitignored。
- **张潇 #14 已再点**（[issue 评论](https://github.com/Suaiii/TraceGuard/issues/14#issuecomment-5005897448)）：确认口径错标已改对（Average 改成真实 Fake Recall 49.60→59.55），剩两项封版前必交——① `train.py`/`eval.py` 死链修复；② 消融两臂「两次独立训练、非单一开关」如实声明（no-MMD checkpoint 已丢，如实说明即可，**不要重训**）。

### 2026-07-17 - 贺杰 #15 / #17-P4 交付物落地

- **#15-A（三类案例图）已完成**：
  - 12 张案例图像（3 样本 × 4 条件）已上传至 `data/case_images/`；扩展 manifest `case_manifest_extended.csv`（3×4=12 行）。
  - `plot_case_evidence.py` 升级：`--roles` 按案例类型筛选、`--variants` 多平台布局、Microsoft YaHei 中文字体、中文标注（判定/伪造概率/风险分/可疑区域/篡改类型）、英文平台标题（Original/Facebook/WeChat/Weibo）、底部中文解释边界声明。
  - **新增三张独立案例图**（#15-A 核心产出）：`socialmedia_case_stable.*` / `socialmedia_case_degraded.*` / `socialmedia_case_conflict.*`，均为 1×4 四平台并排，含黄色【行为】/【关键】叙事框：
    - 稳定案例（SD14）：四平台伪造概率 0.99+ 不动，系统稳定放行
    - 衰减案例（BigGAN）：0.967→0.018 翻转，系统触发转人工而非静默改判
    - 冲突案例（BigGAN）：全局判真但局部持续检出，系统保留分歧转人工
  - **12 张图片已替换为红框 bbox 叠加图**：`generate_bbox_overlays.py` 批量调用 TamperDetector 生成 `data/case_images/bbox/` 下 12 张 bbox 标注图，manifest 同步更新路径。四平台图片各有不同红框分布，不再千篇一律。
  - 合并网格同步更新：3×2（`socialmedia_case_evidence.*`）+ 3×4（`socialmedia_case_evidence_full.*`），均含中文标注 + 叙事框（多案例无行为叙事）。
- **#15-B（篡改标注依据）已完成**：`experiments/localization/verified_results/README.md` 从 4 行占位重写为完整 8 节文档——数据来源（CASIA v1 + AIGC 合成）、标注协议（程序自动生成硬粘贴 GT）、指标定义（IoU/Dice/Pixel F1/Detection Rate/Clean FP + 阈值扫描）、基线对比、结果表（CASIA IoU=0.107/Dice=0.177、AIGC IoU=0.015/Dice=0.029）、局限性（100% clean FP、不支持像素级定位、GT 硬粘贴局限）、与社交媒体案例图关系、复现命令。
- **#17-P4（高危处置叙事）已完成**：`docs/narrative_risk_escalation.md` 含三段叙事——衰减案例证据归零时系统转人工（case_summary 单样本）、策略 B 比策略 A 多捕获 16 个 b_only 样本（risk summary JSON 数据）、冲突案例跨四平台全局/局部分歧（case_classification data）。每段附报告可直接使用的表述和建议位置，含解释边界。
- **#15-D（交付形态合规）已补齐**：对照 `AGENTS.md §12.1` 逐线审计 6 条实验线的 README + provenance.json + 报告级汇总三件套。
  - **`risk/verified_results/`**：
    - README.md：4 行英文重写为 80 行中文口径边界文档——文件清单、策略 A vs B 对比表（Recall 0.910→0.990、b_only 16 样本特征）、holdout 评价（review F1=0.9877 / high F1=1.0）、阈值来源（硬编码 vs 数据驱动）、口径边界（200 张单一来源不可外推、60/40 留出不代表泛化）。
    - provenance.json：补齐 runtime（Python 3.12.4 / Torch 2.6.0+cu124 / RTX 4060）、原始预测三文件 SHA-256（`risk_pipeline_outputs.csv` + `risk_calibration_summary.json` + `risk_conflict_cases.csv`）、cross_checks、gaps 如实标注。
  - **`localization/verified_results/`**：
    - provenance.json：补齐 runtime、**新增 CASIA v1 主评价实验记录**（40+10, seed=42, Au.zip + Modified Tp.zip SHA-256、合成方式、指标、原始预测/汇总/阈值扫描三文件 SHA-256）、cross_checks、gaps（torchvision 待补、AIGC 逐样本预测未保存、GT 硬粘贴局限、无外部 baseline）。
  - 当前 6 条线合规状态：`socialmedia/`（✅ 贺杰）、`crossdomain/`（✅ 张潇）、`perturbation/`（✅ 朱羿帅）、`localization/`（✅ 已补）、`risk/`（✅ 已补）、`platform/`（⚠️ README 英文仅有命令——朱羿帅的线，非本次范围）。
- **Git 记录**：`80f53cd`（中文化+叙事框）、`12d0360`（红框 bbox 叠加+D 合规补齐+DEVLOG），均已推送。`d60c186` 为上一会话交付，未 push（用户要求不推送）。
- 张潇 `2c8899f`（19:57）：REPRODUCIBILITY.md 微调 2 行。#14 消融文档修补仍在进行中。

- 按模板最严格的“章节全部可见汉字”口径核查，第一至第五章分别为 617/4022/1416/447/145，均低于 2000/5000/2000/1000/500 上限。
- 修复摘要、第一章和参考文献因模板固定节容量造成的截断；9 条参考文献全部可见，6 张图和 9 张表编号、引用与文件存在性一致。
- 匿名禁词、身份姓名、邮箱、裸 Windows 路径、SHA-256、占位词和开发痕迹扫描均为 0。
- 补齐测试环境的 `python-docx` 与 `pandas` 后，全量测试基线已更新；新增匿名装配回归后共 191 项，报告、README 和提交进度统一使用 191/191 口径。
- 提交包根因审计发现原脚本全量复制 `git ls-files`，会携带 AGENTS、DEVLOG 和内部计划。现改为运行文件与目录白名单，并以真实装配测试保证内部协作、报告作者和计划文件不进入 `program/`。

### 2026-07-15 - 超监管零样本实验并入、候选稿产品化清洗、报告转向能力前置

- **超监管零样本实验完成并写入报告 3.3.4**（P2，0 失败）：fake 11250/11250、real 1000/1000。零样本 9 生成器 Fake Recall 94.0%–100.0%、总体 98.84%，真图假阳 1.4%；传播扰动 jpeg75 18.2% / jpeg50 8.6% / resize50 100.7% / screenshot 55.5%（表 3.6/3.7）。结论"零样本识别强、抗有损压缩弱"，与主线互证。诚实边界：ExImage 生成器构成比 GenImage 易，绝对值不逐项比。原始产物仅本地，未入 Git。**⚠️ 已被 07-17 纠偏条目取代**：本条的 2250 fake / 500 real 为公开+非公开混合子集，报告数字已换成纯公开的 98.00%、1.4% 已撤，详见顶部 07-17 条目。
- **候选重构稿 `reports/TraceGuard_restructured.md` 完成**：产品化清洗（0 开发痕迹，SHA-256/内部路径/权重版本串全部清零）；resize50 在表 3.4 加 †脚注标为重采样偏置假象；表号重排为连续 3.1–3.9；41 个原生 OMML 公式、0 残留 LaTeX、0 占位泄漏。对应 Word 由 `scripts/build_report_docx.py` 生成（新增 HTML 注释剥离、LaTeX→MathML→OMML 原生公式转换）。**尚未替换主稿。**
- **报告叙事转向能力前置并已落地**（详见上方"当前研究方向与关注点"★节）：队长指出"产品能力没凸显"。诊断为叙事重心/顺序问题——脆弱性数字排在最前定调。已把能力头牌（超监管零样本 98.00%[07-17 纠偏后] + 真图 99.80% + 可信路由 + 单卡 0.52s）提到台前，传播退化 reframe 为"平台自我诊断能力"，局限降为边界脚注。改写覆盖摘要/1.3/1.4/3.1/第四章（重排为 4.1 零样本识别力→4.2 可信路由→4.3 自诊断→4.4-4.7 机制）/第五章；第四章顺带修正两处陈旧表引用（延迟与报告闭环证据均指表 3.9，非旧稿误标的表 3.7）。红线自审+复核全过（身份措辞/开发痕迹/裸路径/占位/残留 LaTeX 均 0），Word 重生成 41 原生公式 0 泄漏。数字一字未改、局限句全保留。
- **分工优先级重排**（#14/#15）：张潇消融原始表升为头号、四套传播前原图降为选做；贺杰三类案例演示图升为头号、多来源阈值校准降为选做。理由：新叙事需要能力证据（消融=跨域能力、案例=可信路由），而非更多退化证据。
- **报告二轮去 AI 腔（队长逐条指出）**：清掉元表述（"诚实脚注""全文最硬的能力""不撒谎""并非产品失败"等 10 处）；2.1 总体架构的 `->` 箭头链改为散文并修正错误的线性顺序（检测权威、解释与定位并行）；2.2「骨干+MK-MMD」、2.4「滑窗检测+特征统计」的 `A+B` 简写改为散文。渲染核验：Word 内字面 `->` 0、`+` 简写 0、AI 腔词 0，41 公式不变。保留的 3 处 `→` 为正当技术记法（层堆叠/色带/real→fake）。当前审阅稿 `output/TraceGuard_restructured_v2.docx`。
- **系统结构图改用 PPT 制作**（照示例论文 ExDA Figure 3 风格）：`scripts/build_figures_pptx.py` 生成 `docs/figures/system/traceguard_figures.pptx`（3 页：图2-1 系统架构、图2-3 Web 流程为完整可编辑图；图2-2 为占位页）。已用 PowerPoint COM 渲染核验三页布局无重叠、红线守住。**待成员 A 在 PPT 微调并给图2-2 填真实检测截图，导出 PNG 替换报告现有 SVG 引用。** 数据图（图3.1/3.2/3.3）仍用脚本生成，不改。
- 未提交文件（待重构定稿后一并处理）：`build_report_docx.py`、`reports/TraceGuard_restructured.md`、`docs/restructure/*`、`docs/report_restructure_plan.md`、`scripts/build_figures_pptx.py`、`docs/figures/system/traceguard_figures.pptx`。

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
- 张潇已提交跨 8 个生成器的平衡盲测结果与复现说明，见 `REPRODUCIBILITY.md` 和 `experiments/crossdomain/verified_results/eval_results.csv`。

### 当前实验基线

| 项目 | 当前记录 | 证据 | 解释边界 |
|---|---:|---|---|
| 8 生成器平均 Accuracy | 79.68% | `experiments/crossdomain/verified_results/eval_results.csv` | 平衡测试集上的宏观平均，不代表所有社交传播条件 |
| BigGAN Accuracy | 97.35% | `experiments/crossdomain/verified_results/eval_results.csv` | 1000 real + 1000 fake |
| BigGAN Fake Recall | 94.90% | `experiments/crossdomain/verified_results/eval_results.csv` | README 中“BigGAN 检出率 94.9%”的正式口径 |
| Real Recall | 99.80% | `experiments/crossdomain/verified_results/eval_results.csv` | 当前 8 组测试使用同一源域 real 子集 |
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
- 已集成贺杰的定位/风险评价基础设施，修正 CLI 重型导入、案例 manifest BOM 和案例冲突方向判定；2026-07-16 全量基线更新为 191 项。

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

### 2026-07-17 - #15-A 案例图中文化 + 红框 bbox 叠加 + 独立叙事图

- `plot_case_evidence.py` 升级：`--roles` 参数、Microsoft YaHei 中文字体、中文标注 + 英文平台标题、案例级【行为】/【关键】叙事框（黄色）、底部中文解释边界声明、左侧标签贴近网格、底部留白收紧。
- 新增 `generate_bbox_overlays.py`：一次性批量调用 TamperDetector 对 12 张案例图生成红框 bbox 叠加图，存入 `data/case_images/bbox/`。manifest 的 `image_path` 同步切换。
- 三张独立案例图（`socialmedia_case_{stable,degraded,conflict}.*`）作为 #15-A 核心产出：1×4 四平台并排、红框 bbox、中文数据标注、行为叙事、解释边界。四平台图片各有不同红框分布。
- 合并网格（3×2 / 3×4）同步更新；`docs/figures/socialmedia/README.md` 更新图录。

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
- GenImage 成对实验完成 32000 个唯一预测键，0 失败；Original 的八生成器 Fake Recall 与 `experiments/crossdomain/verified_results/eval_results.csv` 逐项一致。
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
- 新增：`eval_results.csv`（提交时位于仓库根目录；2026-07-17 按 AGENTS.md §12 的 verified_results 约定迁至 `experiments/crossdomain/verified_results/eval_results.csv`，内容未改动）
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
