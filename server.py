"""
TraceGuard FastAPI 服务入口

用法:
    python server.py                          # 默认 cuda:0, port 8000
    python server.py --device cpu --port 8080
    python server.py --checkpoint checkpoints/best.pth

文档:
    Swagger UI: http://localhost:8000/docs
    ReDoc:      http://localhost:8000/redoc
"""

import argparse
import uvicorn

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='TraceGuard API 服务')
    parser.add_argument('--checkpoint', '-c', default='checkpoints/best.pth',
                        help='模型权重路径')
    parser.add_argument('--config', default=None,
                        help='YAML 配置文件路径 (默认: 使用内置默认值)')
    parser.add_argument('--device', '-d', default='cuda', choices=['cuda', 'cpu'],
                        help='推理设备')
    parser.add_argument('--host', default='0.0.0.0', help='绑定地址')
    parser.add_argument('--port', '-p', type=int, default=8000, help='端口')
    parser.add_argument('--reload', action='store_true', help='开发热重载')
    parser.add_argument('--skip-localization', action='store_true',
                        help='默认跳过定位模块 (请求中可覆盖)')
    parser.add_argument('--language', default='zh', choices=['zh', 'en'],
                        help='默认解释语言')
    args = parser.parse_args()

    # 加载配置文件
    from explanation.config import load_and_convert
    if args.config:
        print(f"[Server] 加载配置: {args.config}")
        pipeline_config = load_and_convert(args.config)
    else:
        pipeline_config = load_and_convert()

    # CLI 参数覆盖
    if args.skip_localization:
        pipeline_config['enable_localization'] = False
    if args.language != 'zh':
        pipeline_config['language'] = args.language

    # 创建 (但不启动) app — uvicorn 会导入并启动
    from explanation.api.routes import create_app
    app = create_app(
        checkpoint_path=args.checkpoint,
        device=args.device,
        pipeline_config=pipeline_config,
    )

    print(f"\n{'='*60}")
    print(f"  TraceGuard API 服务")
    print(f"  地址:  http://{args.host}:{args.port}")
    print(f"  文档:  http://{args.host}:{args.port}/docs")
    print(f"  健康:  http://{args.host}:{args.port}/api/v1/health")
    print(f"  CUDA:  {'enabled' if args.device == 'cuda' else 'disabled'}")
    print(f"{'='*60}\n")

    uvicorn.run(
        app,
        host=args.host,
        port=args.port,
        reload=args.reload,
    )
