# 定位模块定量评价——标注依据与结果

> #15-B 交付物：真实篡改案例的标注依据、指标定义、基线、结果与局限。

## 1. 数据来源

### 1.1 CASIA v1 主评价（40 tampered + 10 clean）

- **数据集**：CASIA v1（CASIA Image Tampering Detection Evaluation Database v1.0），从 CASIA 官方渠道获取
- **使用子集**：
  - `Au/Au/`：800 张真实图像，用作底图
  - `Modified Tp/Tp/`：920 张篡改图像（拼接/复制-移动），用作粘贴 patch 源
- **合成方式**：由 `experiments/synthetic_dataset.py` 以 seed=42 自动生成
  - 从 Au 随机选 40 张作底图，从 Modified Tp 随机裁剪 patch 硬粘贴
  - 粘贴区域即为像素级 GT 掩膜（二值，值 255）
  - 另含 10 张未修改的 clean 负对照
- **版本**：本地工作区现有压缩包（2026-07-13 核查），具体 SHA-256 见 `provenance.json`

### 1.2 AIGC 合成边界评价（10 tampered + 5 clean）

- **数据来源**：Facebook 派生 GenImage 平衡子集
  - 来自 `results/socialmedia/platform_benchmark/raw_predictions.csv`
  - 按 seed=42 抽取 100 real + 100 fake
- **合成方式**：同 `experiments/synthetic_dataset.py`
- **用途**：仅用于定位局限性说明，不作为定位精度主证据

## 2. 标注协议

### 2.1 标注方式
- GT 掩膜由 `experiments/synthetic_dataset.py` **程序自动生成**，非人工标注
- 从 Modified Tp 图像中随机裁剪矩形 patch（尺寸 48-96 px），硬粘贴到 Au 底图
- 粘贴区域即为 GT：白色（255）表示篡改，黑色（0）表示真实
- 无边缘融合、无压缩伪影模拟、非 AIGC 生成式篡改

### 2.2 标注粒度
- 像素级二值掩膜
- GT 为精确矩形——与真实 AIGC 局部篡改的融合边界存在系统性差异
- 此标注粒度不能代表真实 AIGC 局部篡改或社交媒体传播后场景

## 3. 指标定义

所有指标由 `evaluate_localization.py::compute_mask_metrics()` 计算。

| 指标 | 公式 | 说明 |
|------|------|------|
| **IoU** | TP / (TP + FP + FN) | Intersection over Union，越高越好 |
| **Dice** | 2·TP / (2·TP + FP + FN) | 等价于 Pixel F1，越高越好 |
| **Pixel F1** | 2·P·R / (P + R) | P=TP/(TP+FP), R=TP/(TP+FN) |
| **Detection Rate** | 图像级：是否有 ≥1 个 bbox | 在 tampered 样本上的检出率 |
| **Clean FP Rate** | 图像级：clean 样本上产生 ≥1 个 bbox 的比例 | 越低越好，100%=无区分力 |

**阈值扫描**：对 percentile ∈ {50, 60, 70, 75, 80, 85, 90, 92, 95, 97} 各扫描一次。默认工作点为 percentile=90（与 `configs/default.yaml` 的 `threshold_percentile` 一致）。

`evaluate_localization.py::sweep_thresholds()` 实现了全量扫描。详情见 `localization_threshold_sweep.csv`。

## 4. Baseline 对比

本评价为**自评**（self-evaluation），未与外部定位方法对比。当前仅记录：
- 同一检测器在不同数据集上的表现差异
- 不同百分位阈值下的指标变化

| 对比项 | CASIA v1 (40+10) | AIGC 合成 (10+5) |
|--------|-----------------|-------------------|
| 样本数 | 40 tampered + 10 clean | 10 tampered + 5 clean |
| 数据来源 | CASIA v1 Au + Modified Tp | Facebook 派生 GenImage 平衡子集 |
| 用途 | 定位能力参考 | 边界/局限性说明 |

## 5. 结果表

### 5.1 CASIA v1 主评价（percentile=90）

| 指标 | 数值 |
|------|------|
| Tampered 样本 | 40 |
| Clean 样本 | 10 |
| **Avg IoU** | **0.107** |
| **Avg Dice / Pixel F1** | **0.177** |
| Avg Precision | 0.145 |
| Avg Recall | 0.242 |
| Detection Rate | 100% |
| **Clean FP Rate** | **100%** |
| Clean Avg Bbox Count | 7.9 |
| 最佳百分位 (Dice) | 80 (Dice=0.191) |
| 最佳百分位 (IoU) | 85 (IoU=0.113) |

完整阈值扫描见 `results/localization/localization_threshold_sweep.csv`（本地，gitignored）。

### 5.2 AIGC 合成边界评价（percentile=90）

| 指标 | 数值 |
|------|------|
| Tampered 样本 | 10 |
| Clean 样本 | 5 |
| **Avg IoU** | **0.0148** |
| **Avg Dice / Pixel F1** | **0.0286** |
| Avg Precision | 0.0171 |
| Avg Recall | 0.136 |
| Detection Rate | 100% |
| **Clean FP Rate** | **100%** |
| Clean Avg Bbox Count | 9.8 |

完整阈值扫描见 `aigc_synthetic_15_threshold_sweep.csv`。

## 6. 局限性与解释边界

### 6.1 核心局限

1. **Clean FP Rate = 100%**：系统在无篡改图像上仍然输出 bbox，无法区分"干净图"和"有篡改的图"——bbox 仅表示模型关注区域，不代表真实篡改
2. **像素级重叠极低**（IoU < 0.11）：不支持像素级精确定位
3. **GT 是精确矩形，模型输出是热力扩散 + 形态学后处理**：天然不重合

### 6.2 结论

- ✅ 图像级检测存在（100% 检出 tampered 样本）
- ❌ 不支持像素级精确定位
- ❌ bbox 不能作为法庭级篡改证据
- ⚠️ 热力图仅为分类证据响应，Grad-CAM 不代表定位精度

### 6.3 合成数据局限

- GT 掩膜为硬粘贴边界，与真实 AIGC 局部篡改的融合边界存在差异
- CASIA v1 为传统图像拼接/复制-移动篡改，不代表 AIGC 局部生成篡改
- AIGC 合成边界评价的数据量仅 10+5，仅适用于极限情况参考

### 6.4 阈值外推

- 当前 percentile=90 是 `configs/default.yaml` 的默认工作点
- 阈值不可跨数据集、跨场景外推

## 7. 与社交媒体案例图的关系

`docs/figures/socialmedia/` 中的案例图标注了 `bbox_count` 和 `tamper_type`。这些值来自 `case_summary.csv` 中的真实系统输出，但**受本 README 第 6 节全部局限约束**——bbox 数量仅作系统内部证据一致性演示，不代表像素级定位精度。

## 8. 复现命令

```bash
# 第一步：生成合成测试集（需要 CASIA v1 数据集）
python experiments/synthetic_dataset.py \
    --au-dir "dataset/CASIAv1/Au/Au" \
    --tp-dir "dataset/CASIAv1/Modified Tp/Tp" \
    --output-dir results/localization/synthetic_dataset \
    --num-tampered 40 --num-clean 10 --seed 42

# 第二步：运行定位评价（含阈值扫描）
python evaluate_localization.py \
    --synthetic-dir results/localization/synthetic_dataset \
    --checkpoint checkpoints/best.pth \
    --device cuda \
    --output-dir results/localization
```
