# TraceGuard Devlog

更新时间：2026-07-27
技术封版目标：2026-07-20

## 使用规则

- 本文件记录当前已验证进展、阻塞项、下一步任务和负责人。
- 每次 `git fetch`、`git pull`、切换分支或开始新任务后，先阅读本文件，再读取任务相关代码、配置、测试和实验资产。
- 本文件仅仅提供工作导航，不替代 Git 历史、GitHub Issue、实验 CSV、测试输出或接口合同。
- 完成任务、合并 PR、替换权重、更新实验结果或改变下一步优先级后，在同一工作中更新本文件。
- 条目按时间倒序排列。未经当前资产验证的结果必须标记为“待复核”，不得写成已完成事实。

## 当前研究方向与关注点（2026-07-19 更新，队友请先读本节）

**研究方向（已定稿）**：TraceGuard 面向社交媒体传播链末端的可解释 AIGC 图像审核，叠加「超监管高危内容」应用场景，按 **L1 档**执行——报告第三人称引用公开文献 \[9\] 叙述超监管威胁，用自研检测器做零样本 + 传播扰动的边界评测。**绝不接入外部模型/权重/代码复现（B 档，取消资格风险）；ExImage/ExDA 权重与代码不进 Git、不进提交包、不接入系统。**

**★ 2026-07-15 叙事转向（队友务必知悉）**：报告改为**能力前置（capability-forward）**。此前草稿按实验顺序组织，最先出现的都是脆弱性数字（盲测 79.68%、Facebook recall 塌到 21.675%、定位精度低），导致「产品能力没凸显、像个偏弱检测器裹免责声明」。新叙事把**能力头牌**提到台前，**传播退化从"中心贡献"降级为"平台自诊断能力的背书"**：
- **能力头牌 = 零样本超监管识别力 + 可信平台**。开头先亮最硬的数字（超监管零样本 98.00% recall，纯公开子集；真图低误伤以通用盲测 Real Recall 99.80% 为准，见 07-17 纠偏条目），再讲差异化能力：证据退化时系统**自己知道并精准转人工、绝不静默改判**。
- 诚实局限（VQDM/ADM 难例、定位精度低、阈值不可外推）**一条不删、数据不动**，但从各节"主旋律"降为"边界脚注"，不再抢在能力主张前定调。红线不变。

**当前状态一句话**：主稿已同步至 `origin/main@60c0828`；图 2-1 已用 Draw.io MCP 重绘并嵌入真实输入、Stage2 Grad-CAM 与 bbox，`output/TraceGuard.docx` / `.pdf` 共 37 个物理页面、正文页码 1--34，全部页面已渲染核查且无截断或图文重叠。五章可见汉字、匿名扫描和 191/191 测试仍沿用 07-17 已验证基线；本次仅仅替换报告图稿与重建输出，未改检测代码和实验数字。提交包继续使用运行白名单，内部协作与作者文件不进入 `program/`。

- **图 2-1 已用 Draw.io MCP 重绘并覆盖（2026-07-19）**：先执行 `git fetch origin` 与 `git pull --ff-only origin main`，从 `203852a` 快进至 `60c0828`，确认远端仅更新主稿和图 2-1b 后再覆盖。可编辑源为 `docs/figures/system/system_architecture_drawio_v1.drawio`，正式 `PNG/SVG/PDF` 已覆盖 `system_architecture.*`；图内嵌入 `detection_input_real.png`、`detection_gradcam_real.png`、`detection_bbox_real.png` 三份真实证据，外围模块、连线和标签保持可编辑。Draw.io 结构校验为 0 errors / 0 warnings（68 vertices、21 edges）；正式 DOCX 已确认精确嵌入新 PNG，PDF 37 页逐页渲染核查，第 8 页放大检查通过。

- **超监管零样本实验已完成（P2，0 失败）** ⚠️ **数字已被 07-17 纠偏更新**：换纯公开子集后为 9 生成器 92.4%–100.0%、总体 **98.00%**（旧混合集 98.84% 已弃用）；1.4% 真图假阳已撤（公开集无 real，真图判别以通用盲测 Real Recall 99.80% 为准）；传播扰动保持率 jpeg75 **19.8%** / jpeg50 **12.2%** / resize50 **101.1%** / screenshot **56.8%**。已写入报告 3.3.4（表 3.6/3.7）。诚实边界：ExImage 生成器构成比 GenImage 易（无 VQDM/ADM 难例），绝对值不与 GenImage 逐项比，方向性结论"零样本识别可跨内容域迁移"稳健。详见顶部 07-17 纠偏条目。
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

### 2026-07-29 — feature/super-oversight-classifier：集成 MobileCLIP2-S0 零样本内容类别分类器

**分支**: `feature/super-oversight-classifier`（基于 main，4 commits 超前）

**12 个文件变更，+329/-42 行**。核心目标：解决原 `isHighConfidenceFake()` 纯数值判据（`fake_prob≥0.9 && risk_level==high`）无法区分"一张高置信伪造青蛙图"与"超监管领域 AIGC 伪造图"的问题。

#### 新增

- `explanation/content_classifier/` — MobileCLIP2-S0（~54M 参数，~286MB 缓存）零样本分类器
  - 9 个类别：4 个超监管领域（warfare/military conflict, terrorism/extremist violence, weapons/firearms/explosives, graphic violence/human suffering）+ 5 个普通类别（nature, portraits, objects, art, text）
  - 类别文本 `__init__` 预编码为固定向量，推理时仅做一次图像编码 + 矩阵乘法，~15ms GPU
  - 加载失败自动降级：`is_super_oversight_domain` 恒为 false，退回纯数值判据

#### 修改

