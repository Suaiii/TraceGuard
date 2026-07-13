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

def _binary_metrics(df, threshold):
    valid = df.dropna(subset=['risk_score']).copy()
    is_fake = valid['ground_truth'].isin(['fake', 'tampered'])
    predicted = valid['risk_score'] >= threshold
    tp = int((predicted & is_fake).sum())
    fp = int((predicted & ~is_fake).sum())
    fn = int((~predicted & is_fake).sum())
    tn = int((~predicted & ~is_fake).sum())
    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / (tp + fn) if tp + fn else 0.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    f05 = 1.25 * precision * recall / (0.25 * precision + recall) if precision + recall else 0.0
    return {
        'threshold': round(float(threshold), 4),
        'precision': round(precision, 4),
        'recall': round(recall, 4),
        'f1': round(f1, 4),
        'f0_5': round(f05, 4),
        'tp': tp, 'fp': fp, 'fn': fn, 'tn': tn,
    }


def stratified_calibration_split(df, fraction=0.6, seed=42):
    """Split each ground-truth class into calibration and untouched holdout rows."""
    if not 0.0 < fraction < 1.0:
        raise ValueError('calibration fraction must be between 0 and 1')
    calibration_parts = []
    holdout_parts = []
    for offset, (_, group) in enumerate(df.groupby('ground_truth', sort=True)):
        if len(group) < 2:
            raise ValueError('each ground-truth class needs at least two samples')
        calibration_count = min(len(group) - 1, max(1, int(round(len(group) * fraction))))
        calibration = group.sample(n=calibration_count, random_state=seed + offset)
        calibration_parts.append(calibration)
        holdout_parts.append(group.drop(calibration.index))
    return (
        pd.concat(calibration_parts).reset_index(drop=True),
        pd.concat(holdout_parts).reset_index(drop=True),
    )


def calibrate_thresholds(df, high_precision_target=0.95):
    """
    基于实际数据分布校准 low/medium/high 阈值。

    三套方案:
      1. current      — 当前硬编码值 [0, 0.35), [0.35, 0.70), [0.70, 1.0]
      2. equal_freq   — 等频三等分 (tercile)
      3. calibrated   — low/medium 边界最大化 F1；medium/high 边界优先达到高精度目标
    """
    valid = df.dropna(subset=['risk_score']).copy()
    if valid.empty or valid['ground_truth'].nunique() < 2:
        raise ValueError('risk calibration requires valid real and fake samples')

    # ---- 等频分桶 ----
    tercile_1 = float(valid['risk_score'].quantile(1 / 3))
    tercile_2 = float(valid['risk_score'].quantile(2 / 3))

    candidates = sorted(set(float(value) for value in valid['risk_score']))
    review_metrics = max(
        (_binary_metrics(valid, threshold) for threshold in candidates),
        key=lambda metrics: (metrics['f1'], metrics['recall'], metrics['threshold']),
    )
    review_threshold = review_metrics['threshold']

    high_candidates = [
        _binary_metrics(valid, threshold)
        for threshold in candidates
        if threshold > review_threshold
    ]
    target_candidates = [
        metrics for metrics in high_candidates
        if metrics['precision'] >= high_precision_target and metrics['tp'] > 0
    ]
    if target_candidates:
        high_metrics = max(
            target_candidates,
            key=lambda metrics: (metrics['recall'], -metrics['threshold']),
        )
        high_method = 'precision_target'
    elif high_candidates:
        high_metrics = max(
            high_candidates,
            key=lambda metrics: (metrics['f0_5'], metrics['precision'], -metrics['threshold']),
        )
        high_method = 'best_f0_5_fallback'
    else:
        fallback = min(1.0, review_threshold + 0.01)
        high_metrics = _binary_metrics(valid, fallback)
        high_method = 'empty_high_fallback'
    high_threshold = max(high_metrics['threshold'], min(1.0, review_threshold + 0.0001))

    # ---- risk_score 的 PR 曲线数据 (供后续绘图) ----
    pr_points = []
    thresholds = np.arange(0.05, 1.0, 0.05)
    for t in thresholds:
        pr_points.append(_binary_metrics(valid, t))

    return {
        'current': {
            'low': [0.0, 0.35], 'medium': [0.35, 0.70], 'high': [0.70, 1.0],
        },
        'equal_frequency': {
            'low': [0.0, round(tercile_1, 3)],
            'medium': [round(tercile_1, 3), round(tercile_2, 3)],
            'high': [round(tercile_2, 3), 1.0],
        },
        'calibrated': {
            'low': [0.0, review_threshold],
            'medium': [review_threshold, high_threshold],
            'high': [high_threshold, 1.0],
            'review_boundary_metrics': review_metrics,
            'high_boundary_metrics': high_metrics,
            'high_boundary_method': high_method,
            'high_precision_target': high_precision_target,
        },
        'pr_curve_data': pr_points,
    }


