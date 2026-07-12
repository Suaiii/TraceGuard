"""
TraceGuard Explanation Module
可解释检测取证 + 篡改可疑区域定位 + 风险评分 + 自然语言解释

子模块:
  - heatmap:      可解释伪影热力图生成
  - localization: 篡改可疑区域定位
  - risk:         多维度风险评分
  - text:         自然语言解释生成
  - pipeline:     完整分析流水线
  - utils:        公共工具函数
"""

from .pipeline import ExplanationPipeline
from .heatmap import HeatmapGenerator
from .localization import TamperDetector
from .risk import RiskScorer
from .text import TextExplainer

__all__ = [
    'ExplanationPipeline',
    'HeatmapGenerator',
    'TamperDetector',
    'RiskScorer',
    'TextExplainer',
]
