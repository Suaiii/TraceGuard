# TraceGuard 项目开发与工作区规范

版本：v2.1
日期：2026-07-15
适用范围：`Suaiii/TraceGuard` 代码仓库、`E:\aNB\TECH\AI竞赛` 竞赛工作区，以及与本项目直接相关的模型、数据、实验、报告和答辩资产。

---

## 0. 规划者角色与常驻协作约定（2026-07-15 起）

本节记录竞赛队长与 Claude（工作区规划者 / Hermes）之间的固定协作方式，优先级等同其余章节。

### 0.1 主线与分工模型

- 队长（朱羿帅）的集成线**就是主干**，始终直接在 `main` 上工作。模块化分工保证队长内容与队友提交互不冲突，无需为队长内容单开长期分支。
- 队友（张潇 / 贺杰）按模块在功能分支交付，FF 或合并进 `main`。

### 0.2 Claude 的角色 = 规划者，不是执行者

- Claude 的职责只有三件：**分任务、做规划、定 report 思路**。
- 凡判断为 ≥5 分钟的实体任务，一律写成 agent（Hermes）任务派发，不亲自埋头做。
- Claude 与队长对话敲定工程结构与叙事，再把子任务分派给队友或 agent。

### 0.3 常驻职责：随时更新 DEVLOG 与分工方案，给队友有效信息

- 每当方向、状态、分工、优先级、封版材料状态发生变化，**当场更新 `DEVLOG.md` 的「当前研究方向与关注点」与「三人当前关注点」两节**，不等被问。
- 分工变化同步更新对应 GitHub Issue（#14 张潇 / #15 贺杰 / #16 朱羿帅）。
- 给队友的信息必须**有效**：具体、可执行、可追溯——写清「做什么、为什么、交付物、验收标准、优先级升降」，不留空泛指令。
- DEVLOG 的通用更新协议见 §2.1；本节强调这是 Claude 的**主动、常驻**义务。

---

## 1. 项目准口径

项目正式名称：

> **TraceGuard：面向跨域 AIGC 图像的可解释伪造检测与篡改取证平台**

TraceGuard 面向真实网络传播环境中的图像安全审核，提供跨域 AIGC 真伪检测、可解释热力图、局部可疑区域定位、多证据风险融合、Web/API/CLI 使用入口和检测报告输出。

当前最小用户输入是一张 RGB 图像。文件名、格式、尺寸、压缩信息和 EXIF 等属于内部可选信号，不得要求用户理解模型预处理或上传多套模态输入。

系统输出保持三层结构：

```text
全局判断：real/fake、fake_prob
局部证据：heatmap、mask、bbox、区域异常说明
融合结论：risk_score、risk_level、解释文本与检测报告
```

不得把全局检测与局部定位写成二选一关系。跨域检测给出主要真伪判断；热力图解释附着于全局检测；局部定位作为并行证据分支；最终由风险模块形成融合结论。

---

## 2. 当前真相源

开始工作前，根据任务读取以下文件：

1. `DEVLOG.md`：当前已验证进展、阻塞项、下一步任务和负责人。每次同步远端或开始新任务后必须先读。
2. `README.md`：当前可运行入口、模块结构、接口和已验证能力。
3. `docs/project_plan.md`：正式题目、三人分工、目标和阶段安排。
4. `docs/submission_progress.md`：报告快照、当前缺口和近期行动。
5. `configs/default.yaml`：检测、热力图、定位、风险、文本与输出参数的配置真相源。
6. `explanation/api/schemas.py`：HTTP 请求和响应的数据合同。
7. `explanation/api/routes.py`：Web 静态资源、健康检查、配置、单图和批量分析接口。
8. `tests/`：行为回归准入；README 中的测试数字不得替代实际测试结果。
9. `开放式自主命题作品赛参赛指南.pdf`、`作品报告模板.docx`、`原创性说明.docx`：竞赛与交付格式依据。
10. `竞赛计划.md`：早期竞赛计划。若与仓库内 `docs/project_plan.md` 冲突，以后者和用户最新确认口径为准。

优先级如下：

