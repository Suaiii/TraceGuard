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
                        result: dict) -> str:
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
        html = f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{self.title} — {filename}</title>
<style>
{self._css()}
</style>
</head>
<body>

<!-- =============== 页头 =============== -->
<div class="header">
    <div class="header-left">
        <h1>{self.title}</h1>
        <div class="subtitle">{filename} — 生成时间: {now}</div>
    </div>
    <div class="header-right">
        <div class="risk-badge risk-{risk_level}">{RISK_LABELS.get(risk_level, risk_level)}</div>
    </div>
</div>

<!-- =============== 摘要区 =============== -->
<div class="summary">
    <div class="summary-item">
        <span class="summary-label">判定结果</span>
        <span class="summary-value {'fake-color' if label == 'fake' else 'real-color'}">{LABELS.get(label, label)}</span>
    </div>
    <div class="summary-item">
        <span class="summary-label">局部证据类型</span>
        <span class="summary-value {'local-tamper-color' if tamper_type == 'local_tamper' else ''}">{TAMPER_TYPE_LABELS.get(tamper_type, tamper_type)}</span>
    </div>
    <div class="summary-item">
        <span class="summary-label">伪造概率</span>
        <span class="summary-value">{fake_prob:.3f}</span>
    </div>
    <div class="summary-item">
        <span class="summary-label">风险分数</span>
        <span class="summary-value">{risk_score:.2f}</span>
    </div>
    <div class="summary-item">
        <span class="summary-label">风险等级</span>
        <span class="summary-value risk-{risk_level}-text">{RISK_LABELS.get(risk_level, risk_level)}</span>
    </div>
    <div class="summary-item">
        <span class="summary-label">分析耗时</span>
        <span class="summary-value">{elapsed_ms:.0f} ms</span>
    </div>
    <div class="summary-item">
        <span class="summary-label">可疑区域</span>
        <span class="summary-value">{len(bbox_list)} 处</span>
    </div>
</div>

<!-- =============== 主内容区 =============== -->
<div class="main-grid">
    <!-- 左列: 图像 -->
    <div class="col">
        <div class="card">
            <h2>热力图叠加</h2>
            {self._img_tag(result.get('overlay_b64'), '热力图叠加图')}
            <div class="caption">原图 + 半透明热力层 (蓝=低伪造可疑, 红紫=高伪造可疑)</div>
        </div>
        <div class="card">
            <h2>篡改可疑区域</h2>
            {self._img_tag(result.get('tamper_overlay_b64'), '篡改掩膜叠加')}
            <div class="caption">红色标记区域为可疑篡改位置</div>
        </div>
        <div class="card">
            <h2>可疑区域坐标框</h2>
            {self._img_tag(result.get('bbox_image_b64'), 'BBox 标注')}
            <div class="caption">红色矩形框标记可疑区域边界</div>
        </div>
    </div>

    <!-- 右列: 图表 + 解释 -->
    <div class="col">
        {self._radar_section(radar_b64)}
        {self._gauge_section(gauge_b64)}
        <div class="card">
            <h2>解释摘要</h2>
            <div class="explanation-brief">{explanation_brief}</div>
        </div>
        {self._bbox_table(bbox_list)}
    </div>
</div>

<!-- =============== 解释全文 =============== -->
<div class="card explanation-full">
    <h2>详细解释</h2>
    <pre class="explanation-text">{self._escape_html(explanation)}</pre>
</div>

<!-- =============== 维度详情 =============== -->
{self._dimension_table(dim_scores)}

<!-- =============== 元信息 =============== -->
<div class="card meta">
    <h2>分析元信息</h2>
    <table class="meta-table">
        <tr><td>热力图方法</td><td>{metadata.get('heatmap_method', '-')}</td></tr>
        <tr><td>叠加透明度</td><td>{metadata.get('overlay_alpha', '-')}</td></tr>
        <tr><td>定位模块</td><td>{'启用' if metadata.get('localization_enabled') else '禁用'}</td></tr>
        <tr><td>解释语言</td><td>{metadata.get('language', '-')}</td></tr>
        <tr><td>风险权重</td><td>{self._format_weights(metadata.get('risk_weights', {}))}</td></tr>
    </table>
