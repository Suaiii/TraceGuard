# TraceGuard 交付物库存

核查日期：2026-07-13

| 名称 | 相对路径 | 类型 | 来源/生成方式 | Git 状态 | 当前状态 |
|---|---|---|---|---|---|
| 项目 README | `README.md` | 使用与展示文档 | 仓库维护 | tracked | 可使用，但实验结果需结合本清单理解 |
| Web 工作台 | `web/` | 演示前端 | FastAPI 同源托管 | tracked | 已进入代码仓库 |
| FastAPI 服务 | `server.py`、`explanation/api/` | 后端服务 | 仓库维护 | tracked | 支持健康检查、配置、单图和批量接口 |
| TraceGuard PDF | `reports/TraceGuard.pdf` | 报告快照 | 2026-07-09 同步的历史快照 | tracked，但主工作区当前删除 | **不是最终报告**；不得作为当前交付完成证明 |
| Word 报告框架 | `output/doc/traceguard_report_framework.docx` | 报告草稿 | 由模板生成 | ignored/local | 仅为继续写作框架，不是最终报告 |
| 单图案例输出 | `case_study/` | 运行产物 | `run_test.py` 生成 | ignored | 当前不存在，需要重新运行生成 |
| 批量分析输出 | `batch_results/` | 运行产物 | `batch_analyze.py` 生成 | ignored | 当前不存在，且缺少 `tests/BigGAN/` 输入 |

## 交付判定

- 只有当前工作区实际存在、可重新生成并完成视觉/运行验证的文件，才可标记为可交付。
- README 中的历史指标是已有记录，不等同于当前目录中存在可复核的原始批量输出。
- 最终报告需要补齐实验、正式引用、架构图、结果图和局限说明后另行版本化。
- 主工作区对 `reports/TraceGuard.pdf` 的删除属于现有本地状态，本次不自动恢复或提交该删除。
