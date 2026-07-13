"""
TraceGuard 批量数据分析 — 快速扫描大批量图片数据集

只输出检测指标 (不生成热力图/掩膜图)，大幅提速。

用法:
    python batch_analyze.py --input-dir ./images --output results
    python batch_analyze.py --input-dir tests/BigGAN --output batch_results
    python batch_analyze.py --input-dir tests/fixtures --output batch_results --csv results.csv

输出:
    summary.json      — 全部图片的结构化检测结果
    results.csv       — CSV 表格 (可选)
    batch_report.html — 汇总可视化报告 (饼图/柱状图/直方图/散点)
"""

import argparse
import csv
import json
import os
import sys
import time
from pathlib import Path

PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, PROJECT_ROOT)

from detection import Detector
from explanation import ExplanationPipeline
from explanation.visualization import Visualizer

SUPPORTED_EXTS = {'.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.webp'}


def main():
    parser = argparse.ArgumentParser(description='TraceGuard 批量数据分析')
    parser.add_argument('--input-dir', '-i', required=True, help='输入图片目录')
    parser.add_argument('--output', '-o', default='./batch_results', help='输出目录')
    parser.add_argument('--csv', default=None, help='同时导出 CSV 文件路径')
    parser.add_argument('--checkpoint', '-c', default='checkpoints/best.pth')
    parser.add_argument('--device', '-d', default='cuda', choices=['cuda', 'cpu'])
    parser.add_argument('--config', default=None, help='YAML 配置文件')
    parser.add_argument('--skip-localization', action='store_true', help='跳过定位 (极速模式)')

    args = parser.parse_args()

    # ---- 收集图片 ----
    input_dir = Path(args.input_dir)
    if not input_dir.is_dir():
        print(f'[ERROR] 目录不存在: {args.input_dir}')
        sys.exit(1)

    files = sorted([
        str(f) for f in input_dir.iterdir()
        if f.suffix.lower() in SUPPORTED_EXTS
    ])
    if not files:
        print(f'[ERROR] 目录中未找到支持的图片文件')
        sys.exit(1)

    print(f'[batch] 找到 {len(files)} 张图片')
    print(f'[batch] 模式: {"仅检测" if args.skip_localization else "检测+定位"}')

    # ---- 加载模型 ----
    print(f'[batch] 加载模型: {args.checkpoint}')
    detector = Detector(checkpoint_path=args.checkpoint, device=args.device)

    # ---- 配置 ----
    if args.config:
        from explanation.config import load_and_convert
        pipe_config = load_and_convert(args.config)
    else:
        from explanation.config import load_and_convert
        pipe_config = load_and_convert()

    if args.skip_localization:
        pipe_config['enable_localization'] = False

    pipeline = ExplanationPipeline(detector, config=pipe_config)

    # ---- 输出目录 ----
    os.makedirs(args.output, exist_ok=True)

    # ---- 逐张分析（不保存图片） ----
    results = []
    t_start = time.perf_counter()

    for i, path in enumerate(files):
        name = Path(path).name
        print(f'  [{i+1}/{len(files)}] {name:<40s} ', end='', flush=True)

        t0 = time.perf_counter()
        result = pipeline.run(path)
        elapsed = time.perf_counter() - t0

        # 只保留结构化数据，丢弃 base64 图片
        record = {
            'file': name,
            'label': result['label'],
            'tamper_type': result.get('tamper_type', 'unavailable'),
            'fake_prob': round(result['fake_prob'], 6),
            'risk_score': round(result['risk_score'], 4),
            'risk_level': result['risk_level'],
            'bbox_count': len(result['bbox_list']),
            'bbox_list': result['bbox_list'],
            'dimension_scores': result['dimension_scores'],
            'elapsed_ms': result['elapsed_ms'],
            'explanation_brief': result['explanation_brief'],
        }
        results.append(record)

        print(f'{record["label"]:4s}  fake={record["fake_prob"]:.4f}  '
              f'risk={record["risk_score"]:.2f}({record["risk_level"]})  '
              f'{record["bbox_count"]}bbox  {elapsed*1000:.0f}ms', flush=True)

    total_elapsed = (time.perf_counter() - t_start) * 1000

    # ---- 统计 ----
    fake_count = sum(1 for r in results if r['label'] == 'fake')
    real_count = len(results) - fake_count
    high_count = sum(1 for r in results if r['risk_level'] == 'high')
    medium_count = sum(1 for r in results if r['risk_level'] == 'medium')
    low_count = sum(1 for r in results if r['risk_level'] == 'low')

    # ---- 保存 summary.json ----
    summary = {
        'total': len(results),
        'fake': fake_count,
        'real': real_count,
        'high_risk': high_count,
        'medium_risk': medium_count,
        'low_risk': low_count,
        'total_elapsed_ms': round(total_elapsed, 2),
        'avg_elapsed_ms': round(total_elapsed / len(results), 2),
        'results': results,
    }
    json_path = os.path.join(args.output, 'summary.json')
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)
    print(f'\n[batch] JSON: {json_path}')

    # ---- 保存 CSV ----
    csv_path = args.csv or os.path.join(args.output, 'results.csv')
    with open(csv_path, 'w', newline='', encoding='utf-8-sig') as f:
        writer = csv.writer(f)
        writer.writerow(['file', 'label', 'tamper_type', 'fake_prob', 'risk_score', 'risk_level',
                         'bbox_count', 'artifact_intensity', 'tamper_area',
                         'region_count', 'consistency', 'elapsed_ms', 'brief'])
        for r in results:
            dims = r['dimension_scores']
            writer.writerow([
                r['file'], r['label'], r['tamper_type'], r['fake_prob'], r['risk_score'],
                r['risk_level'], r['bbox_count'],
                dims.get('artifact_intensity', 0),
                dims.get('tamper_area', 0),
                dims.get('region_count', 0),
                dims.get('consistency', 0),
                r['elapsed_ms'],
                r['explanation_brief'],
            ])
    print(f'[batch] CSV:  {csv_path}')

    # ---- 汇总 HTML 报告 ----
    viz = Visualizer()
    # 适配 batch_report 期望的格式
    viz_input = [{**r, 'file': os.path.join(str(input_dir), r['file'])} for r in results]
    html = viz.batch_report(viz_input, title=f'TraceGuard 批量分析 — {input_dir.name} ({len(results)} 张)')
    html_path = os.path.join(args.output, 'batch_report.html')
    with open(html_path, 'w', encoding='utf-8') as f:
        f.write(html)
    print(f'[batch] HTML: {html_path}')

    # ---- 终端摘要 ----
    print(f'\n{"="*65}')
    print(f'  TraceGuard 批量分析完成')
    print(f'{"="*65}')
    print(f'  总计:     {len(results)} 张')
    print(f'  Fake:     {fake_count} ({fake_count/len(results)*100:.1f}%)')
    print(f'  Real:     {real_count} ({real_count/len(results)*100:.1f}%)')
    print(f'  高风险:   {high_count} | 中风险: {medium_count} | 低风险: {low_count}')
    print(f'  总耗时:   {total_elapsed:.0f}ms | 平均: {total_elapsed/len(results):.0f}ms/张')
    print(f'  输出目录: {os.path.abspath(args.output)}')
    print(f'{"="*65}')


if __name__ == '__main__':
    main()
