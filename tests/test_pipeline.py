"""
流水线集成测试 (mock-based)
"""

import numpy as np
import pytest
from PIL import Image


class TestPipelineMock:

    @pytest.fixture
    def pipeline(self, mock_detector):
        from explanation.pipeline import ExplanationPipeline
        return ExplanationPipeline(mock_detector, config={
            'overlay_alpha': 0.5,
            'enable_localization': True,
            'language': 'zh',
        })

    @pytest.fixture
    def pipeline_no_loc(self, mock_detector):
        from explanation.pipeline import ExplanationPipeline
        return ExplanationPipeline(mock_detector, config={
            'enable_localization': False,
        })

    # ---- 输出 schema ----

    def test_run_output_schema(self, pipeline, sample_small_image):
        """run() 返回全部预期字段"""
        result = pipeline.run(sample_small_image)
        expected_keys = {
            'overlay_b64', 'mask_b64', 'label', 'fake_prob',
            'risk_score', 'risk_level', 'dimension_scores', 'bbox_list',
            'explanation', 'explanation_brief', 'elapsed_ms', 'metadata',
        }
        for key in expected_keys:
            assert key in result, f"Missing key: {key}"

    def test_run_returns_string_label(self, pipeline, sample_small_image):
        """label 是字符串"""
        result = pipeline.run(sample_small_image)
        assert result['label'] in ('real', 'fake')

    def test_run_fake_prob_range(self, pipeline, sample_small_image):
        """fake_prob 在 [0, 1] 区间"""
        result = pipeline.run(sample_small_image)
        assert 0.0 <= result['fake_prob'] <= 1.0

    def test_run_risk_score_range(self, pipeline, sample_small_image):
        """risk_score 在 [0, 1] 区间"""
        result = pipeline.run(sample_small_image)
        assert 0.0 <= result['risk_score'] <= 1.0

    def test_run_risk_level_valid(self, pipeline, sample_small_image):
        """risk_level 为有效值"""
        result = pipeline.run(sample_small_image)
        assert result['risk_level'] in ('low', 'medium', 'high')

    def test_run_base64_not_empty(self, pipeline, sample_small_image):
        """base64 字符串非空"""
        result = pipeline.run(sample_small_image)
        assert len(result['overlay_b64']) > 0
        assert len(result['mask_b64']) > 0

    def test_run_bbox_list_type(self, pipeline, sample_small_image):
        """bbox_list 是 list"""
        result = pipeline.run(sample_small_image)
        assert isinstance(result['bbox_list'], list)

    def test_run_elapsed_ms(self, pipeline, sample_small_image):
        """记录耗时"""
        result = pipeline.run(sample_small_image)
        assert result['elapsed_ms'] > 0

    def test_run_dimension_scores_keys(self, pipeline, sample_small_image):
        """维度分数包含 5 维度"""
        result = pipeline.run(sample_small_image)
        dims = result['dimension_scores']
        for k in ['fake_prob', 'artifact_intensity', 'tamper_area', 'region_count', 'consistency']:
            assert k in dims

    def test_run_explanation_nonempty(self, pipeline, sample_small_image):
        """解释文本非空"""
        result = pipeline.run(sample_small_image)
        assert len(result['explanation']) > 0

    def test_run_explanation_brief_nonempty(self, pipeline, sample_small_image):
        """摘要文本非空"""
        result = pipeline.run(sample_small_image)
        assert len(result['explanation_brief']) > 0

    def test_run_metadata_keys(self, pipeline, sample_small_image):
        """元信息包含关键字段"""
        result = pipeline.run(sample_small_image)
        meta = result['metadata']
        assert 'heatmap_method' in meta
        assert 'localization_enabled' in meta
        assert 'language' in meta

    # ---- 定位开关 ----

    def test_skip_localization(self, pipeline_no_loc, sample_small_image):
        """enable_localization=False 时无定位图"""
        result = pipeline_no_loc.run(sample_small_image)
        assert result['tamper_mask_b64'] is None
        assert result['tamper_overlay_b64'] is None
        assert result['bbox_image_b64'] is None

    def test_with_localization(self, pipeline, sample_small_image):
        """enable_localization=True 时有定位图"""
        result = pipeline.run(sample_small_image)
        assert result['tamper_mask_b64'] is not None
        assert result['tamper_overlay_b64'] is not None
        assert result['bbox_image_b64'] is not None

    # ---- 批量 ----

    def test_run_batch_returns_list(self, pipeline, sample_small_image):
        """run_batch 返回列表"""
        results = pipeline.run_batch([sample_small_image, sample_small_image])
        assert isinstance(results, list)
        assert len(results) == 2

    def test_run_batch_each_has_keys(self, pipeline, sample_small_image):
        """批量结果每项都有完整字段"""
        results = pipeline.run_batch([sample_small_image])
        for result in results:
            assert 'label' in result
            assert 'fake_prob' in result

    # ---- 不同输入格式 ----

    def test_run_with_path(self, pipeline):
        """文件路径输入正常"""
        import os
        fixtures = os.path.join(
            os.path.dirname(os.path.dirname(__file__)), 'tests', 'fixtures'
        )
        path = os.path.join(fixtures, 'real.png')
        if os.path.exists(path):
            result = pipeline.run(path)
            assert result['label'] in ('real', 'fake')

    def test_run_with_pil_image(self, pipeline, sample_small_image):
        """PIL.Image 输入正常"""
        result = pipeline.run(sample_small_image)
        assert result['label'] in ('real', 'fake')

    def test_invalid_input_type_raises(self, pipeline):
        """无效输入类型抛 TypeError"""
        with pytest.raises(TypeError):
            pipeline.run(42)

    # ---- 不同 fake_prob ----

    def test_high_fake_pipeline(self, mock_detector_high, sample_small_image):
        """高伪造概率流水线"""
        from explanation.pipeline import ExplanationPipeline
        pl = ExplanationPipeline(mock_detector_high)
        result = pl.run(sample_small_image)
        assert result['label'] == 'fake'

    def test_low_fake_pipeline(self, mock_detector_low, sample_small_image):
        """局部证据不得覆盖 Detector 的全局 real 标签"""
        from explanation.pipeline import ExplanationPipeline
        pl = ExplanationPipeline(mock_detector_low)
        evidence_image = Image.new('RGB', sample_small_image.size, color='black')
        pl.tamper_detector.detect = lambda _: {
            'bbox_list': [
                {'x': 8, 'y': 8, 'w': 24, 'h': 24, 'area': 576, 'patch_fake_prob': 0.8}
            ],
            'score_map': np.ones((128, 128), dtype=np.float32) * 0.8,
            'tamper_mask': evidence_image.convert('L'),
            'tamper_mask_overlay': evidence_image,
            'bbox_image': evidence_image,
            'elapsed_ms': 1.0,
        }
        result = pl.run(sample_small_image)
        assert result['label'] == 'real'
        assert result['tamper_type'] == 'local_tamper'
