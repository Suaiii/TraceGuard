#!/usr/bin/env python
"""
定位模块定量评价脚本

在合成测试集上评估 TamperDetector 的像素级定位能力。
计算 IoU / Dice / Pixel F1 / Image Recall。
支持阈值扫描以找到最佳工作点。

用法:
    # 第一步: 生成合成测试集
    python -m experiments.synthetic_dataset \
        --au-dir dataset/CASIAv1/Au/Au \
        --tp-dir "dataset/CASIAv1/Modified Tp" \
        --output-dir results/localization/synthetic_dataset

    # 第二步: 运行定位评价
    python evaluate_localization.py \
        --synthetic-dir results/localization/synthetic_dataset \
        --checkpoint checkpoints/best.pth \
        --device cuda \
        --output-dir results/localization
"""

import sys
import os
import json
import csv
import argparse
import time
from pathlib import Path

import numpy as np
from PIL import Image

# 确保项目根目录在 sys.path 中
PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT))

from detection import Detector
from explanation.localization import TamperDetector
from explanation.localization.postprocess import (
    threshold_percentile,
    threshold_otsu,
    morphological_clean,
)


# =========================================================================
# 指标计算
# =========================================================================

def compute_mask_metrics(pred_mask, gt_mask):
    """
    计算预测掩膜与 GT 掩膜之间的像素级指标。

    Args:
        pred_mask: np.ndarray [H, W] bool — 预测二值掩膜
        gt_mask:   np.ndarray [H, W] bool — GT 二值掩膜

    Returns:
        dict: iou, dice, pixel_f1, precision, recall
    """
    # 对齐尺寸 (预测掩膜和 GT 掩膜应该已同尺寸，此处做安全检查)
    if pred_mask.shape != gt_mask.shape:
        gt_pil = Image.fromarray((gt_mask.astype(np.uint8)) * 255)
        gt_pil = gt_pil.resize(
            (pred_mask.shape[1], pred_mask.shape[0]), Image.NEAREST
        )
        gt_mask = np.array(gt_pil) > 128

    intersection = int((pred_mask & gt_mask).sum())
    pred_sum = int(pred_mask.sum())
    gt_sum = int(gt_mask.sum())
    union = int((pred_mask | gt_mask).sum())

    iou = intersection / union if union > 0 else 0.0
    dice = (2 * intersection / (pred_sum + gt_sum)
            if (pred_sum + gt_sum) > 0 else 0.0)

    tp = intersection
    fp = pred_sum - intersection
    fn = gt_sum - intersection

    precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    pixel_f1 = (2 * precision * recall / (precision + recall)
                if (precision + recall) > 0 else 0.0)

    return {
        'iou': round(iou, 4),
        'dice': round(dice, 4),
        'pixel_f1': round(pixel_f1, 4),
        'precision': round(precision, 4),
        'recall': round(recall, 4),
    }


def evaluate_one(tamper_detector, image_path, gt_mask, percentile=90):
    """
    对单张图片运行定位并计算所有指标。

    Args:
        tamper_detector: TamperDetector 实例
        image_path: 图片路径
        gt_mask: np.ndarray [H, W] bool — GT 掩膜
        percentile: 百分位阈值

    Returns:
        tuple (metrics_dict, score_map)
    """
    img = Image.open(image_path).convert('RGB')
    result = tamper_detector.detect(img)
    score_map = result['score_map']          # [H, W] 0~1
    bbox_list = result['bbox_list']

    # 从 score_map 生成二值掩膜
    binary_mask = threshold_percentile(score_map, percentile)
    binary_mask = morphological_clean(binary_mask, open_radius=3, close_radius=5)

    # 逐像素指标
    metrics = compute_mask_metrics(binary_mask, gt_mask)

    # 图像级指标
    metrics['detected'] = len(bbox_list) > 0
    metrics['bbox_count'] = len(bbox_list)
    metrics['elapsed_ms'] = round(result['elapsed_ms'], 1)
    metrics['score_map_mean'] = round(float(score_map.mean()), 4)
    metrics['score_map_max'] = round(float(score_map.max()), 4)

    return metrics, score_map


