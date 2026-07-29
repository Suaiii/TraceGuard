"""
Pydantic 请求/响应模型 — TraceGuard FastAPI 接口
"""

from typing import Optional
from pydantic import BaseModel, Field


# ==============================================================================
# 请求模型
# ==============================================================================

class AnalysisOptions(BaseModel):
    """单图分析可选参数"""
    heatmap_method: str = Field("gradcam", description="热力图方法: gradcam")
    overlay_alpha: float = Field(0.5, ge=0.0, le=1.0, description="热力图叠加透明度")
    enable_localization: bool = Field(True, description="是否启用篡改定位")
    localization_scales: list[int] = Field([224, 160], description="滑动窗口尺寸列表")
    stride_ratio: float = Field(0.5, ge=0.1, le=1.0, description="滑动步长比例")
    min_region_area: int = Field(256, ge=64, description="最小可疑区域面积")
    language: str = Field("zh", description="解释语言: zh|en")
    detail_level: str = Field("standard", description="解释详细度: brief|standard|detailed")
    evidence_policy: str = Field(
        "all", pattern="^(all|flagged|none)$",
        description="证据图回传策略: all=全部回传(默认) | flagged=仅待处置条目回传 | none=全不回传",
    )


class AnalysisRequest(BaseModel):
    """单图分析请求"""
    image_base64: str = Field(..., description="Base64 编码的原始图像 (PNG/JPEG)")
    options: Optional[AnalysisOptions] = Field(None, description="可选参数")


class BatchRequest(BaseModel):
    """批量分析请求"""
    images_base64: list[str] = Field(..., min_length=1, max_length=50,
                                     description="Base64 编码图像列表 (单请求最多50张，更多请分块提交)")
    options: Optional[AnalysisOptions] = Field(None, description="可选参数")


# ==============================================================================
# 响应子模型
# ==============================================================================

class BBoxItem(BaseModel):
    """可疑区域坐标框"""
    x: int
    y: int
    w: int
    h: int
    area: int
    risk_score: float


class DimensionScores(BaseModel):
    """风险评分维度详情"""
    fake_prob: float
    artifact_intensity: float
    tamper_area: float
    region_count: float
    consistency: float


class SavedFiles(BaseModel):
    """保存到磁盘的文件路径 (仅 --save-dir 时返回)"""
    overlay: Optional[str] = None
    mask: Optional[str] = None
    tamper_mask: Optional[str] = None
    tamper_overlay: Optional[str] = None
    bbox_image: Optional[str] = None


class Metadata(BaseModel):
    """分析元信息"""
    heatmap_method: str
    overlay_alpha: float
    localization_enabled: bool
    language: str
    risk_weights: dict = {}


# ==============================================================================
# 响应模型
# ==============================================================================

class AnalysisResponse(BaseModel):
    """单图分析响应"""
    status: str = "success"
    label: str                                    # real | fake
    tamper_type: str                              # confirmed_real | local_tamper | full_aigc | full_aigc_hotspots
    fake_prob: float                              # 伪造概率
    risk_score: float                             # 综合风险分 0~1
    risk_level: str                               # low | medium | high
    explanation: str                              # 自然语言解释 (多行)
    explanation_brief: str                        # 一句话摘要
    bbox_list: list[BBoxItem] = []                # 可疑区域列表
    dimension_scores: DimensionScores             # 风险维度详情
    # Content classifier output
    content_category: str = "unavailable"          # 内容类别标签（CLIP 零样本分类）
    is_super_oversight_domain: bool = False        # 是否超监管领域（战争/暴恐/枪械/暴力）
    # Base64 图像
    overlay_b64: str                              # 热力图叠加图
    mask_b64: str                                 # 热力掩膜
    tamper_mask_b64: Optional[str] = None         # 篡改掩膜
    tamper_overlay_b64: Optional[str] = None      # 篡改叠加图
    bbox_image_b64: Optional[str] = None          # bbox 标注图
    elapsed_ms: float                             # 总耗时
    metadata: Metadata                            # 配置快照
    saved_files: Optional[SavedFiles] = None      # 保存路径 (可选)


class ErrorResponse(BaseModel):
    """错误响应"""
    status: str = "error"
    message: str
    detail: Optional[str] = None


class HealthResponse(BaseModel):
    """健康检查响应"""
    status: str = "healthy"
    model_loaded: bool
    device: str
    cuda_available: bool
    model_params: str                              # e.g. "44.8M"


class ConfigResponse(BaseModel):
    """当前配置响应"""
    heatmap_method: str
    overlay_alpha: float
    localization_enabled: bool
    localization_scales: list[int]
    stride_ratio: float
    language: str
    detail_level: str
    risk_weights: Optional[dict] = None
    device: str


class BatchResponse(BaseModel):
    """批量分析响应"""
    results: list[AnalysisResponse]
    total_elapsed_ms: float
    success_count: int
    error_count: int


# ==============================================================================
# 报告导出模型
# ==============================================================================

class ReportOptions(BaseModel):
    """报告生成选项"""
    include_llm: bool = Field(True, description="是否调用 LLM 生成研判意见")


class ScreeningContext(BaseModel):
    """取证筛查漏斗上下文 — 说明 results 只是待处置子集，而非原始批次全量"""
    total: int = Field(..., description="筛查总数（本轮送检的图片总张数）")
    passed: int = Field(..., description="筛选通过数（判定为 real 且 low 风险，未进入待处置列表）")
    flagged: int = Field(..., description="待处置数（进入报告的条目数）")
    elapsed_ms: float = Field(0, description="筛查总耗时 (ms)")


class ReportRequest(BaseModel):
    """报告导出请求"""
    type: str = Field(..., description="报告类型: single | batch")
    results: list[dict] = Field(..., min_length=1, description="检测结果列表 (AnalysisResponse dict)")
    options: ReportOptions = Field(default_factory=ReportOptions, description="报告选项")
    screening: Optional[ScreeningContext] = Field(
        None, description="可选的取证筛查上下文；提供时报告按'待处置子集'口径生成"
    )


class ReportPreviewResponse(BaseModel):
    """报告预览响应"""
    html: str = Field(..., description="完整 HTML 报告")
    llm_generated: bool = Field(False, description="是否成功调用了 LLM")
    llm_elapsed_ms: float = Field(0, description="LLM 调用耗时 (ms)")


class PdfRequest(BaseModel):
    """PDF 导出请求 — 直接传入已生成的 HTML"""
    html: str = Field(..., description="完整 HTML 报告字符串")
    type: str = Field("report", description="报告类型: single | batch")
