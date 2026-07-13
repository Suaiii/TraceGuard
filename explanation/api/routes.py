"""
FastAPI routes for TraceGuard analysis service.

Endpoints:
  POST /api/v1/analyze
  POST /api/v1/analyze/batch
  GET  /api/v1/health
  GET  /api/v1/config
  GET  /
"""

import os
import sys
import time
from pathlib import Path

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from .schemas import (
    AnalysisRequest,
    AnalysisResponse,
    AnalysisOptions,
    BatchRequest,
    BatchResponse,
    HealthResponse,
    ConfigResponse,
    BBoxItem,
    DimensionScores,
    Metadata,
)
from detection.inference_api import Detector
from explanation.pipeline import ExplanationPipeline
from explanation.utils import base64_to_image

_detector: Detector | None = None
_pipeline: ExplanationPipeline | None = None
_config: dict | None = None


def get_pipeline() -> ExplanationPipeline:
    if _pipeline is None:
        raise HTTPException(status_code=503, detail="service is not initialized")
    return _pipeline


def get_config() -> dict:
    return _config or {}


def create_app(
    checkpoint_path: str = "checkpoints/best.pth",
    device: str = "cuda",
    pipeline_config: dict | None = None,
) -> FastAPI:
    """Create FastAPI app and initialize detector/pipeline singletons."""
    global _detector, _pipeline, _config

    _config = pipeline_config or {}

    print(f"[API] loading model: {checkpoint_path} (device={device})")
    _detector = Detector(checkpoint_path=checkpoint_path, device=device)

    _pipeline = ExplanationPipeline(_detector, config=_config)
    print("[API] pipeline ready")

    app = FastAPI(
        title="TraceGuard API",
        description="TraceGuard interpretable AIGC image detection service",
        version="0.4.0",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )

    web_dir = Path(PROJECT_ROOT) / "web"
    static_dir = web_dir / "static"
    if static_dir.exists():
        app.mount("/static", StaticFiles(directory=static_dir), name="static")

    @app.get("/", include_in_schema=False)
    async def index_page():
        index = web_dir / "index.html"
        if not index.exists():
            raise HTTPException(status_code=404, detail="frontend page not found")
        return FileResponse(index)

    @app.get("/api/v1/health", response_model=HealthResponse)
    async def health_check():
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
        cfg = get_config()
        return ConfigResponse(
            heatmap_method=cfg.get("heatmap_method", "gradcam"),
            overlay_alpha=cfg.get("overlay_alpha", 0.5),
            localization_enabled=cfg.get("enable_localization", True),
            localization_scales=cfg.get("localization_scales", [224, 160]),
            stride_ratio=cfg.get("localization_stride_ratio", 0.5),
            language=cfg.get("language", "zh"),
            detail_level=cfg.get("detail_level", "standard"),
            risk_weights=cfg.get("risk_weights", None),
            device=str(_detector.device) if _detector else "unknown",
        )

    @app.post("/api/v1/analyze", response_model=AnalysisResponse)
    async def analyze(request: AnalysisRequest):
        pipeline = get_pipeline()

        if request.options:
            _apply_options(pipeline, request.options)

        try:
            img = base64_to_image(request.image_base64)
        except Exception as exc:
            raise HTTPException(status_code=400, detail=f"image decode failed: {exc}") from exc

        try:
            result = pipeline.run(img)
        except Exception as exc:
            raise HTTPException(status_code=500, detail=f"analysis failed: {exc}") from exc

        return _build_response(result)

    @app.post("/api/v1/analyze/batch", response_model=BatchResponse)
    async def analyze_batch(request: BatchRequest):
        if len(request.images_base64) > 20:
            raise HTTPException(status_code=400, detail="batch supports at most 20 images")

        pipeline = get_pipeline()
        if request.options:
            _apply_options(pipeline, request.options)

        t0 = time.perf_counter()
        results = []
        errors = 0

        for b64 in request.images_base64:
            try:
                img = base64_to_image(b64)
                result = pipeline.run(img)
                results.append(_build_response(result))
            except Exception as exc:
                errors += 1
                results.append(
                    AnalysisResponse(
                        status="error",
                        label="error",
                        tamper_type="unavailable",
                        fake_prob=0,
                        risk_score=0,
                        risk_level="error",
                        explanation="",
                        explanation_brief=f"error: {exc}",
                        bbox_list=[],
                        dimension_scores=DimensionScores(
                            fake_prob=0,
                            artifact_intensity=0,
                            tamper_area=0,
                            region_count=0,
                            consistency=0,
                        ),
                        overlay_b64="",
                        mask_b64="",
                        elapsed_ms=0,
                        metadata=Metadata(
                            heatmap_method="",
                            overlay_alpha=0,
                            localization_enabled=False,
                            language="",
                            risk_weights={},
                        ),
                    )
                )

        return BatchResponse(
            results=results,
            total_elapsed_ms=round((time.perf_counter() - t0) * 1000, 2),
            success_count=len(results) - errors,
            error_count=errors,
        )

    return app


def _build_response(result: dict) -> AnalysisResponse:
    return AnalysisResponse(
        status="success",
        label=result["label"],
        tamper_type=result.get("tamper_type", "unavailable"),
        fake_prob=result["fake_prob"],
        risk_score=result["risk_score"],
        risk_level=result["risk_level"],
        explanation=result["explanation"],
        explanation_brief=result["explanation_brief"],
        bbox_list=[BBoxItem(**bbox) for bbox in result.get("bbox_list", [])],
        dimension_scores=DimensionScores(**result.get("dimension_scores", {})),
        overlay_b64=result["overlay_b64"],
        mask_b64=result["mask_b64"],
        tamper_mask_b64=result.get("tamper_mask_b64"),
        tamper_overlay_b64=result.get("tamper_overlay_b64"),
        bbox_image_b64=result.get("bbox_image_b64"),
        elapsed_ms=result["elapsed_ms"],
        metadata=Metadata(
            heatmap_method=result["metadata"].get("heatmap_method", ""),
            overlay_alpha=result["metadata"].get("overlay_alpha", 0),
            localization_enabled=result["metadata"].get("localization_enabled", False),
            language=result["metadata"].get("language", ""),
            risk_weights=result["metadata"].get("risk_weights", {}),
        ),
    )


def _apply_options(pipeline: ExplanationPipeline, options: AnalysisOptions) -> None:
    pipeline.heatmap_generator.overlay_alpha = options.overlay_alpha
    if hasattr(pipeline, "tamper_detector"):
        pipeline.tamper_detector.patch_analyzer.scales = options.localization_scales
        pipeline.tamper_detector.patch_analyzer.stride_ratio = options.stride_ratio
        pipeline.tamper_detector.min_region_area = options.min_region_area
    pipeline.text_explainer.language = options.language
    pipeline.text_explainer.detail_level = options.detail_level
