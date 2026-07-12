"""
MK-MMD Loss (Multi-Kernel Maximum Mean Discrepancy)

从 Transfer-Learning-Library (清华大学) dalib/adaptation/dan.py 中
提取高斯核计算代码，重写为 MKMMD_Loss 类。

使用 5 个不同带宽的高斯核（kernel_num=5）进行线性组合，
计算源域与目标域在再生核希尔伯特空间（RKHS）中的经验 MMD 距离。

Reference: Long et al., "Learning Transferable Features with Deep Adaptation Networks", ICML 2015.
"""

import torch
import torch.nn as nn
import numpy as np


class MKMMD_Loss(nn.Module):
    """
    Multi-Kernel Maximum Mean Discrepancy Loss

    使用多个不同带宽的高斯核进行线性组合，用于度量源域和目标域
    特征分布之间的差异。

    Args:
        kernel_num: 高斯核数量，默认5
        kernel_mul: 核带宽的倍增因子，默认2.0
        fix_sigma: 固定的sigma值，为None则自动计算
    """

    def __init__(self, kernel_num=5, kernel_mul=2.0, fix_sigma=None):
        super(MKMMD_Loss, self).__init__()
        self.kernel_num = kernel_num
        self.kernel_mul = kernel_mul
        self.fix_sigma = fix_sigma

    def _gaussian_kernel(self, source, target):
        """
        计算多核高斯核矩阵

        Args:
            source: 源域特征 [n_s, d]
            target: 目标域特征 [n_t, d]

        Returns:
            kernels: 多核高斯核矩阵 [n_s+n_t, n_s+n_t]
        """
        n_s = source.shape[0]
        n_t = target.shape[0]
        total = torch.cat([source, target], dim=0)  # [n_s+n_t, d]

        # 计算 L2 距离矩阵: ||x_i - x_j||^2
        total0 = total.unsqueeze(0).expand(total.size(0), total.size(0), total.size(1))
        total1 = total.unsqueeze(1).expand(total.size(0), total.size(0), total.size(1))
        L2_distance = ((total0 - total1) ** 2).sum(2)  # [n_s+n_t, n_s+n_t]

        # 自适应带宽计算（基于数据的 median pairwise distance）
        if self.fix_sigma is not None:
            bandwidth = self.fix_sigma
        else:
            # 使用所有样本对的平均距离作为基准带宽
            with torch.no_grad():
                n_total = n_s + n_t
                # 避免除零：只使用非对角线元素
                mask = ~torch.eye(n_total, dtype=torch.bool, device=L2_distance.device)
                bandwidth = L2_distance[mask].mean().item()
                # 防止带宽过小导致核值退化
                bandwidth = max(bandwidth, 1e-6)

        # 生成 5 个不同带宽: bandwidth * kernel_mul^(i - kernel_num//2)
        # 例如 kernel_num=5, kernel_mul=2.0: [0.25b, 0.5b, b, 2b, 4b]
        bandwidth /= self.kernel_mul ** (self.kernel_num // 2)
        bandwidth_list = [bandwidth * (self.kernel_mul ** i) for i in range(self.kernel_num)]

        # 对每个带宽计算高斯核，然后线性组合（等权求和）
        kernel_val = [torch.exp(-L2_distance / bw) for bw in bandwidth_list]
        return sum(kernel_val)  # [n_s+n_t, n_s+n_t]

    def _mmd(self, kernel_matrix, n_s, n_t):
        """
        从核矩阵计算经验 MMD^2 距离

        MMD^2 = E[k(x,x')] + E[k(y,y')] - 2*E[k(x,y)]

        Args:
            kernel_matrix: 核矩阵 [n_s+n_t, n_s+n_t]
            n_s: 源域样本数
            n_t: 目标域样本数

        Returns:
            mmd: MMD^2 值（标量）
        """
        # 提取子矩阵
        K_ss = kernel_matrix[:n_s, :n_s]      # 源域 x 源域
        K_tt = kernel_matrix[n_s:, n_s:]      # 目标域 x 目标域
        K_st = kernel_matrix[:n_s, n_s:]      # 源域 x 目标域

        # MMD^2 = E_s[k(x,x')] + E_t[k(y,y')] - 2*E_st[k(x,y)]
        # 使用 V-statistic (biased estimator)，与原始 DAN 论文一致
        # 比 U-statistic (unbiased) 更稳定，避免负值
        mmd_ss = K_ss.mean()       # 源域-源域
        mmd_tt = K_tt.mean()       # 目标域-目标域
        mmd_st = K_st.mean()       # 源域-目标域（跨域）

        mmd = mmd_ss + mmd_tt - 2 * mmd_st
        return mmd

    def forward(self, source_features, target_features):
        """
        前向传播：计算源域与目标域特征的 MK-MMD 距离

        Args:
            source_features: 源域特征 [batch_size, feature_dim]
            target_features: 目标域特征 [batch_size, feature_dim]

        Returns:
            mmd_loss: MK-MMD 损失值（标量张量，可反向传播）
        """
        n_s = source_features.shape[0]
        n_t = target_features.shape[0]

        # 计算多核高斯核矩阵
        kernel_matrix = self._gaussian_kernel(source_features, target_features)

        # 计算 MMD 距离
        mmd_loss = self._mmd(kernel_matrix, n_s, n_t)

        return mmd_loss


# 为兼容性保留别名
MMDLoss = MKMMD_Loss
