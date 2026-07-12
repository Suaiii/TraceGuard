"""
文本解释测试 (无模型依赖)
"""

import pytest

from explanation.text.generator import TextExplainer


class TestTextExplainer:

    @pytest.fixture
    def explainer_zh(self):
        return TextExplainer(language='zh', detail_level='standard')

    @pytest.fixture
    def explainer_en(self):
        return TextExplainer(language='en', detail_level='standard')

    @pytest.fixture
    def explainer_brief(self):
        return TextExplainer(language='zh', detail_level='brief')

    # ---- 结构完整 ----

    def test_explain_contains_conclusion(self, explainer_zh):
        """包含总体结论段"""
        text = explainer_zh.explain('fake', 0.85)
        assert '【总体结论】' in text

    def test_explain_contains_forensic(self, explainer_zh):
        """包含取证分析段"""
        text = explainer_zh.explain('fake', 0.85)
        assert '【取证分析】' in text

    def test_explain_contains_localization(self, explainer_zh):
        """包含定位详情段"""
        text = explainer_zh.explain(
            'fake', 0.85,
            bbox_list=[{'x': 10, 'y': 10, 'w': 100, 'h': 100, 'area': 10000}],
        )
        assert '【定位详情】' in text

    def test_three_sections_separated(self, explainer_zh):
        """三段之间用双换行分隔"""
        text = explainer_zh.explain(
            'fake', 0.85,
            bbox_list=[{'x': 10, 'y': 10, 'w': 100, 'h': 100, 'area': 10000}],
        )
        sections = text.split('\n\n')
        assert len(sections) >= 3

    # ---- 内容差异 ----

    def test_explain_real_differs_from_fake(self, explainer_zh):
        """real 和 fake 解释文本不同"""
        text_real = explainer_zh.explain('real', 0.04)
        text_fake = explainer_zh.explain('fake', 0.96)
        assert text_real != text_fake

    def test_explain_high_fake_mentions_strong(self, explainer_zh):
        """高伪造概率提到'强烈'"""
        text = explainer_zh.explain('fake', 0.90)
        assert '强烈' in text

    def test_explain_low_fake_mentions_weak(self, explainer_zh):
        """低伪造概率提到'微弱'"""
        text = explainer_zh.explain('real', 0.04)
        assert '微弱' in text

    # ---- 简略版 ----

    def test_explain_brief_format(self, explainer_zh):
        """摘要包含关键信息"""
        brief = explainer_zh.explain_brief('fake', 0.85, 'high')
        assert '85%' in brief
        assert 'high' in brief

    def test_explain_brief_real(self, explainer_zh):
        """真实图摘要格式"""
        brief = explainer_zh.explain_brief('real', 0.04, 'low')
        assert '真实图' in brief or '4%' in brief

    # ---- Edge cases ----

    def test_explain_empty_bbox(self, explainer_zh):
        """无 bbox 时不报错"""
        text = explainer_zh.explain('real', 0.04, bbox_list=[])
        assert isinstance(text, str)
        assert len(text) > 0

    def test_explain_empty_heatmap_stats(self, explainer_zh):
        """无热力图统计时不报错"""
        text = explainer_zh.explain('real', 0.04, heatmap_stats={})
        assert isinstance(text, str)

    def test_explain_extreme_values(self, explainer_zh):
        """极值不崩溃"""
        text = explainer_zh.explain(
            'fake', 1.0, risk_level='high', risk_score=1.0,
            bbox_list=[{'x': 0, 'y': 0, 'w': 10000, 'h': 10000, 'area': 100000000}],
            heatmap_stats={'max': 1.0, 'mean': 1.0},
        )
        assert isinstance(text, str)

    def test_explain_all_risk_levels(self, explainer_zh):
        """所有风险等级都不报错"""
        for level in ['low', 'medium', 'high']:
            text = explainer_zh.explain('fake', 0.5, risk_level=level)
            assert len(text) > 0

    # ---- 详细度 ----

    def test_brief_shorter_than_standard(self, explainer_brief, explainer_zh):
        """brief 模式比 standard 短"""
        text_brief = explainer_brief.explain('real', 0.04)
        text_std = explainer_zh.explain('real', 0.04)
        assert len(text_brief) <= len(text_std)

    # ---- 语言 ----

    def test_language_zh(self, explainer_zh):
        """中文模板正常"""
        text = explainer_zh.explain('fake', 0.80)
        assert len(text) > 0

    def test_bbox_list_in_output(self, explainer_zh):
        """bbox 坐标出现在解释中"""
        text = explainer_zh.explain(
            'fake', 0.8,
            bbox_list=[{'x': 123, 'y': 456, 'w': 200, 'h': 100, 'area': 20000}],
        )
        assert '123' in text
        assert '456' in text
