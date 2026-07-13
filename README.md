# TraceGuard - AIGC 图像安全审核与取证平台

## 跨域检测、可解释取证与篡改可疑区域定位



> 团队成员：朱羿帅（系统集成、产品化、作品报告与答辩）张潇（跨域 AIGC 检测，MambaOut-Small + MK-MMD）｜贺杰（可解释检测与取证）
>
> 2026-07-12 | Web + FastAPI 单进程闭环 | 四象限局部篡改分类 | 1000 张 BigGAN 批量验证（94.9%）

TraceGuard 面向真实网络传播环境中的 AIGC 图像审核需求，将全局真伪判断、可解释热力图、局部可疑区域定位、风险融合和报告输出组织为一条可复核链路。仓库同时提供浏览器工作台、HTTP API、命令行和批量分析入口。

当前可协作报告源：[reports/TraceGuard.md](reports/TraceGuard.md)。该文件仍是工作草稿，待补实验结果、图表和正式参考文献，不代表最终提交版本。

```text
上传图片 -> 跨域真伪检测 -> 热力图与局部定位 -> 风险融合 -> 中文解释与证据展示
```

---

## 一、快速开始

### 1.1 环境

```bash
python -m pip install -r requirements.txt

# 需要运行测试时
python -m pip install -r requirements-dev.txt
```

建议使用 Python 3.10，并根据本机 CUDA 环境安装匹配版本的 PyTorch。模型权重不进入 Git；启动程序会依次查找 `checkpoints/best.pth` 和根目录 `best.pth`。可用小型测试样本位于 `tests/fixtures/`。

`tests/BigGAN/` 是外部大型测试集目录，仓库和当前主工作区均未包含它。需要运行 1000 张批量验证时，应先按 [`docs/inventory/datasets-and-models.md`](docs/inventory/datasets-and-models.md) 补齐来源、校验值和测试划分。

### 1.2 启动 Web 工作台与 API

前端由 FastAPI 直接托管，不需要单独安装 Node.js 或启动第二个开发服务器：

```bash
# 默认使用 CUDA，自动发现本地权重，启动在 8000 端口
python server.py

# CPU 模式
python server.py --device cpu

# 显式指定权重与端口（路径不存在时直接报错）
python server.py --device cpu --port 8080 --checkpoint D:\models\traceguard-best.pth
```

启动后访问：

| 入口 | 默认地址 | 用途 |
|---|---|---|
| Web 工作台 | `http://127.0.0.1:8000/` | 上传图片并查看检测、风险与可解释证据 |
| Swagger UI | `http://127.0.0.1:8000/docs` | 调试 HTTP API |
| 健康检查 | `http://127.0.0.1:8000/api/v1/health` | 核对模型、设备与服务状态 |

### 1.3 CLI 与批量测试

```bash
# 展示用例（精选样本，生成热力图/掩膜/HTML报告）
python run_test.py --input-dir tests/fixtures --output case_study

# 可选：准备 tests/BigGAN 后运行 1000 张批量分析
python batch_analyze.py --input-dir tests/BigGAN --output batch_results --csv batch_results/results.csv

# 单张分析
python run_test.py --input tests/fixtures/040_biggan_00074.png --output my_result

# 全量全流程（1000 张全部生成热力图/掩膜，耗时较长）
python run_test.py --input-dir tests/BigGAN --output case_study

# 跳过定位加速 / CPU 模式
python run_test.py --input-dir tests/fixtures --output case_study --skip-localization --device cpu
```

### 1.4 输出

运行单图/展示用例命令后，每张图会在 `case_study/` 下生成独立子目录，含 8 个文件：

