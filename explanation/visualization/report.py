"""
HTML 报告生成器

生成自包含的 HTML 分析报告（内联 CSS + base64 图片），
可直接在浏览器打开或通过 weasyprint 导出 PDF。

用法:
    from explanation.visualization.report import ReportGenerator

    gen = ReportGenerator()
    html = gen.generate_single('image.jpg', pipeline_result)
    with open('report.html', 'w', encoding='utf-8') as f:
        f.write(html)

    # 批量报告
    html_batch = gen.generate_batch(batch_results)
"""

import os
import time
from datetime import datetime
from PIL import Image

from .charts import radar_chart, risk_gauge, batch_summary


class ReportGenerator:
    """
    HTML 检测报告生成器。

    Args:
        title: 报告标题
        company: 机构名称 (页脚)
        include_charts: 是否嵌入 matplotlib 图表
    """

    def __init__(self, title: str = "TraceGuard 检测报告",
                 company: str = "TraceGuard",
                 include_charts: bool = True):
        self.title = title
        self.company = company
        self.include_charts = include_charts

    # ------------------------------------------------------------------
    # 单图报告
    # ------------------------------------------------------------------

    def generate_single(self, image_path: str,
                        result: dict,
                        llm_opinion: dict = None) -> str:
        """
        生成单张图像完整分析 HTML 报告。

        Args:
            image_path: 原始图像路径 (用于显示文件名)
            result: pipeline.run() 输出 dict

        Returns:
            str — 完整 HTML 文档
        """
        filename = os.path.basename(image_path) if image_path else "unknown"
        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        # ---- 提取数据 ----
        label = result.get('label', 'unknown')
        tamper_type = result.get('tamper_type', 'unavailable')
        fake_prob = result.get('fake_prob', 0)
        risk_score = result.get('risk_score', 0)
        risk_level = result.get('risk_level', 'low')
        explanation = result.get('explanation', '')
        explanation_brief = result.get('explanation_brief', '')
        elapsed_ms = result.get('elapsed_ms', 0)
        bbox_list = result.get('bbox_list', [])
        dim_scores = result.get('dimension_scores', {})
        metadata = result.get('metadata', {})

        # ---- 超监管标记 ----
        is_super_oversight = (
            label == 'fake' and fake_prob >= 0.9 and risk_level == 'high'
        )

        # ---- LLM 研判 ----
        llm = llm_opinion or {}
        llm_opinion_text = llm.get('opinion', '')
        llm_dimension_notes = llm.get('dimension_notes', '')
        llm_region_notes = llm.get('region_notes', '')

        # ---- 生成图表 ----
        radar_b64 = None
        gauge_b64 = None
        if self.include_charts:
            if dim_scores:
                radar_img = radar_chart(dim_scores, size=(420, 420))
                radar_b64 = self._pil_to_b64(radar_img)
            gauge_img = risk_gauge(risk_score, risk_level, size=(520, 160))
            gauge_b64 = self._pil_to_b64(gauge_img)

        # ---- 组装 HTML ----
        report_id = f"TG-{datetime.now().strftime('%Y%m%d%H%M%S')}"
        risk_cls_map = {'low': 'risk-low-v', 'medium': 'risk-medium-v', 'high': 'risk-high-v'}
        verdict_cls = 'verdict-fake' if label == 'fake' else 'verdict-real'
        verdict_color = 'fake' if label == 'fake' else 'real'

        html = f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<title>{self.title} — {filename}</title>
<style>
{self._css()}
</style>
</head>
<body>

<!-- ========== Page Header ========== -->
<div class="page-header">
    <div class="page-header-brand">
        TraceGuard <span>| 多模态图像安全审核系统</span>
    </div>
    <div class="page-header-meta">
        报告编号: {report_id}<br>
        生成时间: {now}
    </div>
</div>

<!-- ========== Super-Oversight Alert ========== -->
{self._super_oversight_alert() if is_super_oversight else ''}

<!-- ========== Key Metrics ========== -->
<div class="metrics-banner">
    <div class="metric-card {verdict_cls}">
        <div class="metric-label">判定结果</div>
        <div class="metric-value {verdict_color}">{LABELS.get(label, label)}</div>
        <div class="metric-sub">{TAMPER_TYPE_LABELS.get(tamper_type, tamper_type)}</div>
    </div>
    <div class="metric-card">
        <div class="metric-label">伪造概率</div>
        <div class="metric-value">{fake_prob:.1%}</div>
        <div class="metric-sub">综合风险分: {risk_score:.2f}</div>
    </div>
    <div class="metric-card">
        <div class="metric-label">风险等级</div>
        <div class="metric-value {risk_cls_map.get(risk_level, '')}">{RISK_LABELS.get(risk_level, risk_level)}</div>
        <div class="metric-sub">可疑区域: {len(bbox_list)} 处 | 耗时: {elapsed_ms:.0f}ms</div>
    </div>
