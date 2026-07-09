"""
TamperClassifier — 局部篡改 vs 全图 AIGC 四象限分类器

判定矩阵:
  ┌──────────┬───────────┬──────────────────────┐
  │ 全局判定  │ 局部定位   │ 结论                  │
  ├──────────┼───────────┼──────────────────────┤
  │ real     │ 无 bbox    │ confirmed_real       │
  │ real     │ 有 bbox    │ local_tamper → fake  │
  │ fake     │ 无 bbox    │ full_aigc            │
  │ fake     │ 有 bbox    │ full_aigc_hotspots   │
  └──────────┴───────────┴──────────────────────┘
"""

TAMPER_TYPE_LABELS = {
    'confirmed_real': '确认真实',
    'local_tamper': '局部篡改',
    'full_aigc': '全图AIGC生成',
    'full_aigc_hotspots': '全图AIGC生成（含重点可疑区域）',
}

TAMPER_TYPE_LABELS_EN = {
    'confirmed_real': 'Confirmed Real',
    'local_tamper': 'Local Tampering',
    'full_aigc': 'Full AIGC',
    'full_aigc_hotspots': 'Full AIGC with Hotspots',
}


def classify_tamper(global_label: str, bbox_list: list) -> str:
    """
    根据全局判定和局部定位结果，输出篡改类型。

    Args:
        global_label: Detector.predict() 输出的 'real' | 'fake'
        bbox_list: TamperDetector 输出的可疑区域列表

    Returns:
        str: 'confirmed_real' | 'local_tamper' | 'full_aigc' | 'full_aigc_hotspots'
    """
    has_bbox = len(bbox_list) > 0

    if global_label == 'real' and not has_bbox:
        return 'confirmed_real'
    elif global_label == 'real' and has_bbox:
        return 'local_tamper'
    elif global_label == 'fake' and not has_bbox:
        return 'full_aigc'
    elif global_label == 'fake' and has_bbox:
        return 'full_aigc_hotspots'
    else:
        return 'confirmed_real'


def get_effective_label(global_label: str, tamper_type: str) -> str:
    """
    计算有效判定标签。

    local_tamper 时：全局判定为 real，但 patch 级发现可疑区域 → 返回 'local_tamper'。
    """
    if tamper_type == 'local_tamper':
        return 'local_tamper'
    return global_label


def get_tamper_type_label(tamper_type: str, language: str = 'zh') -> str:
    """获取篡改类型的中/英文标签"""
    if language == 'zh':
        return TAMPER_TYPE_LABELS.get(tamper_type, tamper_type)
    return TAMPER_TYPE_LABELS_EN.get(tamper_type, tamper_type)