```text
用户最新明确要求
  > 当前代码、配置、测试与接口合同及其验证证据
  > DEVLOG.md 中与当前事实一致的进度导航
  > docs/project_plan.md / docs/submission_progress.md
  > README.md
  > 早期计划、历史报告和临时材料
```

不得用记忆、旧报告或 README 中的陈旧描述覆盖当前代码事实。

### 2.1 同步启动协议

每次 `git fetch`、`git pull`、切换分支或收到他人合并结果后，按以下顺序开始工作：

```text
确认当前分支与工作树
  -> 同步或检查远端差异
  -> 阅读 DEVLOG.md
  -> 核对相关代码、配置、测试和实验资产
  -> 确认当前任务与下一步优先级
```

`DEVLOG.md` 仅仅是进度导航，不得覆盖代码、测试、接口合同、实验 CSV 或 Git 历史。若 devlog 与当前事实不一致，以可验证事实为准，并在同一任务中修正 devlog。

以下变化必须同步更新 `DEVLOG.md`：

- 功能或修复合并到 `main`；
- 权重、数据划分、实验数字或复现方式变化；
- 报告主张由“待验证”变成“已验证”，或被降级、撤回；
- 阻塞项、负责人、截止时间或下一步优先级变化；
- 技术封版或提交材料状态变化。

---

## 3. 工作区与仓库边界

### 3.1 主工作区

`E:\aNB\TECH\AI竞赛` 是当前主工作区，包含：

- GitHub 仓库的可运行代码；
- 本地模型权重 `best.pth`；
- 本地数据集压缩包 `dataset/`；
- 竞赛指南、模板、声明、计划和报告草稿；
- `output/`、`tmp/` 等生成或验证产物。

所有新开发、Issue 实现、验证和提交默认从该目录进行。

### 3.2 次级检出目录

`E:\aNB\TECH\TraceGuard` 是同一 GitHub 仓库的次级检出目录。它可用于运行对照或历史复核，但不得与主工作区同时独立开发同一功能。

需要使用次级目录时，先检查：

```powershell
git -C E:\aNB\TECH\TraceGuard fetch origin
git -C E:\aNB\TECH\TraceGuard rev-list --left-right --count HEAD...origin/main
git -C E:\aNB\TECH\TraceGuard status --short --branch
```

若两个检出目录都有未合并修改，先确定唯一继续开发的目录，不得通过复制覆盖来“同步”。

### 3.3 相邻项目

- `E:\aNB\TECH\FakeTrace`：多模态伪造检测项目，可提供模型或工程经验，但不是 TraceGuard 当前代码真相源。
- `E:\aNB\TECH\ATADD`：音频数据与验证项目，仅在明确的音频验证任务中使用。
- `去年的相关信安内容报告.docx`：仅可参考版式、结构节奏和格式，不得复用技术内容、创新点、系统设计、结果或图表。

不得把 FakeTrace、ATADD 或往届项目的功能、指标和结论自动写成 TraceGuard 已实现能力。

---

## 4. 团队职责

| 成员 | 角色 | 主要责任 | 交付接口 |
|---|---|---|---|
| 朱羿帅 | 竞赛队长；系统集成、产品化、报告与答辩负责人 | 统一项目架构、Web 闭环、仓库与版本、作品报告、演示和提交 | 可运行系统、README、报告、答辩与提交包 |
| 张潇 | 跨域 AIGC 检测负责人 | 跨生成器/数据集/风格/扰动检测，模型与跨域实验 | `Detector.predict()`、真伪概率、检测指标与模型说明 |
| 贺杰 | 可解释检测与取证负责人 | 热力图、局部异常、篡改定位、案例解释 | heatmap/mask/bbox、解释结果与案例证据 |

代码责任不等于独占修改权。跨模块改动必须在 Issue 中写明接口影响，并由相应负责人或竞赛队长复核。

---

## 5. 当前系统结构

```text
web/index.html + web/static/*
  -> GET /api/v1/health
  -> POST /api/v1/analyze
  -> FastAPI create_app()
  -> ExplanationPipeline
       -> Detector.predict()                 全局权威判断
       -> Detector.get_heatmap()             全局解释
       -> Detector.get_spatial_features()    局部特征
       -> HeatmapGenerator
       -> TamperDetector
       -> RiskScorer
       -> TextExplainer
  -> AnalysisResponse
  -> 浏览器证据视图 / CLI / HTML 报告
```