- **pipeline.py** — `run()` 中插入分类器调用，输出 `content_category`、`is_super_oversight_domain`、`super_oversight_score` 三个新字段
- **config.py** — 新增 `ContentClassifierConfig` dataclass，默认 `enabled: True`；`to_pipeline_config()` 透传
- **configs/default.yaml** — 新增 `content_classifier` 配置段
- **server.py** — `--config` 默认值改为 `configs/default.yaml`，不再需要手动传参
- **schemas.py** — `AnalysisResponse` 新增 `content_category: str`、`is_super_oversight_domain: bool`（有默认值，向后兼容）
- **routes.py** — `_build_response()` 透传；error 构造块补默认值；`_is_pass` 新增 `tamper_type != "local_tamper"` 防局部篡改放行
- **prompts.py** — system prompt 措辞更新：从"不具备内容语义分类能力"→"集成轻量级内容类别分类器，当 is_super_oversight_domain==true 时可确认"
- **app.js** — 核心逻辑变更：
  - 新增 `isSuperOversightDomain()`：= `isHighConfidenceFake() && is_super_oversight_domain === true`
  - 横幅分两级：超监管领域 → "超监管领域高危 · 建议立即复核"；普通高置信伪造 → "高置信伪造 · 建议加急复核"
  - `severityRank` 排序：超监管高危(0) > 高置信伪造(1) > AIGC伪造(2) > 局部篡改(3) > 需复核(4) > 失败(5)
  - 卡片 badge 去重：rank 与 verdict 重复时隐藏（修复 "AIGC 伪造" vs "AIGC伪造" 空格差异）
  - `routeResult` / `_is_pass` 同步加 `tamper_type != "local_tamper"`，局部篡改不再错误放行
- **index.html** — 横幅标题/正文动态化（`#soBannerTitle` / `#soBannerText`）；措辞注释 + 能力档案描述更新
- **requirements.txt** — 新增 `open-clip-torch>=2.0`

#### 当前 badge 组合

| verdict | rank badge | 触发条件 |
|---------|-----------|---------|
| `AIGC 伪造` | `超监管高危` | fake + 高置信 + 分类器确认超监管领域 |
| `AIGC 伪造` | `高置信伪造` | fake + 高置信但非超监管领域 |
| `AIGC 伪造` | — | 普通 fake（rank 与 verdict 重复，隐藏） |
| `真实图像` | `局部篡改` | real + tamper_type=local_tamper |
| `真实图像` | `需复核` | real + risk=medium/high 无篡改 |
| `分析失败` | `失败` | status=error |

#### 使用方式

```bash
pip install open-clip-torch                          # 一次性
$env:HF_ENDPOINT = "https://hf-mirror.com"           # 国内加速（可选）
python server.py --port 8867                          # 自动加载 default.yaml
```

首次启动从 HuggingFace 下载模型缓存到 `~/.cache/huggingface/hub/`，之后秒开。

### 2026-07-27 — main：report-export 补测试（B3）+ LLM 空回复守卫（B4）

**B4 空回复守卫**：推理型模型（deepseek-v4 / doubao-seed-2.0 等）在 `max_tokens` 不足以在 reasoning token 之后留出正文时，接口会返回 `content=""` 而**不报错**（实测：`max_tokens=64` 提问"只回复两个字"→ 313 completion token 中 288 为推理，正文为空）。原代码此时仍标 `llm_generated=True`，报告会渲染出三个空研判段却声称由 LLM 生成。现改为空回复抛 `ValueError`，走既有 `except` 统一降级；`analyze_single`（L73）与 `analyze_batch`（L116）各一处。

**B3 补测试**：新增 `tests/test_report_export.py` 14 项，覆盖 feature/report-export 此前零测试的路径。用 `StubClient` 假客户端，不触网：
- 降级路径：无 client / 空回复 / 纯空白四种参数化（`""`/`"   "`/`"\n\n"`/`None`）/ API 抛异常 → 全部降级且研判段非空
- 正常路径：三段解析、`llm_generated=True`、耗时记录
- prompt 忠实性：送入 LLM 的 prompt 必须携带真实检测数值（`fake`/`0.55`/`medium`），防止研判凭空生成
- HTML 渲染：带/不带 `llm_opinion` 均产出完整报告不抛异常；批量同理
- **已做变异验证**：把守卫改成 `if False:` 后 5 项立刻转红，还原后全绿——测试确实在守，不是凑数

**覆盖盲区（已在测试文件 docstring 注明）**：`/report/preview` 与 `/report/pdf` 的装配逻辑（`_get_llm_agent`、`_html_to_pdf`）是 `create_app()` 内闭包，而 `create_app()` 无条件加载 545MB 权重，单测无法低成本触达；已覆盖其调用的全部业务对象，端点本身仍靠手工联调。

**测试总数 202 → 216**，报告表 3.9 与 4.7 已同步。

### 2026-07-27 — main：批量检测改造成取证筛查漏斗 + 后端措辞红线收口 + 能力档案卡（已实测通过）

**产品决策**（朱羿帅拍板，叙事对齐讨论见协作记录）：批量检测重定位为"取证筛查漏斗"——真实且低风险的图**筛选通过只计数**，其余进待处置列表按严重度排序、只对待处置子集出报告；"超监管意识"采用**诚实代理**方案（高置信伪造置顶加急复核 + 提示语"如内容涉严重危害，请按平台超监管流程上报"），**不做** LLM 内容判读（写进展望/roadmap；原因：报告叙事是"机器意识到假、人意识到危害"，加内容判读会稀释自研零样本头牌且第三方依赖碰红线边缘）。

