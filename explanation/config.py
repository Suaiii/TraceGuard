"""
TraceGuard 配置系统

统一管理所有可配置参数，支持 YAML 加载与默认值合并。

用法:
    from explanation.config import load_config, to_pipeline_config

    # 加载配置
    cfg = load_config('configs/default.yaml')

    # 转为 pipeline 兼容的 dict
    pipe_cfg = to_pipeline_config(cfg)
    pipeline = ExplanationPipeline(detector, config=pipe_cfg)
"""

import os
import copy
from dataclasses import dataclass, field, fields
from typing import Optional


# ==============================================================================
# 配置 Dataclass
# ==============================================================================

@dataclass
class DetectionConfig:
    checkpoint_path: str = "checkpoints/best.pth"
    device: str = "cuda"


@dataclass
class HeatmapConfig:
    method: str = "gradcam"
    overlay_alpha: float = 0.5
    smooth_sigma: float = 3.0


@dataclass
class LocalizationConfig:
    enable: bool = True
    enable_patch: bool = True
    enable_feature: bool = True
    patch_weight: float = 0.4
    feature_weight: float = 0.6
    scales: list = field(default_factory=lambda: [224, 160])
    stride_ratio: float = 0.5
    batch_size: int = 32
    max_dim: int = 500
    confidence_floor: float = 0.35
    threshold_method: str = "percentile"
    threshold_percentile: float = 90
    min_region_area: int = 256
    nms_iou_threshold: float = 0.3
    open_radius: int = 3
    close_radius: int = 5


@dataclass
class RiskWeights:
    fake_prob: float = 0.30
    artifact_intensity: float = 0.25
    tamper_area: float = 0.25
    region_count: float = 0.10
    consistency: float = 0.10


@dataclass
class RiskLevels:
    low: list = field(default_factory=lambda: [0.0, 0.35])
    medium: list = field(default_factory=lambda: [0.35, 0.70])
    high: list = field(default_factory=lambda: [0.70, 1.00])


@dataclass
class RiskConfig:
    weights: RiskWeights = field(default_factory=RiskWeights)
    levels: RiskLevels = field(default_factory=RiskLevels)


@dataclass
class TextConfig:
    language: str = "zh"
    detail_level: str = "standard"


@dataclass
class OutputConfig:
    save_images: bool = True
    format: str = "PNG"
    html_title: str = "TraceGuard 检测报告"


@dataclass
class TraceGuardConfig:
    """TraceGuard 全局配置"""
    detection: DetectionConfig = field(default_factory=DetectionConfig)
    heatmap: HeatmapConfig = field(default_factory=HeatmapConfig)
    localization: LocalizationConfig = field(default_factory=LocalizationConfig)
    risk: RiskConfig = field(default_factory=RiskConfig)
    text: TextConfig = field(default_factory=TextConfig)
    output: OutputConfig = field(default_factory=OutputConfig)

    @classmethod
    def defaults(cls) -> "TraceGuardConfig":
        """返回默认配置实例"""
        return cls()


# ==============================================================================
# YAML 加载
# ==============================================================================

def _deep_merge(base: dict, override: dict) -> dict:
    """递归合并字典，override 覆盖 base 中的值"""
    result = copy.deepcopy(base)
    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = value
    return result


def _dict_to_dataclass(cls, data: dict):
    """递归地将字典转换为 dataclass 实例"""
    if data is None:
        return cls()

    kwargs = {}
    for f in fields(cls):
        key = f.name
        if key in data:
            value = data[key]
            # 如果有嵌套 dataclass，递归转换
            if hasattr(f.type, '__dataclass_fields__') if isinstance(f.type, type) else False:
                try:
                    if isinstance(f.type, type) and hasattr(f.type, '__dataclass_fields__'):
                        kwargs[key] = _dict_to_dataclass(f.type, value)
                    else:
                        kwargs[key] = value
                except Exception:
                    kwargs[key] = value
            else:
                kwargs[key] = value
    return cls(**kwargs)


