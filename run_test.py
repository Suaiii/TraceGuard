"""
TraceGuard 一键测试脚本 — 对指定目录下所有图片跑全流程分析

用法:
    # 测试 BigGAN 样本
    python run_test.py --input-dir tests/BigGAN

    # 测试 fixtures 样本
    python run_test.py --input-dir tests/fixtures

    # 测试单张图
    python run_test.py --input tests/fixtures/real.png

    # 指定输出目录
    python run_test.py --input-dir tests/BigGAN --output my_results

输出 (每个输入图片一个子目录):
    analysis.json        结构化结果 (label, fake_prob, risk, bbox, dimensions)
    explanation.txt      三段式中文解释文本
    overlay.png          原图 + 热力图叠加
    mask.png             纯热力掩膜 (蓝→红紫)
    tamper_mask.png      篡改可疑掩膜
    tamper_overlay.png   原图 + 篡改掩膜叠加
    bbox_image.png       原图 + 可疑区域矩形框
    report.html          自包含 HTML 完整报告
    batch_summary.html   所有图片汇总对比报告 (仅在批量模式下生成)
    summary.json         汇总 JSON
"""

import argparse
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
from explanation.utils import base64_to_image

SUPPORTED_EXTS = {'.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.webp'}


def collect_images(path: str) -> list:
    """收集输入图片"""
    p = Path(path)
    if p.is_file():
        if p.suffix.lower() in SUPPORTED_EXTS:
            return [str(p)]
        else:
            raise ValueError(f"不支持的文件格式: {p.suffix}")
    elif p.is_dir():
        files = sorted([
            str(f) for f in p.iterdir()
            if f.suffix.lower() in SUPPORTED_EXTS
        ])
        if not files:
            raise ValueError(f"目录 {path} 中未找到支持的图片文件")
        return files
    else:
        raise FileNotFoundError(f"路径不存在: {path}")


