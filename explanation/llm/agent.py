"""
ReportAgent — 检测报告 LLM 研判编排器

接收 pipeline 检测结果，提取结构化摘要，调用 DeepSeek 生成研判文字，
解析返回文本为结构化 dict。
"""

import json
import logging
import time

from .client import DeepSeekClient
from .prompts import (
    SYSTEM_PROMPT,
    SINGLE_REPORT_PROMPT,
    BATCH_REPORT_PROMPT,
    FALLBACK_SINGLE_OPINION,
    FALLBACK_BATCH_OVERVIEW,
)

logger = logging.getLogger(__name__)


class ReportAgent:
    """
    报告研判 Agent — 与检测 pipeline 解耦的独立服务。

    Usage:
        client = DeepSeekClient(api_key="sk-xxx")
        agent = ReportAgent(client)
        opinion = agent.analyze_single(pipeline_result)
        # opinion = {'opinion': '...', 'dimension_notes': '...', 'region_notes': '...'}
    """

    def __init__(self, client: DeepSeekClient = None):
        self.client = client

    # ------------------------------------------------------------------
    # 公开接口
    # ------------------------------------------------------------------

    def analyze_single(self, result: dict) -> dict:
        """
        对单张图像检测结果生成 LLM 研判。

        Args:
            result: pipeline.run() 输出 dict (完整，含 base64 图片)

        Returns:
            dict: {
                'opinion': str,           # 综合研判意见
                'dimension_notes': str,    # 各维度解读
                'region_notes': str,       # 可疑区域分布解读
                'llm_generated': bool,     # 是否真正调用了 LLM
                'elapsed_ms': float,       # LLM 调用耗时
            }
        """
        if self.client is None or not self.client.is_configured:
            return self._fallback_single()

        try:
            prompt = self._build_single_prompt(result)
            t0 = time.perf_counter()
            reply = self.client.chat([
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ])
            elapsed = (time.perf_counter() - t0) * 1000
            parsed = self._parse_single_reply(reply)
            parsed['llm_generated'] = True
            parsed['elapsed_ms'] = round(elapsed, 2)
            return parsed
        except Exception as exc:
            logger.warning(f"LLM analyze_single failed, using fallback: {exc}")
            fallback = self._fallback_single()
            fallback['llm_generated'] = False
            fallback['elapsed_ms'] = 0
            return fallback

    def analyze_batch(self, results: list) -> dict:
        """
        对批量检测结果生成 LLM 研判。

        Args:
            results: pipeline.run() 输出 dict 列表

        Returns:
            dict: {
                'overview': str,           # 批次整体评估
                'priority_list': str,      # 高风险优先级排序
                'llm_generated': bool,
                'elapsed_ms': float,
            }
        """
        if self.client is None or not self.client.is_configured:
            return self._fallback_batch()

        try:
            prompt = self._build_batch_prompt(results)
            t0 = time.perf_counter()
            reply = self.client.chat([
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ])
            elapsed = (time.perf_counter() - t0) * 1000
            parsed = self._parse_batch_reply(reply)
            parsed['llm_generated'] = True
            parsed['elapsed_ms'] = round(elapsed, 2)
            return parsed
        except Exception as exc:
            logger.warning(f"LLM analyze_batch failed, using fallback: {exc}")
            fallback = self._fallback_batch()
            fallback['llm_generated'] = False
            fallback['elapsed_ms'] = 0
            return fallback

    # ------------------------------------------------------------------
    # Prompt 构建
    # ------------------------------------------------------------------

    def _build_single_prompt(self, result: dict) -> str:
        """从 pipeline 输出提取结构化摘要 JSON"""
        summary = {
            "label": result.get("label", "unknown"),
            "tamper_type": result.get("tamper_type", "unavailable"),
            "fake_prob": round(result.get("fake_prob", 0), 4),
            "risk_score": round(result.get("risk_score", 0), 4),
            "risk_level": result.get("risk_level", "unknown"),
            "explanation_brief": result.get("explanation_brief", ""),
            "explanation": result.get("explanation", ""),
            "dimension_scores": result.get("dimension_scores", {}),
            "bbox_list": self._summarize_bbox_list(result.get("bbox_list", [])),
            "elapsed_ms": result.get("elapsed_ms", 0),
            "metadata": {
                "heatmap_method": result.get("metadata", {}).get("heatmap_method", "gradcam"),
                "localization_enabled": result.get("metadata", {}).get("localization_enabled", False),
                "risk_weights": result.get("metadata", {}).get("risk_weights", {}),
            },
        }

        # 超监管标记
        is_super_oversight = (
            summary["label"] == "fake"
            and summary["fake_prob"] >= 0.9
            and summary["risk_level"] == "high"
        )
        summary["super_oversight"] = is_super_oversight

        return SINGLE_REPORT_PROMPT.format(
            result_json=json.dumps(summary, ensure_ascii=False, indent=2)
        )

    def _build_batch_prompt(self, results: list) -> str:
        """提取批次统计 + 高风险条目摘要"""
        total = len(results)
        fake_count = sum(1 for r in results if r.get("label") == "fake")
        real_count = total - fake_count
        tamper_count = sum(1 for r in results if r.get("tamper_type") == "local_tamper")
        high_risk = sum(1 for r in results if r.get("risk_level") == "high")
        medium_risk = sum(1 for r in results if r.get("risk_level") == "medium")
        low_risk = sum(1 for r in results if r.get("risk_level") == "low")
        super_oversight_count = sum(
            1 for r in results
            if r.get("label") == "fake"
            and r.get("fake_prob", 0) >= 0.9
            and r.get("risk_level") == "high"
        )

        stats = {
            "total": total,
            "fake_count": fake_count,
            "real_count": real_count,
            "local_tamper_count": tamper_count,
            "high_risk_count": high_risk,
            "medium_risk_count": medium_risk,
            "low_risk_count": low_risk,
            "super_oversight_count": super_oversight_count,
            "avg_fake_prob": round(
                sum(r.get("fake_prob", 0) for r in results) / max(total, 1), 4
            ),
            "avg_risk_score": round(
                sum(r.get("risk_score", 0) for r in results) / max(total, 1), 4
            ),
        }

        # 高风险条目摘要 (最多 10 条)
        high_risk_items = []
        for i, r in enumerate(results):
            if r.get("risk_level") == "high":
                high_risk_items.append({
                    "index": i + 1,
                    "label": r.get("label"),
                    "tamper_type": r.get("tamper_type"),
                    "fake_prob": round(r.get("fake_prob", 0), 4),
                    "risk_score": round(r.get("risk_score", 0), 4),
                    "risk_level": r.get("risk_level"),
                    "bbox_count": len(r.get("bbox_list", [])),
                    "explanation_brief": r.get("explanation_brief", ""),
                    "super_oversight": (
                        r.get("label") == "fake"
                        and r.get("fake_prob", 0) >= 0.9
                    ),
                })
        high_risk_items.sort(key=lambda x: x["risk_score"], reverse=True)
        high_risk_items = high_risk_items[:10]

        return BATCH_REPORT_PROMPT.format(
            batch_stats_json=json.dumps(stats, ensure_ascii=False, indent=2),
            high_risk_summary=json.dumps(high_risk_items, ensure_ascii=False, indent=2),
        )

    # ------------------------------------------------------------------
    # 回复解析
    # ------------------------------------------------------------------

    @staticmethod
    def _parse_single_reply(reply: str) -> dict:
        """将 DS 回复解析为 {opinion, dimension_notes, region_notes}"""
        sections = {
            "opinion": "",
            "dimension_notes": "",
            "region_notes": "",
        }

        current_key = None
        for line in reply.split("\n"):
            line_stripped = line.strip()
            if "[综合研判意见]" in line_stripped:
                current_key = "opinion"
                continue
            elif "[维度解读]" in line_stripped:
                current_key = "dimension_notes"
                continue
            elif "[区域解读]" in line_stripped:
                current_key = "region_notes"
                continue

            if current_key and line_stripped:
                sections[current_key] += line_stripped + "\n"

        # 清理尾部空白
        for key in sections:
            sections[key] = sections[key].strip()

        return sections

    @staticmethod
    def _parse_batch_reply(reply: str) -> dict:
        """将 DS 回复解析为 {overview, priority_list, review_suggestions}"""
        sections = {
            "overview": "",
            "priority_list": "",
            "review_suggestions": {},
        }

        current_key = None
        for line in reply.split("\n"):
            line_stripped = line.strip()
            if "[批次整体评估]" in line_stripped:
                current_key = "overview"
                continue
            elif "[高风险优先级排序]" in line_stripped:
                current_key = "priority_list"
                continue
            elif "[逐图复核建议]" in line_stripped:
                current_key = "review_suggestions"
                continue

            if current_key == "review_suggestions":
                # 解析 "#N: suggestion text" 格式
                if line_stripped.startswith("#") and ":" in line_stripped:
                    idx_str, suggestion = line_stripped.split(":", 1)
                    try:
                        idx = int(idx_str.strip("#").strip())
                        sections["review_suggestions"][str(idx)] = suggestion.strip()
                    except ValueError:
                        pass
            elif current_key and line_stripped:
                sections[current_key] += line_stripped + "\n"

        for key in ("overview", "priority_list"):
            sections[key] = sections[key].strip()

        return sections

    # ------------------------------------------------------------------
    # Fallback
    # ------------------------------------------------------------------

    @staticmethod
    def _fallback_single() -> dict:
        return {
            "opinion": FALLBACK_SINGLE_OPINION,
            "dimension_notes": "",
            "region_notes": "",
            "llm_generated": False,
            "elapsed_ms": 0,
        }

    @staticmethod
    def _fallback_batch() -> dict:
        return {
            "overview": FALLBACK_BATCH_OVERVIEW,
            "priority_list": "",
            "review_suggestions": {},
            "llm_generated": False,
            "elapsed_ms": 0,
        }

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _summarize_bbox_list(bbox_list: list) -> list:
        """精简 bbox 信息，去掉冗余字段"""
        return [
            {
                "index": i + 1,
                "x": b.get("x", 0),
                "y": b.get("y", 0),
                "w": b.get("w", 0),
                "h": b.get("h", 0),
                "area": b.get("area", b.get("w", 0) * b.get("h", 0)),
                "local_risk_score": round(b.get("risk_score", 0), 4),
            }
            for i, b in enumerate(bbox_list)
        ]