**后端**（explanation/ 五文件）：
- **措辞红线收口**：prompts.py（LLM 规则 5 改口径 + 新增规则 7 硬约束"不得声称检测超监管内容"）、agent.py（`super_oversight` 字段族全部改 `high_confidence_fake`，喂 LLM 的 JSON 字段名同步）、report.py（横幅/统计卡/行标/卡片标记文案全改"高置信伪造"，内联重复文案合并为 `_high_confidence_alert()` 单一来源）。判定规则 `fake && prob≥0.9 && high` 未变。`grep 超监管 explanation/` 现仅剩提示语与红线注释。
- **筛查支持**：`AnalysisOptions.evidence_policy`（all/flagged/none，默认 all 向后兼容；flagged=筛选通过项不回传任何 b64 证据图，响应体大幅瘦身）；批量单请求上限 20→50（1000 总量由前端分块保证）；`ReportRequest.screening` 上下文 → 报告页眉渲染"取证筛查报告 · 待处置子集 / 共检 N · 筛选通过 M"，LLM prompt 注入 screening_context 防止把子集比例误读为整体。
- 已知限制（注释注明未修）：`_apply_options` 改全局单例 pipeline，多客户端并发会互相污染（本前端串行分块不触发）。
- **勘误**：本条目原记「agent.py 存在历史遗留 `if False:` 空内容守卫死代码，待复核」——**该记录不成立，请勿据此删除守卫**。当时 agent.py 正被变异测试临时改成 `if False:`（用于验证新增守卫测试确实会失灵报警），几秒后已还原。现行代码为 `if not (reply or "").strip(): raise ValueError(...)`，位于 `analyze_single`（L73）与 `analyze_batch`（L116），由 `tests/test_report_export.py` 的 6 项断言守护。

**前端**（web/ 三文件）：
- 文件收集：文件夹选择（webkitdirectory 按钮 + 拖拽文件夹递归遍历）、上限 20→**1000**、扩展名过滤（文件夹 File 常见 type 为空）、Set 去重、objectURL 双 registry 回收（顺手修了单图 setFile 泄漏）、文件列表只渲染前 24 缩略图 + 汇总卡。
- 分块状态机：每块 10 张串行提交（`evidence_policy:"flagged"`）、进度条 n/总数 + 已拦截数 + ETA、**中断停在块边界且已出结果保留**、每块失败自动重试一次后记 error 继续。
- 漏斗 UI：5 格统计（总数/筛选通过/待处置/高置信伪造/失败）+ 分类小字行；待处置卡片按严重度排序（高置信伪造>伪造>局部篡改>需复核真图>失败）带等级徽标，高置信卡带超监管流程提示语；首屏 60 卡增量渲染；通过折叠区懒构建；导出只传待处置子集 + screening 上下文（>100 条 confirm 护栏）。
- 能力档案卡：topbar 入口 + 静态模态框，硬编码已定稿数字（ExImage 零样本 98.00%、Real Recall 99.80%、45.4M、扰动保持率四项†），标注"公开数据子集零样本评测；系统不具备内容语义分类能力"。零新增主张，为演示"超监管实力三件套"提供数字面板（低刺激样例素材待贺杰 #15 产出后纳入演示集）。

**实测**（42 张混合集起服全流程 + API 断言）：漏斗 42→通过18/待处置24/高置信6/失败0 且排序正确；证据裁剪断言通过（通过项 b64 空、待处置项齐全）；51 张限流报错正确；中断精确停在 20/42 且结果保留；报告页眉/研判/TIP 措辞全对且"超监管"仅在提示语中；能力档案卡渲染正确。**文件夹选择对话框无法自动化，待人工冒烟一次**。app.js 留有 `window.__tg` 调试钩子（无害，供联调）。

### 2026-07-27 — main：前端 Modernist 换肤 + 克制动效（来自设计稿 zip，已实测通过）

**背景**：根目录 `TraceGuard 功能页面美化.zip` 是设计工具同步出的 Modernist 风格重设计（Archivo 字体、单红 #ec3013 强调、零圆角、2px 分割线），刻意保留全部 id/类名以兼容 `app.js`。

**已完成**（改动仅 `web/` 三文件 + 新增 `web/static/fonts/`）：
- `web/index.html`：采用设计稿版式（模式标签加 01/02 编号、"多图检测"→"批量检测"、证据面板补标题、去 emoji），资源路径保持 `/static/` 绝对路径。
- `web/static/app.css`：整体替换为 Modernist 样式表；Archivo 可变字体（400–800，latin+latin-ext，共 67KB woff2）**已本地化**到 `web/static/fonts/`，演示现场断网不再依赖 Google Fonts；末尾追加 `Motion+` 动效层（页面入场墨线划入/面板错峰淡入、结论数字滚动计数、维度条从 0 生长、批量卡片错峰入场、证据图切换淡入、检测中按钮斜纹扫描、弹窗淡入），全部带 `prefers-reduced-motion` 降级。
- `web/static/app.js`：5 处小钩子（`replayAnimation`/`animateCount` 工具、dim-bar rAF 起始 0 宽、卡片 `--i` 错峰变量、`.loading`/`.swap`/`.updated` 类切换），不改任何接口与 id。
- **实测**：CPU 起服后用浏览器自动化跑通单图（超监管样例：横幅/维度条/热力图/报告预览弹窗均正常，880px 浅色弹窗内报告无裁切）与批量（2 图：统计条/卡片/展开详情/mini 证据 tab 正常）。旧深色 1200px+scale(0.95) 弹窗方案已被浅色 Modernist 弹窗替代。

**措辞红线联动（队友同步改的，此处记录）**：页面超监管横幅文案已改为「高置信伪造 · 建议加急复核」——系统只判断"是否 AIGC 生成"，无内容类别分类器，前端不得声称检测到"超监管内容"。`app.js` 的 `soVerdictLabel`/`soCardReview`/批量角标已全部对齐为「高置信伪造」。⚠️ **待办**：后端 `explanation/llm/agent.py`、`llm/prompts.py`、`visualization/report.py` 中仍有「超监管」措辞（报告预览横幅实测仍显示"超监管高危内容"），需按同一红线复核改写——建议合并 `feature/report-export-v2` 时一并处理。

