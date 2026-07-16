# TraceGuard — 跨域 AIGC 伪造检测 可复现性文档

## 实验结果

### 跨8生成器盲测 (Balanced Test: 源域real 1:1 目标域fake)

| Generator   | #Real | #Fake | Accuracy   | Real Recall | Fake Recall |
| ----------- | -----:| -----:| ----------:| -----------:| -----------:|
| ADM         | 1000  | 1000  | 68.40%     | 99.80%      | 37.00%      |
| BigGAN      | 1000  | 1000  | 97.35%     | 99.80%      | 94.90%      |
| Glide       | 1000  | 1000  | 86.35%     | 99.80%      | 72.90%      |
| Midjourney  | 1000  | 1000  | 74.50%     | 99.80%      | 49.20%      |
| SD14        | 1000  | 1000  | 86.15%     | 99.80%      | 72.50%      |
| SD15        | 1000  | 1000  | 86.45%     | 99.80%      | 73.10%      |
| VQDM        | 1000  | 1000  | 56.50%     | 99.80%      | 13.20%      |
| Wukong      | 1000  | 1000  | 81.70%     | 99.80%      | 63.60%      |
| **Average** |       |       | **79.68%** |             |             |

> **BigGAN 检出率 94.9%<mark>** 来自 Balanced Test Fake Recall 列。</mark>

### MMD 消融对比 (Ablation Study)

| Generator   | No MMD FakeR | With MMD FakeR | MMD贡献      |
| ----------- | ------------:| --------------:|:----------:|
| ADM         | 25.3%        | 37.0%          | **+11.7%** |
| BigGAN      | 73.3%        | 94.9%          | **+21.6%** |
| Glide       | 65.7%        | 72.9%          | +7.2%      |
| Midjourney  | 43.7%        | 49.2%          | +5.5%      |
| SD14        | 63.9%        | 72.5%          | +8.6%      |
| SD15        | 65.7%        | 73.1%          | +7.4%      |
| VQDM        | 8.9%         | 13.2%          | +4.3%      |
| Wukong      | 50.3%        | 63.6%          | **+13.3%** |
| **Average** | **74.60%**   | **79.68%**     | **+5.08%** |

> MMD 在所有 8 个生成器上均有正向贡献，平均 Fake Recall 提升 5.08 个百分点。BigGAN 提升最大(+21.6%)。原始 CSV: `eval_results.csv` (with MMD) | `eval_results_no_mmd.csv` (without MMD)

## 数据划分

| 数据集              | 角色       | 数量                         | 划分方式               |
| ---------------- | -------- | -------------------------- | ------------------ |
| models/train/    | 源域（有标签）  | 18,000 (9K real + 9K fake) | 85:15 分层划分，seed=42 |
| models/Genimage/ | 目标域（无标签） | 8,000 (8生成器×1000)          | 全部用于盲测             |

源域训练集: 15,300 张 (7,650 real + 7,650 fake)
源域验证集: 2,700 张 (1,350 real + 1,350 fake)

## 评测方式

Balanced Test: 从源域验证集取 N 张 real + 从目标生成器取 N 张 fake → 2N 张混合测试
N = min(source_real_count, generator_fake_count) = min(1350, 1000) = 1000

## 训练配置

| 参数         | 数值                                                                    |
| ---------- | --------------------------------------------------------------------- |
| 骨干网络       | MambaOut-Small (45.44M)                                               |
| 域自适应       | MK-MMD, 5核高斯, kernel_mul=2.0                                          |
| 训练轮数       | 25 epochs                                                             |
| Batch Size | 48                                                                    |
| 差分学习率      | backbone=1e-5, head=1e-3                                              |
| 优化器        | AdamW, weight_decay=1e-4                                              |
| MMD权重β     | 0→1.0 渐进 (10 epoch warmup)                                            |
| LR Warmup  | 5 epochs                                                              |
| 标签平滑       | 0.1                                                                   |
| 梯度裁剪       | max_norm=5.0                                                          |
| 学习率调度      | CosineAnnealing (warmup后)                                             |
| 数据增强       | Resize(256)→RandomCrop(224)→HorizontalFlip(0.5)→ColorJitter→Normalize |
| 预训练        | ImageNet (MambaOut-Small pretrained weights)                          |
| 训练环境       | AutoDL RTX 4090, 24GB VRAM                                            |
| Checkpoint | epoch 16, val_acc 99.26%                                              |

## 复现命令

```bash
# 1. 安装依赖
pip install torch torchvision numpy pillow tqdm scikit-learn

# 2. 数据准备
# 将源域图片放入 models/train/ (文件名含 _real/_fake 标签)
# 将GenImage各生成器放入 models/Genimage/{ADM,BigGAN,Glide,...}/

# 3. 下载预训练权重
# 从 https://hf-mirror.com/timm/mambaout_small.in1k/resolve/main/pytorch_model.bin
# 保存为 mambaout_small.pth

# 4. 训练
python train.py \
    --source_root ./models/train \
    --target_root ./models/Genimage \
    --epochs 25 \
    --batch_size 48 \
    --num_workers 4 \
    --pretrained \
    --pretrained_path ./mambaout_small.pth \
    --save_dir ./checkpoints

# 5. 评测
python eval.py \
    --checkpoint ./checkpoints/best.pth \
    --source_root ./models/train \
    --genimage_root ./models/Genimage

# 结果见 checkpoints/eval_results.csv 或运行 eval.py 的输出
```