| 文件 | 内容 |
|------|------|
| `analysis.json` | label, fake_prob, risk_score, risk_level, bbox_list, dimension_scores |
| `explanation.txt` | 三段式中文解释（总体结论 / 取证分析 / 定位详情） |
| `overlay.png` | 原图 + 半透明热力层叠加 |
| `mask.png` | 纯热力掩膜（蓝 → 红紫 colormap） |
| `tamper_mask.png` | 篡改可疑区域掩膜（红色标记） |
| `tamper_overlay.png` | 原图 + 篡改掩膜叠加 |
| `bbox_image.png` | 原图 + 可疑区域矩形框标注 |
| `report.html` | 自包含 HTML 报告（内联雷达图 + 仪表条 + 维度详情） |

批量模式会生成 `batch_summary.html`（汇总对比报告）和 `summary.json`。这些目录均为本地生成产物，不随仓库提供；当前主工作区尚未生成 `case_study/` 或 `batch_results/`。

---

## 二、项目结构

```text
traceguard_project/
├── run_test.py                             # 一键全流程测试（输出热力图/掩膜/HTML报告）
├── batch_analyze.py                        # 批量数据分析（仅检测指标，输出 CSV/JSON/HTML）
├── server.py                               # FastAPI 服务入口
├── README.md
│
├── web/                                    # 浏览器工作台（由 FastAPI 同源托管）
│   ├── index.html                          # 上传、结果和证据视图
│   └── static/
│       ├── app.css                         # 工作台视觉样式
│       └── app.js                          # 健康检查、上传分析和结果渲染
│
├── detection/                              # [张潇] 跨域 AIGC 检测
│   ├── inference_api.py                    #   Detector — predict / get_heatmap / get_spatial_features
│   └── models/
│       ├── mambaout_custom.py              #   MambaOut-Small 去 GAP 骨干 (stage2 14×14 + stage3 7×7)
│       └── mkmmd.py                        #   MK-MMD 域自适应损失
│
├── explanation/                            # [贺杰] 可解释 + 定位
│   ├── pipeline.py                         #   ExplanationPipeline 总调度
│   ├── cli.py                              #   CLI 命令行
│   ├── batch.py                            #   批量处理
│   ├── config.py                           #   YAML → dataclass 配置加载
│   ├── utils.py                            #   colormap / base64 / 图像叠加
│   ├── heatmap/                            #   可解释热力图
│   │   └── generator.py                    #     HeatmapGenerator (Grad-CAM 后处理)
│   ├── localization/                       #   篡改可疑区域定位
│   │   ├── detector.py                     #     TamperDetector (patch + feature 混合)
│   │   ├── patch_analyzer.py               #     多尺度滑动窗口
│   │   ├── feature_stats.py                #     特征统计异常检测 (14×14)
│   │   ├── tamper_classifier.py            #     局部篡改四象限分类器 (v1.0)
│   │   └── postprocess.py                  #     阈值 / 形态学 / NMS / bbox
│   ├── risk/                               #   风险评分
│   │   └── scorer.py                       #     RiskScorer 五维度加权
│   ├── text/                               #   自然语言解释
│   │   └── generator.py                    #     TextExplainer 三段式
│   ├── api/                                #   FastAPI
│   │   ├── routes.py                       #     4 端点 (health / config / analyze / batch)
│   │   └── schemas.py                      #     Pydantic 模型
│   └── visualization/                      #   图表 + 报告
│       ├── charts.py                       #     雷达图 / 仪表条 / 批量汇总
│       └── report.py                       #     HTML 自包含报告
│
├── configs/default.yaml                    # 全量 YAML 配置
├── checkpoints/best.pth 或 best.pth        # 本地模型权重（不进入 Git）
│
├── tests/
│   ├── conftest.py                         #   MockDetector + FakeModel
│   ├── pytest.ini
│   ├── fixtures/                           #   8 张 BigGAN 精选展示用例
│   ├── BigGAN/                             #   1000 张 BigGAN 生成样本 (全量测试集)
│   ├── test_heatmap.py                     #   热力图测试 (10)
│   ├── test_localization.py                #   定位测试 (22)
│   ├── test_pipeline.py                    #   流水线测试 (23)
│   ├── test_risk.py                        #   风险评分测试 (19)
│   ├── test_text.py                        #   文本解释测试 (17)
│   ├── test_visualization.py               #   可视化测试 (22)
│   ├── test_config.py                      #   配置系统测试 (12)
│   └── test_cli.py                         #   CLI 测试 (6)
│
├── reports/
│   └── TraceGuard.md                       # 当前报告工作草稿
│
└── docs/
    ├── project_plan.md
    └── submission_progress.md
```

