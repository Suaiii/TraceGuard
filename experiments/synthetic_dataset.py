"""
合成篡改测试集生成器

从 CASIA v1 Au (真实图) 与 Tp (篡改图) 构建像素级已知 GT 掩膜的合成测试集:
  - 将 Tp 图的随机 patch 硬粘贴到 Au 底图上
  - 粘贴区域即 GT 掩膜 (精确到像素)
  - 同时保留若干未修改 Au 图作为负对照

用法:
    python -m experiments.synthetic_dataset \
        --au-dir dataset/CASIAv1/Au/Au \
        --tp-dir "dataset/CASIAv1/Modified Tp" \
        --output-dir results/localization/synthetic_dataset \
        --num-tampered 40 --num-clean 10 --seed 42
"""

import os
import json
import random
import argparse
from pathlib import Path

import numpy as np
from PIL import Image


def generate_synthetic_dataset(
    au_dir,
    tp_dir,
    output_dir,
    num_tampered=40,
    num_clean=10,
    seed=42,
):
    """
    Generate synthetic tampered images with pixel-precise GT masks.

    Args:
        au_dir: Path to CASIA Au directory (authentic images, used as background).
        tp_dir: Path to CASIA Modified Tp directory (tampered images, used as patch source).
        output_dir: Output root directory.  Will create images/ and masks/ subdirectories.
        num_tampered: Number of synthetic tampered images to generate.
        num_clean: Number of unmodified Au images to include (negative controls).
        seed: Random seed for reproducibility.
    """
    random.seed(seed)
    np.random.seed(seed)

    out_images = Path(output_dir) / 'images'
    out_masks = Path(output_dir) / 'masks'
    out_images.mkdir(parents=True, exist_ok=True)
    out_masks.mkdir(parents=True, exist_ok=True)

    # --- Collect source images ---
    au_files = sorted(
        list(Path(au_dir).glob('*.jpg')) + list(Path(au_dir).glob('*.png'))
    )
    tp_files = sorted(
        list(Path(tp_dir).rglob('*.jpg')) + list(Path(tp_dir).rglob('*.png'))
    )

    if not au_files:
        raise FileNotFoundError(f'No images found in {au_dir}')
    if not tp_files:
        raise FileNotFoundError(f'No images found in {tp_dir}')

    print(f'Au (background) images : {len(au_files)}')
    print(f'Tp (patch source) images: {len(tp_files)}')

    metadata = []
    sample_id = 0

    # =====================================================================
    # 合成篡改图 — tampered samples
    # =====================================================================
    for i in range(num_tampered):
        # 随机选底图 (Au)
        bg_path = random.choice(au_files)
        bg = Image.open(bg_path).convert('RGB')
        bg_w, bg_h = bg.size

        # 随机选 patch 源 (Tp)
        src_path = random.choice(tp_files)
        src = Image.open(src_path).convert('RGB')
        src_w, src_h = src.size

        # 随机 patch 尺寸: 48–96 px (约占图像 2%–10%)
        max_pw = min(96, src_w, bg_w - 2)
        max_ph = min(96, src_h, bg_h - 2)
        min_pw = min(48, max_pw)
        min_ph = min(48, max_ph)

        if max_pw < 16 or max_ph < 16:
            print(f'  [SKIP] sample {sample_id}: image too small (bg={bg.size}, src={src.size})')
            continue

        patch_w = random.randint(min_pw, max_pw)
        patch_h = random.randint(min_ph, max_ph)

        # 随机裁剪位置 (从 Tp 源)
        src_x = random.randint(0, src_w - patch_w)
        src_y = random.randint(0, src_h - patch_h)
        patch = src.crop((src_x, src_y, src_x + patch_w, src_y + patch_h))

        # 随机粘贴位置 (到底图)
        paste_x = random.randint(0, bg_w - patch_w)
        paste_y = random.randint(0, bg_h - patch_h)

        # 合成
        synthetic = bg.copy()
        synthetic.paste(patch, (paste_x, paste_y))

        # GT mask (255 = tampered, 0 = clean)
        gt_mask = np.zeros((bg_h, bg_w), dtype=np.uint8)
        gt_mask[paste_y:paste_y + patch_h, paste_x:paste_x + patch_w] = 255

        # 保存
        img_path = out_images / f'{sample_id:04d}_synthetic.png'
        mask_path = out_masks / f'{sample_id:04d}_mask.png'
        synthetic.save(img_path)
        Image.fromarray(gt_mask).save(mask_path)

        metadata.append({
            'sample_id': sample_id,
            'type': 'tampered',
            'bg_source': bg_path.name,
            'patch_source': src_path.name,
            'paste_position': [paste_x, paste_y, patch_w, patch_h],
            'bg_size': [bg_w, bg_h],
            'image_path': str(img_path),
            'mask_path': str(mask_path),
        })
        sample_id += 1

    # =====================================================================
    # 未修改真实图 — clean (negative control) samples
    # =====================================================================
    selected_au = random.sample(au_files, min(num_clean, len(au_files)))
    for au_path in selected_au:
        au_img = Image.open(au_path).convert('RGB')
        w, h = au_img.size

        # 空 GT mask (全黑 = 无篡改)
        gt_mask = np.zeros((h, w), dtype=np.uint8)

        img_path = out_images / f'{sample_id:04d}_clean.png'
        mask_path = out_masks / f'{sample_id:04d}_mask.png'
        au_img.save(img_path)
        Image.fromarray(gt_mask).save(mask_path)

        metadata.append({
            'sample_id': sample_id,
            'type': 'clean',
            'bg_source': au_path.name,
            'patch_source': None,
            'paste_position': None,
            'bg_size': [w, h],
            'image_path': str(img_path),
            'mask_path': str(mask_path),
        })
        sample_id += 1

    # 保存元数据
    meta_path = Path(output_dir) / 'metadata.json'
    with open(meta_path, 'w', encoding='utf-8') as f:
        json.dump(metadata, f, indent=2, ensure_ascii=False)

    print(f'\nGenerated {num_tampered} tampered + {len(selected_au)} clean images → {output_dir}')
    print(f'Metadata → {meta_path}')
    return metadata


# =========================================================================
# CLI
# =========================================================================
if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='合成篡改测试集生成器')
    parser.add_argument('--au-dir', required=True)
    parser.add_argument('--tp-dir', required=True)
    parser.add_argument('--output-dir', default='results/localization/synthetic_dataset')
    parser.add_argument('--num-tampered', type=int, default=40)
    parser.add_argument('--num-clean', type=int, default=10)
    parser.add_argument('--seed', type=int, default=42)
    args = parser.parse_args()

    generate_synthetic_dataset(
        au_dir=args.au_dir,
        tp_dir=args.tp_dir,
        output_dir=args.output_dir,
        num_tampered=args.num_tampered,
        num_clean=args.num_clean,
        seed=args.seed,
    )
