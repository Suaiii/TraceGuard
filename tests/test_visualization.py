"""
可视化测试 (无模型依赖)
"""

import pytest
from PIL import Image

from explanation.visualization.charts import (
    radar_chart, risk_gauge, batch_summary, all_charts,
)
from explanation.visualization.report import ReportGenerator
from explanation.visualization import Visualizer


# ==============================================================================
# 图表测试
# ==============================================================================

class TestRadarChart:

    def test_returns_image(self, sample_dimension_scores):
        img = radar_chart(sample_dimension_scores)
        assert isinstance(img, Image.Image)

    def test_size_matches_param(self, sample_dimension_scores):
        img = radar_chart(sample_dimension_scores, size=(300, 300))
        assert img.size[0] <= 310
        assert img.size[1] <= 310

    def test_empty_scores(self):
        """空维度分不报错"""
        img = radar_chart({})
        assert isinstance(img, Image.Image)

    def test_all_ones(self):
        """全 1 不报错"""
        scores = {k: 1.0 for k in ['fake_prob', 'artifact_intensity', 'tamper_area', 'region_count', 'consistency']}
        img = radar_chart(scores)
        assert isinstance(img, Image.Image)

    def test_all_zeros(self):
        """全 0 不报错"""
        scores = {k: 0.0 for k in ['fake_prob', 'artifact_intensity', 'tamper_area', 'region_count', 'consistency']}
        img = radar_chart(scores)
        assert isinstance(img, Image.Image)


class TestRiskGauge:

    def test_returns_image(self):
        img = risk_gauge(0.45, 'medium')
        assert isinstance(img, Image.Image)

    @pytest.mark.parametrize('score,level', [
        (0.10, 'low'),
        (0.50, 'medium'),
        (0.90, 'high'),
    ])
    def test_all_levels_no_error(self, score, level):
        img = risk_gauge(score, level)
        assert isinstance(img, Image.Image)

    def test_size_matches_param(self):
        img = risk_gauge(0.5, 'medium', size=(400, 120))
        assert img.size[0] <= 410


class TestBatchSummary:

    def test_returns_image_with_data(self, sample_batch_results):
        img = batch_summary(sample_batch_results)
        assert isinstance(img, Image.Image)

    def test_empty_returns_placeholder(self):
        img = batch_summary([])
        assert isinstance(img, Image.Image)

    def test_single_item(self):
        img = batch_summary([{'label': 'fake', 'fake_prob': 0.9, 'risk_score': 0.8, 'risk_level': 'high'}])
        assert isinstance(img, Image.Image)


class TestAllCharts:

    def test_all_charts_from_result(self, sample_pipeline_result, sample_batch_results):
        charts = all_charts(sample_pipeline_result, sample_batch_results)
        assert 'radar' in charts
        assert 'gauge' in charts
        assert isinstance(charts['radar'], Image.Image)
        assert isinstance(charts['gauge'], Image.Image)

    def test_all_charts_no_batch(self, sample_pipeline_result):
        charts = all_charts(sample_pipeline_result)
        assert charts['summary'] is None


# ==============================================================================
# HTML 报告测试
# ==============================================================================

class TestReportGenerator:

    @pytest.fixture
    def gen(self):
        return ReportGenerator()

    def test_generate_single_returns_html(self, gen, sample_pipeline_result):
        html = gen.generate_single('test.jpg', sample_pipeline_result)
        assert isinstance(html, str)
        assert '<!DOCTYPE html>' in html
        assert '</html>' in html

    def test_single_contains_key_info(self, gen, sample_pipeline_result):
        html = gen.generate_single('test.jpg', sample_pipeline_result)
        assert 'TraceGuard' in html
        assert 'test.jpg' in html

    def test_generate_single_real_label(self, gen, sample_pipeline_result):
        result = dict(sample_pipeline_result)
        result['label'] = 'real'
        html = gen.generate_single('test.jpg', result)
        assert '真实图像' in html

    def test_generate_single_fake_label(self, gen, sample_pipeline_result):
        result = dict(sample_pipeline_result)
        result['label'] = 'fake'
        html = gen.generate_single('test.jpg', result)
        assert 'AIGC伪造' in html

    def test_generate_batch_returns_html(self, gen, sample_batch_results):
        html = gen.generate_batch(sample_batch_results)
        assert isinstance(html, str)
        assert '<!DOCTYPE html>' in html
        assert '</html>' in html

    def test_batch_contains_summary(self, gen, sample_batch_results):
        html = gen.generate_batch(sample_batch_results)
        assert '3' in html  # total count

    def test_generate_single_without_optional_images(self, gen):
        """缺少可选 base64 图不报错"""
        minimal_result = {
            'label': 'real',
            'fake_prob': 0.04,
            'risk_score': 0.15,
            'risk_level': 'low',
            'explanation': 'test',
            'explanation_brief': 'test brief',
            'elapsed_ms': 1000,
            'bbox_list': [],
            'dimension_scores': {},
            'overlay_b64': None,
            'tamper_overlay_b64': None,
            'bbox_image_b64': None,
            'metadata': {},
        }
        html = gen.generate_single('test.jpg', minimal_result)
        assert isinstance(html, str)

    def test_report_html_self_contained(self, gen, sample_pipeline_result):
        """报告 HTML 自包含，合法结构"""
        html = gen.generate_single('test.jpg', sample_pipeline_result)
        assert html.strip().startswith('<!DOCTYPE html>')
        assert '<html' in html
        assert '<head>' in html
        assert '<body>' in html

    def test_include_charts_false(self, sample_pipeline_result):
        """禁用图表时不报错"""
        gen = ReportGenerator(include_charts=False)
        html = gen.generate_single('test.jpg', sample_pipeline_result)
        assert isinstance(html, str)


class TestVisualizer:

    @pytest.fixture
    def viz(self):
        return Visualizer()

    def test_report_method(self, viz, sample_pipeline_result):
        html = viz.report('image.jpg', sample_pipeline_result)
        assert isinstance(html, str)
        assert len(html) > 0

    def test_batch_report_method(self, viz, sample_batch_results):
        html = viz.batch_report(sample_batch_results)
        assert isinstance(html, str)
        assert len(html) > 0

    def test_charts_method(self, viz, sample_pipeline_result):
        charts = viz.charts(sample_pipeline_result)
        assert 'radar' in charts
        assert 'gauge' in charts

    def test_save_report(self, viz, sample_pipeline_result, tmp_path):
        path = str(tmp_path / 'test.html')
        viz.save_report('<html></html>', path)
        import os
        assert os.path.exists(path)

    def test_save_chart(self, viz, tmp_path):
        path = str(tmp_path / 'chart.png')
        from PIL import Image
        img = Image.new('RGB', (100, 100))
        viz.save_chart(img, path)
        import os
        assert os.path.exists(path)