---

## 三、系统架构

### 3.1 模块分层

```
┌─────────────────────────────────────────────────────────┐
│  调用层:  CLI (cli.py)  │  FastAPI (server.py)  │  Batch │
├─────────────────────────────────────────────────────────┤
│  调度层:  ExplanationPipeline (pipeline.py)              │
├──────────────┬──────────────┬──────────────┬────────────┤
│  HeatmapGen  │ TamperDetect │  RiskScorer  │ TextExplain│
│  (Grad-CAM   │ (patch 0.4 + │  (5维加权)   │ (三段模板) │
│   后处理)     │  feature 0.6)│              │            │
├──────────────┴──────────────┴──────────────┴────────────┤
│  上游:  Detector → MambaOutCustom                        │
│  get_heatmap() → Grad-CAM 14×14                          │
│  get_spatial_features() → feat_s2(14×14) + feat_s3(7×7)  │
└─────────────────────────────────────────────────────────┘
```

### 3.2 核心数据流

```
输入图像
  │
  ├─→ Detector.predict()          ★ 权威判定来源
  │     forward → softmax → label + fake_prob + upstream_risk_score
  │
  ├─→ Detector.get_heatmap()
  │     forward + backward → Grad-CAM on stage2 (384ch × 14×14)
  │     → ReLU → normalize → bilinear upsample → [H, W] 热力图
  │
  ├─→ Detector.get_spatial_features()
  │     forward(return_spatial=True) → feat_s2 [384,14,14] + feat_s3 [576,7,7]
  │
  ├─→ HeatmapGenerator: smooth(σ=3.0) → colormap → α-blend → overlay + mask
  │
  ├─→ TamperDetector:
  │     PatchAnalyzer: 多尺度滑窗(224/160) + 批量推理 → patch_score + raw_score
  │     FeatureStatsAnalyzer: feat_s2 通道方差异常 → feature_score
  │     0.4×patch + 0.6×feature → 归一化 → 百分位阈值 → 形态学 → NMS → bbox
  │     每个 bbox 附加 patch_fake_prob (从 raw_score 区域均值提取)
  │
  ├─→ TamperClassifier:  ★ v1.0 新增
  │     classify_tamper(label, bbox_list) → 四象限分类
  │     local_tamper 时覆盖 label 为 fake (全局 real + 局部 bbox)
  │
  ├─→ RiskScorer:
  │     5维: fake_prob(0.30) + artifact_intensity(0.25) + tamper_area(0.25)
  │           + region_count(0.10) + consistency(0.10)
  │     → global_score → low[0,0.35) / medium[0.35,0.70) / high[0.70,1.0]
  │
  ├─→ TextExplainer:
  │     模板填充 → 【总体结论】【取证分析】【定位详情】
  │
  └─→ 完整 JSON + base64 图像 + HTML 报告
```

> **判定权责**：`label` 和 `fake_prob` 由 `Detector.predict()` 直接输出（MambaOut 模型 softmax 结果，阈值 0.5），下游不再重复计算。`upstream_risk_score` 随元信息透传，供多证据融合模块使用。

---

## 四、核心算法

### 4.1 热力图：Grad-CAM on Stage2 (14×14)

在 MambaOut backbone 的 stage2 输出（384 通道 × 14×14 空间格点）上做 Grad-CAM：