### 2026-07-27 — 分支 `feature/report-export-v2`：批量报告版式重构（4图并排 + LLM逐图复核 + 配色对齐单图）

**背景**：`feature/report-export` 的批量报告版式与单图报告风格不统一（汇总图为单张 2×2、高风险条目仅缩略图+迷你进度条、摘要栏过长、无逐图 LLM 建议）。

**已完成**（6 commits，当前分支 `feature/report-export-v2`，尚未合并）：

**1. 汇总图表：2×2 → 4 张独立图表并排**（`7fa32b4`）
- `charts.py` 新增 4 个独立图表函数：`label_pie_chart` / `risk_level_bar_chart` / `fake_prob_histogram` / `risk_score_distribution`（均 260×220，独立 `matplotlib` figure）
- 报告内 4 列 CSS Grid（`.chart-row-4`）并排展示，替代旧版单张 `batch_summary` 2×2 图
- 后续 fix（`249bead`）：生成后统一 `resize` 到相同像素尺寸，消除饼图因 `bbox_inches='tight'` 修剪差异导致的偏大问题

**2. 逐条分析表格精简**（`7fa32b4`）
- 去掉 `risk_score` 列（综合风险分仅在高风险详情中显示）
- `#` 列宽 36→52px + `white-space: nowrap`，容纳 `⚠ 3` 同行显示
- 摘要列改为三字段紧凑格式：`AIGC伪造图 | 置信度95% | 风险高风险`

**3. 高风险条目详情全面展开**（`7fa32b4`）
- **4 证据图并排**（`.img-row-4` 4 列网格）：热力图叠加 / 热力掩膜 / BBox 标注 / 篡改掩膜叠加
- **双栏分析**（`.hr-detail-two-col`）：左栏五维进度条（`.hr-dim-analysis` 灰蓝底卡片）、右栏 LLM 复核建议（`.hr-llm-suggest` 淡蓝底卡片）
- **可疑区域列表**：复用单图条纹数据表
- **详细解释**：完整展示（fix `d6b7bfb` 移除 600 字符截断）
- 后续 fix（`249bead`）：`.hr-mini-bar-fill` 添加 `display: block`，修复 `<span>` 内联元素高度不生效导致的柱状图无色问题

**4. 全部图片详情（排除高风险后）**（`7fa32b4`）
- 每张图：4 证据图并排 + 可疑区域列表 + 详细解释
- 排除 error/failure 结果

**5. LLM Prompt 扩展：逐图复核建议**（`7fa32b4`）
- `prompts.py`：批量 prompt 新增 `[逐图复核建议]` 段落（格式 `#N: 建议文字`）
- `agent.py`：`_parse_batch_reply` 解析为 `review_suggestions: {idx: suggestion}` dict
- Fallback 模板同步更新

**6. 配色对齐单图报告**：批量报告继续使用同一套 CSS 变量（`--bg: #FAFBFC` / `--card-bg: #FFFFFF` / `--risk-high: #EF4444` / `--accent: #1A56DB` 等），卡片、表格、callout 样式完全一致

**7. PDF 独立命名**（`27b4b7e`）
- 前端：新增 `cachedReportType` 变量，`downloadReport` 生成 `TraceGuard-{type}-{YYYYMMDD-HHmmss}.pdf` 唯一文件名
- 后端：`PdfRequest` 新增 `type` 字段，`Content-Disposition` 动态拼文件名
- 示例：`TraceGuard-single-20260727-143022.pdf` / `TraceGuard-batch-20260727-151530.pdf`

**8. 预览弹窗 iframe 放大**（`b95c62c`）
- iframe 宽度 `80%` → `92%`，scale `0.9` → `0.95`，白色预览区域明显更大

**新增/变更文件**：
| 文件 | 变更 |
|------|------|
| `explanation/visualization/charts.py` | +209 行：4 个独立图表函数 |
| `explanation/visualization/report.py` | +350/−65 行：`generate_batch` 重写、新增 `_high_risk_details_expanded` / `_all_images_details_section`、CSS ~80 行新增 |
| `explanation/visualization/__init__.py` | 导出 4 个新图表函数 |
| `explanation/llm/prompts.py` | 批量 prompt 新增 `[逐图复核建议]` 段落 |
| `explanation/llm/agent.py` | `_parse_batch_reply` 解析 `review_suggestions` |
| `explanation/api/schemas.py` | `PdfRequest` 新增 `type` 字段 |
| `explanation/api/routes.py` | PDF 下载 `Content-Disposition` 动态文件名 |
| `web/static/app.js` | `cachedReportType` + 时间戳文件名生成 |
| `web/static/app.css` | iframe 宽度/缩放调整 |

**分支状态**：`feature/report-export-v2` 本地 6 commits，尚未 push/merge。

### 2026-07-27 — 分支 `feature/super-oversight`：超监管高危内容前端展示 + 风险权重/面积统一

**背景**：ExImage 测试集在平台实测中大量图片被判定为 fake，但无一触发超监管提示。根因是 `risk_level` 几乎全部落在 medium 带（0.35–0.70），五维风险评分中 `tamper_area` 和 `consistency` 的低方差拖累了 `fake_prob` 的主信号。同时 bbox `area` 字段在代码和报告间存在语义不一致。

**已完成（共 7 commits，已通过 `--no-ff` 合并至 `main`：`5d1dc0c`）**：

1. **超监管高危内容展示（方案 A）**（`dad81fb`）
   - HTML/CSS/JS：单图 verdict 下方红色脉冲警示横幅 + 解释摘要顶部人工复核建议段落 + 四维度风险可视化条形图
   - 批量结果卡片：超监管红色边框 + 超监管徽章 + 卡片内维度条与复核提示
   - 触发条件：`label === "fake" && fake_prob >= 0.9 && risk_level === "high"`

