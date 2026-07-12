"""
共享 pytest fixtures — mock 数据 + 样本图像 + detector
"""

import os
import sys
import numpy as np
import torch
from unittest.mock import MagicMock
import pytest
from PIL import Image

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

FIXTURES_DIR = os.path.join(PROJECT_ROOT, 'tests', 'fixtures')


# ==============================================================================
# 轻量 FakeModel — 返回真实 tensor (供 PatchAnalyzer 批量推理)
# ==============================================================================

class FakeModel:
    """模拟 MambaOutCustom，接受 tensor 输入，返回真实 torch.Tensor"""

    def __init__(self, fake_prob: float = 0.5):
        self.fake_prob = fake_prob
        # 保留 bottleneck 以兼容某些测试
        self._bottleneck_weight = np.random.randn(256, 2304).astype(np.float32) * 0.1
        bn_linear = MagicMock()
        bn_linear.weight = MagicMock()
        bn_linear.weight.detach = MagicMock(return_value=bn_linear.weight)
        bn_linear.weight.cpu = MagicMock(return_value=bn_linear.weight)
        bn_linear.weight.detach.return_value = bn_linear.weight
        bn_linear.weight.detach.return_value.cpu.return_value = bn_linear.weight
        bn_linear.weight.detach.return_value.cpu.return_value.numpy.return_value = \
            self._bottleneck_weight
        self.bottleneck = [bn_linear]

    def __call__(self, x, return_features=False, return_spatial=False):
        B = x.shape[0]
        logits = torch.zeros(B, 2)
        logits[:, 0] = np.log(max(1.0 - self.fake_prob, 1e-6))
        logits[:, 1] = np.log(max(self.fake_prob, 1e-6))
        if return_spatial:
            feat_s3 = torch.randn(B, 576, 7, 7)
            feat_s2 = torch.randn(B, 384, 14, 14)
            return logits, feat_s3, feat_s2
        if return_features:
            return logits, torch.randn(B, 256)
        return logits

    def to(self, device):
        return self

    def eval(self):
        return self

    def backbone(self, x):
        """返回 2304 维空间特征"""
        B = x.shape[0]
        return torch.randn(B, 2304)

    def zero_grad(self):
        pass


# ==============================================================================
# Mock Detector
# ==============================================================================

class MockDetector:
    """
    模拟 Detector，不加载真实模型，返回合理的随机特征数据。
    v2 API: get_heatmap() + get_spatial_features()
    """

    def __init__(self, fake_prob: float = 0.5, device: str = 'cpu'):
        self.fake_prob = fake_prob
        self.device = device
        self.model = FakeModel(fake_prob=fake_prob)

        from torchvision import transforms
        self.transform = transforms.Compose([
            transforms.Resize(256),
            transforms.CenterCrop(224),
            transforms.ToTensor(),
            transforms.Normalize(
                mean=[0.485, 0.456, 0.406],
                std=[0.229, 0.224, 0.225],
            ),
        ])

    def get_heatmap(self, image_or_path):
        """Grad-CAM 热力图 API (v2)"""
        img = self._load_image(image_or_path)
        w, h = img.size
        # 模拟 Grad-CAM 输出: 14x14 上采样到原图尺寸
        heatmap_small = np.abs(np.random.randn(14, 14).astype(np.float32))
        from PIL import Image as PILImage
        hm_img = PILImage.fromarray((heatmap_small * 255).astype(np.uint8))
        hm_img = hm_img.resize((w, h), PILImage.BILINEAR)
        heatmap = np.array(hm_img).astype(np.float32) / 255.0
        heatmap = (heatmap - heatmap.min()) / (heatmap.max() - heatmap.min() + 1e-8)
        return {
            'heatmap': heatmap,
            'label': 'fake' if self.fake_prob > 0.5 else 'real',
            'fake_prob': self.fake_prob,
            'original_size': (w, h),
        }

    def get_spatial_features(self, image_or_path):
        """空间特征 API (v2) — 供定位模块"""
        return {
            'feat_s2': np.random.randn(384, 14, 14).astype(np.float32) * 0.3,
            'feat_s3': np.random.randn(576, 7, 7).astype(np.float32) * 0.3,
            'fake_prob': self.fake_prob,
        }

    def predict(self, image_or_path):
        return {
            'label': 'fake' if self.fake_prob > 0.5 else 'real',
            'real_prob': 1.0 - self.fake_prob,
            'fake_prob': self.fake_prob,
            'risk_score': self.fake_prob,
        }

    @staticmethod
    def _load_image(image_or_path):
        if isinstance(image_or_path, str):
            return Image.open(image_or_path).convert('RGB')
        return image_or_path.convert('RGB')


