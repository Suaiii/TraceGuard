"""
MambaOut Custom — 基于 MambaOut-Small 的魔改骨干网络

从克隆的 MambaOut/models/mambaout.py 中提取 mambaout_small 模型，
进行以下核心魔改：

1. 移除全局平均池化层 (GAP)，使网络保留像素级微观伪影
   直接输出 2304 维的密集特征图（576 通道 × 2×2 空间）
2. 加入瓶颈层 (Bottleneck Layer)：
   nn.Linear(2304, 256) → BatchNorm1d → ReLU
   将高维特征强制降维至 256 维，避免 MMD 计算时的维度灾难
3. 分流输出：监督分类分支 nn.Linear(256, 2)

基于 MambaOut: Do We Really Need Mamba for Vision? (CVPR 2025)
原始仓库: https://github.com/yuweihao/MambaOut
"""

from functools import partial
import torch
import torch.nn as nn
import torch.nn.functional as F
from torch.hub import load_state_dict_from_url


# ==============================================================================
# MambaOut 基础构建模块 (与原始 MambaOut 代码一致)
# ==============================================================================

def _trunc_normal_(tensor, mean=0., std=1.):
    """截断正态分布初始化（免 timm 依赖）"""
    import math
    import warnings
    with torch.no_grad():
        size = tensor.shape
        tmp = tensor.new_empty(size + (4,)).normal_()
        valid = (tmp < 2) & (tmp > -2)
        ind = valid.max(-1, keepdim=True)[1]
        tensor.data.copy_(tmp.gather(-1, ind).squeeze(-1))
        tensor.data.mul_(std).add_(mean)
    return tensor


