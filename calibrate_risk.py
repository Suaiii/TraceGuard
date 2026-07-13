#!/usr/bin/env python
"""
风险阈值校准分析脚本

在 CASIA v1 全量数据上运行 ExplanationPipeline, 收集逐样本的
fake_prob、risk_score、五维分数和 bbox 信息, 对比两套审核策略:

  策略 A (fake_prob 单独): fake_prob > 0.5 → 需要人工复核
  策略 B (五维风险融合):  risk_level ∈ {medium, high} → 需要人工复核

同时校准 low/medium/high 的阈值边界。

用法:
    python calibrate_risk.py \
        --au-dir dataset/CASIAv1/Au/Au \
        --tp-dir "dataset/CASIAv1/Modified Tp" \
        --checkpoint checkpoints/best.pth \
        --device cuda \
        --output-dir results/risk
"""

import sys
import os
import json
import csv
import argparse
import time
import math
from pathlib import Path

import numpy as np
import pandas as pd
from PIL import Image
from tqdm import tqdm

# 确保项目根目录在 sys.path 中
PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT))

from detection import Detector
from explanation import ExplanationPipeline


# =========================================================================
# Pipeline 输出收集
# =========================================================================

def collect_pipeline_outputs(image_paths, labels, pipeline, desc='Processing'):
    """
    对所有图片运行 ExplanationPipeline, 收集逐样本结果。

    Args:
        image_paths: list[Path] — 图片路径
        labels: list[str] — 'real' | 'fake' 图像级标签
        pipeline: ExplanationPipeline 实例
        desc: tqdm 进度条描述

    Returns:
        pd.DataFrame — 每行一张图
    """
    rows = []
    error_count = 0

    for img_path, gt_label in tqdm(
        list(zip(image_paths, labels)), desc=desc, unit='img'
    ):
        try:
            result = pipeline.run(str(img_path))
            dims = result['dimension_scores']
            rows.append({
                'filename': img_path.name,
                'ground_truth': gt_label,
                'pred_label': result['label'],
                'fake_prob': result['fake_prob'],
                'tamper_type': result['tamper_type'],
                'risk_score': result['risk_score'],
                'risk_level': result['risk_level'],
                'dim_fake_prob': dims.get('fake_prob', 0.0),
                'dim_artifact_intensity': dims.get('artifact_intensity', 0.0),
                'dim_tamper_area': dims.get('tamper_area', 0.0),
                'dim_region_count': dims.get('region_count', 0.0),
                'dim_consistency': dims.get('consistency', 0.0),
                'bbox_count': len(result['bbox_list']),
                'elapsed_ms': result['elapsed_ms'],
            })
        except Exception as exc:
            error_count += 1
            rows.append({
                'filename': img_path.name,
                'ground_truth': gt_label,
                'pred_label': 'error',
                'fake_prob': None, 'tamper_type': None,
                'risk_score': None, 'risk_level': None,
                'dim_fake_prob': None, 'dim_artifact_intensity': None,
                'dim_tamper_area': None, 'dim_region_count': None,
                'dim_consistency': None, 'bbox_count': None, 'elapsed_ms': None,
            })

    if error_count:
        print(f'  [WARN] {error_count} images failed')

    return pd.DataFrame(rows)


# =========================================================================
# 分布分析
# =========================================================================

