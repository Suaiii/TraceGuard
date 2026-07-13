# TraceGuard 社交媒体实验运行环境

核查日期：2026-07-13

## 环境位置

- Python：`E:\aNB\envs\traceguard\python.exe`
- Python 版本：3.10.20
- PyTorch：2.5.1+cu121
- torchvision：0.20.1+cu121
- GPU：NVIDIA GeForce RTX 4060 Laptop GPU
- NVIDIA 驱动：580.97
- CUDA 可见性：已验证为 `true`

环境仅仅使用 E 盘路径。运行命令显式设置 `PYTHONNOUSERSITE=1`，避免用户级 Python 包污染实验环境。

## 安装命令

```powershell
E:\anaconda\Scripts\conda.exe create -p E:\aNB\envs\traceguard python=3.10 pip -y

$env:PYTHONNOUSERSITE='1'
E:\aNB\envs\traceguard\python.exe -m pip install `
  torch==2.5.1+cu121 torchvision==0.20.1+cu121 `
  --index-url https://download.pytorch.org/whl/cu121
E:\aNB\envs\traceguard\python.exe -m pip install -r requirements-dev.txt
```

首次尝试创建 `E:\anaconda\envs\traceguard` 时，因为 `E:\anaconda\envs` ACL 仅向普通用户提供读取和执行权限而失败。最终环境改建到已验证可写的 `E:\aNB\envs\traceguard`，没有修改现有 `osn_video2` 或基础环境。

## GPU 与权重验证

```powershell
$env:PYTHONNOUSERSITE='1'
E:\aNB\envs\traceguard\python.exe -c "import torch; print(torch.__version__, torch.cuda.is_available(), torch.cuda.get_device_name(0))"
E:\aNB\envs\traceguard\python.exe -c "from detection import Detector; Detector('best.pth', 'cuda'); print('checkpoint_ok')"
```

验证结果：

```text
2.5.1+cu121
True
NVIDIA GeForce RTX 4060 Laptop GPU
checkpoint_ok
```

权重 SHA-256：`29F85CAFFA5FCE11C7F31A2FB29C4DC44F65782D5300064BC4F73ADB153B0474`。

## 实际流式测速

命令：

```powershell
$env:PYTHONNOUSERSITE='1'
E:\aNB\envs\traceguard\python.exe -m experiments.socialmedia.evaluate paired-genimage `
  --manifest dataset\socialmedia\manifests\genimage_socialmedia_pairs.csv `
  --project-root E:\aNB\TECH\AI竞赛 `
  --checkpoint best.pth --device cuda --batch-size 32 --limit 32 `
  --output results\socialmedia\smoke_paired
```

该 smoke run 包含 32 个 `sample_id` 和 Original/Facebook/WeChat/Weibo 四个版本，共 128 张：

- 完成：128
- 失败：0
- 唯一预测键：128
- 平均纯推理时间：约 12.1 ms/张
- 完整运行时间：约 13 秒，包含四个归档的 SHA-256 计算、权重加载和结果写入
- 批大小：32

该样本仅仅覆盖排序后的前 32 张 ADM 图像，只用于环境与吞吐验证，不作为报告结论或正式抽样结果。
