"""
TextExplainer — 自然语言解释生成

将量化检测与定位结果转化为标准化中文解释文本。
三段式结构: 总体结论 → 取证分析 → 定位详情
"""


class TextExplainer:
    """
    结构化自然语言解释生成器。

    输出三段式文本:
      1. [总体结论] — 综合判定结果与风险等级
      2. [取证分析] — 热力图伪影特征描述
      3. [定位详情] — 篡改区域坐标与局部风险

    用法:
        explainer = TextExplainer()
        text = explainer.explain(
            label='fake', fake_prob=0.97,
            risk_level='high', risk_score=0.85,
            bbox_list=[...]
        )
    """

    def __init__(self, language: str = "zh", detail_level: str = "standard"):
        """
        Args:
            language: "zh" | "en"
            detail_level: "brief" | "standard" | "detailed"
        """
        self.language = language
        self.detail_level = detail_level

    def explain(self, label: str, fake_prob: float,
                risk_level: str = "low",
                risk_score: float = 0.0,
                dimension_scores: dict = None,
                bbox_list: list = None,
                heatmap_stats: dict = None,
                tamper_type: str = None) -> str:
        """
        生成完整解释文本。

        Args:
            label: 'real' | 'fake'
            fake_prob: 伪造概率
            risk_level: 'low' | 'medium' | 'high'
            risk_score: 综合风险分
            dimension_scores: 风险维度分数详情
            bbox_list: 可疑区域列表
            heatmap_stats: 热力图统计 {'max': float, 'mean': float}

        Returns:
            str 结构化的自然语言解释
        """
        bbox_list = bbox_list or []
        dimension_scores = dimension_scores or {}
        heatmap_stats = heatmap_stats or {}

        parts = []

        # --- 第1段: 总体结论 ---
        parts.append(self._overall_conclusion(label, fake_prob, risk_level, risk_score, tamper_type))

        # --- 第2段: 取证分析 (热力图) ---
        parts.append(self._forensic_analysis(label, fake_prob, heatmap_stats))

        # --- 第3段: 定位详情 ---
        parts.append(self._localization_details(label, bbox_list, dimension_scores))

        return "\n\n".join(parts)

    # ------------------------------------------------------------------
    # 各段生成
    # ------------------------------------------------------------------

    def _overall_conclusion(self, label, fake_prob, risk_level, risk_score, tamper_type=None):
        """总体结论段 — 根据篡改类型输出不同结论"""
        tamper_descriptions = {
            'confirmed_real': (
                f"该图像被判定为真实图像（全局检测伪造概率{fake_prob:.1%}），"
                f"且未发现局部篡改痕迹，双重确认可信。"
            ),
            'local_tamper': (
                f"该图像的全局标签仍为真实（伪造概率{fake_prob:.1%}），"
                f"但局部滑动窗口检测发现可疑异常区域，需要人工复核。"
            ),
            'full_aigc': (
                f"该图像被判定为AIGC全图生成（检测置信度为{fake_prob:.1%}），"
                f"伪影特征均匀分布，未检测到局部篡改热点。"
            ),
            'full_aigc_hotspots': (
                f"该图像被判定为AIGC全图生成（检测置信度为{fake_prob:.1%}），"
                f"且存在局部重点可疑区域，疑为生成过程中伪影集中区域。"
            ),
        }

        if tamper_type and tamper_type in tamper_descriptions:
            verdict = tamper_descriptions[tamper_type]
        elif label == 'fake' and fake_prob > 0.5:
            verdict = f"该图像被判定为AIGC伪造图像，检测置信度为{fake_prob:.1%}。"
        elif label == 'real' and fake_prob <= 0.5:
            verdict = f"该图像被判定为真实图像，AIGC伪造概率仅为{fake_prob:.1%}。"
        else:
            verdict = f"该图像检测结果不明确，AIGC伪造概率为{fake_prob:.1%}，建议人工复核。"

        if tamper_type == 'local_tamper':
            risk_desc = (
                f"综合风险等级为{risk_level}（{risk_score:.2f}），"
                "但局部证据与全局判断存在冲突，建议人工复核。"
            )
        else:
            risk_desc = {
                'low': f"综合风险等级为低风险（{risk_score:.2f}），无需人工介入。",
                'medium': f"综合风险等级为中风险（{risk_score:.2f}），建议人工抽查确认。",
                'high': f"综合风险等级为高风险（{risk_score:.2f}），强烈建议人工复核处理。",
            }.get(risk_level, f"综合风险分为{risk_score:.2f}。")

        return f"【总体结论】\n{verdict} {risk_desc}"

    def _forensic_analysis(self, label, fake_prob, heatmap_stats):
        """取证分析段 — 基于热力图统计量"""
        if self.detail_level == 'brief' and label == 'real' and fake_prob < 0.3:
            return f"【取证分析】\n热力图中未发现明显AIGC伪影特征，各区域热力响应均匀且处于低水平。"

        hm_max = heatmap_stats.get('max', 0)
        hm_mean = heatmap_stats.get('mean', 0)

        if fake_prob > 0.7:
            artifact_level = "强烈"
            artifact_desc = (
                "热力图中存在大面积高响应区域，疑似检测到GAN生成模式的规则性网格伪影"
                "或扩散模型去噪过程中的典型残留痕迹。这些微观纹理异常是人眼不可见的AIGC指印，"
                "为伪造判定提供了关键证据。"
            )
        elif fake_prob > 0.3:
            artifact_level = "中等"
            artifact_desc = (
                "热力图中检测到局部伪影响应，可能存在部分人工编辑或AIGC生成痕迹。"
                "高响应区域集中在图像纹理复杂区域，建议结合篡改定位结果综合判断。"
            )
        else:
            artifact_level = "微弱"
            artifact_desc = (
                "热力图中未发现显著的AIGC伪影特征。各区域热力响应分布均匀，"
                "与真实自然图像的特征统计模式一致。"
            )

        if hm_max > 0:
            stats_line = (
                f"热力图统计：最大响应强度{hm_max:.3f}，平均响应强度{hm_mean:.3f}。"
            )
        else:
            stats_line = ""

        return f"【取证分析】\n热力图呈现{artifact_level}的AIGC伪影特征。{artifact_desc} {stats_line}"

    def _localization_details(self, label, bbox_list, dimension_scores):
        """定位详情段"""
        if not bbox_list:
            if label == 'real' or dimension_scores.get('tamper_area', 0) < 0.01:
                return "【定位详情】\n未检测到可疑篡改区域。"
            else:
                return "【定位详情】\n未检测到明确的可疑篡改区域，建议人工目视检查。"

        parts = [f"【定位详情】\n共检测到{len(bbox_list)}处可疑篡改区域："]

        for i, bbox in enumerate(bbox_list, 1):
            x, y, w, h = bbox['x'], bbox['y'], bbox['w'], bbox['h']
            area = bbox.get('area', w * h)
            local_score = dimension_scores.get(
                f'local_{i - 1}',
                round(0.4 * 0.5 + 0.6 * min(area / 100000, 1.0), 2)
            )

            parts.append(
                f"  区域{i} — 坐标(x={x}, y={y}, w={w}, h={h}), "
                f"面积={area}px, 局部风险分={local_score}"
            )

        parts.append(
            "\n以上区域疑为拼接合成、局部AIGC替换或图像编辑操作所致，"
            "建议对标记区域进行放大人工复核。"
        )

        return "\n".join(parts)

    # ------------------------------------------------------------------
    # 简略版 (brief mode)
    # ------------------------------------------------------------------

    def explain_brief(self, label: str, fake_prob: float,
                      risk_level: str = "low", bbox_count: int = 0,
                      tamper_type: str = None) -> str:
        """生成一句话摘要"""
        if tamper_type == 'local_tamper':
            return (
                f"全局判定{label} | 局部篡改证据 | 伪造概率{fake_prob:.0%} | 风险{risk_level} | "
                f"可疑区域{bbox_count}处"
            )
        elif label == 'fake':
            return (
                f"AIGC伪造图 | 置信度{fake_prob:.0%} | 风险{risk_level} | "
                f"可疑区域{bbox_count}处"
            )
        else:
            return (
                f"真实图 | 伪造概率{fake_prob:.0%} | 风险{risk_level}"
            )
