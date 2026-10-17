# A03 P1：R2 完整事件前缀样例修订

日期：2026-10-17。状态：READY_FOR_REWORK。只修静态设计和样例，P2 未批准，I01 不释放。

固定基线 `ca4fba4f505467228a8164c3999e0cecc54ffc4e`，设计 `095ed4aa18a56100ce3aabc4a0d6885ad37ab520`；A02 基线仍为 `ec1b4defbfa3ec0f181d291106fb53313983e493`。原工作树 `C:/Users/ASUS/.codex/worktrees/a03-runtime-recovery/1800`，原执行对话 `01a145aa-2fea-7942-97f9-ad260acf4e30`，不合并浮动主分支。

依据 [P1-R1 独立复验](A03-P1-R1-review-report.md)，唯一未闭合项 `A03-P1-R1-PREFIX-01`。报告 SHA256 为 `788de983f08c401de4e045ccd990b090aecd868bbe9148a3615446e59539c318`；清单摘要以原始文件核对值及调度状态为准，不采用聊天中含空格的转录。主调度 [精确 Git 静态复核](../evidence/A03/coordinator/P1-R2/coordinator-check.json)确认缺口；原公开入口与引用闭包两项修订的已有结论保留。

## 唯一目标

成功例 `unattempted-absence-commit` 及复用其 C fact/basis 的 `partial-with-complete-absent` 声称有完整 accepted-plan-to-head 前缀，但只有 PLAN_REGISTERED、A/B intent 和结果；缺 PLAN_ACCEPTED、A 已 APPLIED 前的必经许可消费/派发事件及逐事件可核对的 hash 链。修订必须让成功前提与原严格准入一致。

1. 给出至少一条从 PLAN_ACCEPTED 到当前头、连续且 hash 可验证的成功事件前缀，包含设计要求的动作身份预留、许可发放/消费、DISPATCH_STARTED 与结果事实。明确事件编码/hash 规则和引用边界；若资源仅作摘要，必须绑定另一个真正完整的权威前缀，不能仅改名规避前提。
2. 沿依赖修订序号、CAS 头、basis、fact、receipt/progress 和消费者 input_refs、资源/内容摘要、候选 profile 与清单，避免新引用闭包遗漏。原 69 例保留映射与语义触发，受影响正例使用一致的新前缀。
3. 增加小规模相邻静态反例，至少缺 PLAN_ACCEPTED、APPLIED 前缺 DISPATCH_STARTED、hash 断链三类。预期在完整前缀检查层拒绝；区分静态语义检查和未来运行时实际拒绝。不得信任 complete=true，不豁免必要事件，不补造 C intent/obligation，不续发旧 tail，不解除 B UNKNOWN。
4. 增加有针对性的静态验证，核对成功前缀事件及 hash 链和上述拒绝条件；不能用硬编码 expected 直接充当检验。无需实现 SQLite、恢复 API 或重复未改动的功能套件。

## 允许新增范围

- `docs/a03-recovery-contract-v1-r2-proposal.md`
- `examples/a03/P1-R2/`
- `docs/evidence/A03/execution/P1-R2/`
- `docs/tasks/A03-P1-R2-execution-report.md`

保留 P1/P1-R1 全部原件和失败证据，不改 `src/`、`tests/`、公共合同、根依赖、调度文件或其他任务范围。新案例集应可搬运，精确绑定修订/profile/Schema；不要求重新复制整套仓库或历史验收目录，保留必要反例、引用输入摘要和实际复现材料即可。既有原规则保持，需额外规则改变时先列最小缺口，不自行扩修。

## 交付与停止条件

一次有界修订后交付准确设计及最终提交、干净工作树、可搬运样例、最短静态命令、69 例映射、邻例结果、实际退出码、报告和全量 SHA256 清单（包含日志及 Git 忽略项）。核对旧文件原字节未变；所有实际恢复行为继续标为 NOT_EXECUTED。

停在 P1 REVIEW，由原独立验收对话复验，再由主调度决定 P2。若仍不能闭合，报告具体不一致及最小选项，不自行循环重写。零网络、平台、浏览器、凭据/profile、OCR、付费模型及数据库/恢复实现；不推送或集成。记录遗留自有进程/会话为零的依据。S01、D01、B 确认和真实恢复限制保持。
