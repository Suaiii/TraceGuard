"""
后处理流水线：阈值化 → 形态学 → 轮廓提取 → bbox → NMS
"""

import numpy as np
from PIL import Image, ImageFilter, ImageDraw


def threshold_otsu(score_map: np.ndarray) -> np.ndarray:
    """
    Otsu 自适应阈值二值化。

    Args:
        score_map: [H, W] 可疑度分数 (0~1)

    Returns:
        np.ndarray [H, W] bool 二值掩膜
    """
    # 将 0~1 分数映射到 0~255
    img = (score_map * 255).astype(np.uint8)

    # Otsu 阈值
    hist, _ = np.histogram(img.ravel(), bins=256, range=(0, 256))
    total = img.size
    sum_all = np.dot(np.arange(256), hist)

    best_thresh = 0
    best_variance = 0

    w_b = 0
    sum_b = 0

    for t in range(256):
        w_b += hist[t]
        if w_b == 0:
            continue
        w_f = total - w_b
        if w_f == 0:
            break

        sum_b += t * hist[t]
        m_b = sum_b / w_b
        m_f = (sum_all - sum_b) / w_f

        variance_between = w_b * w_f * (m_b - m_f) ** 2
        if variance_between > best_variance:
            best_variance = variance_between
            best_thresh = t

    return img >= best_thresh


def threshold_percentile(score_map: np.ndarray, percentile: float = 75) -> np.ndarray:
    """
    百分位数阈值二值化。

    Args:
        score_map: [H, W] 可疑度分数 (0~1)
        percentile: 阈值百分位 (0~100)，高于此值的像素标记为可疑

    Returns:
        np.ndarray [H, W] bool 二值掩膜
    """
    thresh = np.percentile(score_map, percentile)
    return score_map >= thresh


def morphological_clean(mask: np.ndarray, open_radius: int = 3,
                        close_radius: int = 5) -> np.ndarray:
    """
    形态学后处理：开运算去噪 + 闭运算填洞。

    Args:
        mask: [H, W] bool 二值掩膜
        open_radius: 开运算核半径 (去除小噪点)
        close_radius: 闭运算核半径 (填充小洞)

    Returns:
        np.ndarray [H, W] bool 清理后掩膜
    """
    from scipy.ndimage import binary_opening, binary_closing, generate_binary_structure

    struct = generate_binary_structure(2, 2)

    # 开运算 — 去除孤立噪点
    if open_radius > 0:
        mask = binary_opening(mask, structure=struct, iterations=open_radius)

    # 闭运算 — 填充内部小洞
    if close_radius > 0:
        mask = binary_closing(mask, structure=struct, iterations=close_radius)

    return mask


def extract_bboxes(mask: np.ndarray, min_area: int = 64) -> list:
    """
    从二值掩膜提取最小外接矩形。

    Args:
        mask: [H, W] bool 二值掩膜
        min_area: 最小区域面积 (像素)，小于此值的忽略

    Returns:
        list[dict]: [{'x': int, 'y': int, 'w': int, 'h': int, 'area': int}, ...]
    """
    from scipy.ndimage import label, find_objects

    labeled, num_features = label(mask)

    bboxes = []
    for i in range(1, num_features + 1):
        region = (labeled == i)
        area = region.sum()
        if area < min_area:
            continue

        # 找到边界
        rows, cols = np.where(region)
        y_min, y_max = rows.min(), rows.max()
        x_min, x_max = cols.min(), cols.max()

        bboxes.append({
            'x': int(x_min),
            'y': int(y_min),
            'w': int(x_max - x_min + 1),
            'h': int(y_max - y_min + 1),
            'area': int(area),
        })

    return bboxes


def nms_bboxes(bboxes: list, iou_threshold: float = 0.3) -> list:
    """
    非极大值抑制，合并高度重叠的框。

    Args:
        bboxes: bbox 列表
        iou_threshold: IoU 阈值，高于此值的框合并

    Returns:
        list[dict] 去重后的 bbox 列表
    """
    if len(bboxes) <= 1:
        return bboxes

    # 按面积降序排列
    bboxes = sorted(bboxes, key=lambda b: b['area'], reverse=True)
    keep = []

    while bboxes:
        best = bboxes.pop(0)
        keep.append(best)

        filtered = []
        for b in bboxes:
            if _iou(best, b) < iou_threshold:
                filtered.append(b)
        bboxes = filtered

    return keep


def mask_to_image(mask: np.ndarray) -> Image.Image:
    """
    将 bool 掩膜转换为白色可疑区域 + 黑色背景的 RGB 图像。

    Args:
        mask: [H, W] bool 二值掩膜

    Returns:
        PIL.Image RGB 模式
    """
    rgba = np.zeros((mask.shape[0], mask.shape[1], 4), dtype=np.uint8)
    # 白色标记可疑区域，半透明
    rgba[mask] = [255, 60, 60, 200]       # 红
    rgba[~mask] = [0, 0, 0, 0]           # 透明背景

    return Image.fromarray(rgba, mode='RGBA')


def overlay_mask_on_image(original: Image.Image, mask_img: Image.Image,
                          alpha: float = 0.4) -> Image.Image:
    """
    将篡改掩膜叠加到原图上。

    Args:
        original: 原始 RGB 图像
        mask_img: RGBA 掩膜图
        alpha: 叠加透明度

    Returns:
        PIL.Image RGB 模式叠加图
    """
    original = original.convert('RGBA')
    mask_img = mask_img.resize(original.size, Image.BILINEAR)

    # 调整透明度
    r, g, b, a = mask_img.split()
    a = a.point(lambda p: int(p * alpha))
    mask_img.putalpha(a)

    blended = Image.alpha_composite(original, mask_img)
    return blended.convert('RGB')


def draw_bboxes_on_image(image: Image.Image, bboxes: list,
                         color: tuple = (255, 60, 60),
                         width: int = 3) -> Image.Image:
    """
    在图像上绘制 bbox 矩形框。

    Args:
        image: PIL.Image RGB 原图
        bboxes: bbox 列表
        color: 框颜色 (R, G, B)
        width: 线宽

    Returns:
        PIL.Image 带框的图像
    """
    img = image.copy().convert('RGB')
    draw = ImageDraw.Draw(img)

    for bbox in bboxes:
        x, y, w, h = bbox['x'], bbox['y'], bbox['w'], bbox['h']
        for i in range(width):
            draw.rectangle([x - i, y - i, x + w + i, y + h + i],
                           outline=color)

    return img


# ------------------------------------------------------------------
# 内部工具
# ------------------------------------------------------------------

def _iou(a: dict, b: dict) -> float:
    """计算两个 bbox 的 IoU"""
    ax1, ay1 = a['x'], a['y']
    ax2, ay2 = a['x'] + a['w'], a['y'] + a['h']
    bx1, by1 = b['x'], b['y']
    bx2, by2 = b['x'] + b['w'], b['y'] + b['h']

    ix1 = max(ax1, bx1)
    iy1 = max(ay1, by1)
    ix2 = min(ax2, bx2)
    iy2 = min(ay2, by2)

    if ix2 <= ix1 or iy2 <= iy1:
        return 0.0

    inter = (ix2 - ix1) * (iy2 - iy1)
    area_a = a['w'] * a['h']
    area_b = b['w'] * b['h']
    union = area_a + area_b - inter

    return inter / union if union > 0 else 0.0
