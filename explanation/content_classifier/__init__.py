"""
Content classifier — zero-shot image content classification using CLIP.

Provides:
  ContentClassifier — lightweight MobileCLIP2-S0 zero-shot classifier
  for super-oversight domain detection (warfare, terrorism, firearms, etc.)
"""

from .classifier import ContentClassifier

__all__ = ["ContentClassifier"]