def main():
    parser = argparse.ArgumentParser(
        description='TraceGuard 一键全流程分析',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python run_test.py --input-dir tests/BigGAN
  python run_test.py --input-dir tests/fixtures
  python run_test.py --input tests/fixtures/real.png --output my_results
  python run_test.py --input-dir tests/BigGAN --device cpu --skip-localization
        """
    )
    parser.add_argument('--input', '--input-dir', '-i', required=True,
                        help='输入图片路径或目录')
    parser.add_argument('--output', '-o', default='./case_study',
                        help='输出目录 (默认: ./case_study)')
    parser.add_argument('--checkpoint', '-c', default='checkpoints/best.pth',
                        help='模型权重路径 (默认: checkpoints/best.pth)')
    parser.add_argument('--device', '-d', default='cuda', choices=['cuda', 'cpu'],
                        help='推理设备 (默认: cuda)')
    parser.add_argument('--config', default=None,
                        help='YAML 配置文件路径 (默认: 使用内置默认值)')
    parser.add_argument('--skip-localization', action='store_true',
                        help='跳过篡改定位模块 (加速)')
    parser.add_argument('--alpha', type=float, default=0.5,
                        help='热力图叠加透明度 (默认: 0.5)')
    parser.add_argument('--language', default='zh', choices=['zh', 'en'],
                        help='解释语言 (默认: zh)')

    args = parser.parse_args()

    # ---- 收集图片 ----
    files = collect_images(args.input)
    print(f'[run_test] 找到 {len(files)} 张图片')

    # ---- 加载模型 ----
    print(f'[run_test] 加载模型: {args.checkpoint} (device={args.device})')
    detector = Detector(checkpoint_path=args.checkpoint, device=args.device)

    # ---- 加载配置 ----
    if args.config:
        from explanation.config import load_and_convert
        pipe_config = load_and_convert(args.config)
    else:
        from explanation.config import load_and_convert
        pipe_config = load_and_convert()

    if args.skip_localization:
        pipe_config['enable_localization'] = False
    pipe_config['overlay_alpha'] = args.alpha
    pipe_config['language'] = args.language

    pipeline = ExplanationPipeline(detector, config=pipe_config)
    viz = Visualizer()

    # ---- 输出目录 ----
    out_root = args.output
    os.makedirs(out_root, exist_ok=True)

    # ---- 逐张分析 ----
    all_results = []
    total_start = time.perf_counter()

    for i, path in enumerate(files):
        name = Path(path).stem
        print(f'\n[{i+1}/{len(files)}] {name}', flush=True)

        t0 = time.perf_counter()
        result = pipeline.run(path)
        wall_ms = (time.perf_counter() - t0) * 1000

        result['file'] = path
        result['case_key'] = name
        all_results.append(result)

        # 为每张图建子目录
        img_dir = os.path.join(out_root, f'{i+1:02d}_{name}')
        os.makedirs(img_dir, exist_ok=True)

        # JSON (不含 base64)
        json_out = {k: v for k, v in result.items()
                    if 'b64' not in k and k != 'explanation'}
        with open(f'{img_dir}/analysis.json', 'w', encoding='utf-8') as f:
            json.dump(json_out, f, ensure_ascii=False, indent=2)
        print(f'  -> analysis.json', flush=True)

        # 解释文本
        with open(f'{img_dir}/explanation.txt', 'w', encoding='utf-8') as f:
            f.write(result['explanation'])
        print(f'  -> explanation.txt', flush=True)

        # 解码图像
        img_map = {
            'overlay': result.get('overlay_b64'),
            'mask': result.get('mask_b64'),
            'tamper_mask': result.get('tamper_mask_b64'),
            'tamper_overlay': result.get('tamper_overlay_b64'),
            'bbox_image': result.get('bbox_image_b64'),
        }
        for img_name, b64 in img_map.items():
            if b64:
                base64_to_image(b64).save(f'{img_dir}/{img_name}.png')
        print(f'  -> overlay/mask/tamper_mask/tamper_overlay/bbox_image.png', flush=True)

        # HTML 报告
        html = viz.report(path, result)
        with open(f'{img_dir}/report.html', 'w', encoding='utf-8') as f:
            f.write(html)
        print(f'  -> report.html', flush=True)

        # 摘要
        print(f'  label={result["label"]}, fake_prob={result["fake_prob"]:.4f}, '
              f'risk={result["risk_score"]:.2f}({result["risk_level"]}), '
              f'{len(result["bbox_list"])}bboxes, {result["elapsed_ms"]:.0f}ms', flush=True)

    # ---- 批量汇总 ----
    total_elapsed = (time.perf_counter() - total_start) * 1000

    if len(all_results) > 1:
        print(f'\n[run_test] 生成批量汇总...', flush=True)
        batch_html = viz.batch_report(all_results,
                                      title=f'TraceGuard Analysis — {Path(args.input).name}')
        with open(f'{out_root}/batch_summary.html', 'w', encoding='utf-8') as f:
            f.write(batch_html)

    # ---- 汇总 JSON ----
    summary = []
    for r in all_results:
        summary.append({
            'file': Path(r['file']).name,
            'label': r['label'],
            'tamper_type': r.get('tamper_type', 'unavailable'),
            'fake_prob': round(r['fake_prob'], 4),
            'risk_score': round(r['risk_score'], 4),
            'risk_level': r['risk_level'],
            'bbox_count': len(r['bbox_list']),
            'dimension_scores': r['dimension_scores'],
            'elapsed_ms': r['elapsed_ms'],
            'brief': r['explanation_brief'],
        })

    with open(f'{out_root}/summary.json', 'w', encoding='utf-8') as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)

    # ---- 最终摘要 ----
    print(f'\n{"="*70}')
    print(f'  Analysis Complete')
    print(f'{"="*70}')
    print(f'  Images:  {len(all_results)}')
    print(f'  Fake:    {sum(1 for s in summary if s["label"] == "fake")}')
    print(f'  局部篡改证据: {sum(1 for s in summary if s["tamper_type"] == "local_tamper")}')
    print(f'  Real:    {sum(1 for s in summary if s["label"] == "real")}')
    print(f'  High:    {sum(1 for s in summary if s["risk_level"] == "high")}')
    print(f'  Medium:  {sum(1 for s in summary if s["risk_level"] == "medium")}')
    print(f'  Low:     {sum(1 for s in summary if s["risk_level"] == "low")}')
    print(f'  Time:    {total_elapsed:.0f}ms total, {total_elapsed/len(all_results):.0f}ms avg')
    print(f'  Output:  {os.path.abspath(out_root)}/')
    print(f'{"="*70}')


if __name__ == '__main__':
    main()