2. **bbox area 语义统一**（`fa485f9`）
   - `explanation/localization/postprocess.py`：`extract_bboxes` 中 `area` 从连通域像素数（`region.sum()`）改为矩形面积（`w × h`）
   - 报告 `latex_ch1_overview.tex` 原文即为「边界框总面积」，代码现已对齐

3. **五维风险权重调整**（`77ecfb5`）
   - `explanation/risk/scorer.py` 默认权重：`fake_prob` 0.30→0.50、`tamper_area` 0.25→0.10、`region_count` 0.10→0.05、`artifact_intensity` 0.25 不变、`consistency` 0.10 不变
   - `explanation/config.py`：`RiskWeights` dataclass 默认值同步
   - 效果：ExImage 强假图综合分从 ~0.56 升至 ~0.70，越过 high 门槛

4. **报告权重同步**（`9ac2af8`）
   - `docs/restructure/latex_ch1_overview.tex` 第 2.4.1 节枚举列表和表头中的五维权重数字全部更新

5. **配置层权重同步**（`7a51993`）
   - `configs/default.yaml`：`risk.weights` 字段更新
   - `explanation/config.py`：`load_config()` 函数内联默认字典更新（**此前只改了 RiskWeights dataclass 和 RiskScorer 默认值，未改此处，导致服务器实际加载配置仍为旧权重**）

6. **超监管 UI 增强**（`75babfd`）
   - 单图模式：verdict 块切换深红黑底 + 白色文字 + 脉冲外发光动画；警示横幅加入左侧红色强调条 + 斜纹底纹 + 伪造概率/综合风险分动态数值；维度分析新增红色综合分徽章
   - 批量模式：超监管卡片左侧 3px 红色强调条 + 卡片头部淡红背景 + 徽章渐变红底呼吸脉冲动画

7. **DEVLOG 记录**（`f76cc8f`）

**变更文件**：`web/index.html`、`web/static/app.css`、`web/static/app.js`、`explanation/risk/scorer.py`、`explanation/config.py`、`explanation/localization/postprocess.py`、`configs/default.yaml`、`docs/restructure/latex_ch1_overview.tex`、`tests/test_config.py`、`DEVLOG.md`

**测试**：58/58 通过（test_risk.py 20/20 + test_text.py 17/17 + test_localization.py 21/21），33/33 通过（test_config.py）。

### 2026-07-27 — 分支 `enhance-platform`：平台功能完善（SPA 单图/多图检测切换、证据展示、交互修复）

**背景**：Web 平台仅支持单图检测，缺少批量入口。多图检测后端 API（`POST /api/v1/analyze/batch`，上限 20 张）已就绪但前端未使用。同时存在文案（审计→检测）和功能（复选框无效）的 bug。

**已合并回 main（`116da0f`，共 7 commits）**：

1. **复选框修复 + 文案统一**（`25503e4`）：`_apply_options` 未写入 `enable_localization`，导致"可疑区域定位"复选框无效；`app.js` 三处遗漏的"审计"改为"检测"
2. **单图/多图检测切换**（`2e33630`）：SPA 方案——`index.html` 内 CSS show/hide 切换两个 workspace；`<nav class="mode-bar">` 放两个 tab；多图左列批量上传（dropzone `multiple` + 缩略图网格 `#fileGrid` + 去重/20 张上限）、右列批量结果；`switchMode()` 切换逻辑
3. **结果卡片迷你证据查看器**（`1cb2c23`）：每张卡片展开后含四 tab 迷你证据图（overlay/mask/bbox/tamper），`switchMiniEvidence()` 切换
4. **三列结果网格**（`6e17428`）：`repeat(3, 1fr)` 固定三列 + 响应式覆写
5. **独立展开/收起**（`4eb9550`）：`expandCard()` 改为独立 toggle（`display !== "none"` 切换），不再手风琴互斥
6. **风险等级文字居中**（`ee58107`）：`.card-stat b` 设置 `display: block`
7. **定位关闭提示文案**（`021b6e6`）：未勾选"可疑区域定位"时，bbox/tamper 证据区显示「勾选"可疑区域定位"后显示」；替换中文弯引号（U+201C/U+201D）为角形引号修复 JS SyntaxError
8. **清空按钮**（`7175cf7`）：多图上传区新增红色「清空所有图片」按钮，有文件时显示/无文件时隐藏；点击清空 `state.files`、`batchResults` 并刷新界面
9. **DEVLOG 记录**（`202016d`）

**变更文件**：`web/index.html`、`web/static/app.css`、`web/static/app.js`、`explanation/api/routes.py`、`DEVLOG.md`

**分支状态**：已于 2026-07-27 通过 `--no-ff` 合并至 `main`。

### 2026-07-27 — 分支 `feature/report-export`：检测报告导出功能（LLM 研判 + PDF 导出）

**目标**：实现单图/批量检测报告的预览与 PDF 导出，接入 LLM 生成专业取证研判意见。

**已实现**（24 commits，已合并至 main `47ba3f5`）：

**后端 — LLM 模块** (`explanation/llm/`)
- `DeepSeekClient`（`client.py`）：OpenAI SDK 兼容，全部配置由 `default.yaml` 控制，代码零硬编码
- `ReportAgent`（`agent.py`）：编排层 — 提取 pipeline 结构化摘要 JSON → 调 LLM → 解析回复为结构化 dict
- `prompts.py`：System prompt（取证专家角色）+ 单图三段式 + 批量两段式 + fallback 文本
- 支持火山方舟 Ark 平台（`/api/coding/v3`），可用 doubao/glm/kimi/deepseek/minimax 全系列模型
- LLM 不可用时自动 fallback 模板文字，不阻断报告生成