# =========================================================================
# 阈值扫描
# =========================================================================

def sweep_thresholds(tamper_detector, metadata, percentiles):
    """
    扫描不同百分位阈值，返回每个阈值下的平均指标。

    Args:
        tamper_detector: TamperDetector 实例
        metadata: 合成数据集元数据列表
        percentiles: 待扫描的百分位值列表

    Returns:
        list[dict]: 每个阈值一行
    """
    # 分离样本类型
    tampered_items = [m for m in metadata if m['type'] == 'tampered']
    clean_items = [m for m in metadata if m['type'] == 'clean']

    results = []
    for pct in percentiles:
        t_metrics = []
        for item in tampered_items:
            gt_mask = _load_gt_mask(item['mask_path'])
            metrics, _ = evaluate_one(tamper_detector, item['image_path'],
                                      gt_mask, percentile=pct)
            t_metrics.append(metrics)

        c_metrics = []
        for item in clean_items:
            gt_mask = _load_gt_mask(item['mask_path'])
            metrics, _ = evaluate_one(tamper_detector, item['image_path'],
                                      gt_mask, percentile=pct)
            c_metrics.append(metrics)

        row = {'percentile': pct}

        if t_metrics:
            row['tampered_avg_iou'] = round(np.mean([m['iou'] for m in t_metrics]), 4)
            row['tampered_avg_dice'] = round(np.mean([m['dice'] for m in t_metrics]), 4)
            row['tampered_avg_pixel_f1'] = round(np.mean([m['pixel_f1'] for m in t_metrics]), 4)
            row['tampered_avg_precision'] = round(np.mean([m['precision'] for m in t_metrics]), 4)
            row['tampered_avg_recall'] = round(np.mean([m['recall'] for m in t_metrics]), 4)
            row['tampered_detection_rate'] = round(np.mean([m['detected'] for m in t_metrics]), 4)
            row['tampered_avg_bbox'] = round(np.mean([m['bbox_count'] for m in t_metrics]), 2)

        if c_metrics:
            row['clean_fp_rate'] = round(np.mean([m['detected'] for m in c_metrics]), 4)
            row['clean_avg_bbox'] = round(np.mean([m['bbox_count'] for m in c_metrics]), 2)

        results.append(row)

        print(f"  pct={pct:3d}  "
              f"IoU={row.get('tampered_avg_iou', 0):.4f}  "
              f"Dice={row.get('tampered_avg_dice', 0):.4f}  "
              f"F1={row.get('tampered_avg_pixel_f1', 0):.4f}  "
              f"DetRate={row.get('tampered_detection_rate', 0):.2%}  "
              f"FP@clean={row.get('clean_fp_rate', 0):.2%}")

    return results


def _load_gt_mask(mask_path):
    """加载 GT mask 为 bool 数组。"""
    img = Image.open(mask_path).convert('L')
    return np.array(img) > 128


# =========================================================================
# 主流程
# =========================================================================

