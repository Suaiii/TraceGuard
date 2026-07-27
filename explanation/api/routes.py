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
    ReportRequest,
    ReportPreviewResponse,
    BBoxItem,
    DimensionScores,
    Metadata,
)
from detection.inference_api import Detector
from explanation.pipeline import ExplanationPipeline
from explanation.utils import base64_to_image
from explanation.visualization import ReportGenerator
from explanation.llm import DeepSeekClient, ReportAgent

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

    # ------------------------------------------------------------------
    # 报告导出
    # ------------------------------------------------------------------

    def _get_llm_agent():
        """延迟初始化 LLM agent"""
        cfg = get_config()
        llm_cfg = cfg.get('llm', {})
        if not llm_cfg.get('enabled', True):
            return None
        api_key = os.environ.get(llm_cfg.get('api_key_env', 'DEEPSEEK_API_KEY'), '')
        if not api_key:
            return None
        client = DeepSeekClient(
            api_key=api_key,
            model=llm_cfg.get('model', 'deepseek-v4-pro'),
            base_url=llm_cfg.get('base_url', 'https://api.deepseek.com'),
            temperature=llm_cfg.get('temperature', 0.3),
            max_tokens=llm_cfg.get('max_tokens', 2048),
        )
        return ReportAgent(client)

    @app.post("/api/v1/report/preview", response_model=ReportPreviewResponse)
    async def report_preview(request: ReportRequest):
        cfg = get_config()
        output_cfg = cfg.get('output', {})
        html_title = output_cfg.get('html_title', 'TraceGuard 检测报告')

        gen = ReportGenerator(title=html_title, include_charts=True)

        llm_generated = False
        llm_elapsed_ms = 0

        # LLM 研判
        agent = None
        if request.options.include_llm:
            agent = _get_llm_agent()

        if request.type == 'single':
            result = request.results[0] if request.results else {}
            llm_opinion = None
            if agent:
                llm_opinion = agent.analyze_single(result)
                llm_generated = llm_opinion.get('llm_generated', False)
                llm_elapsed_ms = llm_opinion.get('elapsed_ms', 0)
            html = gen.generate_single(
                image_path=result.get('file', ''),
                result=result,
                llm_opinion=llm_opinion,
            )
        elif request.type == 'batch':
            llm_opinion = None
            results_raw = [r for r in request.results]
            if agent:
                llm_opinion = agent.analyze_batch(results_raw)
                llm_generated = llm_opinion.get('llm_generated', False)
                llm_elapsed_ms = llm_opinion.get('elapsed_ms', 0)
            html = gen.generate_batch(
                results=results_raw,
                llm_opinion=llm_opinion,
            )
        else:
            raise HTTPException(status_code=400, detail=f"unknown report type: {request.type}")

        return ReportPreviewResponse(
            html=html,
            llm_generated=llm_generated,
            llm_elapsed_ms=llm_elapsed_ms,
        )

    @app.post("/api/v1/report/download")
    async def report_download(request: ReportRequest):
        """返回 PDF 文件下载"""
        cfg = get_config()
        output_cfg = cfg.get('output', {})
        html_title = output_cfg.get('html_title', 'TraceGuard 检测报告')

        gen = ReportGenerator(title=html_title, include_charts=True)

        # LLM 研判
        agent = None
        if request.options.include_llm:
            agent = _get_llm_agent()

        if request.type == 'single':
            result = request.results[0] if request.results else {}
            llm_opinion = None
            if agent:
                llm_opinion = agent.analyze_single(result)
            html = gen.generate_single(
                image_path=result.get('file', ''),
                result=result,
                llm_opinion=llm_opinion,
            )
        elif request.type == 'batch':
            llm_opinion = None
            results_raw = [r for r in request.results]
            if agent:
                llm_opinion = agent.analyze_batch(results_raw)
            html = gen.generate_batch(
                results=results_raw,
                llm_opinion=llm_opinion,
            )
        else:
            raise HTTPException(status_code=400, detail=f"unknown report type: {request.type}")

        # HTML → PDF (Playwright Chromium, async)
        pdf_bytes = None
        try:
            import tempfile
            from playwright.async_api import async_playwright
            pw = await async_playwright().start()
            try:
                browser = await pw.chromium.launch()
                page = await browser.new_page()
                # 写临时文件以支持超大 HTML（含多张 base64 图片）
                with tempfile.NamedTemporaryFile(
                    mode='w', suffix='.html', encoding='utf-8', delete=False
                ) as f:
                    f.write(html)
                    tmp_path = f.name
                try:
                    await page.goto('file:///' + tmp_path.replace('\\', '/'),
                                    wait_until='networkidle', timeout=60000)
                    pdf_bytes = await page.pdf(format='A4', print_background=True)
                finally:
                    os.unlink(tmp_path)
                await browser.close()
            finally:
                await pw.stop()
        except ImportError:
            raise HTTPException(
                status_code=501,
                detail="PDF generation requires playwright. Run: pip install playwright && playwright install chromium"
            )
        except Exception as exc:
            raise HTTPException(status_code=500, detail=f"PDF generation failed: {exc}") from exc

        from fastapi.responses import Response
        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={
                "Content-Disposition": f'attachment; filename="traceguard-report.pdf"',
            },
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
    pipeline.enable_localization = options.enable_localization
    pipeline.heatmap_generator.overlay_alpha = options.overlay_alpha
    if hasattr(pipeline, "tamper_detector"):
        pipeline.tamper_detector.patch_analyzer.scales = options.localization_scales
        pipeline.tamper_detector.patch_analyzer.stride_ratio = options.stride_ratio
        pipeline.tamper_detector.min_region_area = options.min_region_area
    pipeline.text_explainer.language = options.language
    pipeline.text_explainer.detail_level = options.detail_level
