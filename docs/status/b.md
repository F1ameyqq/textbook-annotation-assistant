# B 侧状态

更新时间：2026-10-16（Asia/Shanghai）。负责人：xiaoshanqingpro 一侧。

- 基线：架构分支 `79b7195`（其父提交为 main `561ca5a`）。本分支 `b-side/sync-m0-recognition`。
- 合同：`contracts-v1.md` 尚为草案；本模块使用明确隔离的 `b-source-trial/0.1`、`b-evidence-trial/0.1`，不宣称公共合同已冻结。
- 交付范围：协作模板、A 请求清单、M0 旧结论清理、可移植图片清单驱动的检测/OCR 候选与叠框预览。
- 验证状态：见本分支 `docs/b-validation.md`；接收方验证待 A 记录。
- 不包含：QuestionGraph、新题自动配答、前置质量放行、平台写入、识别精度验收。
- 等待：A 的可执行合同、固定 SourceBundle/样例、模拟消费者、业务政策。详见 `docs/a-side-request.md`。
- 下一步：对接 A 确认的类型和校验器，再实现组题配答及独立覆盖检查。

代码版本以包含本页的提交和 PR head SHA 为准，接收方复现时请记录实际检出的 SHA。