def main():
    parser = argparse.ArgumentParser(description='定位模块定量评价')
    parser.add_argument('--synthetic-dir', required=True,
                        help='合成数据集根目录 (含 metadata.json)')
    parser.add_argument('--checkpoint', default='checkpoints/best.pth',
                        help='模型权重路径')
    parser.add_argument('--device', default='cuda',
                        help='推理设备 (cuda | cpu)')
    parser.add_argument('--output-dir', default='results/localization',
                        help='输出目录')
    parser.add_argument('--threshold-percentile', type=int, default=90,
                        help='默认百分位阈值 (与 configs/default.yaml 保持一致)')
    args = parser.parse_args()

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # ---- 加载合成数据集元数据 ------------------------------------------------
    meta_path = Path(args.synthetic_dir) / 'metadata.json'
    if not meta_path.exists():
        print(f'[ERROR] 未找到 {meta_path}')
        print(f'请先运行: python -m experiments.synthetic_dataset '
              f'--au-dir dataset/CASIAv1/Au/Au '
              f'--tp-dir "dataset/CASIAv1/Modified Tp" '
              f'--output-dir {args.synthetic_dir}')
        sys.exit(1)

    with open(meta_path, 'r', encoding='utf-8') as f:
        metadata = json.load(f)

    tampered_items = [m for m in metadata if m['type'] == 'tampered']
    clean_items = [m for m in metadata if m['type'] == 'clean']
    print(f'合成测试集: {len(tampered_items)} tampered + {len(clean_items)} clean '
          f'= {len(metadata)} samples')

    # ---- 初始化 Detector & TamperDetector -----------------------------------
    print(f'\n加载模型: {args.checkpoint}  (device={args.device})')
    detector = Detector(checkpoint_path=args.checkpoint, device=args.device)
    tamper = TamperDetector(detector, config={
        'enable_patch': True,
        'enable_feature': True,
        'patch_weight': 0.4,
        'feature_weight': 0.6,
        'scales': [224, 160],
        'stride_ratio': 0.5,
        'batch_size': 32,
        'threshold_method': 'percentile',
        'threshold_percentile': args.threshold_percentile,
        'min_region_area': 256,
        'nms_iou_threshold': 0.3,
        'open_radius': 3,
        'close_radius': 5,
    })

    # ---- 逐样本评价 ---------------------------------------------------------
    print(f'\n{"=" * 70}')
    print(f'逐样本评价 (percentile = {args.threshold_percentile})')
    print(f'{"=" * 70}')

    all_metrics = []
    for item in metadata:
        gt_mask = _load_gt_mask(item['mask_path'])
        metrics, score_map = evaluate_one(
            tamper, item['image_path'], gt_mask,
            percentile=args.threshold_percentile,
        )

        metrics['sample_id'] = item['sample_id']
        metrics['type'] = item['type']
        metrics['bg_source'] = item['bg_source']
        all_metrics.append(metrics)

        # 简洁的正确/错误标记
        if item['type'] == 'tampered' and metrics['detected']:
            flag = '[OK] DETECTED'
        elif item['type'] == 'tampered' and not metrics['detected']:
            flag = '[!!] MISSED'
        elif item['type'] == 'clean' and not metrics['detected']:
            flag = '[OK] CLEAN'
        else:
            flag = '[!!] FALSE-POS'

        print(f"  [{flag:14s}] {item['sample_id']:04d} ({item['type']:8s})  "
              f"IoU={metrics['iou']:.3f}  Dice={metrics['dice']:.3f}  "
              f"F1={metrics['pixel_f1']:.3f}  bboxes={metrics['bbox_count']}  "
              f"{metrics['elapsed_ms']:.0f}ms")

    # ---- 按类型汇总 ---------------------------------------------------------
    t_metrics = [m for m in all_metrics if m['type'] == 'tampered']
    c_metrics = [m for m in all_metrics if m['type'] == 'clean']

    print(f'\n{"=" * 70}')
    print(f'汇总 (percentile = {args.threshold_percentile})')
    print(f'{"=" * 70}')

    if t_metrics:
        print(f'\nTampered ({len(t_metrics)} samples):')
        print(f'  Avg IoU:       {np.mean([m["iou"] for m in t_metrics]):.4f}')
        print(f'  Avg Dice:      {np.mean([m["dice"] for m in t_metrics]):.4f}')
        print(f'  Avg Pixel F1:  {np.mean([m["pixel_f1"] for m in t_metrics]):.4f}')
        print(f'  Avg Precision: {np.mean([m["precision"] for m in t_metrics]):.4f}')
        print(f'  Avg Recall:    {np.mean([m["recall"] for m in t_metrics]):.4f}')
        print(f'  Detection Rate:{np.mean([m["detected"] for m in t_metrics]):.2%}')
        print(f'  Avg bboxes:    {np.mean([m["bbox_count"] for m in t_metrics]):.1f}')

    if c_metrics:
        fp_rate = np.mean([m['detected'] for m in c_metrics])
        print(f'\nClean ({len(c_metrics)} samples):')
        print(f'  False-Pos Rate: {fp_rate:.2%}')
        print(f'  Avg bboxes:     {np.mean([m["bbox_count"] for m in c_metrics]):.1f}')

    # ---- 阈值扫描 -----------------------------------------------------------
    print(f'\n{"=" * 70}')
    print('阈值扫描')
    print(f'{"=" * 70}')

    percentiles = [50, 60, 70, 75, 80, 85, 90, 92, 95, 97]
    sweep_results = sweep_thresholds(tamper, metadata, percentiles)

    # ---- 保存输出 -----------------------------------------------------------
    # 逐样本 CSV
    csv_path = output_dir / 'localization_metrics.csv'
    fieldnames = [
        'sample_id', 'type', 'bg_source',
        'iou', 'dice', 'pixel_f1', 'precision', 'recall',
        'detected', 'bbox_count', 'score_map_mean', 'score_map_max', 'elapsed_ms',
    ]
    with open(csv_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction='ignore')
        writer.writeheader()
        writer.writerows(all_metrics)
    print(f'\n逐样本指标 → {csv_path}')

    # 阈值扫描 CSV
    sweep_csv = output_dir / 'localization_threshold_sweep.csv'
    sweep_fields = [
        'percentile',
        'tampered_avg_iou', 'tampered_avg_dice', 'tampered_avg_pixel_f1',
        'tampered_avg_precision', 'tampered_avg_recall',
        'tampered_detection_rate', 'tampered_avg_bbox',
        'clean_fp_rate', 'clean_avg_bbox',
    ]
    with open(sweep_csv, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=sweep_fields, extrasaction='ignore')
        writer.writeheader()
        writer.writerows(sweep_results)
    print(f'阈值扫描 → {sweep_csv}')

    # 汇总 JSON
    best_by_dice = max(
        [r for r in sweep_results if 'tampered_avg_dice' in r],
        key=lambda r: r['tampered_avg_dice'],
        default=None,
    )
    best_by_f1 = max(
        [r for r in sweep_results if 'tampered_avg_pixel_f1' in r],
        key=lambda r: r['tampered_avg_pixel_f1'],
        default=None,
    )

    summary = {
        'dataset': f'{len(tampered_items)} tampered + {len(clean_items)} clean '
                   f'(synthetic, seed=42)',
        'default_percentile': args.threshold_percentile,
        'tampered_metrics': {
            'avg_iou': round(np.mean([m['iou'] for m in t_metrics]), 4) if t_metrics else None,
            'avg_dice': round(np.mean([m['dice'] for m in t_metrics]), 4) if t_metrics else None,
            'avg_pixel_f1': round(np.mean([m['pixel_f1'] for m in t_metrics]), 4) if t_metrics else None,
            'avg_precision': round(np.mean([m['precision'] for m in t_metrics]), 4) if t_metrics else None,
            'avg_recall': round(np.mean([m['recall'] for m in t_metrics]), 4) if t_metrics else None,
            'detection_rate': round(np.mean([m['detected'] for m in t_metrics]), 4) if t_metrics else None,
        },
        'clean_metrics': {
            'fp_rate': round(fp_rate, 4) if c_metrics else None,
            'avg_bbox_count': round(np.mean([m['bbox_count'] for m in c_metrics]), 2) if c_metrics else None,
        },
        'best_percentile_by_dice': best_by_dice['percentile'] if best_by_dice else None,
        'best_percentile_by_f1': best_by_f1['percentile'] if best_by_f1 else None,
        'notes': [
            '合成测试集: 从 CASIA v1 Tp 图像剪裁 patch 硬粘贴到 Au 底图上',
            'GT 掩膜精确到像素, 但硬粘贴的拼接边界可能产生额外伪影',
            '此结果仅反映当前合成条件下的定位能力, 不代表 AIGC 局部篡改场景',
            'CASIA 为传统拼接/copy-move 篡改, 非 AIGC 伪造; 模型未在该域微调',
        ],
    }
    summary_path = output_dir / 'localization_summary.json'
    with open(summary_path, 'w', encoding='utf-8') as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)
    print(f'汇总 JSON → {summary_path}')

    print(f'\n=== 定位评价完成 ===')


if __name__ == '__main__':
    main()
