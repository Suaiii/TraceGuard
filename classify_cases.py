#!/usr/bin/env python
"""
传播链案例自动分类脚本

对同一 sample_id 的原图与各传播条件版本运行 ExplanationPipeline,
对比传播前后变化, 自动分为三类:

  成功案例: 传播后检测、热力图和定位证据依然有效
  衰减案例: 传播后 fake_prob / 热力图 / bbox 明显退化
  冲突案例: 全局判定与局部证据不一致, 需要人工复核

用法:
    python classify_cases.py \
        --manifest propagation_manifest.csv \
        --checkpoint checkpoints/best.pth \
        --device cuda \
        --output-dir results/case_classification

Manifest CSV 格式:
    sample_id,condition,image_path,ground_truth
    S001,original,data/original/S001.png,fake
    S001,wechat,data/wechat/S001.jpg,fake
    S001,weibo,data/weibo/S001.jpg,fake
    S002,original,data/original/S002.png,real
    ...
"""

import sys
import json
import csv
import argparse
import time
import math
from pathlib import Path
from collections import defaultdict

import numpy as np
from PIL import Image
from tqdm import tqdm

PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT))

from detection import Detector
from explanation import ExplanationPipeline


# =========================================================================
# 分类阈值（可按需调整）
# =========================================================================

CLASSIFICATION_CONFIG = {
    # 成功案例要求
    'success': {
        'max_fake_prob_drop': 0.15,       # fake_prob 最大允许下降
        'min_heatmap_ssim': 0.60,         # 热力图最低相似度
        'max_bbox_change_ratio': 0.50,    # bbox 数量最大允许变化比例
        'require_label_correct': True,     # 是否要求 label 仍然正确
        'max_risk_level_jump': 0,          # risk_level 最大允许跳变级数 (0=不变)
    },
    # 衰减案例要求
    'degradation': {
        'min_fake_prob_drop': 0.20,        # fake_prob 最低下降阈值
        'max_heatmap_ssim': 0.40,         # 热力图最高相似度（低于此值视为衰减）
        'min_bbox_drop_ratio': 0.50,      # bbox 数量最低减少比例
        # 满足任一条件即视为衰减
    },
    # 冲突案例要求
    'conflict': {
        # 以下情况视为冲突:
        # - 全局 fake 但无 bbox
        # - 全局 real 但有 bbox
        # - fake_prob 和 risk_level 方向不一致
        # - 传播前后 tamper_type 发生根本性变化
    },
}


# =========================================================================
# 辅助函数
# =========================================================================

def compute_heatmap_ssim(hm1, hm2):
    """计算两张热力图的 SSIM (简化版: 相关性 + 均值接近度)。"""
    if hm1 is None or hm2 is None:
        return 0.0
    if hm1.shape != hm2.shape:
        hm2_pil = Image.fromarray((hm2 * 255).astype(np.uint8))
        hm2_pil = hm2_pil.resize((hm1.shape[1], hm1.shape[0]), Image.BILINEAR)
        hm2 = np.array(hm2_pil).astype(np.float32) / 255.0

    # 使用皮尔逊相关系数作为结构相似度代理
    h1_flat = hm1.flatten()
    h2_flat = hm2.flatten()
    if h1_flat.std() < 1e-8 or h2_flat.std() < 1e-8:
        return 0.0
    corr = np.corrcoef(h1_flat, h2_flat)[0, 1]
    return max(0.0, float(corr))


def risk_level_to_int(level):
    """将 risk_level 转为整数以便计算跳变。"""
    mapping = {'low': 0, 'medium': 1, 'high': 2}
    return mapping.get(level, 0)


