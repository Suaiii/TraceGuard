"""
批量处理脚本

用法:
    # 目录批量处理
    python -m explanation.batch --input-dir ./images --output-dir ./results

    # 文件列表批量
    python -m explanation.batch --input-list filelist.txt --output results.json

    # 并行处理
    python -m explanation.batch --input-dir ./images --output-dir ./results --parallel 2

    # 仅热力图 (跳过定位)
    python -m explanation.batch --input-dir ./images --output-dir ./results --skip-localization
"""

import argparse
import json
import os
import sys
import time
from pathlib import Path

# 项目根路径
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from detection.inference_api import Detector
from explanation.pipeline import ExplanationPipeline
from explanation.config import load_and_convert

SUPPORTED_EXTS = {'.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.webp'}


def process_single(pipeline: ExplanationPipeline, image_path: str,
                   save_dir: str = None) -> dict:
    """
    处理单张图片，返回结果 dict。

    Args:
        pipeline: ExplanationPipeline 实例
        image_path: 图片文件路径
        save_dir: 保存解码图片的目录 (可选)

    Returns:
        dict — pipeline 输出 (不含 base64 的摘要 + 元信息)
    """
    t0 = time.perf_counter()

    try:
        result = pipeline.run(image_path)
    except Exception as e:
        return {
            'file': image_path,
            'status': 'error',
            'error': str(e),
            'elapsed_ms': round((time.perf_counter() - t0) * 1000, 2),
        }

    filename = os.path.basename(image_path)
    elapsed = result['elapsed_ms']

    output = {
        'file': image_path,
        'status': 'success',
        'label': result['label'],
        'fake_prob': result['fake_prob'],
        'risk_score': result['risk_score'],
        'risk_level': result['risk_level'],
        'explanation_brief': result['explanation_brief'],
        'bbox_count': len(result.get('bbox_list', [])),
        'elapsed_ms': elapsed,
    }

    # 保存图片到磁盘
    if save_dir:
        from explanation.utils import base64_to_image
        base_name = os.path.splitext(filename)[0]

        save_map = {
            'overlay': result.get('overlay_b64'),
            'mask': result.get('mask_b64'),
            'tamper_mask': result.get('tamper_mask_b64'),
            'tamper_overlay': result.get('tamper_overlay_b64'),
            'bbox': result.get('bbox_image_b64'),
        }

        saved = {}
        for key, b64 in save_map.items():
            if b64:
                fpath = os.path.join(save_dir, f'{base_name}_{key}.png')
                base64_to_image(b64).save(fpath)
                saved[key] = fpath

        output['saved_files'] = saved

    return output


def process_directory(pipeline: ExplanationPipeline, input_dir: str,
                      output_dir: str, parallel: int = 1) -> list:
    """处理目录下所有图片"""
    image_files = sorted([
        os.path.join(input_dir, f)
        for f in os.listdir(input_dir)
        if os.path.splitext(f)[1].lower() in SUPPORTED_EXTS
    ])

    if not image_files:
        print(f"[batch] 目录 {input_dir} 中未找到支持的图片文件")
        return []

    os.makedirs(output_dir, exist_ok=True)

    if parallel > 1:
        return _process_parallel(pipeline, image_files, output_dir, parallel)
    else:
        return _process_sequential(pipeline, image_files, output_dir)


def _process_sequential(pipeline, image_files, output_dir):
    """顺序处理"""
    results = []
    total = len(image_files)
    t_start = time.perf_counter()

    for i, fpath in enumerate(image_files, 1):
        print(f"[batch] [{i}/{total}] {os.path.basename(fpath)} ... ", end='', flush=True)
        r = process_single(pipeline, fpath, save_dir=output_dir)
        results.append(r)
        print(f"{r['status']} ({r.get('elapsed_ms', 0):.0f}ms)")

    total_time = round((time.perf_counter() - t_start) * 1000, 2)
    print(f"\n[batch] 完成: {total} 张, 总耗时 {total_time}ms")
    return results


def _process_parallel(pipeline, image_files, output_dir, workers):
    """多进程并行处理"""
    from concurrent.futures import ProcessPoolExecutor, as_completed

    # 注意: GPU 模型无法在多进程中共享，parallel > 1 时每进程需独立加载
    # 此处使用简化实现，实际使用建议用 multiprocessing + spawn
    print(f"[batch] 并行模式暂使用顺序执行 (GPU 模型无法跨进程共享)")
    return _process_sequential(pipeline, image_files, output_dir)


def main():
    parser = argparse.ArgumentParser(
        description='TraceGuard 批量处理脚本',
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--input-dir', help='输入图片目录')
    group.add_argument('--input-list', help='图片路径列表文件 (每行一个)')

    parser.add_argument('--output-dir', '-o', default='./batch_output',
                        help='输出目录 (默认: ./batch_output)')
    parser.add_argument('--output-json', default=None,
                        help='输出 JSON 汇总文件路径')
    parser.add_argument('--checkpoint', '-c', default='checkpoints/best.pth',
                        help='模型权重路径')
    parser.add_argument('--config', default=None,
                        help='YAML 配置文件路径 (默认: 使用内置默认值)')
    parser.add_argument('--device', '-d', default='cuda', choices=['cuda', 'cpu'])
    parser.add_argument('--parallel', type=int, default=1,
                        help='并行进程数 (GPU 下建议 1)')
    parser.add_argument('--skip-localization', action='store_true',
                        help='跳过篡改定位 (加速)')
    parser.add_argument('--language', default='zh', choices=['zh', 'en'])
    parser.add_argument('--alpha', type=float, default=0.5)

    args = parser.parse_args()

    # 初始化
    print(f"[batch] 加载模型: {args.checkpoint}")
    detector = Detector(checkpoint_path=args.checkpoint, device=args.device)

    # 加载配置文件
    if args.config:
        print(f"[batch] 加载配置: {args.config}")
        pipe_config = load_and_convert(args.config)
    else:
        pipe_config = load_and_convert()

    # CLI 参数覆盖
    if args.skip_localization:
        pipe_config['enable_localization'] = False
    if args.language != 'zh':
        pipe_config['language'] = args.language
    pipe_config['overlay_alpha'] = args.alpha

    pipeline = ExplanationPipeline(detector, config=pipe_config)

    # 收集输入文件
    if args.input_dir:
        image_files = sorted([
            os.path.join(args.input_dir, f)
            for f in os.listdir(args.input_dir)
            if os.path.splitext(f)[1].lower() in SUPPORTED_EXTS
        ])
    else:
        with open(args.input_list, 'r') as f:
            image_files = [line.strip() for line in f if line.strip()]

    if not image_files:
        print("[batch] 未找到可处理的图片")
        sys.exit(0)

    print(f"[batch] 找到 {len(image_files)} 张图片")
    os.makedirs(args.output_dir, exist_ok=True)

    # 处理
    results = _process_sequential(pipeline, image_files, args.output_dir)

    # 保存 JSON 汇总
    if args.output_json:
        with open(args.output_json, 'w', encoding='utf-8') as f:
            json.dump({
                'total': len(results),
                'success': sum(1 for r in results if r['status'] == 'success'),
                'errors': sum(1 for r in results if r['status'] == 'error'),
                'results': results,
            }, f, ensure_ascii=False, indent=2)
        print(f"[batch] JSON 汇总已保存: {args.output_json}")

    # 摘要
    fake_count = sum(1 for r in results if r.get('label') == 'fake')
    print(f"\n[batch] 摘要: {len(results)}张 | fake={fake_count} | "
          f"real={len(results)-fake_count}")


if __name__ == '__main__':
    main()
