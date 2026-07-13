# 系统图形合同与 QA

- 图 2-1 展示单一 RGB 输入、统一入口、ExplanationPipeline、唯一全局判定来源、并行解释/定位分支与三层响应。
- 图 2-3 展示真实 Web 流程中的上传、校验、API 调用、GPU 推理、证据渲染、人工复核和报告导出。
- 图 2-2 使用真实流水线输出并列展示原图、Grad-CAM 叠加图和可疑区域框。
- 图 2-1 与图 2-3 由 `experiments/plot_system_figures.py` 生成；图 2-2 由 `experiments/plot_detection_example.py` 生成。
- SVG 保留可编辑文字；PDF、PNG 用于文档兼容；600 dpi TIFF 仅仅保留在本地工作区。
- 图内不放报告标题或说明性长句；图名和高层解释由 Word 题注与正文承担。
- 视觉核查确认模块标签位于框内，箭头、状态说明与文字不重叠。
