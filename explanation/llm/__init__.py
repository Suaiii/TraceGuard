"""
LLM 模块 — 检测报告大语言模型研判

提供:
  - DeepSeekClient:  DeepSeek API 客户端
  - ReportAgent:     报告研判编排器
"""

from .client import DeepSeekClient
from .agent import ReportAgent

__all__ = [
    "DeepSeekClient",
    "ReportAgent",
]
