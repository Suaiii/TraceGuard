"""
RiskScorer — 多维度风险评分

综合检测置信度、热力图统计、篡改定位结果，
计算全局风险分数和局部区域风险分数。
"""

import numpy as np


class RiskScorer:
    """
    多维度风险评分器。

    风险维度:
      1. 检测置信度    (weight: 0.30) — fake_prob
      2. 伪影强度      (weight: 0.25) — 热力图 max/mean
      3. 篡改面积比    (weight: 0.25) — 可疑区域面积/总图像面积
      4. 篡改区域数量  (weight: 0.10) — 归一化区域个数
      5. 置信度一致性  (weight: 0.10) — 热力图高响应与掩膜重叠度

    风险等级:
      - low:    [0.00, 0.35)
      - medium: [0.35, 0.70)
      - high:   [0.70, 1.00]

    用法:
        scorer = RiskScorer()
        result = scorer.score(
            fake_prob=0.97,
            heatmap_2d=hm_array,
            image_size=(W, H),
            bbox_list=[...]
        )
    """

    RISK_LEVELS = [
        (0.00, 0.35, "low"),
        (0.35, 0.70, "medium"),
        (0.70, 1.00, "high"),
    ]

    def __init__(self, weights: dict = None):
        """
        Args:
            weights: 自定义权重字典
                - fake_prob_weight: float = 0.30
                - artifact_intensity_weight: float = 0.25
                - tamper_area_weight: float = 0.25
                - region_count_weight: float = 0.10
                - consistency_weight: float = 0.10
        """
        self.weights = {
            'fake_prob': weights.get('fake_prob_weight', 0.30) if weights else 0.30,
            'artifact_intensity': weights.get('artifact_intensity_weight', 0.25) if weights else 0.25,
            'tamper_area': weights.get('tamper_area_weight', 0.25) if weights else 0.25,
            'region_count': weights.get('region_count_weight', 0.10) if weights else 0.10,
            'consistency': weights.get('consistency_weight', 0.10) if weights else 0.10,
        }

    def score(self, fake_prob: float, heatmap_2d: np.ndarray = None,
              image_size: tuple = None, bbox_list: list = None,
              tamper_score_map: np.ndarray = None) -> dict:
        """
        计算综合风险分数。

        Args:
            fake_prob: 检测模块输出的伪造概率 (0~1)
            heatmap_2d: [H, W] 热力图分数阵 (可选)
            image_size: (W, H) 原图尺寸
            bbox_list: 篡改定位 bbox 列表 (可选)
            tamper_score_map: [H, W] 篡改可疑度图 (可选)

        Returns:
            dict:
                'global_score': float — 综合风险分 (0~1)
                'risk_level': str — low|medium|high
                'dimension_scores': dict — 各维度分数详情
                'local_scores': list — 逐 bbox 局部风险分
        """
        dims = {}
        bbox_list = bbox_list or []

        # 维度1: 检测置信度
        dims['fake_prob'] = fake_prob

        # 维度2: 伪影强度 (热力图统计量)
        if heatmap_2d is not None and heatmap_2d.size > 0:
            hm_max = float(np.max(heatmap_2d))
            hm_mean = float(np.mean(heatmap_2d))
            # 组合 max 和 mean: max 占 0.6, mean 占 0.4
            dims['artifact_intensity'] = 0.6 * hm_max + 0.4 * hm_mean
        else:
            dims['artifact_intensity'] = 0.0

        # 维度3: 篡改面积比
        if image_size and bbox_list:
            total_area = image_size[0] * image_size[1]
            tamper_area = sum(b['area'] for b in bbox_list)
            area_ratio = min(tamper_area / total_area, 1.0)
            dims['tamper_area'] = area_ratio
        else:
            dims['tamper_area'] = 0.0

        # 维度4: 篡改区域数量 (对数归一化, 5个以上→1.0)
        if bbox_list:
            n = len(bbox_list)
            import math
            dims['region_count'] = min(math.log2(n + 1) / math.log2(6), 1.0)
        else:
            dims['region_count'] = 0.0

        # 维度5: 置信度一致性 (热力图高分区域与掩膜的重叠)
        if heatmap_2d is not None and tamper_score_map is not None:
            hm_binary = heatmap_2d > np.percentile(heatmap_2d, 75)
            tm_binary = tamper_score_map > np.percentile(tamper_score_map, 75)
            if hm_binary.sum() > 0 and tm_binary.sum() > 0:
                overlap = (hm_binary & tm_binary).sum() / hm_binary.sum()
                dims['consistency'] = float(overlap)
            else:
                dims['consistency'] = 0.0
        else:
            dims['consistency'] = 0.0

        # 加权求和
        global_score = sum(
            dims[k] * self.weights[k]
            for k in self.weights
            if k in dims
        )

        # 限制在 [0, 1]
        global_score = max(0.0, min(1.0, global_score))

        # 风险等级
        risk_level = self._get_level(global_score)

        # 局部风险分数 — 基于 patch 级 fake_prob + 面积
        local_scores = []
        if bbox_list and image_size:
            total_area = image_size[0] * image_size[1]
            for bbox in bbox_list:
                area_frac = bbox['area'] / total_area
                patch_prob = bbox.get('patch_fake_prob', fake_prob)
                local_score = 0.5 * patch_prob + 0.5 * min(area_frac * 10, 1.0)
                local_scores.append(round(local_score, 4))

        return {
            'global_score': round(global_score, 4),
            'risk_level': risk_level,
            'dimension_scores': {k: round(v, 4) for k, v in dims.items()},
            'local_scores': local_scores,
        }

    def _get_level(self, score: float) -> str:
        for lo, hi, level in self.RISK_LEVELS:
            if lo <= score < hi or (hi == 1.0 and score <= hi):
                return level
        return "high"