</div>

<!-- =============== 页脚 =============== -->
<div class="footer">
    <p>© {datetime.now().year} {self.company} — AIGC图像安全审核平台</p>
    <p>本报告由 TraceGuard 自动生成，仅供审核参考。</p>
</div>

</body>
</html>'''

        return html

    # ------------------------------------------------------------------
    # 批量报告
    # ------------------------------------------------------------------

    def generate_batch(self, results: list,
                       title: str = None) -> str:
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

            result_rows += f'''
            <tr>
                <td class="cell-index">{i}</td>
                <td class="cell-file" title="{self._escape_html(file_name)}">{self._escape_html(file_name)}</td>
                <td class="cell-status {label_cls}">{LABELS.get(label, label)}</td>
                <td class="cell-num">{fake_prob:.3f}</td>
                <td class="cell-num">{risk_score:.2f}</td>
                <td class="cell-status {risk_cls}">{RISK_LABELS.get(risk_level, risk_level)}</td>
                <td class="cell-num">{elapsed_ms:.0f}ms</td>
                <td class="cell-brief">{self._escape_html(explanation_brief)}</td>
            </tr>'''

        html = f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{title}</title>
<style>
{self._css()}
</style>
</head>
<body>

<div class="header">
    <div class="header-left">
        <h1>{title}</h1>
        <div class="subtitle">生成时间: {now} — 共 {total} 张图片</div>
    </div>
</div>

<!-- 汇总统计 -->
<div class="summary">
    <div class="summary-item"><span class="summary-label">总图片</span><span class="summary-value">{total}</span></div>
    <div class="summary-item"><span class="summary-label">成功</span><span class="summary-value real-color">{success}</span></div>
    <div class="summary-item"><span class="summary-label">AIGC伪造</span><span class="summary-value fake-color">{fake_count}</span></div>
    <div class="summary-item"><span class="summary-label">局部篡改</span><span class="summary-value local-tamper-color">{tamper_count}</span></div>
    <div class="summary-item"><span class="summary-label">真实图</span><span class="summary-value real-color">{real_count}</span></div>
    <div class="summary-item"><span class="summary-label">高风险</span><span class="summary-value risk-high-text">{high_risk}</span></div>
    <div class="summary-item"><span class="summary-label">中风险</span><span class="summary-value risk-medium-text">{medium_risk}</span></div>
    <div class="summary-item"><span class="summary-label">低风险</span><span class="summary-value risk-low-text">{low_risk}</span></div>
</div>

<!-- 汇总图表 -->
{self._summary_section(summary_b64)}

<!-- 逐条结果表 -->
<div class="card">
    <h2>逐条分析结果</h2>
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

<div class="footer">
    <p>© {datetime.now().year} {self.company} — AIGC图像安全审核平台</p>
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
            :root {
                --bg: #F5F5F5;
                --card-bg: #FFFFFF;
                --text: #212121;
                --text-secondary: #757575;
                --border: #E0E0E0;
                --accent: #1565C0;
                --fake-red: #D32F2F;
                --real-green: #2E7D32;
                --tamper-yellow: #F9A825;
                --risk-low: #4CAF50;
                --risk-medium: #FF9800;
                --risk-high: #F44336;
                --radius: 8px;
            }
            * { box-sizing: border-box; margin: 0; padding: 0; }
            body {
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Microsoft YaHei', sans-serif;
                background: var(--bg);
                color: var(--text);
                max-width: 1100px;
                margin: 0 auto;
                padding: 24px 20px;
                line-height: 1.6;
            }
            .header {
                display: flex;
                justify-content: space-between;
                align-items: center;
                background: var(--card-bg);
                padding: 24px 28px;
                border-radius: var(--radius);
                box-shadow: 0 1px 3px rgba(0,0,0,0.08);
                margin-bottom: 16px;
            }
            .header h1 { font-size: 22px; color: var(--accent); }
            .subtitle { font-size: 13px; color: var(--text-secondary); margin-top: 4px; }
            .risk-badge {
                display: inline-block;
                font-size: 20px;
                font-weight: 700;
                padding: 12px 28px;
                border-radius: var(--radius);
                color: #FFF;
            }
            .risk-low { background: var(--risk-low); }
            .risk-medium { background: var(--risk-medium); }
            .risk-high { background: var(--risk-high); }
            .risk-low-text { color: var(--risk-low); font-weight: 700; }
            .risk-medium-text { color: var(--risk-medium); font-weight: 700; }
            .risk-high-text { color: var(--risk-high); font-weight: 700; }

            /* Summary */
            .summary {
                display: flex;
                flex-wrap: wrap;
                gap: 12px;
                background: var(--card-bg);
                padding: 18px 24px;
                border-radius: var(--radius);
                box-shadow: 0 1px 3px rgba(0,0,0,0.08);
                margin-bottom: 16px;
            }
            .summary-item {
                display: flex;
                flex-direction: column;
                align-items: center;
                min-width: 90px;
            }
            .summary-label { font-size: 12px; color: var(--text-secondary); }
            .summary-value { font-size: 18px; font-weight: 700; }
            .fake-color { color: var(--fake-red); }
            .real-color { color: var(--real-green); }
            .local-tamper-color { color: var(--tamper-yellow); }

            /* Grid */
            .main-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; margin-bottom: 16px; }
            @media (max-width: 800px) { .main-grid { grid-template-columns: 1fr; } }

            /* Card */
            .card {
                background: var(--card-bg);
                border-radius: var(--radius);
                box-shadow: 0 1px 3px rgba(0,0,0,0.08);
                padding: 20px;
                margin-bottom: 16px;
            }
            .card h2 {
                font-size: 15px;
                color: var(--accent);
                border-bottom: 2px solid var(--border);
                padding-bottom: 8px;
                margin-bottom: 12px;
            }
            .card img {
                width: 100%;
                border-radius: 4px;
                border: 1px solid var(--border);
            }
            .caption {
                font-size: 12px;
                color: var(--text-secondary);
                margin-top: 8px;
                text-align: center;
            }

            /* Explanation */
            .explanation-brief {
                font-size: 14px;
                font-weight: 600;
                color: var(--text);
                padding: 8px 0;
            }
            .explanation-full pre.explanation-text {
                white-space: pre-wrap;
                font-family: inherit;
                font-size: 14px;
                line-height: 1.8;
                background: #FAFAFA;
                padding: 16px;
                border-radius: 4px;
                border: 1px solid var(--border);
            }

            /* Tables */
            .meta-table { width: 100%; border-collapse: collapse; }
            .meta-table td {
                padding: 8px 12px;
                border-bottom: 1px solid var(--border);
                font-size: 13px;
            }
            .meta-table td:first-child { font-weight: 600; color: var(--text-secondary); width: 140px; }

            .dim-table { width: 100%; border-collapse: collapse; margin-top: 8px; }
            .dim-table th, .dim-table td {
                padding: 10px 12px;
                border-bottom: 1px solid var(--border);
                text-align: center;
                font-size: 13px;
            }
            .dim-table th { background: #F5F5F5; font-weight: 600; color: var(--text-secondary); }
            .dim-bar {
                display: inline-block;
                height: 8px;
                border-radius: 4px;
                background: var(--accent);
                vertical-align: middle;
                margin-right: 6px;
            }

            .result-table { width: 100%; border-collapse: collapse; font-size: 13px; }
            .result-table th {
                background: #F5F5F5;
                padding: 10px 8px;
                text-align: left;
                font-weight: 600;
                color: var(--text-secondary);
                border-bottom: 2px solid var(--border);
                position: sticky;
                top: 0;
            }
            .result-table td { padding: 8px; border-bottom: 1px solid var(--border); }
            .cell-index { width: 36px; text-align: center; color: var(--text-secondary); }
            .cell-file { max-width: 160px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
            .cell-num { text-align: center; font-variant-numeric: tabular-nums; }
            .cell-status { text-align: center; font-weight: 700; }
            .cell-brief {
                max-width: 200px;
                overflow: hidden;
                text-overflow: ellipsis;
                white-space: nowrap;
                font-size: 12px;
                color: var(--text-secondary);
            }
            .table-scroll { overflow-x: auto; }

            /* BBox table */
            .bbox-table { width: 100%; border-collapse: collapse; font-size: 13px; }
            .bbox-table th {
                background: #F5F5F5;
                padding: 8px;
                text-align: center;
                font-weight: 600;
                color: var(--text-secondary);
                border-bottom: 2px solid var(--border);
            }
            .bbox-table td { padding: 8px; text-align: center; border-bottom: 1px solid var(--border); }

            /* Footer */
            .footer {
                text-align: center;
                padding: 24px;
                color: var(--text-secondary);
                font-size: 12px;
                border-top: 1px solid var(--border);
                margin-top: 16px;
            }
            .no-image {
                display: flex;
                align-items: center;
                justify-content: center;
                height: 120px;
                background: #FAFAFA;
                border: 1px dashed var(--border);
                border-radius: 4px;
                color: var(--text-secondary);
                font-size: 13px;
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

    def _radar_section(self, radar_b64) -> str:
        if not radar_b64:
            return ''
        return f'''<div class="card">
            <h2>风险维度雷达图</h2>
            <img src="data:image/png;base64,{radar_b64}" alt="五维度雷达图">
        </div>'''

    def _gauge_section(self, gauge_b64) -> str:
        if not gauge_b64:
            return ''
        return f'''<div class="card">
            <h2>风险分数</h2>
            <img src="data:image/png;base64,{gauge_b64}" alt="风险仪表条">
        </div>'''

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
            <h2>可疑区域列表</h2>
            <p style="color:var(--text-secondary);font-size:13px;">未检测到可疑篡改区域</p>
        </div>'''

        rows = ''
        for i, bbox in enumerate(bbox_list, 1):
            local_score = bbox.get('risk_score', 0)
            rows += f'''<tr>
                <td>{i}</td>
                <td>({bbox['x']}, {bbox['y']})</td>
                <td>{bbox['w']}×{bbox['h']}</td>
                <td>{bbox.get('area', bbox['w']*bbox['h'])}</td>
                <td style="font-weight:700;">{local_score:.2f}</td>
            </tr>'''

        return f'''<div class="card">
            <h2>可疑区域列表 ({len(bbox_list)}处)</h2>
            <table class="bbox-table">
                <thead><tr><th>#</th><th>坐标 (x,y)</th><th>尺寸 (w×h)</th><th>面积 (px)</th><th>局部风险分</th></tr></thead>
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

        rows = ''
        for key, label in dim_names.items():
            val = dim_scores.get(key, 0)
            pct = int(val * 100)
            rows += f'''<tr>
                <td style="text-align:left;font-weight:600;">{label}</td>
                <td>{val:.4f}</td>
                <td>
                    <span class="dim-bar" style="width:{pct}%;min-width:2px;"></span>
                    {pct}%
                </td>
            </tr>'''

        return f'''<div class="card">
            <h2>风险维度详情</h2>
            <table class="dim-table">
                <thead><tr><th style="text-align:left;">维度</th><th>分数</th><th>百分比</th></tr></thead>
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
