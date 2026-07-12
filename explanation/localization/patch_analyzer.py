"""
PatchAnalyzer — 多尺度滑动窗口可疑度检测

将图像分割为重叠 patch，每个 patch 独立输入 Detector，
构建空间可疑度分数图。大图自动降采样以加速分析。
"""

import numpy as np
import torch
from PIL import Image


class PatchAnalyzer:
    """
    基于滑动窗口 patch 的空间可疑度分析。

    优化策略:
      - 大图自动降采样 (max_dim=500) 加速推理
      - 置信度过滤 (只保留 fake_prob > confidence_floor 的分数)
      - 多尺度融合取 max (保留最强信号)

    用法:
        from detection import Detector
        analyzer = PatchAnalyzer(detector)
        score_map = analyzer.analyze(image)  # [H, W] 0~1 分数图
    """

    def __init__(self, detector, scales: list = None,
                 stride_ratio: float = 0.5,
                 batch_size: int = 32,
                 max_dim: int = 500,
                 confidence_floor: float = 0.35):
        """
        Args:
            detector: Detector 实例
            scales: 窗口尺寸列表，默认 [224, 160]
            stride_ratio: 步长比例 (相对于窗口尺寸), 越大越快
            batch_size: 每批处理的 patch 数量
            max_dim: 大图降采样最大边长 (px)
            confidence_floor: 低于此 fake_prob 的 patch 分数置零
        """
        self.detector = detector
        self.scales = scales or [224, 160]
        self.stride_ratio = stride_ratio
        self.batch_size = batch_size
        self.max_dim = max_dim
        self.confidence_floor = confidence_floor

    def analyze(self, image_or_path) -> np.ndarray:
        """
        多尺度滑动窗口分析，返回空间可疑度分数图。

        Args:
            image_or_path: PIL.Image 或文件路径

        Returns:
            np.ndarray [H, W] 可疑度分数 (0~1)
        """
        img = self._load_image(image_or_path)
        orig_w, orig_h = img.size

        # 大图降采样以加速
        need_upsample = False
        if max(orig_w, orig_h) > self.max_dim:
            need_upsample = True
            scale_factor = self.max_dim / max(orig_w, orig_h)
            analysis_w = int(orig_w * scale_factor)
            analysis_h = int(orig_h * scale_factor)
            analysis_img = img.resize((analysis_w, analysis_h), Image.BILINEAR)
        else:
            analysis_w, analysis_h = orig_w, orig_h
            analysis_img = img

        # 多尺度分析: 取各尺度最大值 (保留最强信号)
        score_map = np.zeros((analysis_h, analysis_w), dtype=np.float32)

        for scale in self.scales:
            # 如果分析图比 patch 还小，使用整图
            effective_scale = min(scale, analysis_w, analysis_h)
            stride = max(int(effective_scale * self.stride_ratio), 32)
            scale_score = self._analyze_single_scale(
                analysis_img, effective_scale, stride
            )
            # 取最大值融合
            score_map = np.maximum(score_map, scale_score)

        # 保存过滤前的原始分数（供局部篡改检测使用）
        self._raw_score_map = score_map.copy()

        # 置信度过滤
        score_map[score_map < self.confidence_floor] = 0

        # 回放大到原图尺寸
        if need_upsample:
            score_map = self._upsample(score_map, (orig_w, orig_h))

        # 归一化
        smax = score_map.max()
        if smax > 0:
            score_map = score_map / smax

        return score_map

    def _analyze_single_scale(self, img: Image.Image,
                               patch_size: int,
                               stride: int) -> np.ndarray:
        """
        单尺度滑动窗口分析。

        Returns:
            np.ndarray [H, W] 该尺度下的可疑度分数图
        """
        w, h = img.size
        score_map = np.zeros((h, w), dtype=np.float32)
        count_map = np.zeros((h, w), dtype=np.float32)

        # 生成 patch 位置
        patches = []
        positions = []

        for y in range(0, h - patch_size + 1, stride):
            for x in range(0, w - patch_size + 1, stride):
                patch = img.crop((x, y, x + patch_size, y + patch_size))
                patches.append(patch)
                positions.append((x, y))

        # 确保覆盖右下角
        x_last = max(0, w - patch_size)
        y_last = max(0, h - patch_size)
        if x_last > 0 or y_last > 0:
            patch = img.crop((x_last, y_last, x_last + patch_size, y_last + patch_size))
            patches.append(patch)
            positions.append((x_last, y_last))

        if not patches:
            return score_map

        # 批量推理
        fake_probs = self._batch_predict(patches)

        # 累积到分数图 (每个像素取所覆盖 patch 中的最大分数)
        for (x, y), prob in zip(positions, fake_probs):
            score_map[y:y + patch_size, x:x + patch_size] = np.maximum(
                score_map[y:y + patch_size, x:x + patch_size], prob
            )

        return score_map

    def _batch_predict(self, patches: list) -> np.ndarray:
        """批量预测 fake_prob"""
        all_probs = []

        for i in range(0, len(patches), self.batch_size):
            batch = patches[i:i + self.batch_size]
            tensors = [self.detector.transform(p) for p in batch]
            batch_tensor = torch.stack(tensors).to(self.detector.device)

            with torch.no_grad():
                logits = self.detector.model(batch_tensor, return_features=False)
                probs = torch.softmax(logits, dim=1)[:, 1]

            all_probs.extend(probs.cpu().numpy().tolist())

        return np.array(all_probs)

    @staticmethod
    def _upsample(arr: np.ndarray, target_size: tuple) -> np.ndarray:
        img = Image.fromarray((arr * 255).astype(np.uint8))
        img = img.resize(target_size, Image.BILINEAR)
        return np.array(img).astype(np.float32) / 255.0

    @staticmethod
    def _load_image(image_or_path) -> Image.Image:
        if isinstance(image_or_path, str):
            return Image.open(image_or_path).convert('RGB')
        elif isinstance(image_or_path, Image.Image):
            return image_or_path.convert('RGB')
        else:
            raise TypeError(f"需要 PIL.Image 或 文件路径")
