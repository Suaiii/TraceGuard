"""
Visualization 子模块 — 图表生成 + HTML 报告

提供:
  - Visualizer:       便捷入口，一键生成全部图表
  - ReportGenerator:  HTML 报告生成器 (支持单图/批量/PDF导出)
  - radar_chart:      五维度风险雷达图
  - risk_gauge:       风险等级仪表条
  - batch_summary:    批量处理汇总图
"""

from .charts import radar_chart, risk_gauge, batch_summary, all_charts
from .report import ReportGenerator


class Visualizer:
    """
    便捷可视化入口，封装常用图表生成和报告导出。

    Usage:
        from explanation.visualization import Visualizer

        viz = Visualizer()
        report_html = viz.report('image.jpg', pipeline_result)
        viz.save_report(report_html, 'output.html')
    """

    def __init__(self, title: str = "TraceGuard 检测报告",
                 include_charts: bool = True):
        self.report_gen = ReportGenerator(
            title=title,
            include_charts=include_charts,
        )

    def report(self, image_path: str, result: dict) -> str:
        """生成单图 HTML 报告"""
        return self.report_gen.generate_single(image_path, result)

    def batch_report(self, results: list, title: str = None) -> str:
        """生成批量 HTML 报告"""
        return self.report_gen.generate_batch(results, title=title)

    def charts(self, result: dict) -> dict:
        """生成全部图表 (radar, gauge)"""
        return all_charts(result)

    @staticmethod
    def save_report(html: str, path: str):
        """保存 HTML 报告到文件"""
        with open(path, 'w', encoding='utf-8') as f:
            f.write(html)

    @staticmethod
    def save_chart(img, path: str):
        """保存单个图表为 PNG"""
        img.save(path, format='PNG')

    @staticmethod
    def to_pdf(html: str, path: str) -> str:
        """HTML → PDF (需要 weasyprint)"""
        return ReportGenerator.to_pdf(html, path)


__all__ = [
    'Visualizer',
    'ReportGenerator',
    'radar_chart',
    'risk_gauge',
    'batch_summary',
    'all_charts',
]