def classify_sample(original_result, variant_result, variant_condition, config=None):
    """
    对比原图与传播变体的 pipeline 输出, 返回分类结果。

    Args:
        original_result: ExplanationPipeline.run() 在原图上的输出
        variant_result: ExplanationPipeline.run() 在传播变体上的输出
        variant_condition: str — 'wechat' | 'weibo' | 'jpeg' | 'resize' | 'screenshot'
        config: 分类阈值配置

    Returns:
        dict: 分类详情
    """
    config = config or CLASSIFICATION_CONFIG

    o = original_result
    v = variant_result

    # --- 基本变化量 ---
    fake_prob_delta = o['fake_prob'] - v['fake_prob']
    bbox_count_o = len(o['bbox_list'])
    bbox_count_v = len(v['bbox_list'])
    bbox_change = bbox_count_o - bbox_count_v
    bbox_change_ratio = abs(bbox_change) / max(bbox_count_o, 1)
    risk_jump = risk_level_to_int(o['risk_level']) - risk_level_to_int(v['risk_level'])

    # 热力图 SSIM (需要从 base64 解码 — 跳过此步骤，用 dim_scores 的 artifact_intensity 变化替代)
    artifact_delta = (
        o['dimension_scores'].get('artifact_intensity', 0)
        - v['dimension_scores'].get('artifact_intensity', 0)
    )

    # --- 冲突检测 ---
    has_conflict = False
    conflict_reasons = []

    # 全局 fake 但无 bbox
    if v['label'] == 'fake' and bbox_count_v == 0:
        has_conflict = True
        conflict_reasons.append('fake_label_no_bbox')

    # 全局 real 但有 bbox
    if v['label'] in ('real', 'local_tamper') and bbox_count_v > 0 and v['label'] != 'local_tamper':
        has_conflict = True
        conflict_reasons.append('real_label_with_bbox')

    # tamper_type 根本性变化 (local_tamper ↔ full_aigc)
    tamper_types = {o.get('tamper_type', ''), v.get('tamper_type', '')}
    if 'local_tamper' in tamper_types and 'full_aigc' in tamper_types:
        has_conflict = True
        conflict_reasons.append('tamper_type_flip')

    # fake_prob 与 risk_level 方向不一致 (fake_prob 下降但 risk_level 上升, 或反之)
    if fake_prob_delta < -0.1 and risk_jump < 0:
        has_conflict = True
        conflict_reasons.append('prob_down_risk_up')
    if fake_prob_delta > 0.1 and risk_jump > 0:
        has_conflict = True
        conflict_reasons.append('prob_up_risk_down')

    # --- 衰减检测 ---
    deg_cfg = config['degradation']
    is_degraded = (
        fake_prob_delta >= deg_cfg['min_fake_prob_drop']
        or artifact_delta >= 0.15  # 热力图响应明显减弱
        or (bbox_count_o > 0 and bbox_count_v == 0)  # bbox 完全消失
        or risk_jump >= 1  # risk_level 下降一级
    )

    # --- 成功检测 ---
    suc_cfg = config['success']
    is_success = (
        fake_prob_delta <= suc_cfg['max_fake_prob_drop']
        and artifact_delta <= 0.10
        and bbox_change_ratio <= suc_cfg['max_bbox_change_ratio']
        and risk_jump <= suc_cfg['max_risk_level_jump']
        and not has_conflict
    )

    # --- 综合判定 ---
    if has_conflict and is_degraded:
        category = 'conflict_degraded'
        priority = 1
    elif has_conflict:
        category = 'conflict'
        priority = 2
    elif is_degraded and not is_success:
        category = 'degradation'
        priority = 3
    elif is_success:
        category = 'success'
        priority = 4
    else:
        category = 'moderate'  # 不属于典型三类, 证据部分保留
        priority = 5

    return {
        'variant_condition': variant_condition,
        'category': category,
        'priority': priority,
        'fake_prob_delta': round(fake_prob_delta, 4),
        'artifact_delta': round(artifact_delta, 4),
        'bbox_change': bbox_change,
        'bbox_change_ratio': round(bbox_change_ratio, 2),
        'risk_jump': risk_jump,
        'has_conflict': has_conflict,
        'conflict_reasons': ';'.join(conflict_reasons) if conflict_reasons else '',
        'is_degraded': is_degraded,
        'original': {
            'fake_prob': o['fake_prob'], 'label': o['label'],
            'risk_score': o['risk_score'], 'risk_level': o['risk_level'],
            'bbox_count': bbox_count_o, 'tamper_type': o.get('tamper_type', ''),
        },
        'variant': {
            'fake_prob': v['fake_prob'], 'label': v['label'],
            'risk_score': v['risk_score'], 'risk_level': v['risk_level'],
            'bbox_count': bbox_count_v, 'tamper_type': v.get('tamper_type', ''),
        },
    }


# =========================================================================
# 批量处理
# =========================================================================

