"""
TamperDetector — 篡改可疑区域定位器

混合策略:
  1. Patch-based 滑动窗口检测 (主) → 高分辨率可疑度图
  2. 特征统计异常检测 (辅) → 粗粒度异常信号
  3. 加权融合 + 后处理 → 二值掩膜 + bbox 列表
"""

import time
import numpy as np
from PIL import Image

from .patch_analyzer import PatchAnalyzer
from .feature_stats import FeatureStatsAnalyzer
from .postprocess import (
    threshold_otsu,
    threshold_percentile,
    morphological_clean,
    extract_bboxes,
    nms_bboxes,
    mask_to_image,
    overlay_mask_on_image,
    draw_bboxes_on_image,
)

from ..utils import image_to_base64


class TamperDetector:
    """
    篡改可疑区域定位器。

    Usage:
        from detection import Detector
        from explanation.localization import TamperDetector

        detector = Detector(checkpoint_path='checkpoints/best.pth')
        localizer = TamperDetector(detector)

        result = localizer.detect('test.jpg')
        # result['tamper_mask']   → PIL.Image  篡改掩膜 (RGBA)
        # result['bbox_list']     → list[dict] 可疑区域坐标
        # result['score_map']     → np.ndarray 原始可疑度图
    """

    def __init__(self, detector, config: dict = None):
        """
        Args:
            detector: Detector 实例
            config: 可选配置
              - enable_patch: bool = True      启用 patch 滑动窗口
              - enable_feature: bool = True    启用特征统计辅助
              - patch_weight: float = 0.7      patch 方法权重
              - feature_weight: float = 0.3    特征方法权重
              - scales: list = [224, 160, 112] 滑动窗口尺寸
              - stride_ratio: float = 0.25     滑动步长比例
              - threshold_method: str = "otsu" 阈值方法 (otsu|percentile)
              - threshold_percentile: float    百分位阈值 (默认75)
              - min_region_area: int = 64      最小可疑区域面积
              - nms_iou_threshold: float = 0.3 NMS IoU 阈值
              - open_radius: int = 3           开运算半径
              - close_radius: int = 5          闭运算半径
        """
        config = config or {}
        self.detector = detector

        self.enable_patch = config.get('enable_patch', True)
        self.enable_feature = config.get('enable_feature', True)
        self.patch_weight = config.get('patch_weight', 0.4)
        self.feature_weight = config.get('feature_weight', 0.6)
        self.threshold_method = config.get('threshold_method', 'percentile')
        self.threshold_percentile = config.get('threshold_percentile', 90)
        self.min_region_area = config.get('min_region_area', 256)
        self.nms_iou_threshold = config.get('nms_iou_threshold', 0.3)
        self.open_radius = config.get('open_radius', 3)
        self.close_radius = config.get('close_radius', 5)

        # 初始化子分析器
        self.patch_analyzer = PatchAnalyzer(
            detector=detector,
            scales=config.get('scales', [224, 160, 112]),
            stride_ratio=config.get('stride_ratio', 0.25),
            batch_size=config.get('batch_size', 16),
        )
        self.feature_analyzer = FeatureStatsAnalyzer(
            method=config.get('feature_method', 'variance'),
        )

    def detect(self, image_or_path) -> dict:
        """
        执行篡改区域定位。

        Args:
            image_or_path: PIL.Image 或文件路径

        Returns:
            dict:
                'tamper_mask':   PIL.Image — RGBA 篡改掩膜 (红=可疑)
                'tamper_mask_overlay': PIL.Image — 原图+掩膜叠加
                'bbox_image':    PIL.Image — 原图+bbox 标注
                'bbox_list':     list[dict] — 可疑区域坐标
                'score_map':     np.ndarray — 融合后可疑度图 (调试用)
                'elapsed_ms':    float — 定位耗时
        """
        t0 = time.perf_counter()
        img = self._load_image(image_or_path)
        w, h = img.size

        # --- 1. Patch 滑动窗口分析 (主) ---
        patch_score = None
        if self.enable_patch:
            patch_score = self.patch_analyzer.analyze(img)

        # --- 2. 特征统计异常检测 (辅) ---
        feature_score = None
        if self.enable_feature:
            spatial = self.detector.get_spatial_features(img)
            feat_s2 = spatial['feat_s2']  # [384, 14, 14] — stage2 fine spatial
            feature_score = self.feature_analyzer.analyze(feat_s2, (w, h))

        # --- 3. 加权融合 ---
        if patch_score is not None and feature_score is not None:
            score_map = (self.patch_weight * patch_score +
                         self.feature_weight * feature_score)
        elif patch_score is not None:
            score_map = patch_score
        elif feature_score is not None:
            score_map = feature_score
        else:
            score_map = np.zeros((h, w), dtype=np.float32)

        # 归一化
        smax = score_map.max()
        if smax > 0:
            score_map = score_map / smax

        # --- 4. 阈值二值化 ---
        if self.threshold_method == 'otsu':
            binary_mask = threshold_otsu(score_map)
        else:
            binary_mask = threshold_percentile(score_map, self.threshold_percentile)

        # --- 5. 形态学后处理 ---
        binary_mask = morphological_clean(
            binary_mask,
            open_radius=self.open_radius,
            close_radius=self.close_radius,
        )

        # --- 6. 提取 bbox ---
        bboxes = extract_bboxes(binary_mask, min_area=self.min_region_area)

        # --- 7. NMS 去重 ---
        bboxes = nms_bboxes(bboxes, iou_threshold=self.nms_iou_threshold)

        # --- 7.5 为每个 bbox 计算 patch 级 fake_prob ---
        # 使用 confidence_floor 过滤前的原始 patch_score，保留真实模型输出
        raw_patch = None
        if self.enable_patch and hasattr(self.patch_analyzer, '_raw_score_map'):
            raw_patch = self.patch_analyzer._raw_score_map

        if raw_patch is not None:
            for bbox in bboxes:
                x, y, bw, bh = bbox['x'], bbox['y'], bbox['w'], bbox['h']
                y2, x2 = min(y + bh, h), min(x + bw, w)
                region = raw_patch[y:y2, x:x2]
                bbox['patch_fake_prob'] = round(float(region.mean()), 4) if region.size > 0 else 0.0
        else:
            for bbox in bboxes:
                bbox['patch_fake_prob'] = 0.0

        # --- 8. 生成输出图像 ---
        tamper_mask = mask_to_image(binary_mask)

        # 掩膜叠加到原图
        tamper_overlay = overlay_mask_on_image(img, tamper_mask, alpha=0.4)

        # bbox 标注图
        bbox_image = draw_bboxes_on_image(img, bboxes, color=(255, 40, 40), width=3)

        elapsed = (time.perf_counter() - t0) * 1000

        return {
            'tamper_mask': tamper_mask,
            'tamper_mask_overlay': tamper_overlay,
            'bbox_image': bbox_image,
            'bbox_list': bboxes,
            'score_map': score_map,
            'elapsed_ms': elapsed,
        }

    def detect_base64(self, image_or_path) -> dict:
        """
        执行定位并返回 base64 编码结果。

        Returns:
            dict: 含 tamper_mask_b64, tamper_overlay_b64, bbox_image_b64, bbox_list
        """
        result = self.detect(image_or_path)
        return {
            'tamper_mask_b64': image_to_base64(result['tamper_mask'].convert('RGB')),
            'tamper_overlay_b64': image_to_base64(result['tamper_mask_overlay']),
            'bbox_image_b64': image_to_base64(result['bbox_image']),
            'bbox_list': result['bbox_list'],
            'elapsed_ms': result['elapsed_ms'],
        }

    @staticmethod
    def _load_image(image_or_path) -> Image.Image:
        if isinstance(image_or_path, str):
            return Image.open(image_or_path).convert('RGB')
        elif isinstance(image_or_path, Image.Image):
            return image_or_path.convert('RGB')
        else:
            raise TypeError(f"需要 PIL.Image 或 文件路径, 收到: {type(image_or_path)}")