# ==============================================================================
# Session-scoped fixtures
# ==============================================================================

@pytest.fixture(scope='session')
def mock_detector():
    return MockDetector(fake_prob=0.55)


@pytest.fixture(scope='session')
def mock_detector_low():
    return MockDetector(fake_prob=0.04)


@pytest.fixture(scope='session')
def mock_detector_high():
    return MockDetector(fake_prob=0.92)


# ==============================================================================
# 样本图像
# ==============================================================================

@pytest.fixture(scope='session')
def sample_real():
    path = os.path.join(FIXTURES_DIR, 'real.png')
    assert os.path.exists(path), f"Fixture missing: {path}"
    return Image.open(path).convert('RGB')


@pytest.fixture(scope='session')
def sample_aigc():
    path = os.path.join(FIXTURES_DIR, 'full_aigc.png')
    assert os.path.exists(path), f"Fixture missing: {path}"
    return Image.open(path).convert('RGB')


@pytest.fixture(scope='session')
def sample_tamper():
    path = os.path.join(FIXTURES_DIR, 'local_tamper.png')
    assert os.path.exists(path), f"Fixture missing: {path} (run tests/generate_fixtures.py)"
    return Image.open(path).convert('RGB')


@pytest.fixture(scope='session')
def sample_small_image():
    return Image.new('RGB', (128, 128), color=(100, 150, 200))


# ==============================================================================
# Mock data
# ==============================================================================

@pytest.fixture
def sample_dimension_scores():
    return {
        'fake_prob': 0.55, 'artifact_intensity': 0.72,
        'tamper_area': 0.15, 'region_count': 0.39, 'consistency': 0.48,
    }


@pytest.fixture
def sample_bbox_list():
    return [
        {'x': 100, 'y': 50, 'w': 200, 'h': 150, 'area': 30000},
        {'x': 400, 'y': 300, 'w': 120, 'h': 100, 'area': 12000},
    ]


@pytest.fixture
def sample_pipeline_result(sample_dimension_scores, sample_bbox_list):
    return {
        'label': 'fake', 'fake_prob': 0.55,
        'risk_score': 0.45, 'risk_level': 'medium',
        'explanation': '【总体结论】\ntest\n\n【取证分析】\ntest\n\n【定位详情】\ntest',
        'explanation_brief': 'AIGC伪造图 | 55% | medium | 2处',
        'elapsed_ms': 3500.0,
        'overlay_b64': 'iVBORw0...',
        'mask_b64': 'iVBORw0...',
        'tamper_mask_b64': 'iVBORw0...',
        'tamper_overlay_b64': 'iVBORw0...',
        'bbox_image_b64': 'iVBORw0...',
        'bbox_list': sample_bbox_list,
        'dimension_scores': sample_dimension_scores,
        'metadata': {
            'heatmap_method': 'gradcam', 'overlay_alpha': 0.5,
            'localization_enabled': True, 'language': 'zh',
            'risk_weights': {},
        },
    }


@pytest.fixture
def sample_batch_results(sample_pipeline_result):
    import copy
    r1 = copy.deepcopy(sample_pipeline_result)
    r2 = copy.deepcopy(sample_pipeline_result)
    r2['label'] = 'real'; r2['fake_prob'] = 0.04
    r2['risk_score'] = 0.15; r2['risk_level'] = 'low'; r2['bbox_list'] = []
    r3 = copy.deepcopy(sample_pipeline_result)
    r3['fake_prob'] = 0.92; r3['risk_score'] = 0.88; r3['risk_level'] = 'high'
    return [r1, r2, r3]


@pytest.fixture
def sample_heatmap_2d():
    return np.array([[0.2, 0.8], [0.3, 0.6]], dtype=np.float32)


@pytest.fixture
def sample_score_map():
    return np.random.RandomState(42).rand(64, 64).astype(np.float32)