def analyze_distribution(df):
    """
    fake_prob 和 risk_score 的分布统计。

    Returns:
        tuple (stats_dict, level_dist_dict, level_by_gt_dict)
    """
    valid = df.dropna(subset=['fake_prob', 'risk_score'])

    stats = {}
    for col in ['fake_prob', 'risk_score']:
        real_vals = valid[valid['ground_truth'] == 'real'][col]
        fake_vals = valid[valid['ground_truth'] == 'fake'][col]

        stats[col] = {
            'real': {
                'mean': round(float(real_vals.mean()), 4),
                'std':  round(float(real_vals.std()), 4),
                'min':  round(float(real_vals.min()), 4),
                'max':  round(float(real_vals.max()), 4),
                'median': round(float(real_vals.median()), 4),
                'q25':  round(float(real_vals.quantile(0.25)), 4),
                'q75':  round(float(real_vals.quantile(0.75)), 4),
            },
            'fake': {
                'mean': round(float(fake_vals.mean()), 4),
                'std':  round(float(fake_vals.std()), 4),
                'min':  round(float(fake_vals.min()), 4),
                'max':  round(float(fake_vals.max()), 4),
                'median': round(float(fake_vals.median()), 4),
                'q25':  round(float(fake_vals.quantile(0.25)), 4),
                'q75':  round(float(fake_vals.quantile(0.75)), 4),
            },
        }

    # 风险等级分布
    level_dist = valid['risk_level'].value_counts().to_dict()
    level_by_gt = (
        valid.groupby('ground_truth')['risk_level']
        .value_counts()
        .unstack(fill_value=0)
        .to_dict()
    )

    return stats, level_dist, level_by_gt


# =========================================================================
# 策略对比
# =========================================================================

def compare_strategies(df):
    """
    对比 "fake_prob 单独" vs "五维风险融合" 两套审核触发策略。

    策略 A: fake_prob > 0.5  → needs_review
    策略 B: risk_level ∈ {medium, high}  → needs_review

    Returns:
        dict: agreement_rate, per-strategy PRF, conflict case counts & details
    """
    valid = df.dropna(subset=['fake_prob', 'risk_score', 'risk_level']).copy()
    if len(valid) == 0:
        return {'error': 'No valid samples after dropping NA', 'total_samples': 0}

    valid['strategy_A_review'] = valid['fake_prob'] > 0.5
    valid['strategy_B_review'] = valid['risk_level'].isin(['medium', 'high'])
    valid['is_fake_gt'] = valid['ground_truth'].isin(['fake', 'tampered'])

    # 一致率
    agreement = float((valid['strategy_A_review'] == valid['strategy_B_review']).mean())

    # A 复核但 B 不触发 — 风险融合"放行"
    a_only = valid[valid['strategy_A_review'] & ~valid['strategy_B_review']]

    # B 复核但 A 不触发 — 风险融合"独特捕获" (核心关注)
    b_only = valid[~valid['strategy_A_review'] & valid['strategy_B_review']]

    # 以 GT 为准计算 Precision / Recall / F1
    def compute_prf(col):
        tp = int((valid[col] & valid['is_fake_gt']).sum())
        fp = int((valid[col] & ~valid['is_fake_gt']).sum())
        fn = int((~valid[col] & valid['is_fake_gt']).sum())
        tn = int((~valid[col] & ~valid['is_fake_gt']).sum())
        p = tp / (tp + fp) if (tp + fp) > 0 else 0.0
        r = tp / (tp + fn) if (tp + fn) > 0 else 0.0
        f1 = 2 * p * r / (p + r) if (p + r) > 0 else 0.0
        return {
            'precision': round(p, 4), 'recall': round(r, 4), 'f1': round(f1, 4),
            'tp': tp, 'fp': fp, 'fn': fn, 'tn': tn,
        }

    return {
        'agreement_rate': round(agreement, 4),
        'total_samples': len(valid),
        'strategy_A': compute_prf('strategy_A_review'),
        'strategy_B': compute_prf('strategy_B_review'),
        'a_only_count': len(a_only),
        'b_only_count': len(b_only),
        'b_only_summary': {
            'mean_fake_prob': round(float(b_only['fake_prob'].mean()), 4) if len(b_only) > 0 else 0,
            'mean_risk_score': round(float(b_only['risk_score'].mean()), 4) if len(b_only) > 0 else 0,
            'mean_bbox_count': round(float(b_only['bbox_count'].mean()), 1) if len(b_only) > 0 else 0,
            'true_fake_ratio': round(float(b_only['is_fake_gt'].mean()), 4) if len(b_only) > 0 else 0,
        },
        'conflict_cases': b_only[[
            'filename', 'ground_truth', 'fake_prob', 'risk_score',
            'risk_level', 'bbox_count', 'tamper_type'
        ]].to_dict('records'),
    }


