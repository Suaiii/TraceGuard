# TraceGuard 数据集与模型库存

核查日期：2026-07-13

校验算法：SHA-256

大型数据和模型仅保存在本地，不进入 Git。当前文件来源记录仅能追溯到工作区现有资产；原始下载链接、许可文件或训练运行编号未随文件保存的项目，必须在对外发布或正式实验前补齐。

| 名称 | 相对路径 | 大小（字节） | SHA-256 | 当前可确认来源 | 用途 | Git 状态 |
|---|---|---:|---|---|---|---|
| TraceGuard 检测权重 | `best.pth` | 545610247 | `29F85CAFFA5FCE11C7F31A2FB29C4DC44F65782D5300064BC4F73ADB153B0474` | 本地现有 MambaOut-Small 检测权重；原始训练运行或下载链接待补 | Web/API/CLI 的全局 AIGC 真伪检测 | ignored |
| CASIA v1 压缩包 | `dataset/CASIAv1.zip` | 95106074 | `5A08E3795EAF1BE8FF1FA530AE6ADCD9DFE2C47563200F99FCC1A465150602A9` | 本地工作区现有 CASIA v1 数据包；压缩包内含 Au、Modified Tp、Original Tp；下载链接和许可文件待补 | 传统图像篡改/定位对照与案例验证候选 | ignored |
| GenImage 测试压缩包 | `dataset/GenImage.zip` | 2977302525 | `4A5B7BCCFA525D07E04C26DEC4CCDBF80934F26AED0D82998C92B6F2B7F95089` | 本地工作区现有 GenImage 测试包；压缩包内为 `GenImage_Test.zip`；下载链接和许可文件待补 | 跨生成器 AIGC 图像检测实验候选 | ignored |
| Real 图像压缩包 | `dataset/Real.zip` | 33584590 | `4D588CE9DB0422C941E312599C3D4082ADBC77384B1BBDE5C6F88106CCFF02DC` | 本地 UUID 命名真实图像集合；采集规则、原始站点和许可待补 | 真实图像对照、误报分析和阈值校准候选 | ignored |

## 权重放置规则

`server.py` 默认按以下顺序自动发现：

1. `checkpoints/best.pth`
2. `best.pth`

显式传入 `--checkpoint PATH` 时仅使用该路径；路径不存在会直接报错，不会静默回退。

## 当前数据状态

- `tests/BigGAN/` 不存在，README 中的 1000 张 BigGAN 批量命令当前不能直接运行。
- 上表数据尚未建立正式 train/validation/test 划分。
- 未补齐来源链接和许可前，不得将这些本地压缩包描述为可公开再分发资产。
- 解压、重命名、抽样或重划分后必须新增派生记录，不能覆盖本表原始文件记录。