</div>

<!-- ========== LLM 综合研判 ========== -->
{self._llm_callout(llm_opinion_text)}

<!-- ========== 2×2 证据图网格 ========== -->
<div class="img-grid">
    <div class="card">
        <h2>热力图叠加</h2>
        {self._img_tag(result.get('overlay_b64'), '热力图叠加图')}
        <div class="caption">原图 + Grad-CAM 热力层 (蓝=低响应, 红紫=高响应)</div>
    </div>
    <div class="card">
        <h2>风险维度雷达图</h2>
        {self._radar_img(radar_b64)}
    </div>
    <div class="card">
        <h2>可疑区域坐标框</h2>
        {self._img_tag(result.get('bbox_image_b64'), 'BBox 标注')}
        <div class="caption">红色矩形框标记可疑区域边界</div>
    </div>
    <div class="card">
        <h2>篡改可疑区域</h2>
        {self._img_tag(result.get('tamper_overlay_b64'), '篡改掩膜叠加')}
        <div class="caption">红色区域为可疑篡改位置</div>
    </div>
</div>

<!-- ========== Two-column: Gauge + Dimensions ========== -->
<div class="two-col">
    <div class="card">
        <h2>风险分数仪表</h2>
        {self._gauge_img(gauge_b64)}
    </div>
    {self._dimension_table(dim_scores)}
</div>

<!-- ========== BBox + LLM Region Notes ========== -->
{self._bbox_table(bbox_list)}
{self._llm_region_notes_card(llm_region_notes)}

<!-- ========== Full Explanation ========== -->
<div class="card">
    <h2>详细解释</h2>
    <pre class="explanation-text">{self._escape_html(explanation)}</pre>
</div>

<!-- ========== LLM Dimension Notes ========== -->
{self._llm_dimension_notes_card(llm_dimension_notes)}

<!-- ========== Metadata ========== -->
<div class="card">
    <h2>分析元信息</h2>
    <div class="meta-grid">
        <div class="meta-item"><span class="meta-key">热力图方法</span><span class="meta-val">{metadata.get('heatmap_method', '-')}</span></div>
        <div class="meta-item"><span class="meta-key">叠加透明度</span><span class="meta-val">{metadata.get('overlay_alpha', '-')}</span></div>
        <div class="meta-item"><span class="meta-key">定位模块</span><span class="meta-val">{'启用' if metadata.get('localization_enabled') else '禁用'}</span></div>
        <div class="meta-item"><span class="meta-key">解释语言</span><span class="meta-val">{metadata.get('language', '-')}</span></div>
        <div class="meta-item"><span class="meta-key">风险权重</span><span class="meta-val">{self._format_weights(metadata.get('risk_weights', {}))}</span></div>
    </div>
</div>

<!-- ========== Page Footer ========== -->
<div class="page-footer">
    <span>© {datetime.now().year} TraceGuard — AIGC 图像安全审核平台</span>
    <span>本报告由系统自动生成 · 仅供审核参考</span>
</div>

