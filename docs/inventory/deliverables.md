# TraceGuard 交付物库存

核查日期：2026-07-13

| 名称 | 相对路径 | 类型 | 来源/生成方式 | Git 状态 | 当前状态 |
|---|---|---|---|---|---|
| 项目 README | `README.md` | 使用与展示文档 | 仓库维护 | tracked | 可使用，但实验结果需结合本清单理解 |
| Web 工作台 | `web/` | 演示前端 | FastAPI 同源托管 | tracked | 已进入代码仓库 |
| FastAPI 服务 | `server.py`、`explanation/api/` | 后端服务 | 仓库维护 | tracked | 支持健康检查、配置、单图和批量接口 |
| TraceGuard Markdown 报告 | `reports/TraceGuard.md` | 报告工作源 | 本地现有 Markdown 草稿 | tracked | 当前协作版本；仍含待补表格、图片和参考文献，不是最终报告 |
| TraceGuard PDF | `reports/TraceGuard.pdf` | 历史报告快照 | 2026-07-09 同步的历史快照 | removed | 已由 Markdown 工作源替代，不再保留在仓库 |
| Word 报告框架 | `output/doc/traceguard_report_framework.docx` | 报告草稿 | 由模板生成 | ignored/local | 仅为继续写作框架，不是最终报告 |
| 单图案例输出 | `case_study/` | 运行产物 | `run_test.py` 生成 | ignored | 当前不存在，需要重新运行生成 |
| 批量分析输出 | `batch_results/` | 运行产物 | `batch_analyze.py` 生成 | ignored | 当前不存在，且缺少 `tests/BigGAN/` 输入 |

## 交付判定

- 只有当前工作区实际存在、可重新生成并完成视觉/运行验证的文件，才可标记为可交付。
- README 中的历史指标是已有记录，不等同于当前目录中存在可复核的原始批量输出。
- 最终报告需要补齐实验、正式引用、架构图、结果图和局限说明后另行版本化。
- 报告更新以 `reports/TraceGuard.md` 为源；需要 PDF/DOCX 时从确认版本生成，不直接维护多个互相分叉的正文。