**LLM 配置完全解耦**（`configs/default.yaml` `llm` 段）：
```yaml
llm:
  provider: "volcengine_ark"
  model: "deepseek-v4-pro"        # 改这一行即可切换模型
  api_key_env: "ARK_API_KEY"
  base_url: "https://ark.cn-beijing.volces.com/api/coding/v3"
  temperature: 0.3
  max_tokens: 2048
  enabled: true
```
`routes.py` 通过 `load_config()` 直接读取 YAML，`client.py` 无任何硬编码默认值。

**后端 — 报告模板** (`explanation/visualization/report.py`，已全面重构)
- **设计风格**：冷白底色 `#FAFBFC` + 白色卡片 + 微阴影边框；高危赤红 `#DC2626` / 低危青蓝 `#06B6D4` / 中危琥珀 `#F59E0B`
- **单图报告版式**：页头品牌栏（TraceGuard | 报告编号 | 日期）→ 3 列 Key Metrics 大卡片 → LLM 智能分析 Callout（蓝色左边条）→ 2×2 证据图网格 → 双列（仪表+维度表）→ 可疑区域条纹数据表 → 详细解释 → 元信息 → 页脚
- **批量报告**：统计仪表板 → LLM 批量研判 → 汇总图表 → 逐条条纹表（超监管/高风险行着色）→ 高风险条目详情卡片
- **超监管**：`fake_prob ≥ 0.9 + risk_level = high` 触发红色全宽警示横幅
- **分页控制**：全线 padding/margin 压缩 30-40% 紧凑布局；图片/小卡片 `page-break-inside: avoid`；长文本卡片允许跨页；`@page` 边距 14mm

**后端 — API**
- `POST /api/v1/report/preview`：生成完整 HTML（LLM 研判 + 模板 + matplotlib 图表），返回预览
- `POST /api/v1/report/pdf`：接收预览缓存的 HTML，Playwright Chromium 渲染 PDF（A4 格式）
- 预览/下载解耦：预览缓存 HTML，下载不复调 LLM，秒级响应
- PDF 生成：临时文件加载 → `page.goto(wait_until='networkidle')` → 等 base64 图片渲染完毕 → 导出

**前端 — 预览弹窗**
- 暗色文档阅读器风格：`#2C2C2C` 外框 + `#1E1E1E` 顶/底栏 + `#3A3A3A` 深灰预览区
- iframe 白纸：80% 宽度居中（两侧各 10% 暗色留白）+ `scale(0.9)` + `max-width: 1000px` + 重阴影
- iframe `scrolling="no"` + onload 自适应高度 + overflow hidden → 消除双层滚动条
- 弹窗 `height: 85vh` + padding 32px 不贴边 + 深色遮罩 blur 8px
- 加载动画：spinner + 状态栏反馈（"正在生成报告..." / "PDF 已下载"）
- 导出/下载按钮切换状态；ESC 关闭弹窗

**配置与依赖**
- `configs/default.yaml`：新增 `llm` 配置段（provider/model/api_key_env/base_url）
- `requirements.txt`：`openai>=1.0`、`playwright>=1.40`

**分支状态**：已于 2026-07-27 通过 `--no-ff` 合并至 `main`（`47ba3f5`）。

### 2026-07-21 - 第一章 v2：定名"社交媒体传播场景" + 相关工作改基金写法

队长两点反馈落地（`docs/restructure/latex_ch1_overview.tex` 已更新为 v2）：

- **定名**："传播链末端"全文弃用（"末端"无法精确定义、非共识词）。标题共识词改为**"社交媒体传播场景"**（与基金申报材料话语一致，对应学界 OSN-shared/in-the-wild 概念）；建议标题：**TraceGuard：面向社交媒体传播场景的可解释 AIGC 图像审核平台**（作品名前置为竞赛惯例，保留）。正文精确概念在 1.1 首次出现处定义**"传播后裸图"**后沿用。背景图两处用词同步改（`传播后「裸图」`/`第三道防线：传播后第三方审核`），已重导出 png/pdf/svg。
- **1.2 相关工作改基金申报写法**（参照 `基金研究报告.docx` 2.1 节范式）：总起句 + "本节从 X 方面梳理进展与不足" + 分点 (1)–(4)（伪造痕迹检测/通用泛化检测/可解释归因/数据与评测基准），每段以"从以上分析可以看出，……但……"收缺口，末尾"综合以上四方面，可归纳出三点不足……构成本作品的直接依据"再接表 1.1。
- **字数**：队长指示完成度第一、字数可超——1.5 成员分工（匿名 A/B/C + 阶段计划）已并入本文件，全章正文约 2400 汉字（名义上限 2000，暂不压缩）。
- 队友动作：Overleaf 封面标题改为上述建议标题；第一章整体替换为本文件内容；`figures/background_threat_chain.pdf` 重新上传（图内文字有改动）。

### 2026-07-21（续） - 封面与全文版式对齐官方 Word 模板

`docs/restructure/latex_ch1_overview.tex` 现已是**全文主稿**（队长把 Overleaf 整份文档同步了进来），不再只是第一章片段。本地 `xelatex` 全文编译通过：36 页、0 错误、0 重复标签、0 未定义引用（MiKTeX 已装，可本地验版）。

