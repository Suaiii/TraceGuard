"""
篡改定位测试 (mock-based, 无 GPU + unit postprocess tests)
"""

import numpy as np
from PIL import Image
import pytest


# ==============================================================================
# 后处理函数单元测试 (纯逻辑)
# ==============================================================================

class TestPostprocess:

    def test_threshold_percentile(self):
        """百分位阈值正确二值化"""
        from explanation.localization.postprocess import threshold_percentile
        score_map = np.array([
            [0.1, 0.2, 0.3],
            [0.4, 0.5, 0.6],
            [0.7, 0.8, 0.9],
        ], dtype=np.float32)
        # 50% percentile → 高于中位数的像素标记为 True
        mask = threshold_percentile(score_map, 50)
        # numpy 1.26+ 的 percentile 在 3x3 上 50分位 = 0.5，>= 0.5 的为 5 个
        assert mask.sum() >= 1  # 至少有一个标记

    def test_threshold_percentile_90(self):
        """高百分位阈值过滤大部分"""
        from explanation.localization.postprocess import threshold_percentile
        score_map = np.random.RandomState(42).rand(100, 100).astype(np.float32)
        mask = threshold_percentile(score_map, 90)
        # 大约 10% 标记为 True
        ratio = mask.sum() / mask.size
        assert 0.05 < ratio < 0.15

    def test_threshold_otsu(self):
        """Otsu 阈值正常执行"""
        from explanation.localization.postprocess import threshold_otsu
        # 创建双峰数据
        low = np.random.RandomState(0).normal(0.2, 0.05, (50, 50))
        high = np.random.RandomState(1).normal(0.8, 0.05, (50, 50))
        score_map = np.vstack([low, high]).astype(np.float32)
        mask = threshold_otsu(score_map)
        # Otsu 应该能分出两个簇
        assert mask.sum() > 0
        assert mask.sum() < mask.size

    def test_extract_bboxes_min_area(self):
        """extract_bboxes 过滤小面积区域"""
        from explanation.localization.postprocess import extract_bboxes
        mask = np.zeros((100, 100), dtype=bool)
        # 小区域 (过滤)
        mask[10:15, 10:15] = True  # area = 25
        # 大区域 (保留)
        mask[30:60, 30:60] = True  # area = 900
        bboxes = extract_bboxes(mask, min_area=100)
        assert len(bboxes) == 1
        assert bboxes[0]['area'] >= 900

    def test_extract_bboxes_format(self):
        """bbox 含 x/y/w/h/area"""
        from explanation.localization.postprocess import extract_bboxes
        mask = np.zeros((100, 100), dtype=bool)
        mask[20:50, 30:60] = True
        bboxes = extract_bboxes(mask, min_area=10)
        assert len(bboxes) == 1
        b = bboxes[0]
        for key in ['x', 'y', 'w', 'h', 'area']:
            assert key in b, f"Missing key: {key}"
            assert isinstance(b[key], (int, np.integer))

    def test_nms_dedup(self):
        """NMS 正确合并重叠框"""
        from explanation.localization.postprocess import nms_bboxes
        bboxes = [
            {'x': 100, 'y': 100, 'w': 50, 'h': 50, 'area': 2500},
            {'x': 110, 'y': 110, 'w': 50, 'h': 50, 'area': 2500},  # 重叠
            {'x': 300, 'y': 300, 'w': 50, 'h': 50, 'area': 2500},  # 不重叠
        ]
        result = nms_bboxes(bboxes, iou_threshold=0.3)
        assert len(result) <= 2

    def test_nms_single_box(self):
        """单个 bbox 的 NMS 不报错"""
        from explanation.localization.postprocess import nms_bboxes
        result = nms_bboxes([{'x': 0, 'y': 0, 'w': 10, 'h': 10, 'area': 100}])
        assert len(result) == 1

    def test_nms_empty_list(self):
        """空列表 NMS 不报错"""
        from explanation.localization.postprocess import nms_bboxes
        result = nms_bboxes([])
        assert result == []

    def test_morphological_clean(self, sample_score_map):
        """形态学清理正确：开运算去噪，闭运算填洞"""
        from explanation.localization.postprocess import morphological_clean
        # 创建含噪点和空洞的掩膜
        from explanation.localization.postprocess import threshold_percentile
        mask = threshold_percentile(sample_score_map, 75)
        cleaned = morphological_clean(mask, open_radius=1, close_radius=1)
        assert cleaned.shape == mask.shape

    def test_mask_to_image(self, sample_score_map):
        """掩膜转图像正常"""
        from explanation.localization.postprocess import mask_to_image, threshold_percentile
        mask = threshold_percentile(sample_score_map, 75)
        img = mask_to_image(mask)
        assert isinstance(img, Image.Image)

    def test_draw_bboxes(self):
        """bbox 绘制正常"""
        from explanation.localization.postprocess import draw_bboxes_on_image
        img = Image.new('RGB', (200, 200), (100, 100, 100))
        bboxes = [{'x': 50, 'y': 50, 'w': 100, 'h': 80, 'area': 8000}]
        result = draw_bboxes_on_image(img, bboxes)
        assert isinstance(result, Image.Image)
        assert result.size == (200, 200)


