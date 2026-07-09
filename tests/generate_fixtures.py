"""
生成测试夹具 local_tamper.png: 真实图 + 局部AIGC替换

用法:
    python tests/generate_fixtures.py
"""

import os
import sys
import numpy as np
from PIL import Image, ImageFilter

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

FIXTURES_DIR = os.path.join(PROJECT_ROOT, 'tests', 'fixtures')
REAL_PATH = os.path.join(FIXTURES_DIR, 'real.png')
AIGC_PATH = os.path.join(FIXTURES_DIR, 'full_aigc.png')
OUTPUT_PATH = os.path.join(FIXTURES_DIR, 'local_tamper.png')


def generate():
    """从真实图和AIGC图合成局部篡改样本"""
    print(f"加载真实图: {REAL_PATH}")
    real = Image.open(REAL_PATH).convert('RGB')
    print(f"  尺寸: {real.size}")

    print(f"加载AIGC图: {AIGC_PATH}")
    aigc = Image.open(AIGC_PATH).convert('RGB')
    print(f"  尺寸: {aigc.size}")

    # 从 AIGC 图中心裁剪一块区域
    patch_size = 400
    aw, ah = aigc.size
    left = (aw - patch_size) // 2
    top = (ah - patch_size) // 2
    aigc_patch = aigc.crop((left, top, left + patch_size, top + patch_size))

    # 粘贴到真实图右下角
    rw, rh = real.size
    paste_x = rw - patch_size - 50   # 距右边 50px
    paste_y = rh - patch_size - 50   # 距底边 50px

    # 创建羽化 mask (边缘渐隐，使拼接更自然)
    mask = Image.new('L', (patch_size, patch_size), 255)
    # 对 mask 做高斯模糊边缘 (先缩小再放大)
    feather = 20
    mask_array = np.array(mask, dtype=np.float32)
    # 边缘渐变
    for i in range(feather):
        val = int(255 * i / feather)
        mask_array[i, :] = np.minimum(mask_array[i, :], val)
        mask_array[-i-1, :] = np.minimum(mask_array[-i-1, :], val)
        mask_array[:, i] = np.minimum(mask_array[:, i], val)
        mask_array[:, -i-1] = np.minimum(mask_array[:, -i-1], val)
    mask = Image.fromarray(mask_array.astype(np.uint8))
    mask = mask.filter(ImageFilter.GaussianBlur(radius=8))

    # 合成
    result = real.copy()
    result.paste(aigc_patch, (paste_x, paste_y), mask)

    result.save(OUTPUT_PATH)
    print(f"已保存: {OUTPUT_PATH}")
    print(f"  篡改区域: ({paste_x}, {paste_y}, {patch_size}x{patch_size})")

    # 验证
    loaded = Image.open(OUTPUT_PATH)
    assert loaded.size == real.size, f"尺寸不匹配: {loaded.size} != {real.size}"
    print("验证通过: 尺寸一致")


if __name__ == '__main__':
    generate()