1. **Forward hook** 捕获 stage2 激活 `A ∈ R^{384×14×14}`
2. **Backward** 对 fake 类 logit 求梯度，捕获 stage2 梯度 `G ∈ R^{384×14×14}`
3. **通道权重** `w_c = mean(G_c)` → 加权激活 `CAM = ReLU(Σ w_c · A_c)` → [14, 14]
4. **Bilinear upsample** 到原图尺寸 → [H, W], 归一化到 [0, 1]

相比 v1 的 2×2 (4 格点) Weighted Channel Attribution，空间分辨率提升 **49 倍**。

### 4.2 篡改定位：混合策略

| 子分析器 | 方法 | 权重 | 分辨率 | 速度 |
|----------|------|------|--------|------|
| PatchAnalyzer | 多尺度滑窗(224/160) + 批量 Detector 推理 | 0.4 | 高 | 慢 (~80ms) |
| FeatureStatsAnalyzer | stage2 特征(384ch×14×14) 通道方差异常 | 0.6 | 高 | 极快 (<1ms) |

后处理流水线：`融合 score_map → 归一化 → 百分位阈值(90%) → 形态学(开/闭) → scipy.label → 最小外接矩形 → NMS(IoU=0.3)`

### 4.3 风险评分：五维度加权

| 维度 | 权重 | 计算 |
|------|------|------|
| 检测置信度 | 0.30 | fake_prob |
| 伪影强度 | 0.25 | 0.6×heatmap_max + 0.4×heatmap_mean |
| 篡改面积比 | 0.25 | Σ bbox_area / total_area |
| 区域数量 | 0.10 | log₂(n+1) / log₂(6) |
| 一致性 | 0.10 | IoU(热力图高分区域, 掩膜高分区域) |

等级：`low [0, 0.35)` / `medium [0.35, 0.70)` / `high [0.70, 1.0]`

> **全局风险分数 vs 局部风险分**：全局风险分反映整张图需要人工复核的紧迫程度。局部风险分基于该 bbox 区域的 **patch 级 fake_prob**（非全局 fake_prob）计算：`0.5 × patch_fake_prob + 0.5 × min(area_frac × 10, 1.0)`，确保局部篡改场景下即使全局 fake_prob 很低，可疑区域也能获得合理的高分。
>
> **热力图 vs bbox 为什么不一致**：热力图来自 Grad-CAM（stage2 梯度反向传播），bbox 来自 TamperDetector（滑窗推理 + 特征统计）。两者独立计算，不一致是正常的。

### 4.2.5 局部篡改判定（四象限分类）

在全局判定 + 局部定位结果上做二次分类：

| 全局判定 | 局部定位 | 篡改类型 | 最终 label | 含义 |
|----------|----------|----------|------------|------|
| real | 无 bbox | `confirmed_real` | real | 全图真，局部无异常，双重确认 |
| real | 有 bbox | `local_tamper` | local_tamper (显示: 局部篡改) | 全图看着真，但 patch 级发现异常 → 标记为局部篡改 |
| fake | 无 bbox | `full_aigc` | fake | 全图假，伪影均匀分布 |
| fake | 有 bbox | `full_aigc_hotspots` | fake | 全图假，且某些区域伪影更集中 |

> **关键逻辑**：`real + 有 bbox → local_tamper` 是唯一覆盖全局判定的分支，不归入 AIGC 伪造类别，而是独立标记为"局部篡改"。224×224 缩略图上小面积篡改的信号被全图稀释，全局 softmax 看不出来，但 patch 滑窗能定位到。

### 4.4 解释文本：三段式模板

```
【总体结论】判定结果 + 置信度 + 风险等级 + 处置建议
【取证分析】基于热力图统计量的伪影特征描述
【定位详情】逐区域坐标 + 面积 + 局部风险分
```

### 4.5 自定义 Colormap

| 位置 | 颜色 | RGB | 含义 |
|------|------|-----|------|
| 0.00 | 深蓝 | (10, 40, 120) | 低伪造可疑 |
| 0.40 | 青色 | (40, 200, 160) | |
| 0.55 | 绿色 | (80, 220, 60) | |
| 0.70 | 黄色 | (230, 210, 30) | |
| 0.85 | 橙红 | (240, 100, 30) | |
| 1.00 | 红紫 | (180, 20, 140) | 高伪造可疑 |