def load_config(yaml_path: str = None) -> TraceGuardConfig:
    """
    加载 YAML 配置文件，返回 Typed Config 对象。

    加载逻辑:
      1. 先取全部默认值
      2. 若 yaml_path 存在，读取并深度合并
      3. 返回 TraceGuardConfig 实例

    Args:
        yaml_path: YAML 配置文件路径，None 则使用默认值

    Returns:
        TraceGuardConfig
    """
    # 1. 默认配置
    cfg_data = {
        'detection': {'checkpoint_path': 'checkpoints/best.pth', 'device': 'cuda'},
        'heatmap': {'method': 'gradcam', 'overlay_alpha': 0.5, 'smooth_sigma': 3.0},
        'localization': {
            'enable': True, 'enable_patch': True, 'enable_feature': True,
            'patch_weight': 0.4, 'feature_weight': 0.6,
            'scales': [224, 160], 'stride_ratio': 0.5, 'batch_size': 32,
            'max_dim': 500, 'confidence_floor': 0.35,
            'threshold_method': 'percentile', 'threshold_percentile': 90,
            'min_region_area': 256, 'nms_iou_threshold': 0.3,
            'open_radius': 3, 'close_radius': 5,
        },
        'risk': {
            'weights': {
                'fake_prob': 0.30, 'artifact_intensity': 0.25,
                'tamper_area': 0.25, 'region_count': 0.10, 'consistency': 0.10,
            },
            'levels': {
                'low': [0.0, 0.35], 'medium': [0.35, 0.70], 'high': [0.70, 1.00],
            },
        },
        'text': {'language': 'zh', 'detail_level': 'standard'},
        'output': {'save_images': True, 'format': 'PNG', 'html_title': 'TraceGuard 检测报告'},
    }

    # 2. 读取 YAML 并合并
    if yaml_path and os.path.exists(yaml_path):
        import yaml
        with open(yaml_path, 'r', encoding='utf-8') as f:
            yaml_data = yaml.safe_load(f)
        if yaml_data:
            cfg_data = _deep_merge(cfg_data, yaml_data)

    # 3. 转换为 dataclass
    return _dict_to_dataclass(TraceGuardConfig, cfg_data)


# ==============================================================================
# 转换为 pipeline 兼容 dict (向后兼容)
# ==============================================================================

def to_pipeline_config(cfg: TraceGuardConfig) -> dict:
    """
    将 TraceGuardConfig 转为 ExplanationPipeline 接受的 dict 格式。

    保持与 pipeline.__init__ 中 config 参数完全兼容，
    无需修改 pipeline 内部代码。

    Args:
        cfg: TraceGuardConfig 实例

    Returns:
        dict — 可直接传给 ExplanationPipeline(config=...)
    """
    loc = cfg.localization
    risk = cfg.risk

    # 构建 risk_weights dict (兼容 RiskScorer 使用 .get() 方法)
    risk_weights = {
        'fake_prob_weight': risk.weights.fake_prob,
        'artifact_intensity_weight': risk.weights.artifact_intensity,
        'tamper_area_weight': risk.weights.tamper_area,
        'region_count_weight': risk.weights.region_count,
        'consistency_weight': risk.weights.consistency,
    }

    return {
        # Heatmap (Grad-CAM from detector)
        'smooth_sigma': cfg.heatmap.smooth_sigma,
        'overlay_alpha': cfg.heatmap.overlay_alpha,

        # Localization
        'enable_localization': loc.enable,
        'enable_patch': loc.enable_patch,
        'enable_feature': loc.enable_feature,
        'localization_scales': loc.scales,
        'localization_stride_ratio': loc.stride_ratio,
        'localization_batch_size': loc.batch_size,
        'threshold_method': loc.threshold_method,
        'threshold_percentile': loc.threshold_percentile,
        'min_region_area': loc.min_region_area,
        'nms_iou_threshold': loc.nms_iou_threshold,
        'open_radius': loc.open_radius,
        'close_radius': loc.close_radius,

        # Risk
        'risk_weights': risk_weights,

        # Text
        'language': cfg.text.language,
        'detail_level': cfg.text.detail_level,
    }


# ==============================================================================
# CLI/server 快捷函数
# ==============================================================================

def load_and_convert(yaml_path: str = None) -> dict:
    """便捷函数: 加载 YAML → 返回 pipeline dict"""
    cfg = load_config(yaml_path)
    return to_pipeline_config(cfg)


# 测试
if __name__ == '__main__':
    import json

    # 默认配置
    cfg = load_config()
    print("=== 默认配置 (dataclass) ===")
    print(f"  device:          {cfg.detection.device}")
    print(f"  heatmap method:  {cfg.heatmap.method}")
    print(f"  localization:    {cfg.localization.enable}")
    print(f"  risk weights:    {cfg.risk.weights}")
    print(f"  language:        {cfg.text.language}")

    # 转为 pipeline dict
    pipe_cfg = to_pipeline_config(cfg)
    print("\n=== Pipeline config dict ===")
    print(json.dumps(pipe_cfg, indent=2, ensure_ascii=False, default=str))

    # 尝试加载 YAML 文件
    if os.path.exists('configs/default.yaml'):
        cfg2 = load_config('configs/default.yaml')
        assert cfg2.detection.device == 'cuda'
        assert cfg2.heatmap.overlay_alpha == 0.5
        print("\n✅ YAML 加载测试通过")