class StemLayer(nn.Module):
    """MambaOut 第一阶段的 Stem 下采样层
    两层 stride=2 的 3x3 卷积，将 224×224 下采样至 56×56
    """
    def __init__(self, in_channels=3, out_channels=96,
                 act_layer=nn.GELU, norm_layer=partial(nn.LayerNorm, eps=1e-6)):
        super().__init__()
        self.conv1 = nn.Conv2d(in_channels, out_channels // 2,
                               kernel_size=3, stride=2, padding=1)
        self.norm1 = norm_layer(out_channels // 2)
        self.act = act_layer()
        self.conv2 = nn.Conv2d(out_channels // 2, out_channels,
                               kernel_size=3, stride=2, padding=1)
        self.norm2 = norm_layer(out_channels)

    def forward(self, x):
        x = self.conv1(x)
        x = x.permute(0, 2, 3, 1)
        x = self.norm1(x)
        x = x.permute(0, 3, 1, 2)
        x = self.act(x)
        x = self.conv2(x)
        x = x.permute(0, 2, 3, 1)
        x = self.norm2(x)
        return x


class DownsampleLayer(nn.Module):
    """MambaOut 阶段间的下采样层
    单层 stride=2 的 3x3 卷积
    """
    def __init__(self, in_channels=96, out_channels=192,
                 norm_layer=partial(nn.LayerNorm, eps=1e-6)):
        super().__init__()
        self.conv = nn.Conv2d(in_channels, out_channels,
                              kernel_size=3, stride=2, padding=1)
        self.norm = norm_layer(out_channels)

    def forward(self, x):
        x = self.conv(x.permute(0, 3, 1, 2)).permute(0, 2, 3, 1)
        x = self.norm(x)
        return x


class DropPath(nn.Module):
    """Stochastic Depth (Drop Path)"""
    def __init__(self, drop_prob=None):
        super().__init__()
        self.drop_prob = drop_prob

    def forward(self, x):
        if self.drop_prob == 0. or not self.training:
            return x
        keep_prob = 1 - self.drop_prob
        shape = (x.shape[0],) + (1,) * (x.ndim - 1)
        random_tensor = keep_prob + torch.rand(shape, dtype=x.dtype, device=x.device)
        random_tensor.floor_()
        output = x.div(keep_prob) * random_tensor
        return output


class GatedCNNBlock(nn.Module):
    """MambaOut 核心模块：门控 CNN Block

    基于 Gated CNN (https://arxiv.org/pdf/1612.08083)，
    结合 MetaFormer 架构设计。
    conv_ratio 控制深度卷积的通道比例。
    """
    def __init__(self, dim, expansion_ratio=8/3, kernel_size=7, conv_ratio=1.0,
                 norm_layer=partial(nn.LayerNorm, eps=1e-6),
                 act_layer=nn.GELU, drop_path=0.):
        super().__init__()
        self.norm = norm_layer(dim)
        hidden = int(expansion_ratio * dim)
        self.fc1 = nn.Linear(dim, hidden * 2)
        self.act = act_layer()
        conv_channels = int(conv_ratio * dim)
        self.split_indices = (hidden, hidden - conv_channels, conv_channels)
        self.conv = nn.Conv2d(conv_channels, conv_channels,
                              kernel_size=kernel_size, padding=kernel_size // 2,
                              groups=conv_channels)
        self.fc2 = nn.Linear(hidden, dim)
        self.drop_path = DropPath(drop_path) if drop_path > 0. else nn.Identity()

    def forward(self, x):
        shortcut = x
        x = self.norm(x)
        g, i, c = torch.split(self.fc1(x), self.split_indices, dim=-1)
        c = c.permute(0, 3, 1, 2)
        c = self.conv(c)
        c = c.permute(0, 2, 3, 1)
        x = self.fc2(self.act(g) * torch.cat((i, c), dim=-1))
        x = self.drop_path(x)
        return x + shortcut


# ==============================================================================
# MambaOut 骨干网络（保留完整 backbone，去掉分类头）
# ==============================================================================

class MambaOutBackbone(nn.Module):
    """MambaOut 骨干网络

    Args:
        in_chans: 输入通道数
        depths: 各阶段的 Block 数量，mambaout_small: [3, 4, 27, 3]
        dims: 各阶段的特征维度，mambaout_small: [96, 192, 384, 576]
        drop_path_rate: Stochastic Depth 概率
    """
    def __init__(self, in_chans=3, depths=(3, 4, 27, 3), dims=(96, 192, 384, 576),
                 conv_ratio=1.0, kernel_size=7, drop_path_rate=0.,
                 norm_layer=partial(nn.LayerNorm, eps=1e-6),
                 act_layer=nn.GELU):
        super().__init__()
        self.num_stage = len(depths)
        self.dims = dims

        # 下采样层: StemLayer (stride 4) + 3× DownsampleLayer (各 stride 2)
        down_dims = [in_chans] + list(dims)
        downsample_layers = [StemLayer] + [DownsampleLayer] * (self.num_stage - 1)
        self.downsample_layers = nn.ModuleList(
            [downsample_layers[i](down_dims[i], down_dims[i + 1])
             for i in range(self.num_stage)]
        )

        # Stochastic Depth 线性递增
        dp_rates = [x.item() for x in torch.linspace(0, drop_path_rate, sum(depths))]

        # 构建 4 个阶段
        self.stages = nn.ModuleList()
        cur = 0
        for i in range(self.num_stage):
            stage = nn.Sequential(*[
                GatedCNNBlock(
                    dim=dims[i], norm_layer=norm_layer, act_layer=act_layer,
                    kernel_size=kernel_size, conv_ratio=conv_ratio,
                    drop_path=dp_rates[cur + j],
                ) for j in range(depths[i])
            ])
            self.stages.append(stage)
            cur += depths[i]

        self.norm = norm_layer(dims[-1])

        # 自适应池化 → 2304 维密集特征图 (576 × 2 × 2)
        self.adaptive_pool = nn.AdaptiveAvgPool2d((2, 2))

        self._init_weights()

    def _init_weights(self):
        for m in self.modules():
            if isinstance(m, (nn.Conv2d, nn.Linear)):
                _trunc_normal_(m.weight, std=.02)
                if m.bias is not None:
                    nn.init.constant_(m.bias, 0)

    def forward_features(self, x, return_spatial=False):
        """前向特征提取 — 无 GAP，保留空间结构"""
        stage2_feat = None  # [B, 384, 14, 14] — 更精细的空间特征
        for i in range(self.num_stage):
            x = self.downsample_layers[i](x)
            x = self.stages[i](x)
            # 捕获 stage 2 的输出 (14×14 分辨率)
            if return_spatial and i == 2:
                # x: [B, 14, 14, 384] — 倒数第二层，空间信息更丰富
                stage2_feat = x.permute(0, 3, 1, 2)    # [B, 384, 14, 14]

        # x: [B, 7, 7, 576]
        x = self.norm(x)                          # LayerNorm over last dim
        x = x.permute(0, 3, 1, 2)                # [B, 576, 7, 7]
        stage3_feat = x                           # 7x7 空间特征
        x = self.adaptive_pool(x)                 # [B, 576, 2, 2]
        x = x.reshape(x.size(0), -1)             # [B, 2304]
        if return_spatial:
            # stage3_feat: [B, 576, 7, 7]  (深层语义)
            # stage2_feat: [B, 384, 14, 14] (更精细的空间定位)
            return x, stage3_feat, stage2_feat
        return x

    def forward(self, x, return_spatial=False):
        return self.forward_features(x, return_spatial)


# ==============================================================================
# MambaOut Custom — 完整魔改模型
# ==============================================================================

class MambaOutCustom(nn.Module):
    """基于 MambaOut-Small 的域自适应 AIGC 伪造检测模型

    核心改动:
    - ❌ 移除 GAP → ✅ 保留 2304 维像素级伪影特征
    - ➕ 瓶颈层: 2304 → 256 (避免 MMD 维度灾难)
    - ➕ 双流输出: 256 维特征 (供 MMD 计算) + 2 分类 logits

    Args:
        num_classes: 分类类别数，AIGC 真伪检测 = 2
        bottleneck_dim: 瓶颈层输出维度，默认 256
        pretrained: 是否加载 MambaOut-Small 预训练权重
        drop_path_rate: Stochastic Depth 概率
    """

    PRETRAINED_URL = (
        'https://github.com/yuweihao/MambaOut/releases/download/model/'
        'mambaout_small.pth'
    )
    # 备选镜像 (hf-mirror.com，国内可访问)
    PRETRAINED_MIRROR_URL = (
        'https://huggingface.co/timm/mambaout_small.in1k/resolve/main/'
        'model.safetensors'
    )

    def __init__(self, num_classes=2, bottleneck_dim=256,
                 pretrained=False, pretrained_path=None, drop_path_rate=0.1):
        super().__init__()

        # --- MambaOut-Small 骨干 (depths=[3,4,27,3], dims=[96,192,384,576]) ---
        self.backbone = MambaOutBackbone(
            in_chans=3,
            depths=(3, 4, 27, 3),
            dims=(96, 192, 384, 576),
            conv_ratio=1.0,
            kernel_size=7,
            drop_path_rate=drop_path_rate,
        )

        # --- 瓶颈层: 2304 → 256 (避免 MMD 计算时的维度灾难) ---
        self.bottleneck = nn.Sequential(
            nn.Linear(2304, bottleneck_dim),    # 2304 = 576 × 2 × 2
            nn.BatchNorm1d(bottleneck_dim),
            nn.ReLU(inplace=True),
        )

        # --- 监督分类分支: 256 → 2 ---
        self.classifier = nn.Linear(bottleneck_dim, num_classes)

        # 初始化新增层
        self._init_new_layers()

        # 可选加载预训练权重
        if pretrained:
            self._load_pretrained(pretrained_path)

    def _init_new_layers(self):
        """对新增层进行权重初始化"""
        for m in [self.bottleneck, self.classifier]:
            if isinstance(m, nn.Sequential):
                for layer in m:
                    if isinstance(layer, nn.Linear):
                        _trunc_normal_(layer.weight, std=.02)
                        if layer.bias is not None:
                            nn.init.constant_(layer.bias, 0)
            elif isinstance(m, nn.Linear):
                _trunc_normal_(m.weight, std=.02)
                if m.bias is not None:
                    nn.init.constant_(m.bias, 0)

    def _remap_timm_to_backbone(self, state_dict):
        """将 timm/HuggingFace 格式的 key 映射到我们的 backbone 格式

        timm 格式:
            stem.conv1.* → stages.0.blocks.Y.* → stages.X.downsample.* → norm.* → head.*
        我们的 backbone 格式:
            downsample_layers.0.* → stages.0.Y.* → downsample_layers.X.* → norm.*
        """
        remapped = {}
        skipped = 0

        for k, v in state_dict.items():
            new_k = k

            # ---- 跳过与 backbone 无关的 key ----
            # head.fc*, head.pre_logits* — 分类头，跳过
            if k.startswith(('head.fc', 'head.pre_logits')):
                skipped += 1
                continue

            # head.norm.* → norm.* (timm 把 output_norm 放在 head 下)
            if k.startswith('head.norm.'):
                new_k = k.replace('head.norm.', 'norm.')
            # head.* — 其他 head 相关，跳过
            elif k.startswith('head.'):
                skipped += 1
                continue

            # stem.* → downsample_layers.0.*
            elif k.startswith('stem.'):
                new_k = k.replace('stem.', 'downsample_layers.0.')

            # stages.X.blocks.Y.* → stages.X.Y.*
            elif '.blocks.' in k:
                new_k = k.replace('.blocks.', '.')

            # stages.X.downsample.* → downsample_layers.X.*
            elif '.downsample.' in k:
                import re
                new_k = re.sub(r'stages\.(\d+)\.downsample\.', r'downsample_layers.\1.', k)

            remapped[new_k] = v

        return remapped, skipped

    def _load_pretrained(self, local_path=None):
        """加载 MambaOut-Small 预训练权重到 backbone

        加载优先级:
        1. local_path (用户手动下载的 .pth 文件)
        2. GitHub Release (PRETRAINED_URL)
        3. 失败则警告并继续训练

        自动检测两种 key 格式:
        - 原始 MambaOut: downsample_layers.*, stages.*.*, norm.*, head.*
        - timm/HuggingFace: stem.*, stages.X.blocks.Y.*, stages.X.downsample.*, norm.*, head.*
        """
        state_dict = None

        # 方式1: 从本地文件加载
        if local_path is not None:
            import os
            if os.path.exists(local_path):
                print(f"[Pretrained] 从本地文件加载: {local_path}")
                state_dict = torch.load(local_path, map_location='cpu',
                                        weights_only=True)
                if isinstance(state_dict, dict) and 'state_dict' in state_dict:
                    state_dict = state_dict['state_dict']
                elif isinstance(state_dict, dict) and 'model' in state_dict:
                    state_dict = state_dict['model']
            else:
                print(f"[Warning] 本地文件不存在: {local_path}，尝试在线下载...")

        # 方式2-3: 在线下载 (此处省略，用户已有本地文件)
        if state_dict is None:
            print(f"[Warning] 未找到预训练权重文件")
            print(f"[Hint] 请从以下地址下载 mambaout_small.pth:")
            print(f"       https://hf-mirror.com/timm/mambaout_small.in1k/resolve/main/pytorch_model.bin")
            print(f"       然后设置 pretrained_path='mambaout_small.pth'")
            return

        # ---- 自动检测格式并映射 ----
        sample_key = next(iter(state_dict.keys()))
        backbone_keys = set(self.backbone.state_dict().keys())

        # 检查是否直接兼容 (原始 MambaOut 格式)
        if sample_key in backbone_keys:
            # 格式兼容，直接过滤
            backbone_state = {}
            skipped = 0
            for k, v in state_dict.items():
                if k.startswith('head.'):
                    skipped += 1
                    continue
                if k in backbone_keys:
                    backbone_state[k] = v
                else:
                    skipped += 1
        else:
            # 需要映射 (timm/HuggingFace 格式)
            print(f"[Pretrained] 检测到 timm 格式权重，自动映射 key...")
            backbone_state, skipped = self._remap_timm_to_backbone(state_dict)

        # 加载
        missing, unexpected = self.backbone.load_state_dict(backbone_state, strict=False)

        loaded = len(backbone_state)
        print(f"[Pretrained] 加载完成:")
        print(f"  - 成功加载: {loaded} 个参数")
        print(f"  - 跳过:     {skipped} 个参数 (分类头等)")
        print(f"  - 缺失:     {len(missing)} 个参数 (随机初始化)")
        if len(missing) > 0:
            print(f"    缺失列表: {missing[:5]}...")
        if len(unexpected) > 0:
            print(f"  - 多余:     {len(unexpected)} 个参数")

    def forward_features(self, x):
        """提取 256 维瓶颈层特征（供 MMD 分布对齐使用）"""
        feat_2304 = self.backbone(x)           # [B, 2304]
        feat_256 = self.bottleneck(feat_2304)  # [B, 256]
        return feat_256

    def forward(self, x, return_features=False, return_spatial=False):
        """前向传播

        Args:
            x: 输入图像 [B, 3, 224, 224]
            return_features: 返回瓶颈层 256 维特征
            return_spatial:  返回多尺度空间特征（热力图用）

        Returns:
            若 return_spatial=True: (logits, feat_s3, feat_s2)
              feat_s3: [B, 576, 7, 7]   深层语义
              feat_s2: [B, 384, 14, 14]  精细空间定位
            若 return_features=True: (logits, features_256)
            否则: logits
        """
        if return_spatial:
            feat_2304, feat_s3, feat_s2 = self.backbone(x, return_spatial=True)
            feat_256 = self.bottleneck(feat_2304)
            logits = self.classifier(feat_256)
            return logits, feat_s3, feat_s2
        elif return_features:
            feat_256 = self.forward_features(x)
            logits = self.classifier(feat_256)
            return logits, feat_256
        else:
            feat_256 = self.forward_features(x)
            logits = self.classifier(feat_256)
            return logits


# ==============================================================================
# 工厂函数
# ==============================================================================

def mambaout_custom_small(pretrained=False, pretrained_path=None,
                         num_classes=2, bottleneck_dim=256, **kwargs):
    """创建 MambaOutCustom-Small 模型

    Args:
        pretrained: 是否加载预训练权重（在线下载）
        pretrained_path: 本地预训练权重路径（优先于在线下载）
        num_classes: 分类类别数
        bottleneck_dim: 瓶颈层维度
    """
    return MambaOutCustom(
        num_classes=num_classes,
        bottleneck_dim=bottleneck_dim,
        pretrained=pretrained,
        pretrained_path=pretrained_path,
        **kwargs
    )


if __name__ == '__main__':
    # 快速测试
    model = mambaout_custom_small(pretrained=False)
    x = torch.randn(4, 3, 224, 224)
    logits, features = model(x, return_features=True)
    print(f"Input shape:  {x.shape}")
    print(f"Logits shape: {logits.shape}")     # [4, 2]
    print(f"Features shape: {features.shape}")  # [4, 256]
    print(f"Total params: {sum(p.numel() for p in model.parameters()) / 1e6:.2f}M")