主要目录职责：

| 路径 | 职责 |
|---|---|
| `detection/` | MambaOut 检测器、空间特征和 MK-MMD 跨域适配能力 |
| `explanation/heatmap/` | Grad-CAM 热力图生成与叠加 |
| `explanation/localization/` | patch/feature 融合定位、后处理和局部篡改分类 |
| `explanation/risk/` | 多维风险分数和等级 |
| `explanation/text/` | 面向用户的中文/英文解释 |
| `explanation/visualization/` | 图表、自包含 HTML 和批量报告 |
| `explanation/api/` | FastAPI 路由和 Pydantic 合同 |
| `web/` | 与 API 同源托管的浏览器工作台 |
| `tests/` | 当前回归测试及精选样例；测试数量以实际收集结果为准 |
| `reports/` | `TraceGuard.md` 报告工作源；不作为实验真相源 |

新增模块前，先证明现有模块无法准确承载该职责。不得为同一概念创建平行检测器、第二套风险分数或第二份响应合同。

---

## 6. 核心合同

### 6.1 检测权责

- `label` 与 `fake_prob` 仅由 `Detector.predict()` 产生。
- 下游解释、定位和风险模块不得重新定义真伪概率。
- 局部证据可以支持或质疑全局判断，但必须保留来源和差异，不得静默覆盖。

### 6.2 API 合同

当前正式接口：

```text
GET  /
GET  /api/v1/health
GET  /api/v1/config
POST /api/v1/analyze
POST /api/v1/analyze/batch
```

单图请求核心字段为 `image_base64`，批量请求最多 20 张。字段增删、类型变化、枚举语义变化或错误格式变化必须先修改 `explanation/api/schemas.py`，同步前端、测试和 README。

### 6.3 风险合同

`risk_score` 是由检测概率、伪影强度、可疑面积、区域数量和一致性形成的融合指标，不等同于模型的 `fake_prob`。风险权重和等级边界由 `configs/default.yaml` 管理。

### 6.4 信息完整性

不得静默截断图像证据、模型输出、错误信息、实验记录或报告依据。界面可使用 CSS 省略显示，但原始数据和可追溯记录必须保留。

---

## 7. 标准开发管线

除非常小的错别字或路径修正外，功能开发必须走：

```text
需求澄清
  -> Issue / Contract
  -> Routing Gate
  -> 功能分支
  -> 实现与测试
  -> 本地验收
  -> Code Review
  -> PR
  -> 合并 main
  -> 两个本地检出目录按需同步
```

每次只处理一个可独立验收的垂直切片。不要机械拆成“前端 Issue”和“后端 Issue”；一次用户流程涉及的前端、接口和后端改动应在同一 Issue 中闭环。

---

## 8. Issue 与 Routing Gate

Issue 至少包含：

```text
Title
User Value
Current Evidence
Scope
Out of Scope
Affected Modules
Data Contract / API Impact
Acceptance Criteria
Validation Commands
Asset / Report Impact
Risks and Rollback
Status
```

进入实现前回答：

1. 用户价值和可见结果是否明确？
2. 是否有当前代码、测试或实验事实支持需求？
3. 是否修改 `Detector`、`AnalysisResponse` 或风险语义？
4. 是否涉及 Web、API、CLI 和报告中的多个入口？
5. 是否需要新增数据、权重或实验资产？
6. 验收能否由命令和浏览器流程复现？
7. 失败后能否回退单个 PR？

结果仅为：

```text
ready-for-implementation
needs-more-evidence
needs-more-spec
```

后两种状态不得直接实现。

---

## 9. 实现规范

### 9.1 通用

- 先读取 Issue、相关合同和邻近模块，再修改。
- 仅修改当前 Issue 需要的文件；保留用户已有改动。
- 不增加无证据 fallback、吞异常、静默纠正或重复状态。
- 外部输入、文件系统、模型文件和网络等真实边界必须返回明确错误。
- 引入依赖时锁定版本，说明用途，并验证 Windows/Python/PyTorch 兼容性。

### 9.2 检测与解释后端