- **封面按 `作品报告模板.docx` 重做**（老师反馈 TraceGuard 放下方奇怪）。模板封面只有四个字段：作品名称 / 作品类型 / 电子邮箱 / 提交日期，**没有组长、组员、学校栏**。原封面自制的大标题+组长组员学校块已整体替换为模板填空式，TraceGuard 随「作品名称：」值出现在首位。
- **删掉了封面的「学校：上海交通大学」**——模板填写说明第 5 条：报告中应避免出现作者所在学校、院系和指导教师等泄露身份的信息。组长/组员两行同时删除（模板无此字段）。
- **补入模板「填写说明」页**：模板明确标注"(本页不删除)"，此前的稿子漏了这一页。
- 版式对齐：页边距取模板 sectPr（上下 2.54cm、左 2.86cm、右 2.59cm）；正文 1.5 倍行距；`\ctexset` 把章标题设为黑体三号居中「第一章 作品概述」；表图仍保持阿拉伯 3.1 编号（`\thetable` 显式取 `\arabic{section}`）；目录标题「目　　录」。
- **修掉三处合并残留**：① `tab:related_compare` 有两份重复表，删掉后一份；② 新插入的网图 figure 用了和图 1.1 相同的 `fig:threat_chain` 标签（会让 `\cref` 指错），改名 `fig:realworld_cases`；③ 摘要与 4.3 节标题里残留的"传播链末端"改为"传播场景/传播后裸图"。
- **背景图 v2 重做**（队长评价 v1"太丑"，要求照《AIGC 的伪造媒体内容检测与安全防御申报材料》pptx 的风格）：参照该 PPT 背景概述页（slide2 四阶段递进 / slide4 数据卡）的排版范式重画——贯穿式大箭头压在阶段胶囊下层、胶囊配色随威胁递进加重（米→米→亮蓝→深藏蓝）、白底橙描边内容卡、红色关键词强调、右侧红框实测数据卡（蓝标题＋大号红数字）。**只借版式不借素材**：没有复制该 PPT 的任何图片（第三方/网络来源，版权与身份红线），图中无实验室/导师/团队措辞，数据仍是本作品实测。新源 `background_threat_chain_drawio_v2.drawio`，v1 与 matplotlib 版已删（git 历史可查）。
  - 坑：mxCell 的 `value="..."` 里内嵌 HTML 的双引号必须写 `&quot;`，否则 XML 属性提前截断，导出图从该处起整段丢失（第一次导出只画出了一个阶段）。跨列防线条的虚线要显式设 `entryX` 才垂直。
- **背景图 v3：一张横图拆成两张**（队长反馈"字太小根本看不见，非得搞横图，两张图不行吗"）。根因是**画布宽度直接决定正文里的实际字号**：`实际字号(mm) = fontSize × 155.5 / canvas_width`（正文 textwidth 15.55cm）。原 1600 宽 + fontSize 14 → 约 3.9pt，不可读。现按论证逻辑拆分并把画布压窄：
  - **图 1.1 威胁链路与三道防线**（论证：为何需要第三道防线），画布 1000×500，正文字号 20/23 → 约 9~11pt，按 `\linewidth` 排；
  - **图 1.2 同图传播前后检测输出对比**（证据：0.9671 → 0.0180），画布 800×570，按 `0.9\linewidth` 排，伪造概率用 40 号红字做视觉重心。
  - 一份脚本 `build_threat_chain_drawio.py` 同时产出两张源文件；`docs/figures/background/README.md` 已写入上述字号公式，**以后加图先按公式算一遍再画**。
  - LaTeX 同步拆成两个 figure（`fig:threat_chain` / `fig:evidence_decay`），1.1 正文相应分成"链路失效"与"证据衰减"两段承接。全文重编译 36 页，0 错误。
- **待队长确认的两项**：① 封面电子邮箱现为占位 `traceguard.team@example.com`，须换成中性团队邮箱（不含姓名/学校标识）；提交日期待填。② 新插入的网图（`figures/image.png`，特朗普被捕/Obama-Peele/泽连斯基深伪）为第三方新闻与演示素材，版权与来源不可控，且文件名是粘贴默认名——建议要么补来源与授权说明，要么去掉只保留图 1.1（自测数据图，无版权风险）。

### 2026-07-20 - LaTeX 第一章扩充稿 + 背景图（威胁链路与证据衰减）

**背景**：报告已迁往 latex.sjtu.edu.cn 共享项目（Overleaf），队长反馈第一章过于单薄、无背景图。本次产出扩充稿与配图，供粘贴/上传到 Overleaf。

- **新图 `docs/figures/background/background_threat_chain.{pdf,png,svg}`**：左侧威胁链路示意（生成→发布→平台处理→末端裸图 + 三道防线，第一/二道标失效、第三道标本作品），右侧实测证据衰减案例（degraded 案例 BigGAN，fake_prob 0.9671→0.0180，数值取自 `case_manifest_extended.csv`）。**正式版已改用 Draw.io 工作流重绘**（队长反馈 matplotlib 版不够好看）：可编辑源 `background_threat_chain_drawio_v1.drawio`（由 `build_threat_chain_drawio.py` 生成，案例图 base64 内嵌自包含），视觉语言对齐图 2-1（#F8FAFC 浅底、粉彩卡片、雅黑、图内无大标题），draw.io CLI 导出 PNG(2x)/PDF(crop)/SVG。注意 draw.io 单实例：导出前须关闭已开窗口，否则静默不写出（本次已遇到并处理）。旧 matplotlib 脚本 `plot_threat_chain.py` 留档不再维护。**未用任何外部网图**——FakeTrace 仓库里的候选图（MF2DA 直升机、Forensic-MoE 示例、TruFor 拼接样例）均为第三方模型仓库素材，版权/来源不可控，弃用；也未触碰超监管图像（红线）。
- **新稿 `docs/restructure/latex_ch1_overview.tex`**：1.1 增威胁链路叙述并引图 1.1；1.2 扩为三条研究线 + **新增表 1.1 五维能力对比**（CNNSpot/UnivFD/Grad-CAM/GenImage/ExDA vs 本作品）；1.3 三场景走查展开；1.4 微调。正文 1.1–1.4 共 1180 汉字（脚本实数，不含图表），加 1.5 约 1900，仍在本章 2000 上限内。依赖宏包 booktabs/amssymb；图需上传 Overleaf `figures/`。
- 本机 Python 环境注意：仓库脚本用 `E:\aNB\envs\traceguard\python.exe`（PATH 里的 python/py 均不可用）。
- 待办：队长把 tex 与 PDF 图贴进 Overleaf 后核对 \cref 编号（tab:table36 引用沿用现稿）；600dpi TIFF 如需投稿版另行导出。

