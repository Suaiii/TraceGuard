"""
CLI 命令行接口

用法:
    # 单张分析 (JSON 输出到 stdout)
    python -m explanation.cli --input tests/fixtures/real.png

    # 保存解码后的图片
    python -m explanation.cli --input tests/fixtures/real.png --save-dir ./output

    # 跳过篡改定位 (仅热力图)
    python -m explanation.cli --input test.jpg --skip-localization

    # 指定 checkpoint 路径
    python -m explanation.cli --input test.jpg --checkpoint checkpoints/best.pth
"""

import argparse
import json
import os
import sys

# 将项目根目录加入 path，确保可导入 detection 模块
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from detection.inference_api import Detector
from explanation.pipeline import ExplanationPipeline
from explanation.config import load_and_convert


def main():
    parser = argparse.ArgumentParser(
        description='TraceGuard 可解释分析 CLI (热力图 + 篡改定位)',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python -m explanation.cli --input tests/fixtures/real.png
  python -m explanation.cli --input tests/fixtures/real.png --save-dir ./output
  python -m explanation.cli --input test.jpg --skip-localization
  python -m explanation.cli --input test.jpg --device cpu
  python -m explanation.cli --input test.jpg --config configs/default.yaml
        """
    )
    parser.add_argument('--input', '-i', required=True, help='输入图片路径')
    parser.add_argument('--config', default=None,
                        help='YAML 配置文件路径 (默认: 使用内置默认值)')
    parser.add_argument('--checkpoint', '-c', default='checkpoints/best.pth',
                        help='模型权重路径 (默认: checkpoints/best.pth)')
    parser.add_argument('--device', '-d', default='cuda', choices=['cuda', 'cpu'],
                        help='推理设备 (默认: cuda)')
    parser.add_argument('--save-dir', '-s', default=None,
                        help='保存解码后的 PNG 到此目录')
    parser.add_argument('--alpha', '-a', type=float, default=0.5,
                        help='热力图叠加透明度 (默认: 0.5)')
    parser.add_argument('--skip-localization', action='store_true',
                        help='跳过篡改定位模块 (仅输出热力图)')
    parser.add_argument('--scales', nargs='+', type=int, default=None,
                        help='滑动窗口尺寸列表 (默认: 从配置读取)')
    parser.add_argument('--stride-ratio', type=float, default=None,
                        help='滑动步长比例 (默认: 从配置读取)')
    parser.add_argument('--min-area', type=int, default=None,
                        help='最小可疑区域面积 (默认: 从配置读取)')
    parser.add_argument('--pretty', '-p', action='store_true', default=True,
                        help='格式化 JSON 输出 (默认开启)')
    parser.add_argument('--language', default='zh', choices=['zh', 'en'],
                        help='解释语言 (默认: zh)')
    parser.add_argument('--detail-level', default='standard',
                        choices=['brief', 'standard', 'detailed'],
                        help='解释详细程度 (默认: standard)')

    args = parser.parse_args()

    # 检查输入文件
    if not os.path.exists(args.input):
        print(f'[ERROR] 输入文件不存在: {args.input}', file=sys.stderr)
        sys.exit(1)

    # 初始化
    print(f'[CLI] 加载模型: {args.checkpoint}', file=sys.stderr)
    detector = Detector(checkpoint_path=args.checkpoint, device=args.device)

    # 加载配置 (YAML 优先, CLI 参数覆盖)
    if args.config:
        print(f'[CLI] 加载配置: {args.config}', file=sys.stderr)
        pipe_config = load_and_convert(args.config)
    else:
        pipe_config = load_and_convert()  # 使用默认值

    # CLI 参数覆盖配置文件中的默认值
    if args.alpha != 0.5:
        pipe_config['overlay_alpha'] = args.alpha
    if args.skip_localization:
        pipe_config['enable_localization'] = False
    if args.scales is not None:
        pipe_config['localization_scales'] = args.scales
    if args.stride_ratio is not None:
        pipe_config['localization_stride_ratio'] = args.stride_ratio
    if args.min_area is not None:
        pipe_config['min_region_area'] = args.min_area
    if args.language != 'zh':
        pipe_config['language'] = args.language
    if args.detail_level != 'standard':
        pipe_config['detail_level'] = args.detail_level

    pipeline = ExplanationPipeline(detector, config=pipe_config)

    # 推理
    mode = '热力图' if args.skip_localization else '热力图 + 篡改定位'
    print(f'[CLI] 分析图片: {args.input} (模式: {mode})', file=sys.stderr)
    result = pipeline.run(args.input)

    # 构建输出 JSON
    output = {
        'label': result['label'],
        'fake_prob': result['fake_prob'],
        'risk_score': result['risk_score'],
        'risk_level': result['risk_level'],
        'explanation': result['explanation'],
        'explanation_brief': result['explanation_brief'],
        'elapsed_ms': result['elapsed_ms'],
        'overlay_b64': result['overlay_b64'],
        'mask_b64': result['mask_b64'],
        'bbox_list': result.get('bbox_list', []),
        'dimension_scores': result.get('dimension_scores', {}),
        'metadata': result['metadata'],
    }

    # 包含定位结果
    if not args.skip_localization:
        output['tamper_mask_b64'] = result.get('tamper_mask_b64')
        output['tamper_overlay_b64'] = result.get('tamper_overlay_b64')
        output['bbox_image_b64'] = result.get('bbox_image_b64')
        output['localization_elapsed_ms'] = result.get('localization_elapsed_ms')

    json_str = json.dumps(output, indent=2 if args.pretty else None,
                          ensure_ascii=False)

    # 保存图片到文件
    if args.save_dir:
        from explanation.utils import base64_to_image
        os.makedirs(args.save_dir, exist_ok=True)
        base_name = os.path.splitext(os.path.basename(args.input))[0]

        files_to_save = [
            ('overlay', result['overlay_b64'], f'{base_name}_overlay.png'),
            ('mask', result['mask_b64'], f'{base_name}_mask.png'),
        ]
        if not args.skip_localization:
            files_to_save += [
                ('tamper_mask', result.get('tamper_mask_b64'), f'{base_name}_tamper_mask.png'),
                ('tamper_overlay', result.get('tamper_overlay_b64'), f'{base_name}_tamper_overlay.png'),
                ('bbox_image', result.get('bbox_image_b64'), f'{base_name}_bbox.png'),
            ]

        output['saved_files'] = {}
        for label, b64, fname in files_to_save:
            if b64:
                fpath = os.path.join(args.save_dir, fname)
                base64_to_image(b64).save(fpath)
                output['saved_files'][label] = fpath
                print(f'[CLI] 已保存: {fpath}', file=sys.stderr)

        json_str = json.dumps(output, indent=2 if args.pretty else None,
                              ensure_ascii=False)

    # 打印摘要 (不含 base64 和长文本)
    exclude_keys = ('overlay_b64', 'mask_b64',
                    'tamper_mask_b64', 'tamper_overlay_b64',
                    'bbox_image_b64', 'explanation')
    summary = {k: v for k, v in output.items() if k not in exclude_keys}
    print(f'[CLI] 结果摘要:', file=sys.stderr)
    print(json.dumps(summary, indent=2, ensure_ascii=False), file=sys.stderr)

    # stdout 输出完整 JSON (可重定向)
    print(json_str)


if __name__ == '__main__':
    main()