# =========================================================================
# 阈值校准
# =========================================================================

def calibrate_thresholds(df):
    """
    基于实际数据分布校准 low/medium/high 阈值。

    三套方案:
      1. current      — 当前硬编码值 [0, 0.35), [0.35, 0.70), [0.70, 1.0]
      2. equal_freq   — 等频三等分 (tercile)
      3. gt_optimized — 以 GT 为准, 扫阈值最大化 F1
    """
    valid = df.dropna(subset=['risk_score']).copy()
    valid['is_fake'] = valid['ground_truth'].isin(['fake', 'tampered'])

    # ---- 等频分桶 ----
    tercile_1 = float(valid['risk_score'].quantile(1 / 3))
    tercile_2 = float(valid['risk_score'].quantile(2 / 3))

    # ---- GT 优化 ----
    # 寻找高风险阈值 (区分 medium → high), 最大化 F1
    best_f1, best_high = 0.0, 0.70
    for t in np.arange(0.30, 0.95, 0.02):
        pred = valid['risk_score'] >= t
        tp = int((pred & valid['is_fake']).sum())
        fp = int((pred & ~valid['is_fake']).sum())
        fn = int((~pred & valid['is_fake']).sum())
        p = tp / (tp + fp) if (tp + fp) > 0 else 0.0
        r = tp / (tp + fn) if (tp + fn) > 0 else 0.0
        f1 = 2 * p * r / (p + r) if (p + r) > 0 else 0.0
        if f1 > best_f1:
            best_f1, best_high = f1, t

    # 寻找中风险阈值 (区分 low → medium), 最大化 F1
    best_f1_med, best_medium = 0.0, 0.35
    for t in np.arange(0.10, 0.60, 0.02):
        pred = valid['risk_score'] >= t
        tp = int((pred & valid['is_fake']).sum())
        fp = int((pred & ~valid['is_fake']).sum())
        fn = int((~pred & valid['is_fake']).sum())
        p = tp / (tp + fp) if (tp + fp) > 0 else 0.0
        r = tp / (tp + fn) if (tp + fn) > 0 else 0.0
        f1 = 2 * p * r / (p + r) if (p + r) > 0 else 0.0
        if f1 > best_f1_med:
            best_f1_med, best_medium = f1, t

    # ---- risk_score 的 PR 曲线数据 (供后续绘图) ----
    pr_points = []
    thresholds = np.arange(0.05, 1.0, 0.05)
    for t in thresholds:
        pred = valid['risk_score'] >= t
        tp = int((pred & valid['is_fake']).sum())
        fp = int((pred & ~valid['is_fake']).sum())
        fn = int((~pred & valid['is_fake']).sum())
        p = tp / (tp + fp) if (tp + fp) > 0 else 0.0
        r = tp / (tp + fn) if (tp + fn) > 0 else 0.0
        pr_points.append({
            'threshold': round(float(t), 2),
            'precision': round(p, 4),
            'recall': round(r, 4),
            'tp': tp, 'fp': fp, 'fn': fn,
        })

    return {
        'current': {
            'low': [0.0, 0.35], 'medium': [0.35, 0.70], 'high': [0.70, 1.0],
        },
        'equal_frequency': {
            'low': [0.0, round(tercile_1, 3)],
            'medium': [round(tercile_1, 3), round(tercile_2, 3)],
            'high': [round(tercile_2, 3), 1.0],
        },
        'gt_optimized': {
            'low': [0.0, round(best_medium, 3)],
            'medium': [round(best_medium, 3), round(best_high, 3)],
            'high': [round(best_high, 3), 1.0],
            'medium_boundary_f1': round(best_f1_med, 4),
            'high_boundary_f1': round(best_f1, 4),
        },
        'pr_curve_data': pr_points,
    }


# =========================================================================
# 主流程
# =========================================================================