### 2026-07-17 - 超监管零样本数据来源纠偏：换纯公开子集，98.84%→98.00%，撤 1.4%

**背景**：#17 复核发现旧超监管实验（07-15 写入报告 3.3.4）的 2250 fake / 500 real 是**公开(js 中缀)+ 非公开(db 中缀)混合子集**，真图半区来自未公开的内部 ExImage-v2。按红线「不依赖未公开内部资源」，必须换成纯公开可复现数据。

- **crc32 独立复核（未解码任何图像，仅读 ZIP 中央目录）**：旧 `fake_subset.zip` 2250 张中，js 中缀 1152/1152 命中公开 ExImage.zip、db 中缀 0/1098 命中——证实旧集一半来自非公开数据。
- **纯公开重跑**：`experiments/eximage/build_public_subset.py`（seed=42 确定性抽样，9 生成器 × 250 = 2250 fake，各生成器 test/ 实为 800 张、LatentDM 仅 405，全部够抽、无重复 crc32）→ `evaluate.py paired-derived` 补全 5 变体 × 2250 = **11250 行，0 失败**（CPU，无可用 CUDA）。
- **新数字（纯公开、可复现、无来源争议）**：original 总体 Fake Recall **98.00%**（旧混合集 98.84%，仅 -0.84pp，`comparable=false` 不可混用）；逐生成器 92.4%–100.0%（MJ 92.4 最低，CycleGAN/Flux 100）。传播扰动保持率 jpeg75 **19.8%** / jpeg50 **12.2%** / resize50 **101.1%** / screenshot **56.8%**。
- **1.4% 真图假阳率已撤**：公开 ExImage 未释出 real 半区，本内容域假阳率无法在公开子集复现；报告改以通用八生成器盲测 Real Recall 99.80% 撑「真图低误伤」。
- **核心价值**：换纯公开数据后头牌数字毫发无损，且在**全新内容域独立复现「JPEG 量化是证据破坏主通道」**（98%→19%→12%，resize 近无损、截图居中）——从「补窟窿」变「添独立佐证」。
- **已落地**：报告 3.3.4 表 3.6/3.7 + 摘要/1.3/4.1/结论共 6+ 处数字全线更新并自洽；`experiments/eximage/verified_results/` 冻结（README 口径边界 + provenance.json 哈希锚点[已相对化绝对路径] + 3 份汇总 CSV），代码 + test（11 项全绿）入库，**无数据无权重无图片**。commit `2ac53f9`，已 push。数据/权重/output 全 gitignored。
- **张潇 #14 已再点**（[issue 评论](https://github.com/Suaiii/TraceGuard/issues/14#issuecomment-5005897448)）：确认口径错标已改对（Average 改成真实 Fake Recall 49.60→59.55），剩两项封版前必交——① `train.py`/`eval.py` 死链修复；② 消融两臂「两次独立训练、非单一开关」如实声明（no-MMD checkpoint 已丢，如实说明即可，**不要重训**）。
  - **07-18 张潇已交（commit `ea72898`）**：② **受控变量声明做得到位**——两臂两次独立训练、共享 seed=42 划分、唯一差异 β=0、Real Recall 99.80 vs 99.60、+9.96pp 含训练随机性不可全归因、no-MMD checkpoint 存 AutoDL 未随仓库发布。**封版硬卡点（过度声明）已解除。** ① 上传了 `train.py`/`eval.py` 并补全 CSV 路径，但脚本复现完整性仍有两处残留（严重度低一档，已按队长指示"记录即可、按需再说"）：eval.py 只算 Accuracy、不产 Fake Recall、不写 `eval_results.csv`（文档表为 Fake Recall）；两脚本在仓库根却 `from models.X` import，包在 `detection/models/`，从根跑会 ImportError。已在 `REPRODUCIBILITY.md` 复现命令段补「脚本口径说明」如实记录：脚本以 `detection/` 为工作根运行、附带 eval.py 是 Accuracy 快查、原始 Fake Recall CSV 由完整管线产出并冻结；一键整合脚本按需再补。

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

### 2026-07-18 - #15-A 三案例纵向拼接总图（学术重构）

- **重构脚本**：`experiments/socialmedia/plot_case_combined.py`（替代旧的 PIL 拼接方案），使用 matplotlib 原生渲染三卡片纵向总图，保存时用 PIL 裁白边替代 `bbox_inches='tight'` 避免坐标漂移。
- **输出**：`docs/figures/socialmedia/socialmedia_case_combined.{png,svg,pdf}`（PNG 3434×3515，300 DPI）。
- **设计规格（按用户要求重做）**：
  - 布局：三大组（稳定/衰减/冲突）各为一张极浅灰卡片（#F8F9FA），圆角细边（#DEE2E6），卡片间留白可见；左侧标签改为左上角水平 Badge（彩色圆点 + 中文粗体 + 英文斜体灰色）。
  - 文字层级：一级标题（Original/Facebook 等）13pt Arial 粗体居中对齐；二级数据去掉灰框，标签 #ADB5BD 小字右对齐、数值 #212529 加粗左对齐；三级结论去掉老式黄框，改为 #FFF3CD 无边框底纹 + 左侧 #FFC107 粗竖线强调。
  - 脚注：8.5pt #6C757D 居中，与底边留足够白边。
- 旧的 `stitch_combined_case.py`（PIL 拼接）已删除，被 `plot_case_combined.py` 完全替代。

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