def evaluate_calibrated_levels(df, levels):
    """Evaluate frozen review/high boundaries on rows not used for calibration."""
    return {
        'sample_count': int(len(df)),
        'review': _binary_metrics(df, levels['medium'][0]),
        'high': _binary_metrics(df, levels['high'][0]),
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
    parser.add_argument('--calibration-fraction', type=float, default=0.6,
                        help='分层校准集比例；其余样本仅用于留出评估')
    parser.add_argument('--seed', type=int, default=42,
                        help='分层划分随机种子')
    parser.add_argument('--high-precision-target', type=float, default=0.95,
                        help='高风险边界的目标 precision')
    parser.add_argument('--dataset-name', default='custom balanced image set',
                        help='写入汇总的样本来源描述')
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

    calibration_df, holdout_df = stratified_calibration_split(
        df.dropna(subset=['risk_score']),
        fraction=args.calibration_fraction,
        seed=args.seed,
    )
    calibration = calibrate_thresholds(
        calibration_df,
        high_precision_target=args.high_precision_target,
    )
    holdout_evaluation = evaluate_calibrated_levels(
        holdout_df,
        calibration['calibrated'],
    )
    schemes = ['current', 'equal_frequency', 'calibrated']
    for scheme in schemes:
        c = calibration[scheme]
        print(f'\n{scheme}:')
        print(f'  low:    [{c["low"][0]:.3f}, {c["low"][1]:.3f})')
        print(f'  medium: [{c["medium"][0]:.3f}, {c["medium"][1]:.3f})')
        print(f'  high:   [{c["high"][0]:.3f}, {c["high"][1]:.3f}]')
        if scheme == 'calibrated':
            print(f'  review boundary calibration F1={c["review_boundary_metrics"]["f1"]:.4f}')
            print(f'  high boundary method={c["high_boundary_method"]}, '
                  f'precision={c["high_boundary_metrics"]["precision"]:.4f}')
    print(f'\n留出集评估 ({len(holdout_df)} samples): {holdout_evaluation}')

    # ---- 保存汇总 ---------------------------------------------------------
    conflict_cases = comparison.pop('conflict_cases', [])
    summary = {
        'dataset': f'{args.dataset_name}: {len(au_files)} real + {len(tp_files)} fake = {total} images',
        'distribution': stats,
        'risk_level_distribution': {str(k): v for k, v in level_dist.items()},
        'strategy_comparison': comparison,
        'threshold_calibration': calibration,
        'calibration_split': {
            'seed': args.seed,
            'calibration_fraction': args.calibration_fraction,
            'calibration_samples': len(calibration_df),
            'holdout_samples': len(holdout_df),
        },
        'holdout_evaluation': holdout_evaluation,
        'notes': [
            f'数据来源: {args.dataset_name}',
            'fake_prob 来自跨域 AIGC 检测器 (MambaOut-Small)',
            '风险阈值和策略对比结论仅适用于本次来源、划分和固定权重',
            '阈值仅在分层校准集上选择, 报告指标来自未参与选阈值的留出集',
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
