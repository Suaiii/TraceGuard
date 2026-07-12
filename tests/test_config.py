"""
配置系统测试 (无模型依赖)
"""

import os
import pytest

from explanation.config import (
    load_config, to_pipeline_config, load_and_convert,
    TraceGuardConfig, DetectionConfig, HeatmapConfig,
)


class TestConfigLoading:

    def test_load_default_config(self):
        """默认配置加载不报错"""
        cfg = load_config()
        assert isinstance(cfg, TraceGuardConfig)
        assert cfg.detection.device == 'cuda'
        assert cfg.heatmap.overlay_alpha == 0.5

    def test_load_yaml_config(self):
        """YAML 文件加载"""
        cfg = load_config('configs/default.yaml')
        assert isinstance(cfg, TraceGuardConfig)
        assert cfg.localization.scales == [224, 160]
        assert cfg.risk.weights.fake_prob == 0.30

    def test_nonexistent_config_uses_defaults(self):
        """不存在的配置文件回退默认值"""
        cfg = load_config('configs/nonexistent.yaml')
        assert cfg.heatmap.overlay_alpha == 0.5

    def test_config_defaults_classmethod(self):
        """类方法 defaults() 返回默认配置"""
        cfg = TraceGuardConfig.defaults()
        assert cfg.detection.checkpoint_path == 'checkpoints/best.pth'


class TestPipelineConfigConversion:

    def test_to_pipeline_config_keys(self):
        """转换 dict 包含所有必要 key"""
        cfg = load_config()
        pipe_cfg = to_pipeline_config(cfg)
        required_keys = [
            'overlay_alpha', 'smooth_sigma',
            'enable_localization', 'localization_scales',
            'language', 'detail_level', 'risk_weights',
        ]
        for key in required_keys:
            assert key in pipe_cfg, f"Missing key: {key}"

    def test_load_and_convert(self):
        """load_and_convert 快捷函数"""
        pipe_cfg = load_and_convert()
        assert isinstance(pipe_cfg, dict)
        assert pipe_cfg['enable_localization'] is True
        assert isinstance(pipe_cfg, dict)

    def test_load_and_convert_with_path(self):
        """带路径的 load_and_convert"""
        pipe_cfg = load_and_convert('configs/default.yaml')
        assert isinstance(pipe_cfg, dict)
        assert pipe_cfg['language'] == 'zh'

    def test_overlay_alpha_passthrough(self):
        """配置中的 overlay_alpha 正确传递"""
        cfg = load_config()
        cfg.heatmap.overlay_alpha = 0.75
        pipe_cfg = to_pipeline_config(cfg)
        assert pipe_cfg['overlay_alpha'] == 0.75

    def test_localization_disabled(self):
        """localization.enable=False 正确传递"""
        cfg = load_config()
        cfg.localization.enable = False
        pipe_cfg = to_pipeline_config(cfg)
        assert pipe_cfg['enable_localization'] is False


class TestRiskWeightsConversion:

    def test_weights_format_compatible(self):
        """权重格式兼容 RiskScorer"""
        cfg = load_config()
        pipe_cfg = to_pipeline_config(cfg)
        weights = pipe_cfg['risk_weights']
        # RiskScorer 使用 .get(key, default) 访问
        assert 'fake_prob_weight' in weights
        assert 'artifact_intensity_weight' in weights
        assert weights.get('fake_prob_weight', 0) == 0.30


class TestConfigEdgeCases:

    def test_empty_config_uses_defaults(self):
        """空路径使用默认值"""
        cfg = load_config(None)
        assert cfg is not None

    def test_all_subconfigs_exist(self):
        """所有子配置对象存在"""
        cfg = load_config()
        assert isinstance(cfg.detection, DetectionConfig)
        assert isinstance(cfg.heatmap, HeatmapConfig)