def run_classification(manifest_df, pipeline, output_dir):
    """
    对 manifest 中所有样本运行分类。

    manifest_df: list[dict], 每行含 sample_id, condition, image_path, ground_truth
    pipeline: ExplanationPipeline 实例
    output_dir: Path

    Returns:
        list[dict]: 所有对比结果
    """
    # 按 sample_id 分组
    groups = defaultdict(list)
    for row in manifest_df:
        groups[row['sample_id']].append(row)

    all_results = []
    errors = []

    for sample_id, rows in tqdm(groups.items(), desc='Classifying', unit='sample'):
        # 找到 original
        orig_row = next((r for r in rows if r['condition'] == 'original'), None)
        if orig_row is None:
            errors.append({'sample_id': sample_id, 'error': 'no original row'})
            continue

        gt = orig_row['ground_truth']

        # 跑原图 pipeline
        try:
            orig_result = pipeline.run(orig_row['image_path'])
        except Exception as exc:
            errors.append({'sample_id': sample_id, 'error': f'original pipeline: {exc}'})
            continue

        # 对每个传播变体跑 pipeline 并对比
        variant_rows = [r for r in rows if r['condition'] != 'original']
        for vrow in variant_rows:
            try:
                var_result = pipeline.run(vrow['image_path'])
            except Exception as exc:
                errors.append({
                    'sample_id': sample_id,
                    'condition': vrow['condition'],
                    'error': f'variant pipeline: {exc}',
                })
                continue

            comparison = classify_sample(orig_result, var_result, vrow['condition'])
            comparison['sample_id'] = sample_id
            comparison['ground_truth'] = gt
            comparison['original_path'] = orig_row['image_path']
            comparison['variant_path'] = vrow['image_path']
            all_results.append(comparison)

    if errors:
        print(f'[WARN] {len(errors)} errors:')
        for e in errors[:5]:
            print(f'  {e}')

    return all_results


# =========================================================================
# 汇总与精选
# =========================================================================

def summarize(results, output_dir):
    """汇总分类统计并精选每类最佳案例。"""
    categories = defaultdict(list)
    for r in results:
        categories[r['category']].append(r)

    print(f'\n{"=" * 60}')
    print('案例分类统计')
    print(f'{"=" * 60}')
    for cat in ['success', 'degradation', 'conflict', 'conflict_degraded', 'moderate']:
        items = categories.get(cat, [])
        print(f'  {cat:20s}: {len(items):4d}')

    # --- 精选每类代表性案例 ---
    selected = {}

    # 成功案例: 选 fake_prob 下降最少、bbox 保持最好的
    success_items = categories.get('success', [])
    if success_items:
        success_items.sort(key=lambda r: abs(r['fake_prob_delta']))
        selected['success'] = success_items[:5]

    # 衰减案例: 选 fake_prob 下降最多、证据退化最明显的
    degradation_items = categories.get('degradation', []) + categories.get('conflict_degraded', [])
    if degradation_items:
        degradation_items.sort(key=lambda r: -r['fake_prob_delta'])
        selected['degradation'] = degradation_items[:5]

    # 冲突案例: 选证据矛盾最尖锐的（有 bbox 但 label=real 优先）
    conflict_items = categories.get('conflict', []) + categories.get('conflict_degraded', [])
    if conflict_items:
        conflict_items.sort(
            key=lambda r: (
                -len(r.get('conflict_reasons', '').split(';')),
                -abs(r['fake_prob_delta']),
            )
        )
        # 去重（conflict_degraded 可能同时出现在两个列表）
        seen = set()
        unique_conflicts = []
        for r in conflict_items:
            key = (r['sample_id'], r['variant_condition'])
            if key not in seen:
                seen.add(key)
                unique_conflicts.append(r)
        selected['conflict'] = unique_conflicts[:5]

    # --- 输出精选案例 ---
    print(f'\n{"=" * 60}')
    print('精选案例')
    print(f'{"=" * 60}')

    selected_csv = output_dir / 'case_classification_selected.csv'
    selected_rows = []
    for cat, items in selected.items():
        print(f'\n--- {cat} ---')
        for item in items:
            print(f"  {item['sample_id']} ({item['variant_condition']}): "
                  f"fake_prob {item['original']['fake_prob']:.3f}→{item['variant']['fake_prob']:.3f} "
                  f"(Δ={item['fake_prob_delta']:+.3f}), "
                  f"bbox {item['original']['bbox_count']}→{item['variant']['bbox_count']}, "
                  f"risk {item['original']['risk_level']}→{item['variant']['risk_level']}")
            if item.get('conflict_reasons'):
                print(f"        冲突原因: {item['conflict_reasons']}")
            selected_rows.append({
                'category': cat,
                'sample_id': item['sample_id'],
                'variant_condition': item['variant_condition'],
                'original_fake_prob': item['original']['fake_prob'],
                'variant_fake_prob': item['variant']['fake_prob'],
                'fake_prob_delta': item['fake_prob_delta'],
                'original_bbox': item['original']['bbox_count'],
                'variant_bbox': item['variant']['bbox_count'],
                'original_risk': item['original']['risk_level'],
                'variant_risk': item['variant']['risk_level'],
                'conflict_reasons': item.get('conflict_reasons', ''),
                'category_detail': item['category'],
            })

    with open(selected_csv, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=selected_rows[0].keys())
        writer.writeheader()
        writer.writerows(selected_rows)
    print(f'\n精选案例 → {selected_csv}')

    # --- 按传播条件汇总 ---
    print(f'\n{"=" * 60}')
    print('按传播条件汇总')
    print(f'{"=" * 60}')
    by_condition = defaultdict(lambda: defaultdict(int))
    for r in results:
        by_condition[r['variant_condition']][r['category']] += 1

    for cond in sorted(by_condition.keys()):
        counts = by_condition[cond]
        total = sum(counts.values())
        success_rate = counts.get('success', 0) / max(total, 1)
        degrade_rate = (counts.get('degradation', 0) + counts.get('conflict_degraded', 0)) / max(total, 1)
        conflict_rate = (counts.get('conflict', 0) + counts.get('conflict_degraded', 0)) / max(total, 1)
        print(f'  {cond:12s}: {total:3d} samples  '
              f'success={success_rate:.1%}  degrade={degrade_rate:.1%}  conflict={conflict_rate:.1%}')

    return selected, dict(categories)