---

## 五、接口参考

### 5.1 Python API

```python
from detection import Detector
from explanation import ExplanationPipeline

from server import resolve_checkpoint_path

detector = Detector(checkpoint_path=str(resolve_checkpoint_path()), device='cuda')
pipeline = ExplanationPipeline(detector, config={'overlay_alpha': 0.5, 'smooth_sigma': 3.0})

# 文件路径 或 PIL.Image
result = pipeline.run('tests/fixtures/real.png')

print(result['label'])            # 'real' | 'fake'
print(result['fake_prob'])        # 0.0388
print(result['risk_level'])       # 'low' | 'medium' | 'high'
print(result['explanation'])      # 三段式中文解释
print(result['bbox_list'])        # [{'x','y','w','h','area','risk_score'}, ...]

# 直接使用子模块
from explanation.heatmap import HeatmapGenerator
gen = HeatmapGenerator(detector)
hm = gen.generate('test.jpg')     # {'overlay': PIL.Image, 'mask': PIL.Image, ...}
```

### 5.2 CLI

```bash
python -m explanation.cli --input tests/fixtures/real.png
python -m explanation.cli --input test.jpg --save-dir ./output --skip-localization
python -m explanation.cli --input test.jpg --config configs/default.yaml
```

### 5.3 FastAPI

```bash
python server.py                           # CUDA，自动发现权重，Web 与 API 启动在 8000 端口
python server.py --device cpu --port 8080  # CPU 与自定义端口
```

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/` | TraceGuard Web 工作台 |
| GET | `/api/v1/health` | GPU 状态 |
| GET | `/api/v1/config` | 当前配置 |
| POST | `/api/v1/analyze` | 单图分析 (base64) |
| POST | `/api/v1/analyze/batch` | 批量 (≤20张) |

### 5.4 批量处理

```bash
python -m explanation.batch --input-dir ./images --output-dir ./results
python -m explanation.batch --input-dir ./images --output-json results.json
```

### 5.5 JSON 响应格式

```json
{
  "label": "fake",
  "fake_prob": 0.9702,
  "tamper_type": "full_aigc_hotspots",
  "risk_score": 0.48,
  "risk_level": "medium",
  "explanation": "【总体结论】\n...\n\n【取证分析】\n...\n\n【定位详情】\n...",
  "explanation_brief": "AIGC伪造图 | 置信度97% | 风险medium",
  "bbox_list": [{"x": 10, "y": 20, "w": 180, "h": 150, "area": 27000, "risk_score": 0.72}],
  "dimension_scores": {"fake_prob": 0.97, "artifact_intensity": 0.85, "tamper_area": 0.12, "region_count": 0.39, "consistency": 0.45},
  "overlay_b64": "(base64 PNG)",
  "mask_b64": "(base64 PNG)",
  "tamper_mask_b64": "(base64 PNG)",
  "tamper_overlay_b64": "(base64 PNG)",
  "bbox_image_b64": "(base64 PNG)",
  "elapsed_ms": 74,
  "metadata": {"heatmap_method": "gradcam", "overlay_alpha": 0.5, "localization_enabled": true,
               "detection_source": "Detector.predict()", "upstream_risk_score": 0.97, ...}
}
```

---

## 六、案例结果

> 本节保存的是已有实验记录，不是当前目录中的现场输出。当前缺少 `tests/BigGAN/`、`case_study/` 和 `batch_results/`，因此必须先恢复相同数据、权重和命令，再复核以下数字。

### 6.1 BigGAN 全量验证（1000 张，v2 Grad-CAM，更新版 checkpoint）

| 指标 | 数值 |
|------|------|
| 总图片数 | 1000 |
| 判定为 AIGC 伪造 | 949 (94.9%) |
| 判定为真实 | 51 (5.1%) |
| 高风险 / 中风险 / 低风险 | 0 / 951 / 49 |
| 伪造图平均 fake_prob | 0.9182 |
| 伪造图最高 fake_prob | 0.9998 |
| 真实图最高 fake_prob | 0.4938（无跨越阈值误判） |
| 总体平均 risk_score | 0.4885 |
| 平均推理耗时 | ~90ms/张 |

> **检出率 94.9%，接近张潇模型预期（~97%）**。此前旧 checkpoint 的 69.7% 为模型权重版本问题，已更新解决。
> Grad-CAM 热力图在 AIGC 图像上呈现清晰的块状/网格状伪影热点区域，检测分数与热力响应高度一致。
> 51 张 real 图中无一误判为 fake（最高 fake_prob=0.49 < 0.50），决策边界清晰。
> 无高风险案例（risk_score ≥ 0.70），风险评分体系偏保守，Phase 7 将进行阈值校准。

### 6.2 典型单图案例

| 图像 | 判定 | fake_prob | risk_score | 等级 | 耗时 |
|------|------|-----------|------------|------|------|
| 040_biggan_00074 | **fake** | 0.9973 | 0.54 | medium | 92ms |
| 158_biggan_00127 | **fake** | 0.9946 | 0.51 | medium | 104ms |
| 052_biggan_00143 | **fake** | 0.9938 | 0.55 | medium | 88ms |
| 807_biggan_00035 | **fake** | 0.9983 | 0.52 | medium | ~100ms |
| 233_biggan_00035 | real | 0.0104 | 0.16 | low | 96ms |
| 316_biggan_00035 | real | 0.0766 | 0.15 | low | 116ms |
| 983_biggan_00143 | real | 0.0075 | 0.21 | low | 105ms |
| 216_biggan_00035 | fake | 0.9334 | 0.50 | medium | ~90ms |
| 233_biggan_00035 | real | 0.0104 | 0.17 | low | ~90ms |

> 高置信度 fake 图 (fake_prob > 0.90) 的热力图呈现大面积高响应伪影区域。51 张 real 图无一跨越 0.50 阈值，检测-热力图一致性良好。

### 6.3 可视化报告

```python
from explanation.visualization import Visualizer

