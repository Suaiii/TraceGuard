# TraceGuard 交付物库存

核查日期：2026-07-13

| 名称 | 相对路径 | 类型 | 来源/生成方式 | Git 状态 | 当前状态 |
|---|---|---|---|---|---|
| 项目 README | `README.md` | 使用与展示文档 | 仓库维护 | tracked | 可使用，但实验结果需结合本清单理解 |
| Web 工作台 | `web/` | 演示前端 | FastAPI 同源托管 | tracked | 已进入代码仓库 |
| FastAPI 服务 | `server.py`、`explanation/api/` | 后端服务 | 仓库维护 | tracked | 支持健康检查、配置、单图和批量接口 |
| Windows 可执行入口 | `start_traceguard.bat` | 启动程序 | 调用当前 Python 环境并透传 `server.py` 参数 | tracked | 支持双击启动；依赖缺失或权重缺失时明确报错 |
| TraceGuard Markdown 报告 | `reports/TraceGuard.md` | 报告工作源 | 仓库协作维护 | tracked | 已含系统图、传播实验、案例、平台验收和正式引用；算法负责人证据未齐，不是最终报告 |
| TraceGuard PDF | `reports/TraceGuard.pdf` | 历史报告快照 | 2026-07-09 同步的历史快照 | removed | 已由 Markdown 工作源替代，不再保留在仓库 |
| Word 报告工作稿 | `output/doc/TraceGuard_作品报告_工作稿.docx`、`.pdf` | 官方模板报告 | `scripts/build_report_docx.py` 从 Markdown 工作源生成 | ignored/local | 23 页，含 10 个官方模板节、14 张图，目录/页码/题注/可访问性与逐页渲染均已核查；等待队友证据和封面字段后封版 |
| 原创性声明待签章稿 | `output/doc/TraceGuard_原创性声明_待签章.docx`、`.pdf` | 官方模板声明 | `scripts/build_originality_statement.py` 预填作品名 | ignored/local | 单页渲染通过；签名和日期保持空白，等待全员手写签名与教务公章 |
| 答辩与演示运行手册 | `docs/defense/defense_runbook.md` | 答辩素材 | 当前系统、报告和验收证据整理 | tracked | 十分钟结构、三分钟演示、故障回退和问答边界已固定；三页指标内容等待队友原始材料 |
| 提交包装配脚本与工作包 | `scripts/build_submission_package.ps1`、`output/submission/TraceGuard_submission_working_20260713_210646/` | 提交工具/本地工作包 | 从 Git 跟踪源码、本地报告和正式权重生成 | tracked + ignored/local | 已装配程序、四份材料、正式权重和 SHA-256 清单；包内启动器返回 0，明确标记为未封版 |
| 社交媒体案例输出 | `output/cases/socialmedia/` | 运行产物 | `run_test.py` 生成 | ignored | 12 个传播版本已完成完整流水线分析；小型汇总和报告级图已进入 Git |
| 批量分析输出 | `batch_results/` | 运行产物 | `batch_analyze.py` 生成 | ignored | 当前不存在，且缺少 `tests/BigGAN/` 输入 |

## 交付判定

- 只有当前工作区实际存在、可重新生成并完成视觉/运行验证的文件，才可标记为可交付。
- README 中的历史指标是已有记录，不等同于当前目录中存在可复核的原始批量输出。
- 最终报告仍需补齐消融、定位评价、风险校准、封面字段和签章上传状态后另行版本化。
- 报告更新以 `reports/TraceGuard.md` 为源；需要 PDF/DOCX 时从确认版本生成，不直接维护多个互相分叉的正文。
- 官方初赛提交包必须包含作品报告、原创性声明、源程序、可执行程序及其他相关材料，由高校联络教师统一上传。