</body>
</html>'''

        return html

    # ------------------------------------------------------------------
    # 批量报告
    # ------------------------------------------------------------------

    def generate_batch(self, results: list,
                       title: str = None,
                       llm_opinion: dict = None) -> str:
        """
        生成批量分析汇总 HTML 报告。

        Args:
            results: pipeline.run() 输出列表
            title: 报告标题

        Returns:
            str — 完整 HTML 文档
        """
        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        total = len(results)
        success = sum(1 for r in results if r.get('status', 'success') == 'success')
        fake_count = sum(1 for r in results if r.get('label') == 'fake')
        tamper_count = sum(1 for r in results if r.get('tamper_type') == 'local_tamper')
        real_count = sum(1 for r in results if r.get('label') == 'real')
        high_risk = sum(1 for r in results if r.get('risk_level') == 'high')
        medium_risk = sum(1 for r in results if r.get('risk_level') == 'medium')
        low_risk = sum(1 for r in results if r.get('risk_level') == 'low')
        super_oversight_count = sum(
            1 for r in results
            if r.get('label') == 'fake'
            and r.get('fake_prob', 0) >= 0.9
            and r.get('risk_level') == 'high'
        )

        # ---- LLM 研判 ----
        llm = llm_opinion or {}
        llm_overview = llm.get('overview', '')
        llm_priority = llm.get('priority_list', '')

        # 汇总图表
        summary_b64 = None
        if self.include_charts and results:
            summary_img = batch_summary(results, size=(800, 640))
            summary_b64 = self._pil_to_b64(summary_img)

        if title is None:
            title = f'{self.title} — 批量分析汇总'

        # 逐条结果行
        result_rows = ''
        for i, r in enumerate(results, 1):
            label = r.get('label', '-')
            fake_prob = r.get('fake_prob', 0)
            risk_score = r.get('risk_score', 0)
            risk_level = r.get('risk_level', '-')
            explanation_brief = r.get('explanation_brief', '')
            elapsed_ms = r.get('elapsed_ms', 0)
            file_name = os.path.basename(r.get('file', '')) if r.get('file') else f'#{i}'

            label_cls = 'fake-color' if label == 'fake' else 'real-color'
            risk_cls = f'risk-{risk_level}-text'
            row_cls = ''
            so_prefix = ''
            if label == 'fake' and fake_prob >= 0.9 and risk_level == 'high':
                row_cls = ' class="row-super-oversight"'
                so_prefix = '&#9888; '
            elif risk_level == 'high':
                row_cls = ' class="row-high-risk"'

            result_rows += f'''
            <tr{row_cls}>
                <td class="cell-index">{so_prefix}{i}</td>
                <td class="cell-file" title="{self._escape_html(file_name)}">{self._escape_html(file_name)}</td>
                <td class="cell-status {label_cls}">{LABELS.get(label, label)}</td>
                <td class="cell-num">{fake_prob:.3f}</td>
                <td class="cell-num">{risk_score:.2f}</td>
                <td class="cell-status {risk_cls}">{RISK_LABELS.get(risk_level, risk_level)}</td>
                <td class="cell-num">{elapsed_ms:.0f}ms</td>
                <td class="cell-brief">{self._escape_html(explanation_brief)}</td>
            </tr>'''

        report_id = f"TG-BATCH-{datetime.now().strftime('%Y%m%d%H%M%S')}"

        html = f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<title>{title}</title>
<style>
{self._css()}
</style>
</head>
<body>

<!-- ========== Page Header ========== -->
<div class="page-header">
    <div class="page-header-brand">
        TraceGuard <span>| 批量检测报告</span>
    </div>
    <div class="page-header-meta">
        报告编号: {report_id}<br>
        生成时间: {now} &nbsp;|&nbsp; 共 {total} 张图片
    </div>
</div>

<!-- ========== Key Metrics ========== -->
<div class="metrics-banner">
    <div class="metric-card">
        <div class="metric-label">总图片</div>
        <div class="metric-value">{total}</div>
        <div class="metric-sub">成功 {success} / 失败 {total - success}</div>
    </div>
    <div class="metric-card verdict-fake">
        <div class="metric-label">风险分布</div>
        <div class="metric-value fake">{fake_count}</div>
        <div class="metric-sub">AIGC伪造 (含局部篡改 {tamper_count})</div>
    </div>
    <div class="metric-card">
        <div class="metric-label">风险等级</div>
        <div class="metric-value" style="color:var(--risk-high);">{high_risk} <span style="font-size:16px;color:var(--text-secondary);">/ {medium_risk} / {low_risk}</span></div>
        <div class="metric-sub">高 / 中 / 低{f' &nbsp;|&nbsp; 超监管 {super_oversight_count}' if super_oversight_count > 0 else ''}</div>
    </div>
</div>

<!-- ========== LLM 研判 ========== -->
{self._llm_batch_overview_section(llm_overview, llm_priority)}

<!-- ========== Summary Fig ========== -->
{self._summary_section(summary_b64)}

<!-- ========== Result Table ========== -->
<div class="card">
    <h2>逐条分析结果 <span class="card-badge">{total} 条</span></h2>
    <div class="table-scroll">
    <table class="result-table">
        <thead>
            <tr>
                <th>#</th>
                <th>文件名</th>
                <th>判定</th>
                <th>fake_prob</th>
                <th>risk_score</th>
                <th>风险</th>
                <th>耗时</th>
                <th>摘要</th>
            </tr>
        </thead>
        <tbody>
            {result_rows}
        </tbody>
    </table>
    </div>
</div>

<!-- ========== High-Risk Details ========== -->
{self._high_risk_details_section(results)}

<!-- ========== Page Footer ========== -->
<div class="page-footer">
    <span>© {datetime.now().year} TraceGuard — AIGC 图像安全审核平台</span>
    <span>本报告由系统自动生成 · 仅供审核参考</span>
</div>

</body>
</html>'''

        return html

    # ------------------------------------------------------------------
    # PDF 导出 (可选依赖)
    # ------------------------------------------------------------------

    @staticmethod
    def to_pdf(html_string: str, output_path: str) -> str:
        """
        将 HTML 报告导出为 PDF（需安装 weasyprint）。

        pip install weasyprint

        Args:
            html_string: HTML 字符串
            output_path: PDF 输出路径

        Returns:
            str — 输出文件路径
        """
        try:
            from weasyprint import HTML
            HTML(string=html_string).write_pdf(output_path)
            return output_path
        except ImportError:
            raise ImportError(
                "PDF 导出需要 weasyprint 库。请执行: pip install weasyprint"
            )

    # ------------------------------------------------------------------
    # CSS
    # ------------------------------------------------------------------

    @staticmethod
    def _css() -> str:
        return '''
            @page { size: A4; margin: 18mm 16mm 22mm 16mm; }
            :root {
                --bg: #FAFBFC;
                --card-bg: #FFFFFF;
                --text: #1A1D23;
                --text-secondary: #6B7280;
                --border: #E5E7EB;
                --accent: #1A56DB;
                --accent-light: #EFF6FF;
                --fake-red: #DC2626;
                --fake-red-bg: #FEF2F2;
                --real-green: #059669;
                --real-green-bg: #ECFDF5;
                --tamper-amber: #D97706;
                --risk-low: #06B6D4;
                --risk-low-bg: #ECFEFF;
                --risk-medium: #F59E0B;
                --risk-medium-bg: #FFFBEB;
                --risk-high: #EF4444;
                --risk-high-bg: #FEF2F2;
                --so-red: #991B1B;
                --so-red-bg: #FEE2E2;
                --radius: 10px;
                --radius-sm: 6px;
                --shadow-sm: 0 1px 2px rgba(0,0,0,0.04);
                --shadow: 0 1px 3px rgba(0,0,0,0.06), 0 1px 2px rgba(0,0,0,0.04);
            }
            * { box-sizing: border-box; margin: 0; padding: 0; }
            body {
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Microsoft YaHei', 'PingFang SC', sans-serif;
                background: var(--bg);
                color: var(--text);
                font-size: 13px;
                line-height: 1.6;
                max-width: 960px;
                margin: 0 auto;
                padding: 20px 16px;
                -webkit-print-color-adjust: exact;
                print-color-adjust: exact;
            }

            /* ========== Page Header ========== */
            .page-header {
                display: flex;
                justify-content: space-between;
                align-items: flex-end;
                padding-bottom: 12px;
                margin-bottom: 20px;
                border-bottom: 2px solid var(--accent);
            }
            .page-header-brand {
                font-size: 18px;
                font-weight: 800;
                color: var(--text);
                letter-spacing: -0.01em;
            }
            .page-header-brand span { color: var(--accent); font-weight: 400; }
            .page-header-meta {
                text-align: right;
                font-size: 10px;
                color: var(--text-secondary);
                line-height: 1.5;
            }

            /* ========== Key Metrics Banner ========== */
            .metrics-banner {
                display: grid;
                grid-template-columns: 1fr 1fr 1fr;
                gap: 12px;
                margin-bottom: 16px;
            }
            .metric-card {
                background: var(--card-bg);
                border: 1px solid var(--border);
                border-radius: var(--radius);
                padding: 16px 20px;
                box-shadow: var(--shadow-sm);
                text-align: center;
            }
            .metric-card.verdict-fake {
                border-color: #FECACA;
                background: var(--fake-red-bg);
            }
            .metric-card.verdict-real {
                border-color: #A7F3D0;
                background: var(--real-green-bg);
            }
            .metric-label {
                font-size: 11px;
                font-weight: 600;
                text-transform: uppercase;
                letter-spacing: 0.06em;
                color: var(--text-secondary);
                margin-bottom: 6px;
            }
            .metric-value {
                font-size: 28px;
                font-weight: 800;
                letter-spacing: -0.02em;
            }
            .metric-value.fake { color: var(--fake-red); }
            .metric-value.real { color: var(--real-green); }
            .metric-value.risk-high-v { color: var(--risk-high); }
            .metric-value.risk-medium-v { color: var(--risk-medium); }
            .metric-value.risk-low-v { color: var(--risk-low); }
            .metric-sub {
                font-size: 11px;
                color: var(--text-secondary);
                margin-top: 2px;
            }

            /* ========== Super-Oversight Alert ========== */
            .so-alert {
                display: flex;
                align-items: center;
                gap: 12px;
                background: var(--so-red-bg);
                border: 1.5px solid #FCA5A5;
                border-radius: var(--radius);
                padding: 14px 20px;
                margin-bottom: 16px;
            }
            .so-alert-icon {
                font-size: 24px;
                flex-shrink: 0;
            }
            .so-alert-text strong {
                display: block;
                font-size: 14px;
                color: var(--so-red);
                margin-bottom: 2px;
            }
            .so-alert-text p {
                font-size: 12px;
                color: #7F1D1D;
                line-height: 1.5;
            }

            /* ========== Card ========== */
            .card {
                background: var(--card-bg);
                border: 1px solid var(--border);
                border-radius: var(--radius);
                box-shadow: var(--shadow);
                padding: 18px 20px;
                margin-bottom: 14px;
                page-break-inside: avoid;
            }
            .card h2 {
                font-size: 13px;
                font-weight: 700;
                color: var(--text);
                margin-bottom: 12px;
                padding-bottom: 8px;
                border-bottom: 1px solid var(--border);
                display: flex;
                align-items: center;
                gap: 8px;
            }
            .card h2 .card-badge {
                display: inline-block;
                font-size: 10px;
                font-weight: 600;
                padding: 2px 8px;
                border-radius: 100px;
                background: var(--accent-light);
                color: var(--accent);
            }
            .card img {
                width: 100%;
                border-radius: var(--radius-sm);
                border: 1px solid var(--border);
            }
            .card .caption {
                font-size: 11px;
                color: var(--text-secondary);
                margin-top: 6px;
                text-align: center;
            }

            /* ========== 2x2 Image Grid ========== */
            .img-grid {
                display: grid;
                grid-template-columns: 1fr 1fr;
                gap: 12px;
                margin-bottom: 14px;
                page-break-inside: avoid;
            }
            .img-grid .card {
                margin-bottom: 0;
            }
            .img-grid .card h2 {
                font-size: 12px;
                margin-bottom: 8px;
                padding-bottom: 6px;
            }

            /* ========== Callout / LLM ========== */
            .callout {
                background: #F8FAFC;
                border-left: 4px solid var(--accent);
                border-radius: 0 var(--radius-sm) var(--radius-sm) 0;
                padding: 16px 20px;
                margin-bottom: 14px;
                page-break-inside: avoid;
            }
            .callout h2 {
                font-size: 13px;
                font-weight: 700;
                color: var(--accent);
                margin-bottom: 8px;
            }
            .callout-body {
                font-size: 13px;
                line-height: 1.75;
                white-space: pre-wrap;
                color: #374151;
            }

            /* ========== Striped Table ========== */
            .data-table {
                width: 100%;
                border-collapse: collapse;
                font-size: 12px;
            }
            .data-table th {
                background: #F9FAFB;
                padding: 9px 12px;
                text-align: left;
                font-weight: 700;
                font-size: 11px;
                text-transform: uppercase;
                letter-spacing: 0.04em;
                color: var(--text-secondary);
                border-bottom: 2px solid var(--border);
            }
            .data-table th.center { text-align: center; }
            .data-table td {
                padding: 8px 12px;
                border-bottom: 1px solid #F3F4F6;
            }
            .data-table td.center { text-align: center; font-variant-numeric: tabular-nums; }
            .data-table tbody tr:nth-child(even) { background: #F9FAFB; }
            .data-table tbody tr:hover { background: var(--accent-light); }

            /* Dim bar */
            .dim-bar-wrap {
                display: flex;
                align-items: center;
                gap: 8px;
            }
            .dim-bar {
                flex: 1;
                height: 6px;
                background: #E5E7EB;
                border-radius: 3px;
                overflow: hidden;
            }
            .dim-bar-fill {
                height: 100%;
                border-radius: 3px;
            }
            .dim-bar-val {
                width: 36px;
                text-align: right;
                font-weight: 700;
                font-size: 12px;
                font-variant-numeric: tabular-nums;
            }

            /* ========== Two-column layout ========== */
            .two-col {
                display: grid;
                grid-template-columns: 1fr 1fr;
                gap: 12px;
                margin-bottom: 14px;
            }
            .two-col .card { margin-bottom: 0; }

            /* ========== Page Footer ========== */
            .page-footer {
                margin-top: 20px;
                padding-top: 10px;
                border-top: 1px solid var(--border);
                display: flex;
                justify-content: space-between;
                font-size: 10px;
                color: var(--text-secondary);
            }

            /* ========== Explanation ========== */
            .explanation-text {
                white-space: pre-wrap;
                font-family: inherit;
                font-size: 13px;
                line-height: 1.8;
                color: #4B5563;
            }

            /* ========== Meta table (compact) ========== */
            .meta-grid {
                display: grid;
                grid-template-columns: 1fr 1fr 1fr;
                gap: 8px 16px;
                font-size: 12px;
            }
            .meta-item { display: flex; gap: 6px; }
            .meta-key { color: var(--text-secondary); flex-shrink: 0; }
            .meta-val { font-weight: 600; color: var(--text); }

            /* ========== Batch table ========== */
            .result-table { width: 100%; border-collapse: collapse; font-size: 12px; }
            .result-table th {
                background: #F9FAFB;
                padding: 9px 8px;
                text-align: left;
                font-weight: 700;
                font-size: 10px;
                text-transform: uppercase;
                letter-spacing: 0.04em;
                color: var(--text-secondary);
                border-bottom: 2px solid var(--border);
            }
            .result-table td { padding: 7px 8px; border-bottom: 1px solid #F3F4F6; }
            .result-table tbody tr:nth-child(even) { background: #F9FAFB; }
            .cell-index { width: 36px; text-align: center; color: var(--text-secondary); }
            .cell-file { max-width: 140px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
            .cell-num { text-align: center; font-variant-numeric: tabular-nums; }
            .cell-status { text-align: center; font-weight: 700; font-size: 11px; }
            .cell-brief { max-width: 180px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; font-size: 11px; color: var(--text-secondary); }
            .table-scroll { overflow-x: auto; }
            .row-super-oversight { background: var(--so-red-bg) !important; }
            .row-high-risk { background: var(--risk-high-bg) !important; }
            .fake-color { color: var(--fake-red); font-weight: 700; }
            .real-color { color: var(--real-green); font-weight: 700; }
            .risk-low-text { color: var(--risk-low); font-weight: 700; }
            .risk-medium-text { color: var(--risk-medium); font-weight: 700; }
            .risk-high-text { color: var(--risk-high); font-weight: 700; }
            .so-summary { color: var(--so-red) !important; font-weight: 700; }

            /* ========== High-risk detail card ========== */
            .high-risk-detail-card {
                border: 1px solid var(--border);
                border-left: 4px solid var(--risk-high);
                background: #FFF;
                border-radius: var(--radius-sm);
                padding: 16px 18px;
                margin-bottom: 12px;
                page-break-inside: avoid;
            }
            .high-risk-detail-card h3 {
                font-size: 13px;
                color: var(--risk-high);
                margin-bottom: 8px;
            }
            .hr-meta-row { display: flex; flex-wrap: wrap; gap: 12px; font-size: 12px; margin-bottom: 8px; }
            .hr-meta-item { display: flex; flex-direction: column; min-width: 70px; }
            .hr-meta-label { font-size: 10px; color: var(--text-secondary); text-transform: uppercase; letter-spacing: 0.04em; }
            .hr-meta-value { font-weight: 700; font-size: 14px; }
            .hr-thumb { max-width: 180px; border-radius: var(--radius-sm); border: 1px solid var(--border); margin-bottom: 6px; }
            .hr-mini-bars { display: flex; flex-direction: column; gap: 3px; margin-bottom: 8px; }
            .hr-mini-bar-row { display: flex; align-items: center; gap: 6px; font-size: 11px; }
            .hr-mini-bar-label { width: 70px; text-align: right; color: var(--text-secondary); }
            .hr-mini-bar-track { flex: 1; height: 5px; background: #E5E7EB; border-radius: 3px; overflow: hidden; }
            .hr-mini-bar-fill { height: 100%; border-radius: 3px; }
            .hr-mini-bar-val { width: 36px; text-align: right; font-weight: 700; font-size: 11px; }

            /* ========== No-image placeholder ========== */
            .no-image {
                display: flex; align-items: center; justify-content: center;
                height: 100px; background: #F9FAFB; border: 1px dashed var(--border);
                border-radius: var(--radius-sm); color: var(--text-secondary); font-size: 12px;
            }

            /* ========== Print helpers ========== */
            @media print {
                body { background: #FFF; max-width: none; margin: 0; padding: 0; }
                .card { box-shadow: none; }
            }
        '''

    # ------------------------------------------------------------------
    # 内部 HTML 片段
    # ------------------------------------------------------------------

    @staticmethod
    def _img_tag(b64_data, alt="图像") -> str:
        if not b64_data:
            return f'<div class="no-image">暂无图片</div>'
        return f'<img src="data:image/png;base64,{b64_data}" alt="{alt}" loading="lazy">'

    @staticmethod
    def _radar_img(radar_b64) -> str:
        if not radar_b64:
            return '<div class="no-image">雷达图不可用</div>'
        return f'<img src="data:image/png;base64,{radar_b64}" alt="五维度雷达图" loading="lazy">'

    @staticmethod
    def _gauge_img(gauge_b64) -> str:
        if not gauge_b64:
            return '<div class="no-image">仪表图不可用</div>'
        return f'<img src="data:image/png;base64,{gauge_b64}" alt="风险仪表条" loading="lazy">'

    def _summary_section(self, summary_b64) -> str:
        if not summary_b64:
            return ''
        return f'''<div class="card">
            <h2>汇总图表</h2>
            <img src="data:image/png;base64,{summary_b64}" alt="批量分析汇总图">
        </div>'''

    def _bbox_table(self, bbox_list: list) -> str:
        if not bbox_list:
            return '''<div class="card">
            <h2>可疑区域列表 <span class="card-badge">0 处</span></h2>
            <p style="color:var(--text-secondary);font-size:12px;">未检测到可疑篡改区域</p>
        </div>'''

        rows = ''
        for i, bbox in enumerate(bbox_list, 1):
            local_score = bbox.get('risk_score', 0)
            score_color = '#059669' if local_score < 0.5 else ('#D97706' if local_score < 0.8 else '#DC2626')
            rows += f'''<tr>
                <td class="center">{i}</td>
                <td class="center">({bbox['x']}, {bbox['y']})</td>
                <td class="center">{bbox['w']}&times;{bbox['h']}</td>
                <td class="center">{bbox.get('area', bbox['w']*bbox['h'])}</td>
                <td class="center" style="font-weight:700;color:{score_color};">{local_score:.2f}</td>
            </tr>'''

        return f'''<div class="card">
            <h2>可疑区域列表 <span class="card-badge">{len(bbox_list)} 处</span></h2>
            <table class="data-table">
                <thead><tr><th class="center">#</th><th class="center">坐标 (x, y)</th><th class="center">尺寸 (w&times;h)</th><th class="center">面积 (px)</th><th class="center">局部风险分</th></tr></thead>
                <tbody>{rows}</tbody>
            </table>
        </div>'''

    @staticmethod
    def _dimension_table(dim_scores: dict) -> str:
        if not dim_scores:
            return ''

        dim_names = {
            'fake_prob': '检测置信度',
            'artifact_intensity': '伪影强度',
            'tamper_area': '篡改面积比',
            'region_count': '区域数量',
            'consistency': '一致性',
        }
        weights = {'fake_prob': 0.50, 'artifact_intensity': 0.25, 'tamper_area': 0.10,
                   'region_count': 0.05, 'consistency': 0.10}

        rows = ''
        for key, label in dim_names.items():
            val = dim_scores.get(key, 0)
            pct = int(val * 100)
            if val < 0.5:
                bar_color = '#06B6D4'
            elif val < 0.8:
                bar_color = '#F59E0B'
            else:
                bar_color = '#EF4444'
            w = weights.get(key, 0)
            rows += f'''<tr>
                <td style="font-weight:600;">{label}</td>
                <td style="color:var(--text-secondary);">{w:.0%}</td>
                <td class="center">{val:.4f}</td>
                <td>
                    <div class="dim-bar-wrap">
                        <div class="dim-bar"><div class="dim-bar-fill" style="width:{pct}%;background:{bar_color};"></div></div>
                        <span class="dim-bar-val">{pct}%</span>
                    </div>
                </td>
            </tr>'''

        return f'''<div class="card">
            <h2>风险维度详情 <span class="card-badge">5 维</span></h2>
            <table class="data-table">
                <thead><tr><th>维度</th><th>权重</th><th class="center">分数</th><th>百分比</th></tr></thead>
                <tbody>{rows}</tbody>
            </table>
        </div>'''

    @staticmethod
    def _format_weights(weights: dict) -> str:
        if not weights:
            return '-'
        parts = []
        name_map = {
            'fake_prob': '检测置信度',
            'artifact_intensity': '伪影强度',
            'tamper_area': '篡改面积',
            'region_count': '区域数量',
            'consistency': '一致性',
        }
        for k, v in weights.items():
            # 兼容两种 key 格式
            key = k.replace('_weight', '')
            label = name_map.get(key, k)
            parts.append(f'{label}={v:.2f}')
        return ', '.join(parts)

    # ------------------------------------------------------------------
    # LLM / 超监管 相关 HTML 片段
    # ------------------------------------------------------------------

    @staticmethod
    def _super_oversight_alert() -> str:
        return '''<div class="so-alert">
        <span class="so-alert-icon">&#9888;</span>
        <div class="so-alert-text">
            <strong>超监管高危内容</strong>
            <p>该图像伪造概率极高且综合风险为高风险等级，建议立即标记并限制传播，优先进行人工复核。</p>
        </div>
    </div>'''

    @staticmethod
    def _llm_callout(text: str) -> str:
        if not text:
            return ''
        return f'''<div class="callout">
        <h2>&#128269; 智能分析与复核建议</h2>
        <div class="callout-body">{text}</div>
    </div>'''

    @staticmethod
    def _llm_dimension_notes_card(text: str) -> str:
        if not text:
            return ''
        return f'''<div class="callout">
        <h2>&#129514; 维度解读</h2>
        <div class="callout-body">{text}</div>
    </div>'''

    @staticmethod
    def _llm_region_notes_card(text: str) -> str:
        if not text:
            return ''
        return f'''<div class="callout">
        <h2>&#128506; 可疑区域分布解读</h2>
        <div class="callout-body">{text}</div>
    </div>'''

    @staticmethod
    def _llm_batch_overview_section(overview: str, priority: str) -> str:
        if not overview:
            return ''
        priority_html = ''
        if priority:
            priority_html = f'''<h3 style="margin-top:12px;font-size:13px;color:var(--accent);">高风险优先级排序</h3>
        <div class="callout-body">{priority}</div>'''
        return f'''<div class="callout">
        <h2>&#128269; 批量综合研判意见</h2>
        <div class="callout-body">{overview}</div>
        {priority_html}
    </div>'''

    def _high_risk_details_section(self, results: list) -> str:
        """批量报告：高风险条目详情展开"""
        high_risk_items = [
            (i, r) for i, r in enumerate(results, 1)
            if r.get('risk_level') == 'high'
        ]
        if not high_risk_items:
            return ''

        cards = ''
        dim_keys = ['fake_prob', 'artifact_intensity', 'tamper_area', 'region_count', 'consistency']
        dim_labels_zh = {
            'fake_prob': '检测置信度',
            'artifact_intensity': '伪影强度',
            'tamper_area': '篡改面积',
            'region_count': '区域数量',
            'consistency': '一致性',
        }

        for idx, r in high_risk_items:
            label = r.get('label', '-')
            fake_prob = r.get('fake_prob', 0)
            risk_score = r.get('risk_score', 0)
            risk_level = r.get('risk_level', '-')
            bbox_count = len(r.get('bbox_list', []))
            dim_scores = r.get('dimension_scores', {})
            explanation_brief = r.get('explanation_brief', '')
            overlay_b64 = r.get('overlay_b64', '')
            file_name = f'#{idx}'

            is_so = (label == 'fake' and fake_prob >= 0.9)
            so_mark = ' &#9888; 超监管' if is_so else ''

            # 迷你维度进度条
            mini_bars = ''
            for key in dim_keys:
                val = dim_scores.get(key, 0)
                pct = int(val * 100)
                color = '#4CAF50' if val < 0.5 else ('#FF9800' if val < 0.8 else '#F44336')
                mini_bars += f'''<div class="hr-mini-bar-row">
                <span class="hr-mini-bar-label">{dim_labels_zh.get(key, key)}</span>
                <span class="hr-mini-bar-track"><span class="hr-mini-bar-fill" style="width:{pct}%;background:{color};"></span></span>
                <span class="hr-mini-bar-val">{val:.2f}</span>
            </div>'''

            # 热力图缩略图
            thumb_html = ''
            if overlay_b64:
                thumb_html = f'<img class="hr-thumb" src="data:image/png;base64,{overlay_b64}" alt="热力叠加缩略图" loading="lazy">'

            cards += f'''<div class="high-risk-detail-card">
        <h3>#{idx}{so_mark} — 伪造概率 {fake_prob:.3f} | 综合风险 {risk_score:.2f} | {RISK_LABELS.get(risk_level, risk_level)}</h3>
        <div class="hr-meta-row">
            <div class="hr-meta-item"><span class="hr-meta-label">判定</span><span class="hr-meta-value {'fake-color' if label == 'fake' else 'real-color'}">{LABELS.get(label, label)}</span></div>
            <div class="hr-meta-item"><span class="hr-meta-label">伪造概率</span><span class="hr-meta-value">{fake_prob:.3f}</span></div>
            <div class="hr-meta-item"><span class="hr-meta-label">风险分数</span><span class="hr-meta-value">{risk_score:.2f}</span></div>
            <div class="hr-meta-item"><span class="hr-meta-label">可疑区域</span><span class="hr-meta-value">{bbox_count} 处</span></div>
        </div>
        {thumb_html}
        <div class="hr-mini-bars">{mini_bars}</div>
        <p style="font-size:13px;color:#424242;">{self._escape_html(explanation_brief)}</p>
    </div>'''

        return f'''<div class="card">
    <h2>高风险条目详情 ({len(high_risk_items)}条)</h2>
    {cards}
</div>'''

    @staticmethod
    def _escape_html(text: str) -> str:
        return text.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;').replace('"', '&quot;')

    @staticmethod
    def _pil_to_b64(img: Image.Image, fmt: str = 'PNG') -> str:
        import base64
        import io
        buf = io.BytesIO()
        img.save(buf, format=fmt)
        return base64.b64encode(buf.getvalue()).decode('utf-8')


# ==============================================================================
# 中文标签映射
# ==============================================================================

LABELS = {
    'fake': 'AIGC伪造',
    'real': '真实图像',
    'local_tamper': '局部篡改',
    'error': '错误',
}

TAMPER_TYPE_LABELS = {
    'confirmed_real': '未发现局部异常',
    'local_tamper': '局部篡改证据',
    'full_aigc': '全图AIGC证据',
    'full_aigc_hotspots': '全图AIGC证据（含热点）',
    'unavailable': '不可用',
}

RISK_LABELS = {
    'low': '低风险',
    'medium': '中风险',
    'high': '高风险',
    'error': '错误',
}