viz = Visualizer()
html = viz.report('image.jpg', pipeline_result)    # 单图 HTML 报告
viz.save_report(html, 'report.html')

# 雷达图 / 仪表条 / 批量汇总图
from explanation.visualization.charts import radar_chart, risk_gauge, batch_summary
radar_chart(dim_scores).save('radar.png')
risk_gauge(0.48, 'medium').save('gauge.png')
```

---

## 七、配置系统

`configs/default.yaml` 统一管理所有参数，按模块分组：

```yaml
detection:    {checkpoint_path, device}
heatmap:      {method: gradcam, overlay_alpha: 0.5, smooth_sigma: 3.0}
localization: {enable, scales: [224,160], stride_ratio: 0.5, threshold_percentile: 90, ...}
risk:         {weights: {fake_prob: 0.30, ...}, levels: {low: [0,0.35], ...}}
text:         {language: zh, detail_level: standard}
output:       {format: PNG, html_title: ...}
```

加载方式：

```python
from explanation.config import load_and_convert
pipe_config = load_and_convert('configs/default.yaml')
pipeline = ExplanationPipeline(detector, config=pipe_config)
```

优先级：`CLI 参数 > YAML 配置 > 内置默认值`

---

## 八、测试

```bash
python -m pytest tests/ -v              # 无 GPU 回归测试
python -m pytest tests/ -v -m "gpu"     # GPU 集成测试
```

| 模块 | 用例数 |
|------|--------|
| test_heatmap | 10 |
| test_localization | 21 |
| test_pipeline | 21 |
| test_risk | 20 |
| test_text | 16 |
| test_visualization | 29 |
| test_config | 13 |
| test_cli | 6 |
| test_server | 4 |
| **合计** | **140** |
