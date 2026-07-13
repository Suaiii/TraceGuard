"""
Localization 子模块 — 篡改可疑区域定位 + 局部篡改分类
"""

from .detector import TamperDetector
from .tamper_classifier import classify_tamper, get_tamper_type_label

__all__ = ['TamperDetector', 'classify_tamper', 'get_tamper_type_label']
