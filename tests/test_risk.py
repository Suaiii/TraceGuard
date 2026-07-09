"""
风险评分测试 (无模型依赖)
"""

import pytest
import numpy as np

from explanation.risk.scorer import RiskScorer


class TestRiskScorer:

    @pytest.fixture
    def scorer(self):
        return RiskScorer()

    # ---- 全局分数 ----

    def test_risk_score_range(self, scorer, sample_heatmap_2d):
        """global_score 在 [0,1] 区间"""
        result = scorer.score(
            fake_prob=0.5,
            heatmap_2d=sample_heatmap_2d,
            image_size=(800, 600),
            bbox_list=[],
        )
        assert 0.0 <= result['global_score'] <= 1.0

    def test_risk_score_all_fake(self, scorer):
        """高伪造概率 + 多 bbox → 高分"""
        result = scorer.score(
            fake_prob=0.95,
            heatmap_2d=np.ones((64, 64), dtype=np.float32),
            image_size=(800, 600),
            bbox_list=[
                {'x': 0, 'y': 0, 'w': 400, 'h': 300, 'area': 120000},
            ],
        )
        assert result['global_score'] > 0.5

    def test_risk_score_all_real(self, scorer):
        """低伪造概率 + 空 bbox → 低分"""
        result = scorer.score(
            fake_prob=0.02,
            heatmap_2d=np.zeros((64, 64), dtype=np.float32),
            image_size=(800, 600),
            bbox_list=[],
        )
        assert result['global_score'] < 0.3

    # ---- 风险等级 ----

    @pytest.mark.parametrize('score,expected_level', [
        (0.00, 'low'),
        (0.10, 'low'),
        (0.34, 'low'),
        (0.35, 'medium'),
        (0.50, 'medium'),
        (0.69, 'medium'),
        (0.70, 'high'),
        (0.85, 'high'),
        (1.00, 'high'),
    ])
    def test_risk_level_boundaries(self, scorer, score, expected_level):
        """风险等级边界值测试"""
        level = scorer._get_level(score)
        assert level == expected_level, f"Score {score} should be {expected_level}, got {level}"

    # ---- 维度分数 ----

    def test_dimension_scores_keys(self, scorer, sample_heatmap_2d):
        """返回 5 维度全部 key"""
        result = scorer.score(
            fake_prob=0.5,
            heatmap_2d=sample_heatmap_2d,
            image_size=(800, 600),
            bbox_list=[],
        )
        expected_keys = {'fake_prob', 'artifact_intensity', 'tamper_area',
                         'region_count', 'consistency'}
        assert set(result['dimension_scores'].keys()) == expected_keys

    def test_weights_sum_to_one(self, scorer):
        """默认权重和为 1.0"""
        total = sum(scorer.weights.values())
        assert abs(total - 1.0) < 0.001, f"Weights sum to {total}"

    def test_local_scores_count(self, scorer, sample_bbox_list):
        """local_scores 数量 = bbox 数量"""
        result = scorer.score(
            fake_prob=0.5,
            image_size=(800, 600),
            bbox_list=sample_bbox_list,
        )
        assert len(result['local_scores']) == len(sample_bbox_list)

    # ---- 空输入处理 ----

    def test_zero_output_on_empty(self, scorer):
        """空输入时返回合理默认值"""
        result = scorer.score(fake_prob=0.0)
        assert result['global_score'] < 0.1
        assert result['risk_level'] == 'low'
        assert result['local_scores'] == []

    def test_no_heatmap_handled_gracefully(self, scorer):
        """无热力图时不报错"""
        result = scorer.score(fake_prob=0.5, image_size=(800, 600), bbox_list=[])
        assert 'global_score' in result

    # ---- 自定义权重 ----

    def test_custom_weights(self):
        """自定义权重生效"""
        scorer = RiskScorer(weights={
            'fake_prob_weight': 1.0,
            'artifact_intensity_weight': 0.0,
            'tamper_area_weight': 0.0,
            'region_count_weight': 0.0,
            'consistency_weight': 0.0,
        })
        result = scorer.score(fake_prob=0.8)
        assert abs(result['global_score'] - 0.8) < 0.01

    # ---- 局部风险分 ----

    def test_local_score_range(self, scorer, sample_bbox_list):
        """局部风险分在 [0,1] 区间"""
        result = scorer.score(
            fake_prob=0.5,
            image_size=(800, 600),
            bbox_list=sample_bbox_list,
        )
        for s in result['local_scores']:
            assert 0.0 <= s <= 1.0

    def test_large_bbox_higher_local_score(self, scorer):
        """大面积 bbox 局部风险分更高"""
        small = scorer.score(
            fake_prob=0.5, image_size=(1000, 1000),
            bbox_list=[{'x': 0, 'y': 0, 'w': 10, 'h': 10, 'area': 100}],
        )
        large = scorer.score(
            fake_prob=0.5, image_size=(1000, 1000),
            bbox_list=[{'x': 0, 'y': 0, 'w': 500, 'h': 500, 'area': 250000}],
        )
        assert large['local_scores'][0] > small['local_scores'][0]
