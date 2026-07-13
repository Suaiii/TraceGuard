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


class AnalysisRequest(BaseModel):
    """单图分析请求"""
    image_base64: str = Field(..., description="Base64 编码的原始图像 (PNG/JPEG)")
    options: Optional[AnalysisOptions] = Field(None, description="可选参数")


class BatchRequest(BaseModel):
    """批量分析请求"""
    images_base64: list[str] = Field(..., min_length=1, max_length=20,
                                     description="Base64 编码图像列表 (最多20张)")
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