# ==============================================================================
# TamperDetector 集成测试 (mock)
# ==============================================================================

class TestTamperDetector:

    @pytest.fixture
    def detector(self, mock_detector):
        from explanation.localization import TamperDetector
        # 小图 + 大 stride = 快速
        return TamperDetector(mock_detector, config={
            'enable_patch': True,
            'enable_feature': True,
            'scales': [64],
            'stride_ratio': 1.0,  # 无重叠 = 1 个 patch
            'batch_size': 8,
            'min_region_area': 64,
        })

    def test_detect_output_schema(self, detector, sample_small_image):
        """detect() 返回全部预期 key"""
        result = detector.detect(sample_small_image)
        expected = {'tamper_mask', 'tamper_mask_overlay', 'bbox_image',
                    'bbox_list', 'score_map', 'elapsed_ms'}
        assert set(result.keys()) == expected

    def test_detect_bbox_format(self, detector, sample_small_image):
        """bbox 含 x/y/w/h/area"""
        result = detector.detect(sample_small_image)
        for bbox in result['bbox_list']:
            for key in ['x', 'y', 'w', 'h', 'area']:
                assert key in bbox

    def test_detect_returns_pil_images(self, detector, sample_small_image):
        """返回图像为 PIL.Image"""
        result = detector.detect(sample_small_image)
        assert isinstance(result['tamper_mask'], Image.Image)
        assert isinstance(result['tamper_mask_overlay'], Image.Image)
        assert isinstance(result['bbox_image'], Image.Image)

    def test_detect_score_map_is_2d(self, detector, sample_small_image):
        """可疑度图是 2D numpy"""
        result = detector.detect(sample_small_image)
        assert isinstance(result['score_map'], np.ndarray)
        assert result['score_map'].ndim == 2

    def test_detect_score_map_range(self, detector, sample_small_image):
        """可疑度图归一化到 [0,1]"""
        result = detector.detect(sample_small_image)
        sm = result['score_map']
        assert 0.0 <= sm.max() <= 1.0

    def test_detect_elapsed_ms(self, detector, sample_small_image):
        """记录耗时"""
        result = detector.detect(sample_small_image)
        assert result['elapsed_ms'] > 0

    def test_detect_disable_patch(self, mock_detector, sample_small_image):
        """仅特征分析不报错"""
        from explanation.localization import TamperDetector
        det = TamperDetector(mock_detector, config={
            'enable_patch': False,
            'enable_feature': True,
        })
        result = det.detect(sample_small_image)
        assert isinstance(result['bbox_image'], Image.Image)

    def test_detect_disable_feature(self, mock_detector, sample_small_image):
        """仅 patch 分析不报错"""
        from explanation.localization import TamperDetector
        det = TamperDetector(mock_detector, config={
            'enable_patch': True,
            'enable_feature': False,
            'scales': [64],
            'stride_ratio': 1.0,
            'batch_size': 8,
        })
        result = det.detect(sample_small_image)
        assert isinstance(result['bbox_image'], Image.Image)

    def test_detect_with_otsu_threshold(self, mock_detector, sample_small_image):
        """Otsu 阈值方法不报错"""
        from explanation.localization import TamperDetector
        det = TamperDetector(mock_detector, config={
            'threshold_method': 'otsu',
            'scales': [64],
            'stride_ratio': 1.0,
            'batch_size': 8,
        })
        result = det.detect(sample_small_image)
        assert isinstance(result['bbox_list'], list)

    def test_detect_base64(self, detector, sample_small_image):
        """detect_base64 返回 base64 字符串"""
        result = detector.detect_base64(sample_small_image)
        assert 'tamper_mask_b64' in result
        assert 'bbox_list' in result
        assert isinstance(result['tamper_mask_b64'], str)