def main():
    parser = argparse.ArgumentParser(description='风险阈值校准分析')
    parser.add_argument('--au-dir', required=True,
                        help='CASIA Au 目录 (真实图像)')
    parser.add_argument('--tp-dir', required=True,
                        help='CASIA Modified Tp 目录 (篡改图像)')
    parser.add_argument('--checkpoint', default='checkpoints/best.pth',
                        help='模型权重路径')
    parser.add_argument('--device', default='cuda',
                        help='推理设备 (cuda | cpu)')
    parser.add_argument('--output-dir', default='results/risk',
                        help='输出目录')
    parser.add_argument('--max-samples', type=int, default=0,
                        help='限制样本数 (0 = 全量, 用于快速验证)')
    args = parser.parse_args()

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # ---- 收集图片路径 --------------------------------------------------------
    au_dir = Path(args.au_dir)
    tp_dir = Path(args.tp_dir)

    au_files = sorted(
        list(au_dir.glob('*.jpg')) + list(au_dir.glob('*.png'))
    )
    tp_files = sorted(
        list(tp_dir.rglob('*.jpg')) + list(tp_dir.rglob('*.png'))
    )

    print(f'Au  (real)    : {len(au_files)} images')
    print(f'Tp  (tampered): {len(tp_files)} images')

    if args.max_samples > 0:
        n_each = args.max_samples // 2
        au_files = au_files[:n_each]
        tp_files = tp_files[:n_each]
        print(f'  → limited to {len(au_files)} Au + {len(tp_files)} Tp')

    all_paths = au_files + tp_files
    all_labels = ['real'] * len(au_files) + ['fake'] * len(tp_files)
    total = len(all_paths)

    # ---- 初始化 Pipeline ----------------------------------------------------
    print(f'\n加载模型: {args.checkpoint}  (device={args.device})')
    detector = Detector(checkpoint_path=args.checkpoint, device=args.device)
    pipeline = ExplanationPipeline(detector, config={
        'enable_localization': True,
        'language': 'zh',
        'overlay_alpha': 0.5,
        'smooth_sigma': 3.0,
        'localization_scales': [224, 160],
        'localization_stride_ratio': 0.5,
        'localization_batch_size': 32,
        'threshold_method': 'percentile',
        'threshold_percentile': 90,
        'min_region_area': 256,
        'nms_iou_threshold': 0.3,
        'open_radius': 3,
        'close_radius': 5,
    })

    # ---- 运行全量 Pipeline ------------------------------------------------
    print(f'\n对 {total} 张图片运行完整 pipeline ...')
    t0 = time.perf_counter()
    df = collect_pipeline_outputs(all_paths, all_labels, pipeline,
                                  desc='Pipeline')
    elapsed = time.perf_counter() - t0
    print(f'完成: {elapsed:.0f}s ({elapsed / total:.2f}s/image)')

    # 保存原始输出
    csv_path = output_dir / 'risk_pipeline_outputs.csv'
    df.to_csv(csv_path, index=False)
    print(f'原始输出 → {csv_path}')

    # ---- 分布分析 ---------------------------------------------------------
    print(f'\n{"=" * 60}')
    print('分布分析')
    print(f'{"=" * 60}')

    stats, level_dist, level_by_gt = analyze_distribution(df)

    print(f'\nfake_prob 分布:')
    for gt in ['real', 'fake']:
        s = stats['fake_prob'][gt]
        print(f'  {gt:5s}: mean={s["mean"]:.4f}  median={s["median"]:.4f}  '
              f'q25={s["q25"]:.4f}  q75={s["q75"]:.4f}  '
              f'range=[{s["min"]:.4f}, {s["max"]:.4f}]')

    print(f'\nrisk_score 分布:')
    for gt in ['real', 'fake']:
        s = stats['risk_score'][gt]
        print(f'  {gt:5s}: mean={s["mean"]:.4f}  median={s["median"]:.4f}  '
              f'q25={s["q25"]:.4f}  q75={s["q75"]:.4f}  '
              f'range=[{s["min"]:.4f}, {s["max"]:.4f}]')

    print(f'\n风险等级分布: {level_dist}')

    # ---- 策略对比 ---------------------------------------------------------
    print(f'\n{"=" * 60}')
    print('策略对比: fake_prob-only vs 五维风险融合')
    print(f'{"=" * 60}')

    comparison = compare_strategies(df)
    print(f'\n一致率 (Agreement): {comparison["agreement_rate"]:.2%}')
    print(f'\n策略 A (fake_prob > 0.5 → 复核):')
    a = comparison['strategy_A']
    print(f'  P={a["precision"]:.4f}  R={a["recall"]:.4f}  F1={a["f1"]:.4f}  '
          f'(TP={a["tp"]}  FP={a["fp"]}  FN={a["fn"]})')
    print(f'\n策略 B (risk_level ≥ medium → 复核):')
    b = comparison['strategy_B']
    print(f'  P={b["precision"]:.4f}  R={b["recall"]:.4f}  F1={b["f1"]:.4f}  '
          f'(TP={b["tp"]}  FP={b["fp"]}  FN={b["fn"]})')
    print(f'\nA 触发但 B 不触发: {comparison["a_only_count"]}  ← 风险融合"放行"')
    print(f'B 触发但 A 不触发: {comparison["b_only_count"]}  ← 风险融合"独特捕获"')
    if comparison['b_only_count'] > 0:
        bs = comparison['b_only_summary']
        print(f'  独特捕获样本: mean fake_prob={bs["mean_fake_prob"]:.4f}, '
              f'mean risk_score={bs["mean_risk_score"]:.4f}, '
              f'mean bbox={bs["mean_bbox_count"]:.1f}, '
              f'其中真篡改={bs["true_fake_ratio"]:.2%}')

    # ---- 阈值校准 ---------------------------------------------------------
    print(f'\n{"=" * 60}')
    print('阈值校准')
    print(f'{"=" * 60}')

    calibration = calibrate_thresholds(df)
    schemes = ['current', 'equal_frequency', 'gt_optimized']
    for scheme in schemes:
        c = calibration[scheme]
        print(f'\n{scheme}:')
        print(f'  low:    [{c["low"][0]:.3f}, {c["low"][1]:.3f})')
        print(f'  medium: [{c["medium"][0]:.3f}, {c["medium"][1]:.3f})')
        print(f'  high:   [{c["high"][0]:.3f}, {c["high"][1]:.3f}]')
        if scheme == 'gt_optimized':
            print(f'  (medium boundary F1={c["medium_boundary_f1"]:.4f}, '
                  f'high boundary F1={c["high_boundary_f1"]:.4f})')

    # ---- 保存汇总 ---------------------------------------------------------
    conflict_cases = comparison.pop('conflict_cases', [])
    summary = {
        'dataset': f'{len(au_files)} real (Au) + {len(tp_files)} tampered (Tp) = {total} images',
        'distribution': stats,
        'risk_level_distribution': {str(k): v for k, v in level_dist.items()},
        'strategy_comparison': comparison,
        'threshold_calibration': calibration,
        'notes': [
            '数据来自 CASIA v1 (传统拼接/copy-move 篡改), 非 AIGC 伪造',
            'fake_prob 来自跨域 AIGC 检测器 (MambaOut-Small), 未经传统篡改数据微调',
            '因此 fake_prob 分布可能整体偏低, risk_score 同理',
            '风险阈值和策略对比结论应标注数据域差异, 不可直接推广到 AIGC 场景',
            '最终阈值确定需结合张潇跨域实验数据复核',
            '当前 RiskScorer 的阈值在 scorer.py 中硬编码, YAML risk.levels 不生效 (已知问题)',
        ],
    }
    summary_path = output_dir / 'risk_calibration_summary.json'
    with open(summary_path, 'w', encoding='utf-8') as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)
    print(f'\n汇总 JSON → {summary_path}')

    # 冲突案例 CSV
    if conflict_cases:
        conflict_path = output_dir / 'risk_conflict_cases.csv'
        with open(conflict_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=conflict_cases[0].keys())
            writer.writeheader()
            writer.writerows(conflict_cases)
        print(f'冲突案例 → {conflict_path}')

    print(f'\n=== 风险校准分析完成 ===')


if __name__ == '__main__':
    main()
