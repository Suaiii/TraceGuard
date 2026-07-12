"""
公共工具函数
- 自定义蓝→红紫 colormap
- PIL 图像处理
- base64 编解码
"""

import base64
import io
import numpy as np
from PIL import Image, ImageFilter


# ==============================================================================
# 自定义 Colormap: 蓝色(低风险) → 青色 → 绿色 → 黄色 → 红色 → 红紫(高风险)
# ==============================================================================

def blue_redpurple_colormap(n_colors: int = 256) -> np.ndarray:
    """
    生成自定义 diverging colormap (RGBA 查找表)。

    颜色映射:
      0.00 → 深蓝 (低可疑)
      0.25 → 青色
      0.50 → 绿色
      0.75 → 橙红
      1.00 → 红紫 (高伪造可疑)

    Args:
        n_colors: 查找表颜色数量

    Returns:
        np.ndarray [n_colors, 4] RGBA 值, dtype=uint8
    """
    import numpy as np

    x = np.linspace(0, 1, n_colors)

    # 分段定义关键颜色锚点 (R, G, B)
    anchors = [
        (0.00, (10, 40, 120)),     # 深蓝
        (0.20, (30, 140, 200)),    # 蓝
        (0.40, (40, 200, 160)),    # 青色
        (0.55, (80, 220, 60)),     # 绿色
        (0.70, (230, 210, 30)),    # 黄色
        (0.85, (240, 100, 30)),    # 橙红
        (1.00, (180, 20, 140)),    # 红紫
    ]

    # 在各段之间线性插值
    colors = np.zeros((n_colors, 4), dtype=np.uint8)
    colors[:, 3] = 255  # alpha = 255

    for c in range(3):  # R, G, B
        for i in range(len(anchors) - 1):
            x0, (r0, g0, b0) = anchors[i]
            x1, (r1, g1, b1) = anchors[i + 1]
            anchor_vals = [r0, g0, b0]
            next_vals = [r1, g1, b1]

            mask = (x >= x0) & (x <= x1)
            if i == len(anchors) - 2:
                mask = (x >= x0) & (x <= x1)

            t = np.where(
                (x1 - x0) > 0,
                (x[mask] - x0) / (x1 - x0),
                0.0
            )
            colors[mask, c] = (anchor_vals[c] + t * (next_vals[c] - anchor_vals[c])).astype(np.uint8)

    return colors


# ==============================================================================
# 图像处理工具
# ==============================================================================

def apply_colormap(heatmap: np.ndarray, colormap: np.ndarray = None) -> Image.Image:
    """
    将二维热力分数数组映射为 RGBA 彩色图像。

    Args:
        heatmap: [H, W] 归一化热力分数 (0~1)
        colormap: [256, 4] RGBA 查找表，默认使用 blue_redpurple_colormap

    Returns:
        PIL.Image RGBA 模式彩色热力图
    """
    if colormap is None:
        colormap = blue_redpurple_colormap()

    # 归一化到 [0, 1]
    h_min, h_max = heatmap.min(), heatmap.max()
    if h_max - h_min > 1e-8:
        heatmap = (heatmap - h_min) / (h_max - h_min)
    else:
        heatmap = np.zeros_like(heatmap)

    # 映射到 0~255 索引
    indices = (heatmap * 255).astype(np.uint8)
    rgba = colormap[indices]  # [H, W, 4]

    return Image.fromarray(rgba, mode='RGBA')


def overlay_heatmap(original: Image.Image, heatmap_rgba: Image.Image,
                    alpha: float = 0.5) -> Image.Image:
    """
    将原图与热力图 RGBA 半透明叠加。

    Args:
        original: 原始 RGB 图像
        heatmap_rgba: RGBA 热力图 (尺寸与 original 一致为佳)
        alpha: 热力层透明度 (0=全透明, 1=完全不透明)

    Returns:
        PIL.Image RGB 模式融合图
    """
    original = original.convert('RGBA')
    heatmap_rgba = heatmap_rgba.resize(original.size, Image.BILINEAR)

    # 调整热力图 alpha 通道
    hm = heatmap_rgba.copy()
    r, g, b, a = hm.split()
    a = a.point(lambda p: int(p * alpha))
    hm.putalpha(a)

    # Alpha 合成
    blended = Image.alpha_composite(original, hm)
    return blended.convert('RGB')


def smooth_heatmap(heatmap: np.ndarray, sigma: float = 1.5) -> np.ndarray:
    """
    对热力图进行高斯平滑。

    Args:
        heatmap: [H, W] 热力分数
        sigma: 高斯核标准差

    Returns:
        np.ndarray 平滑后的热力图
    """
    img = Image.fromarray((heatmap * 255).astype(np.uint8))
    smoothed = img.filter(ImageFilter.GaussianBlur(radius=sigma))
    return np.array(smoothed).astype(np.float32) / 255.0


def upsample_heatmap(heatmap: np.ndarray, target_size: tuple) -> np.ndarray:
    """
    双线性插值上采样热力图。

    Args:
        heatmap: [H, W] 低分辨率热力图
        target_size: (width, height) 目标尺寸

    Returns:
        np.ndarray [target_H, target_W] 上采样后热力图
    """
    img = Image.fromarray(heatmap.astype(np.float32), mode='F')
    img = img.resize(target_size, Image.BILINEAR)
    return np.array(img)


# ==============================================================================
# Base64 编解码
# ==============================================================================

def image_to_base64(image: Image.Image, format: str = 'PNG') -> str:
    """
    将 PIL.Image 编码为 base64 字符串。

    Args:
        image: PIL 图像
        format: 图像格式 (PNG/JPEG)

    Returns:
        base64 编码字符串
    """
    buf = io.BytesIO()
    image.save(buf, format=format)
    return base64.b64encode(buf.getvalue()).decode('utf-8')


def base64_to_image(b64_str: str) -> Image.Image:
    """
    将 base64 字符串解码为 PIL.Image。

    Args:
        b64_str: base64 编码的图像字符串

    Returns:
        PIL.Image
    """
    return Image.open(io.BytesIO(base64.b64decode(b64_str)))
