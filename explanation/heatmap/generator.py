"""
HeatmapGenerator — 可解释伪影热力图生成器

基于上游 Detector 的 Grad-CAM (stage2, 14×14) 热力图，
做高斯平滑 + colormap + 原图叠加。
"""

import numpy as np
from PIL import Image

from ..utils import (
    apply_colormap,
    overlay_heatmap,
    smooth_heatmap,
    image_to_base64,
)


class HeatmapGenerator:
    """
    可解释伪影热力图生成器。

    热力图由上游 Detector.get_heatmap() 通过 Grad-CAM 在 stage2
    (384ch × 14×14) 计算并上采样到原图尺寸，本模块负责后处理与可视化。

    Usage:
        from detection import Detector
        from explanation.heatmap import HeatmapGenerator

        detector = Detector(checkpoint_path='checkpoints/best.pth')
        generator = HeatmapGenerator(detector)

        result = generator.generate('test.jpg')
        # result['overlay']   — PIL.Image  原图叠加半透明热力层
        # result['mask']      — PIL.Image  纯热力掩膜 (蓝→红紫)
    """

    def __init__(self, detector,
                 smooth_sigma: float = 3.0,
                 overlay_alpha: float = 0.5):
        """
        Args:
            detector: Detector 实例 (来自 detection.inference_api)
            smooth_sigma: 高斯平滑标准差 (14×14 → 原图需要更大平滑)
            overlay_alpha: 叠加透明度
        """
        self.detector = detector
        self.smooth_sigma = smooth_sigma
        self.overlay_alpha = overlay_alpha

    def generate(self, image_or_path) -> dict:
        """
        生成热力图，返回 overlay 和 mask。

        Args:
            image_or_path: PIL.Image 或文件路径

        Returns:
            dict:
                'overlay':    PIL.Image — 原图叠加半透明热力层 (RGB)
                'mask':       PIL.Image — 纯热力掩膜 (RGBA, 蓝→红紫)
                'heatmap_2d': np.ndarray — 原始热力分数矩阵 [H, W]
                'fake_prob':  float — 检测伪造概率
        """
        # 1. 获取上游 Grad-CAM 热力图 (已上采样到原图尺寸, 0~1)
        data = self.detector.get_heatmap(image_or_path)

        heatmap_full = data['heatmap']          # [H, W] 0~1
        fake_prob = data['fake_prob']
        original_size = data['original_size']   # (W, H)

        # 2. 高斯平滑
        heatmap_full = smooth_heatmap(heatmap_full, sigma=self.smooth_sigma)

        # 3. 生成彩色热力图 (RGBA)
        heatmap_rgba = apply_colormap(heatmap_full)

        # 4. 加载原图并调整尺寸
        original_img = self._load_image(image_or_path)
        original_img = original_img.resize(original_size, Image.BILINEAR)

        # 5. 叠加图: 原图 + 半透明热力层
        overlay = overlay_heatmap(original_img, heatmap_rgba, alpha=self.overlay_alpha)

        # 6. 纯热力掩膜: 去除 alpha 通道 → RGB
        mask = heatmap_rgba.convert('RGB')

        return {
            'overlay': overlay,
            'mask': mask,
            'heatmap_2d': heatmap_full,
            'fake_prob': fake_prob,
            'label': data['label'],              # 直接使用张潇 Detector 的判定
        }

    def generate_base64(self, image_or_path) -> dict:
        """
        生成热力图并返回 base64 编码字符串（供前端/API 使用）。

        Returns:
            dict:
                'overlay_b64': str — 叠加图 base64 (PNG)
                'mask_b64':    str — 掩膜图 base64 (PNG)
                'fake_prob':   float
                'label':       str — 'real' | 'fake'
        """
        result = self.generate(image_or_path)
        return {
            'overlay_b64': image_to_base64(result['overlay']),
            'mask_b64': image_to_base64(result['mask']),
            'fake_prob': result['fake_prob'],
            'label': result['label'],            # 直接使用张潇 Detector 的判定
        }

    # ------------------------------------------------------------------
    # 内部工具
    # ------------------------------------------------------------------

    @staticmethod
    def _load_image(image_or_path) -> Image.Image:
        """加载图像，统一返回 PIL.Image (RGB)"""
        if isinstance(image_or_path, str):
            return Image.open(image_or_path).convert('RGB')
        elif isinstance(image_or_path, Image.Image):
            return image_or_path.convert('RGB')
        else:
            raise TypeError(f"image_or_path 必须是 PIL.Image 或 文件路径, 收到: {type(image_or_path)}")