- 保持 `Detector` 为全局判定入口。
- 权重不进入 Git；`server.py` 默认依次查找 `checkpoints/best.pth` 和根目录 `best.pth`，显式路径不存在时不得静默回退。
- 修改热力图或定位算法时，必须检查输出尺寸、归一化范围、bbox 坐标和空区域行为。
- 修改风险权重或阈值时，必须提供验证集来源、指标定义、旧值对比和局限，不能只凭个例调参。

### 9.3 Web 前端

- `web/` 是工作台，不是营销首页。
- 用户操作围绕上传、结论、风险、证据和解释展开。
- UI 必须支持 loading、empty、error 和分析完成状态。
- 前端只消费 API 合同，不得在 JavaScript 中重新计算真伪或风险结论。
- 改动后用真实浏览器检查桌面和窄屏布局、上传流程、API 状态和证据切换。

### 9.4 CLI 与批量入口

- CLI、批量脚本和 Web 使用同一 `ExplanationPipeline`。
- 新参数必须说明默认值、优先级和与 YAML 的关系。
- 批量处理失败项必须可定位，不得因单个错误丢失其他结果。

---

## 10. 测试与验收

### 10.1 回归测试

当前代码可收集 140 项测试。修改代码后至少运行受影响模块；合并前运行全量：

```powershell
python -m pytest tests -q
```

不得仅凭 README 中的测试数量宣称当前测试通过。默认 `E:\anaconda\python.exe` 当前没有安装 pytest；干净环境应先安装 `requirements-dev.txt`，或使用已经具备 pytest 的明确 Python 环境。

`tests/test_pipeline.py::TestPipelineMock::test_low_fake_pipeline` 存在依赖随机特征产生 bbox 的非确定性问题，已记录为 GitHub Issue #7；该问题修复前，测试失败必须区分随机基线问题与当前改动回归，不能隐瞒或简单重试后宣称稳定。

### 10.2 本地系统验收

需要证明 Web/API 闭环时：

```powershell
python server.py --device cpu
```

然后检查：

```text
GET /api/v1/health 返回 200 且 model_loaded=true
GET / 返回工作台
上传 tests/fixtures 中的图片
POST /api/v1/analyze 返回 200
页面显示 label、fake_prob、risk_level、bbox 和证据图
```

浏览器验收应保存必要截图或快照，但 `.playwright-cli/` 和 `case_study/` 属于本地产物，不纳入 Git。

### 10.3 报告验收

DOCX/PDF 必须做视觉渲染核查。文本提取只能检查内容存在，不能证明题注、分页、图表、字体和版式正确。

---

## 11. 实验与证据规范

测试章节或实验记录必须解释：

- 数据来源与许可；
- 训练/验证/测试划分；
- 指标来源和定义；
- baseline 或旧版本；
- 实验目的和变量；
- 结果、解释和局限；
- 对 TraceGuard 平台主张的支持范围。

不得把内部路径、文件名、“对应输出”或单张截图当作实验逻辑。未经当前产物验证的 Accuracy、F1、AUC、Recall、鲁棒性、速度和稳定性不得写成完成结果。

当前 1000 张 BigGAN 的 94.9% 是特定权重和特定数据上的已有记录，不自动等同于跨域泛化能力，也不等同于正式比赛成绩。

---

## 12. 资产与库存管理

| 类别 | 位置 | Git 策略 |
|---|---|---|
| 源代码、配置、测试、Markdown | 仓库目录 | tracked |
| 精选小型测试图片 | `tests/fixtures/` | tracked |
| 模型权重 | `checkpoints/`、根目录 `best.pth` | ignored；记录 SHA-256 |
| 大型数据集 | `dataset/`、`tests/BigGAN/` | ignored/external；记录来源、版本、划分和校验值 |
| 运行输出 | `case_study/`、`output/`、`results/` | ignored；必要结果转成报告级表格或图 |
| 竞赛原件 | 工作区根目录的指南、模板、声明 | external-reference 或经确认后 tracked |
| 正式报告快照 | `reports/` | 仅保留明确版本和来源 |
| 临时材料 | `tmp/`、`tmp_*` | ignored 或任务后清理 |

库存记录建议放在：

```text
docs/inventory/source-assets.md
docs/inventory/datasets-and-models.md
docs/inventory/deliverables.md
```

