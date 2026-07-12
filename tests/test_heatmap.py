"""
热力图测试 (mock-based, 无 GPU)
v2: Grad-CAM 热力图 (14x14 → 原图尺寸)
"""

import numpy as np
from PIL import Image
import pytest


class TestHeatmapGenerator:

    @pytest.fixture
    def generator(self, mock_detector):
        from explanation.heatmap import HeatmapGenerator
        return HeatmapGenerator(mock_detector, smooth_sigma=1.0, overlay_alpha=0.5)

    # ---- generate() 输出 ----

    def test_generate_output_keys(self, generator, sample_small_image):
        """generate() 返回所有预期 key"""
        result = generator.generate(sample_small_image)
        expected = {'overlay', 'mask', 'heatmap_2d', 'fake_prob', 'label'}
        assert set(result.keys()) == expected

    def test_generate_returns_pil_images(self, generator, sample_small_image):
        """overlay 和 mask 是 PIL.Image"""
        result = generator.generate(sample_small_image)
        assert isinstance(result['overlay'], Image.Image)
        assert isinstance(result['mask'], Image.Image)

    def test_generate_returns_float_fake_prob(self, generator, sample_small_image):
        """fake_prob 是 float"""
        result = generator.generate(sample_small_image)
        assert isinstance(result['fake_prob'], float)

    def test_generate_heatmap_2d_is_2d(self, generator, sample_small_image):
        """heatmap_2d 是 2D numpy 数组"""
        result = generator.generate(sample_small_image)
        assert isinstance(result['heatmap_2d'], np.ndarray)
        assert result['heatmap_2d'].ndim == 2

    def test_generate_heatmap_range(self, generator, sample_small_image):
        """热力值在 [0, 1] 范围"""
        result = generator.generate(sample_small_image)
        hm = result['heatmap_2d']
        assert 0.0 <= hm.min() <= hm.max() <= 1.0

    def test_generate_overlay_size_matches_input(self, generator, sample_small_image):
        """overlay 尺寸 = 输入尺寸"""
        result = generator.generate(sample_small_image)
        assert result['overlay'].size == sample_small_image.size

    # ---- 不同尺寸输入 ----

    def test_different_sizes_no_crash(self, generator):
        """不同分辨率不崩溃"""
        for size in [(64, 64), (128, 256), (512, 512), (100, 300)]:
            img = Image.new('RGB', size)
            result = generator.generate(img)
            assert isinstance(result['overlay'], Image.Image)

    # ---- 高分/低分 ----

    def test_high_fake_prob_generator(self, mock_detector_high, sample_small_image):
        """高伪造概率时正常输出"""
        from explanation.heatmap import HeatmapGenerator
        gen = HeatmapGenerator(mock_detector_high)
        result = gen.generate(sample_small_image)
        assert result['fake_prob'] > 0.9
        assert result['overlay'] is not None

    def test_low_fake_prob_generator(self, mock_detector_low, sample_small_image):
        """低伪造概率时正常输出"""
        from explanation.heatmap import HeatmapGenerator
        gen = HeatmapGenerator(mock_detector_low)
        result = gen.generate(sample_small_image)
        assert result['fake_prob'] < 0.1
        assert result['overlay'] is not None

    # ---- base64 输出 ----

    def test_generate_base64(self, generator, sample_small_image):
        """generate_base64 返回 base64 字符串"""
        result = generator.generate_base64(sample_small_image)
        assert 'overlay_b64' in result
        assert 'mask_b64' in result
        assert isinstance(result['overlay_b64'], str)
        assert isinstance(result['label'], str)