# =========================================================================
# 主流程
# =========================================================================

def main():
    parser = argparse.ArgumentParser(description='传播链案例自动分类')
    parser.add_argument('--manifest', required=True,
                        help='CSV 文件: sample_id, condition, image_path, ground_truth')
    parser.add_argument('--checkpoint', default='checkpoints/best.pth',
                        help='模型权重路径')
    parser.add_argument('--device', default='cuda',
                        help='推理设备 (cuda | cpu)')
    parser.add_argument('--output-dir', default='results/case_classification',
                        help='输出目录')
    args = parser.parse_args()

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # ---- 加载 manifest ----------------------------------------------------
    manifest_path = Path(args.manifest)
    if not manifest_path.exists():
        print(f'[ERROR] Manifest 文件不存在: {manifest_path}')
        print(f'\n期望 CSV 格式 (UTF-8):')
        print(f'  sample_id,condition,image_path,ground_truth')
        print(f'  S001,original,data/original/S001.png,fake')
        print(f'  S001,wechat,data/wechat/S001.jpg,fake')
        print(f'  S001,weibo,data/weibo/S001.jpg,fake')
        print(f'  S002,original,data/original/S002.png,real')
        print(f'  ...')
        print(f'\n其中 condition 为: original, wechat, weibo, jpeg, resize, screenshot')
        sys.exit(1)

    with open(manifest_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        manifest = list(reader)

    required_cols = {'sample_id', 'condition', 'image_path', 'ground_truth'}
    if not required_cols.issubset(set(manifest[0].keys())):
        missing = required_cols - set(manifest[0].keys())
        print(f'[ERROR] CSV 缺少列: {missing}')
        print(f'当前列: {list(manifest[0].keys())}')
        sys.exit(1)

    sample_ids = sorted(set(r['sample_id'] for r in manifest))
    conditions = sorted(set(r['condition'] for r in manifest))
    print(f'Manifest: {len(sample_ids)} samples, '
          f'{len(manifest)} rows, '
          f'conditions: {conditions}')

    # ---- 初始化 Pipeline --------------------------------------------------
    print(f'\n加载模型: {args.checkpoint}  (device={args.device})')
    detector = Detector(checkpoint_path=args.checkpoint, device=args.device)
    pipeline = ExplanationPipeline(detector, config={
        'enable_localization': True,
        'language': 'zh',
        'overlay_alpha': 0.5,
        'smooth_sigma': 3.0,
    })

    # ---- 运行分类 ---------------------------------------------------------
    t0 = time.perf_counter()
    results = run_classification(manifest, pipeline, output_dir)
    elapsed = time.perf_counter() - t0
    print(f'\n完成: {elapsed:.0f}s ({elapsed / max(len(results), 1):.1f}s/comparison)')

    if not results:
        print('[ERROR] 无有效结果, 请检查 manifest 路径是否可访问')
        sys.exit(1)

    # ---- 汇总 & 精选 ------------------------------------------------------
    selected, categories = summarize(results, output_dir)

    # ---- 保存全量结果 -----------------------------------------------------
    all_csv = output_dir / 'case_classification_all.csv'
    fieldnames = [
        'sample_id', 'ground_truth', 'variant_condition', 'category', 'priority',
        'fake_prob_delta', 'artifact_delta', 'bbox_change', 'bbox_change_ratio',
        'risk_jump', 'has_conflict', 'conflict_reasons', 'is_degraded',
        'original_fake_prob', 'original_label', 'original_risk_score',
        'original_risk_level', 'original_bbox_count', 'original_tamper_type',
        'variant_fake_prob', 'variant_label', 'variant_risk_score',
        'variant_risk_level', 'variant_bbox_count', 'variant_tamper_type',
        'original_path', 'variant_path',
    ]
    with open(all_csv, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction='ignore')
        writer.writeheader()
        for r in results:
            row = {k: r.get(k, '') for k in fieldnames}
            # 展开嵌套字段
            row['original_fake_prob'] = r.get('original', {}).get('fake_prob', '')
            row['original_label'] = r.get('original', {}).get('label', '')
            row['original_risk_score'] = r.get('original', {}).get('risk_score', '')
            row['original_risk_level'] = r.get('original', {}).get('risk_level', '')
            row['original_bbox_count'] = r.get('original', {}).get('bbox_count', '')
            row['original_tamper_type'] = r.get('original', {}).get('tamper_type', '')
            row['variant_fake_prob'] = r.get('variant', {}).get('fake_prob', '')
            row['variant_label'] = r.get('variant', {}).get('label', '')
            row['variant_risk_score'] = r.get('variant', {}).get('risk_score', '')
            row['variant_risk_level'] = r.get('variant', {}).get('risk_level', '')
            row['variant_bbox_count'] = r.get('variant', {}).get('bbox_count', '')
            row['variant_tamper_type'] = r.get('variant', {}).get('tamper_type', '')
            writer.writerow(row)
    print(f'全量结果 → {all_csv}')

    # ---- 保存汇总 JSON -----------------------------------------------------
    summary = {
        'total_samples': len(sample_ids),
        'total_comparisons': len(results),
        'conditions': conditions,
        'category_counts': {cat: len(items) for cat, items in categories.items()},
        'selected_cases': {
            cat: [
                {
                    'sample_id': r['sample_id'],
                    'variant_condition': r['variant_condition'],
                    'fake_prob_delta': r['fake_prob_delta'],
                    'category': r['category'],
                }
                for r in items
            ]
            for cat, items in selected.items()
        },
        'classification_config': CLASSIFICATION_CONFIG,
        'notes': [
            '分类基于传播前后 ExplanationPipeline 全量输出对比',
            '阈值可在脚本顶部的 CLASSIFICATION_CONFIG 中调整',
            '精选案例为自动排序结果, 最终入报告的案例需人工复核挑选',
        ],
    }
    summary_path = output_dir / 'case_classification_summary.json'
    with open(summary_path, 'w', encoding='utf-8') as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)
    print(f'汇总 JSON → {summary_path}')

    # ---- 生成 manifest 模板 (供张潇参考) -----------------------------------
    template_path = output_dir / 'manifest_template.csv'
    with open(template_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['sample_id', 'condition', 'image_path', 'ground_truth'])
        writer.writerow(['S001', 'original', 'data/original/S001.png', 'fake'])
        writer.writerow(['S001', 'wechat', 'data/wechat/S001.jpg', 'fake'])
        writer.writerow(['S001', 'weibo', 'data/weibo/S001.jpg', 'fake'])
        writer.writerow(['S001', 'jpeg', 'data/jpeg/S001.jpg', 'fake'])
        writer.writerow(['S001', 'resize', 'data/resize/S001.png', 'fake'])
        writer.writerow(['S001', 'screenshot', 'data/screenshot/S001.png', 'fake'])
        writer.writerow(['S002', 'original', 'data/original/S002.png', 'real'])
        writer.writerow(['S002', 'wechat', 'data/wechat/S002.jpg', 'real'])
        writer.writerow(['...', '...', '...', '...'])
    print(f'Manifest 模板 → {template_path}')

    print(f'\n=== 案例分类完成 ===')
    print(f'\n下一步: 张潇按 {template_path} 格式提供 manifest, ')
    print(f'再运行本脚本即可自动分类并精选入报告案例。')


if __name__ == '__main__':
    main()
