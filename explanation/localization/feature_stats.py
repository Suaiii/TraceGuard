"""
FeatureStatsAnalyzer — 基于多尺度空间特征的统计异常检测

利用 Stage2 (384ch × 14×14) 或 Stage3 (576ch × 7×7)
各通道在空间网格上的分布统计偏差作为辅助可疑度信号。
单次前向传播，速度极快。
"""

import numpy as np
from PIL import Image


class FeatureStatsAnalyzer:
    """
    基于中间层空间特征的统计异常检测。

    原理:
      正常区域各通道的空间分布趋于一致，被篡改/AIGC 区域
      可能在某些通道上表现出空间异质性。
      计算每个空间位置的通道统计偏差作为异常分数。

    新架构 (v2): 使用 stage2 14×14 (384ch) 特征，
    空间格点从 4 个提升到 196 个，定位精度大幅提高。

    用法:
        analyzer = FeatureStatsAnalyzer()
        score_map = analyzer.analyze(feat_s2, (14, 14), image_size)
    """

    def __init__(self, method: str = "variance",
                 smooth_sigma: float = 3.0):
        """
        Args:
            method: 统计量类型
              - "variance": 通道内空间方差 (默认)
              - "deviation": 与全局中位数的偏离
            smooth_sigma: 上采样后高斯平滑标准差
        """
        self.method = method
        self.smooth_sigma = smooth_sigma

    def analyze(self, spatial_features: np.ndarray,
                image_size: tuple) -> np.ndarray:
        """
        分析空间特征异常。

        Args:
            spatial_features: [C, H, W] 空间特征图
                stage2: [384, 14, 14], stage3: [576, 7, 7]
            image_size: (width, height) 原始图像尺寸

        Returns:
            np.ndarray [H, W] 异常分数图 (0~1)
        """
        C, H, W = spatial_features.shape

        if self.method == "variance":
            # 每个通道在空间上的方差 → [C]
            anomaly_per_channel = spatial_features.var(axis=(1, 2))  # [C]

        elif self.method == "deviation":
            # 每个通道的空间中位数偏离
            medians = np.median(spatial_features, axis=(1, 2), keepdims=True)  # [C, 1, 1]
            deviation = np.abs(spatial_features - medians)  # [C, H, W]
            anomaly_per_channel = deviation.sum(axis=(1, 2))  # [C]
        else:
            raise ValueError(f"Unknown method: {self.method}")

        # 归一化通道异常分数
        amax = anomaly_per_channel.max()
        if amax > 0:
            anomaly_per_channel = anomaly_per_channel / amax

        # 用通道异常分数加权特征 → H×W 空间异常图
        anomaly_map = np.zeros((H, W), dtype=np.float32)
        for c in range(C):
            anomaly_map += anomaly_per_channel[c] * np.abs(spatial_features[c])

        # 归一化
        amax = anomaly_map.max()
        if amax > 0:
            anomaly_map = anomaly_map / amax

        # 双线性插值上采样到原图尺寸
        anomaly_full = self._upsample(anomaly_map, image_size)

        # 高斯平滑
        if self.smooth_sigma > 0:
            anomaly_full = self._gaussian_smooth(anomaly_full)

        return anomaly_full

    @staticmethod
    def _upsample(arr_2d: np.ndarray, target_size: tuple) -> np.ndarray:
        """双线性上采样 H×W → 原图尺寸"""
        img = Image.fromarray((arr_2d * 255).astype(np.uint8))
        img = img.resize(target_size, Image.BILINEAR)
        return np.array(img).astype(np.float32) / 255.0

    @staticmethod
    def _gaussian_smooth(arr: np.ndarray, sigma: float = 3.0) -> np.ndarray:
        """高斯平滑"""
        from PIL import ImageFilter
        img = Image.fromarray((arr * 255).astype(np.uint8))
        smoothed = img.filter(ImageFilter.GaussianBlur(radius=sigma))
        return np.array(smoothed).astype(np.float32) / 255.0
