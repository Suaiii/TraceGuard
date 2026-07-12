"""
FastAPI 路由定义 — TraceGuard 可解释分析服务

端点:
  POST /api/v1/analyze        — 单图完整分析
  POST /api/v1/analyze/batch  — 批量分析 (最多20张)
  GET  /api/v1/health         — 健康检查
  GET  /api/v1/config         — 当前配置
"""

import sys
import os
import time

# 确保项目根在 path
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__))))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from .schemas import (
    AnalysisRequest, AnalysisResponse, AnalysisOptions,
    BatchRequest, BatchResponse,
    HealthResponse, ConfigResponse,
    BBoxItem, DimensionScores, Metadata, SavedFiles,
)
from detection.inference_api import Detector
from explanation.pipeline import ExplanationPipeline
from explanation.utils import base64_to_image

# ------------------------------------------------------------------
# 全局单例
# ------------------------------------------------------------------

_detector: Detector = None
_pipeline: ExplanationPipeline = None
_config: dict = None


def get_pipeline() -> ExplanationPipeline:
    global _pipeline
    if _pipeline is None:
        raise HTTPException(status_code=503, detail="服务未初始化，请稍后重试")
    return _pipeline


def get_config() -> dict:
    global _config
    return _config or {}


# ------------------------------------------------------------------
# 应用工厂
# ------------------------------------------------------------------

def create_app(checkpoint_path: str = "checkpoints/best.pth",
               device: str = "cuda",
               pipeline_config: dict = None) -> FastAPI:
    """
    创建 FastAPI 应用，加载模型和流水线。

    Args:
        checkpoint_path: 模型权重路径
        device: 推理设备 (cuda|cpu)
        pipeline_config: 流水线配置

    Returns:
        FastAPI 实例
    """
    global _detector, _pipeline, _config

    _config = pipeline_config or {}

    # 加载检测器
    print(f"[API] 加载模型: {checkpoint_path} (device={device})")
    _detector = Detector(checkpoint_path=checkpoint_path, device=device)

    # 初始化流水线
    _pipeline = ExplanationPipeline(_detector, config=_config)
    print(f"[API] 流水线已就绪")

    app = FastAPI(
        title="TraceGuard API",
        description="AIGC 图像安全审核 — 可解释检测取证 + 篡改定位",
        version="0.4.0",
    )

    # CORS (允许前端跨域)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ------ 路由定义 ------

    @app.get("/api/v1/health", response_model=HealthResponse)
    async def health_check():
        """健康检查"""
        import torch
        model = _detector.model if _detector else None
        total_params = sum(p.numel() for p in model.parameters()) / 1e6 if model else 0
        return HealthResponse(
            status="healthy",
            model_loaded=_detector is not None,
            device=str(_detector.device) if _detector else "unknown",
            cuda_available=torch.cuda.is_available(),
            model_params=f"{total_params:.1f}M",
        )

    @app.get("/api/v1/config", response_model=ConfigResponse)
    async def current_config():
        """查看当前流水线配置"""
        cfg = get_config()
        return ConfigResponse(
            heatmap_method=cfg.get('heatmap_method', 'gradcam'),
            overlay_alpha=cfg.get('overlay_alpha', 0.5),
            localization_enabled=cfg.get('enable_localization', True),
            localization_scales=cfg.get('localization_scales', [224, 160]),
            stride_ratio=cfg.get('localization_stride_ratio', 0.5),
            language=cfg.get('language', 'zh'),
            detail_level=cfg.get('detail_level', 'standard'),
            risk_weights=cfg.get('risk_weights', None),
            device=str(_detector.device) if _detector else "unknown",
        )

    @app.post("/api/v1/analyze", response_model=AnalysisResponse)
    async def analyze(request: AnalysisRequest):
        """
        单图完整分析: 热力图 + 篡改定位 + 风险评分 + 自然语言解释
        """
        pipeline = get_pipeline()

        # 合并请求级 options 到 pipeline config
        if request.options:
            _apply_options(pipeline, request.options)

        try:
            # 解码图像
            img = base64_to_image(request.image_base64)
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"图像解码失败: {e}")

        try:
            result = pipeline.run(img)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"分析失败: {e}")

        return _build_response(result)

    @app.post("/api/v1/analyze/batch", response_model=BatchResponse)
    async def analyze_batch(request: BatchRequest):
        """
        批量分析 (最多20张)
        """
        if len(request.images_base64) > 20:
            raise HTTPException(status_code=400, detail="批量最多支持20张图片")

        pipeline = get_pipeline()
        if request.options:
            _apply_options(pipeline, request.options)

        t0 = time.perf_counter()
        results = []
        errors = 0

        for b64 in request.images_base64:
            try:
                img = base64_to_image(b64)
                r = pipeline.run(img)
                results.append(_build_response(r))
            except Exception as e:
                errors += 1
                # 错误条目返回占位响应
                results.append(AnalysisResponse(
                    status="error",
                    label="error",
                    fake_prob=0, risk_score=0, risk_level="error",
                    explanation="", explanation_brief=f"错误: {e}",
                    bbox_list=[],
                    dimension_scores=DimensionScores(
                        fake_prob=0, artifact_intensity=0,
                        tamper_area=0, region_count=0, consistency=0
                    ),
                    overlay_b64="", mask_b64="",
                    elapsed_ms=0,
                    metadata=Metadata(
                        heatmap_method="", overlay_alpha=0,
                        localization_enabled=False, language="",
                        risk_weights={}
                    ),
                ))

        return BatchResponse(
            results=results,
            total_elapsed_ms=round((time.perf_counter() - t0) * 1000, 2),
            success_count=len(results) - errors,
            error_count=errors,
        )

    return app


# ------------------------------------------------------------------
# 辅助函数
# ------------------------------------------------------------------

def _build_response(result: dict) -> AnalysisResponse:
    """将 pipeline 结果转换为 Pydantic 响应对象"""
    return AnalysisResponse(
        status="success",
        label=result['label'],
        fake_prob=result['fake_prob'],
        risk_score=result['risk_score'],
        risk_level=result['risk_level'],
        explanation=result['explanation'],
        explanation_brief=result['explanation_brief'],
        bbox_list=[BBoxItem(**b) for b in result.get('bbox_list', [])],
        dimension_scores=DimensionScores(**result.get('dimension_scores', {})),
        overlay_b64=result['overlay_b64'],
        mask_b64=result['mask_b64'],
        tamper_mask_b64=result.get('tamper_mask_b64'),
        tamper_overlay_b64=result.get('tamper_overlay_b64'),
        bbox_image_b64=result.get('bbox_image_b64'),
        elapsed_ms=result['elapsed_ms'],
        metadata=Metadata(
            heatmap_method=result['metadata'].get('heatmap_method', ''),
            overlay_alpha=result['metadata'].get('overlay_alpha', 0),
            localization_enabled=result['metadata'].get('localization_enabled', False),
            language=result['metadata'].get('language', ''),
            risk_weights=result['metadata'].get('risk_weights', {}),
        ),
    )


def _apply_options(pipeline: ExplanationPipeline, options: AnalysisOptions):
    """动态更新流水线配置 (部分参数)"""
    pipeline.heatmap_generator.overlay_alpha = options.overlay_alpha
    if hasattr(pipeline, 'tamper_detector'):
        pipeline.tamper_detector.patch_analyzer.scales = options.localization_scales
        pipeline.tamper_detector.patch_analyzer.stride_ratio = options.stride_ratio
        pipeline.tamper_detector.min_region_area = options.min_region_area
    pipeline.text_explainer.language = options.language
    pipeline.text_explainer.detail_level = options.detail_level
