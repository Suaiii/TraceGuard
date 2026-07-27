"""报告导出（LLM 研判 + HTML 渲染）契约测试。

覆盖 feature/report-export 引入但此前无任何测试的路径：
  - ReportAgent 在无 client / 空回复 / 调用异常时的降级行为
  - ReportAgent 对正常回复的三段解析
  - ReportGenerator 在有/无 llm_opinion 两种情况下都能产出完整 HTML

说明：`/api/v1/report/preview` 与 `/report/pdf` 两个端点的装配逻辑（_get_llm_agent、
_html_to_pdf）是 create_app() 内的闭包，而 create_app() 会无条件加载 545MB 权重，
无法在单元测试中低成本触达；故此处覆盖其调用的全部业务对象，端点本身依赖手工
联调（见 DEVLOG 2026-07-27 实测记录）。
"""

import pytest

from explanation.llm.agent import ReportAgent
from explanation.visualization import ReportGenerator


class StubClient:
    """可配置回复的假 LLM 客户端，避免测试触网。"""

    def __init__(self, reply="", raises=None, configured=True):
        self._reply = reply
        self._raises = raises
        self._configured = configured
        self.calls = 0

    @property
    def is_configured(self):
        return self._configured

    def chat(self, messages, temperature=None, max_tokens=None):
        self.calls += 1
        if self._raises is not None:
            raise self._raises
        return self._reply


WELL_FORMED_REPLY = """[综合研判意见]
该图像被判定为 AIGC 全图生成，置信度较高，建议人工复核。

[维度解读]
- 检测置信度：分数偏高，模型判断明确。

[区域解读]
共 2 处可疑区域，面积较小且分布分散。"""


# ---------------------------------------------------------------- 降级路径


def test_single_without_client_uses_fallback(sample_pipeline_result):
    """无 client（未配置 API Key）时给出降级研判段，而非空内容。"""
    result = ReportAgent(None).analyze_single(sample_pipeline_result)

    assert result["llm_generated"] is False
    assert "综合研判意见" in result["opinion"]
    assert result["opinion"].strip()


def test_single_empty_reply_falls_back(sample_pipeline_result):
    """接口返回空 content 时必须降级，不能标记为 LLM 生成。

    推理型模型在 max_tokens 不足时会把预算耗在 reasoning token 上，
    返回 content='' 而不报错；若此时仍标记 llm_generated=True，
    报告会渲染出空研判段却声称由 LLM 生成。
    """
    client = StubClient(reply="")
    result = ReportAgent(client).analyze_single(sample_pipeline_result)

    assert client.calls == 1, "应当真的调用过接口"
    assert result["llm_generated"] is False
    assert "综合研判意见" in result["opinion"]


@pytest.mark.parametrize("blank", ["", "   ", "\n\n", None])
def test_single_blank_variants_all_fall_back(sample_pipeline_result, blank):
    result = ReportAgent(StubClient(reply=blank)).analyze_single(sample_pipeline_result)
    assert result["llm_generated"] is False


def test_single_api_error_falls_back(sample_pipeline_result):
    """接口抛异常时降级，且不向上传播。"""
    client = StubClient(raises=RuntimeError("boom"))
    result = ReportAgent(client).analyze_single(sample_pipeline_result)

    assert result["llm_generated"] is False
    assert result["elapsed_ms"] == 0


def test_batch_empty_reply_falls_back(sample_batch_results):
    result = ReportAgent(StubClient(reply="")).analyze_batch(sample_batch_results)

    assert result["llm_generated"] is False
    assert result["overview"].strip()


def test_batch_without_client_uses_fallback(sample_batch_results):
    result = ReportAgent(None).analyze_batch(sample_batch_results)

    assert result["llm_generated"] is False
    assert "批次整体评估" in result["overview"]


# ---------------------------------------------------------------- 正常路径


def test_single_parses_three_sections(sample_pipeline_result):
    """正常回复解析为三段，并标记为 LLM 生成。"""
    result = ReportAgent(StubClient(reply=WELL_FORMED_REPLY)).analyze_single(
        sample_pipeline_result
    )

    assert result["llm_generated"] is True
    assert "AIGC 全图生成" in result["opinion"]
    assert result["dimension_notes"].strip()
    assert result["region_notes"].strip()
    assert result["elapsed_ms"] >= 0


def test_prompt_carries_actual_detection_values(sample_pipeline_result):
    """送入 LLM 的 prompt 必须携带真实检测数值，避免研判凭空生成。"""
    prompt = ReportAgent(None)._build_single_prompt(sample_pipeline_result)

    assert "fake" in prompt
    assert "0.55" in prompt          # fake_prob
    assert "medium" in prompt        # risk_level


# ---------------------------------------------------------------- HTML 渲染


def test_html_report_includes_llm_sections(sample_pipeline_result):
    """带 llm_opinion 时，三段研判文字进入 HTML。"""
    opinion = ReportAgent(StubClient(reply=WELL_FORMED_REPLY)).analyze_single(
        sample_pipeline_result
    )
    html = ReportGenerator().generate_single(
        image_path="sample.png", result=sample_pipeline_result, llm_opinion=opinion
    )

    assert html.lstrip().lower().startswith("<!doctype html")
    assert "AIGC 全图生成" in html
    assert "共 2 处可疑区域" in html


def test_html_report_without_llm_opinion_still_complete(sample_pipeline_result):
    """未启用 LLM 时报告仍需完整产出，不得抛异常。"""
    html = ReportGenerator().generate_single(
        image_path="sample.png", result=sample_pipeline_result, llm_opinion=None
    )

    assert html.lstrip().lower().startswith("<!doctype html")
    assert "</html>" in html
    assert str(sample_pipeline_result["risk_level"]) in html


def test_batch_html_report_renders(sample_batch_results):
    html = ReportGenerator().generate_batch(results=sample_batch_results)

    assert html.lstrip().lower().startswith("<!doctype html")
    assert "</html>" in html