大型资产记录必须包含相对路径、来源、用途、大小、SHA-256、最近核查日期和是否可再生成。禁止只替换权重或数据而不更新记录和实验说明。

---

## 13. 竞赛报告约束

TraceGuard 报告应围绕“全局判断 + 局部证据 + 融合结论”的可解释图像安全审核平台展开。

- 技术章节使用逻辑小节、架构/流程图和段落级推理，不做纯文字堆砌。
- 图内只保留模块、箭头、坐标、图例和简短标注；图名和高层说明进入 Word 题注与正文。
- 图表默认使用本地 `nature-figure` Python 工作流，除非用户指定其他方式。
- 当前代码没有实现的能力只能写为计划、局限或未来工作。
- FakeTrace 或 ATADD 的证据只有在明确完成接口映射和验证后才能进入 TraceGuard 报告。
- 往届报告仅参考格式，不得复用技术创新内容。

---

## 14. Git 与 GitHub 工作流

远端：`https://github.com/Suaiii/TraceGuard.git`

默认分支：`main`

开发分支：`codex/<issue-slug>` 或团队约定的功能分支。

开始前：

```powershell
git fetch origin
git status --short --branch
git rev-list --left-right --count HEAD...origin/main
```

正常流程：

```text
创建 GitHub Issue
  -> 从最新 main 创建分支
  -> 显式暂存 Issue 范围文件
  -> 验证 diff 和测试
  -> commit
  -> push
  -> PR（正文关联 Closes #N）
  -> Review / checks
  -> merge main
```

禁止：

- `git add .` 未经范围复核；
- 提交权重、数据集、密钥、临时目录或浏览器产物；
- 在 `main` 上直接开发大功能；
- 强推、改写共享历史或删除他人分支；
- 用复制文件代替 Git 合并；
- 在两个本地检出目录同时形成未合并实现。

提交前必须检查：

```powershell
git diff --check
git diff --cached --stat
git diff --cached --name-only
```

---

## 15. Code Review 规范

Review 以 findings 开头，按严重程度排序：

1. **Blocking**：模型/数据来源污染、真伪判定被下游覆盖、合同破坏、敏感信息或大型资产误提交、不可追溯结果。
2. **High**：Web/API/CLI 行为分叉、风险语义混淆、指标无来源、前后端不闭环、关键错误被吞。
3. **Medium**：缺少边界状态、缺测试、配置与文档不同步、报告解释不完整。
4. **Low**：命名、文案、局部结构或清理问题。

必查：

- `fake_prob` 是否仍来自 `Detector.predict()`；
- API schema、路由、前端和 README 是否一致；
- 新实验是否可复现并说明局限；
- 权重和数据是否未进入 Git；
- Web 是否通过真实浏览器验证；
- 报告是否区分已实现、已验证和计划中能力；
- 是否误用了 FakeTrace、ATADD 或往届内容。

---

## 16. 当前基线与优先事项

截至 2026-07-13，仓库已具备：

- MambaOut-Small 检测入口和本地权重加载；
- Grad-CAM 热力图；
- patch + feature 局部定位；
- 五维风险融合与中文解释；
- Web、FastAPI、CLI 和批量处理入口；
- 140 项可收集测试；
- 报告框架和已有 PDF 快照。

当前不能直接宣称已完成的部分：

- 严格跨生成器/跨数据集泛化实验；
- JPEG、缩放、裁剪和截图转存的系统鲁棒性实验；
- 风险阈值与权重的验证集校准；
- 可解释模块的定量评价；
- 平台压力、并发和长期稳定性测试；
- 全部正式引用、最终架构图和最终提交报告。

`reports/TraceGuard.md` 是当前报告工作源，但仍含待补内容，不能视为最终报告；PDF/DOCX 应从确认后的 Markdown 或正式文档源生成。

推荐优先 Issue 顺序：

1. 建立数据、权重和交付物库存清单并固定校验值。
2. 完成跨域实验合同、数据划分和 baseline 表格。
3. 完成传播扰动鲁棒性测试与可复现实验脚本。
4. 校准风险分数和等级阈值，解释其与 `fake_prob` 的差异。
5. 将验证结果转成报告级图表、案例和局限说明。
