"""
ExplanationPipeline — 完整可解释分析流水线

Phase 3: HeatmapGenerator + TamperDetector + RiskScorer + TextExplainer
"""

import time
import numpy as np
from PIL import Image

from .heatmap import HeatmapGenerator
from .localization import TamperDetector
from .risk import RiskScorer
from .text import TextExplainer
from .utils import image_to_base64


class ExplanationPipeline:
    """
    可解释分析 + 篡改定位 + 风险评分 + 自然语言解释的完整流水线。

    Usage:
        from detection import Detector
        from explanation import ExplanationPipeline

        detector = Detector(checkpoint_path='checkpoints/best.pth')
        pipeline = ExplanationPipeline(detector)

        result = pipeline.run('input.jpg')
        print(result['explanation'])       # 自然语言解释文本
        print(result['risk_level'])        # low|medium|high
        print(result['risk_score'])        # 0.00~1.00
    """

    def __init__(self, detector, config: dict = None):
        config = config or {}
        self.detector = detector
        self.enable_localization = config.get('enable_localization', True)
        self.language = config.get('language', 'zh')

        # Heatmap (Grad-CAM from detector.get_heatmap())
        self.heatmap_generator = HeatmapGenerator(
            detector=detector,
            smooth_sigma=config.get('smooth_sigma', 3.0),
            overlay_alpha=config.get('overlay_alpha', 0.5),
        )

        # Localization
        self.tamper_detector = TamperDetector(
            detector=detector,
            config={
                'enable_patch': config.get('enable_patch', True),
                'enable_feature': config.get('enable_feature', True),
                'scales': config.get('localization_scales', [224, 160]),
                'stride_ratio': config.get('localization_stride_ratio', 0.5),
                'batch_size': config.get('localization_batch_size', 32),
                'threshold_method': config.get('threshold_method', 'percentile'),
                'threshold_percentile': config.get('threshold_percentile', 90),
                'min_region_area': config.get('min_region_area', 256),
                'nms_iou_threshold': config.get('nms_iou_threshold', 0.3),
                'open_radius': config.get('open_radius', 3),
                'close_radius': config.get('close_radius', 5),
            },
        )

        # Risk scoring
        self.risk_scorer = RiskScorer(
            weights=config.get('risk_weights', None),
        )

        # Text explanation
        self.text_explainer = TextExplainer(
            language=config.get('language', 'zh'),
            detail_level=config.get('detail_level', 'standard'),
        )

    def run(self, image_or_path) -> dict:
        """
        执行完整分析流水线。

        Returns:
            dict:
                # Base64 图像
                'overlay_b64':          str
                'mask_b64':             str
                'tamper_mask_b64':      str | None
                'tamper_overlay_b64':   str | None
                'bbox_image_b64':       str | None
                # 检测
                'label':                str
                'fake_prob':            float
                # 风险
                'risk_score':           float
                'risk_level':           str     (low|medium|high)
                'dimension_scores':     dict
                'bbox_list':            list    (含 local_risk_score)
                # 解释
                'explanation':          str
                'explanation_brief':    str
                # 元信息
                'elapsed_ms':           float
                'metadata':             dict
        """
        t0 = time.perf_counter()

        # --- 加载原图 ---
        img = self._load_image(image_or_path)

        # --- 检测判定 (张潇接口，权威来源) ---
        pred = self.detector.predict(image_or_path)
        label = pred['label']
        fake_prob = pred['fake_prob']
        upstream_risk = pred['risk_score']

        # --- Heatmap (Grad-CAM 可视化) ---
        hm_result = self.heatmap_generator.generate(image_or_path)
        heatmap_2d = hm_result['heatmap_2d']

        # --- Localization ---
        loc_result = None
        bbox_list = []
        tamper_score_map = None

        if self.enable_localization:
            loc_result = self.tamper_detector.detect(image_or_path)
            bbox_list = loc_result['bbox_list']
            tamper_score_map = loc_result['score_map']

            # --- 局部篡改分类 ---
            from .localization.tamper_classifier import classify_tamper
            tamper_type = classify_tamper(label, bbox_list)
        else:
            tamper_type = 'confirmed_real' if label == 'real' else 'full_aigc'

        # --- Risk Scoring ---
        risk_result = self.risk_scorer.score(
            fake_prob=fake_prob,
            heatmap_2d=heatmap_2d,
            image_size=img.size,
            bbox_list=bbox_list,
            tamper_score_map=tamper_score_map,
        )

        # 将局部风险分合并到 bbox_list
        for i, bbox in enumerate(bbox_list):
            if i < len(risk_result['local_scores']):
                bbox['risk_score'] = risk_result['local_scores'][i]

        # --- Text Explanation ---
        explanation = self.text_explainer.explain(
            label=label,
            fake_prob=fake_prob,
            risk_level=risk_result['risk_level'],
            risk_score=risk_result['global_score'],
            dimension_scores=risk_result['dimension_scores'],
            bbox_list=bbox_list,
            heatmap_stats={
                'max': float(heatmap_2d.max()) if heatmap_2d.size > 0 else 0,
                'mean': float(heatmap_2d.mean()) if heatmap_2d.size > 0 else 0,
            },
            tamper_type=tamper_type,
        )

        explanation_brief = self.text_explainer.explain_brief(
            label=label,
            fake_prob=fake_prob,
            risk_level=risk_result['risk_level'],
            bbox_count=len(bbox_list),
            tamper_type=tamper_type,
        )

        # --- 组装输出 ---
        elapsed = (time.perf_counter() - t0) * 1000

        output = {
            # Heatmap images
            'overlay_b64': image_to_base64(hm_result['overlay']),
            'mask_b64': image_to_base64(hm_result['mask']),
            # Detection
            'label': label,
            'fake_prob': fake_prob,
            'tamper_type': tamper_type,           # confirmed_real|local_tamper|full_aigc|full_aigc_hotspots
            # Risk
            'risk_score': risk_result['global_score'],
            'risk_level': risk_result['risk_level'],
            'dimension_scores': risk_result['dimension_scores'],
            # Localization
            'bbox_list': bbox_list,
            # Explanation
            'explanation': explanation,
            'explanation_brief': explanation_brief,
            # Meta
            'elapsed_ms': round(elapsed, 2),
            'metadata': {
                'heatmap_method': 'gradcam',
                'overlay_alpha': self.heatmap_generator.overlay_alpha,
                'localization_enabled': self.enable_localization,
                'language': self.language,
                'risk_weights': self.risk_scorer.weights,
                'detection_source': 'Detector.predict()',
                'upstream_risk_score': upstream_risk,
            },
        }

        # Localization images
        if loc_result:
            output['tamper_mask_b64'] = image_to_base64(loc_result['tamper_mask'].convert('RGB'))
            output['tamper_overlay_b64'] = image_to_base64(loc_result['tamper_mask_overlay'])
            output['bbox_image_b64'] = image_to_base64(loc_result['bbox_image'])
            output['localization_elapsed_ms'] = loc_result['elapsed_ms']
        else:
            output['tamper_mask_b64'] = None
            output['tamper_overlay_b64'] = None
            output['bbox_image_b64'] = None
            output['localization_elapsed_ms'] = 0

        return output

    def run_batch(self, image_list: list) -> list:
        return [self.run(img) for img in image_list]

    @staticmethod
    def _load_image(image_or_path) -> Image.Image:
        if isinstance(image_or_path, str):
            return Image.open(image_or_path).convert('RGB')
        elif isinstance(image_or_path, Image.Image):
            return image_or_path.convert('RGB')
        else:
            raise TypeError(f"需要 PIL.Image 或 文件路径")
