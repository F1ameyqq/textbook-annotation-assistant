# A03 P2-R11-R1：仅归档收口

2026-10-18（Asia/Shanghai）。原 A03 独立验收对话 `01a145aa-8d59-7c70-8d81-731712103a9a` 续接，保留用户 model/thinking，不委派。候选产品仍为 `cc5966dc58c62017a27266c40ca0cedc5c68485c`，base 为 `1c26b4a8eb378af33e57668472d2071e9ea6afff`。本任务不是产品返工或新的功能复验；只处理已完成 R11 独立验收的报告生成失败。

## 已冻结事实

[原 R11 独立报告](A03-P2-R11-crash-cuts-review-report.md)最终为 REWORK，SHA256 `a964ef76d836c9935dd391ad72e073f49395196ffbcd5aa43040a8cd5498127c`。原目录 `docs/evidence/A03/review/P2-R11-crash-cuts/` 的 `sha256-manifest.json` SHA256 为 `eff77340f2577d1cf66eaa3c69ad4609b2673b87002951333d7f856b158f494c`，`process-release.json` 为 `eded396dddfa7b46d1b4e0c35bd5ed9af9853ba9d2ad89ce955e36c5d6c98d4a`。从派发消息指定 workflow 的 raw Git 读取，本地原件也只读。

原四例各首轮功能结果和双库/进程审计已形成；独立证据含32份阶段 SQLite 原件。一次静态纠正用于修正 process-audit-01 对观察包装层的比较，首次错误、纠正记录和 process-audit-02 均已保留。随后 report-01 因 `write_report.py` 非 UTF-8 源码 SyntaxError 在生成报告/coverage-map 前退出；已达到原轮一次纠正上限，所以正确停止并冻结失败包。不得改写原轮停止、失败或 REWORK 历史。

[调度文件预检](../evidence/coordinator/heartbeat-20261018-0745/review-failure-preflight.json)核实1208个 manifest 条目、677个 raw Git 输入、77个源码种子以及33条实际登记进程/原始输出/退出记录。它不替代功能验收，也尚未作调度功能接受。失败不是执行者产品修改所致，不给执行对话安排产品修复。

## 一次有界处理

允许原验收者依据**既有、冻结、已完成的独立运行**完成一次报告与覆盖表收口。该授权单独登记，原轮两个归档错误和一次纠正事实仍保留。首次收口失败或发现实质证据矛盾时停止，报告明确缺口；本任务不授予第二次收口尝试，也不自动开启下轮修复。

1. 静态核对报告生成失败的具体编码原因与输出缺口。保留原坏脚本、失败输出及原 REWORK 报告原字节；在新目录中准备 UTF-8 文本/脚本，先用显式 UTF-8 解码及 `compile` 检查新源码，不导入或执行产品。也可直接用文件工具生成报告，无需重试旧脚本。
2. 只读原 manifest、四例结果、case-and-boundary-review、process-and-import-review、driver/输入登记、32份阶段原件的已存检查记录、纠正记录及最终失败包。核对新报告与原始依据的精确对应；不得把 case audit 内部的通过字段直接当作最终验收。
3. 补齐原计划的覆盖说明及最终判定。分别列出 F1-F4 结果、观察/回执/恢复引用、效果数0/0/1/1、原尝试事实、阶段文件索引、未执行范围、作者 F2/F3 中间原件缺失限制，以及原归档失败如何在本次仅文件收口中处理。独立阶段原件不能追溯补成作者原件。
4. 如既有冻结证据足以支撑原标准，可给出 `ACCEPTED_FOUR_CRASH_CUTS_ONLY`；若仍有实质缺口则 REWORK/BLOCKED，并指向具体原条款。不得降低标准、增加业务标准、豁免其他原清单范围或直接改调度状态。

**功能调用数必须为0。** 不重新运行 F1-F4、reconcile、run_plan、PRE/POST、旧功能组、归档中的产品脚本或测试。无需重做已完成的64次 SQLite 审计；只读其冻结结果和原文件摘要即可，不能连接活动库或构造缺失库。不能改候选产品、原隔离工作目录、原证据、作者目录、旧 manifest 或旧报告。无功能补证据、无作者重跑、无扩大矩阵。

## 产物、检查与释放

仅新增 `docs/tasks/A03-P2-R11-R1-archive-closure-review-report.md` 和 `docs/evidence/A03/review/P2-R11-R1-archive-closure/`。新文件引用原证据，不复制历史全集。新 manifest 覆盖新报告和本轮文件，只排除自身；包含原冻结 manifest/report/关键依据的摘要引用，核验原目录全部文件原字节未变。

若使用自有子进程，先登记实际源码/输入、argv/cwd/限时，再运行文件检查/生成，保存真实 stdout/stderr/exit；每个子进程最多45秒，限一轮。没有子进程则如实写无，不能生成假 PID。保留本次首次失败（若有），不继续修正到成功。完成后交付新报告、manifest、旧字节不变检查和实际释放证明；原用户 model/thinking 不改。

whole A03、产品集成和 I01 继续未放行；B 映射未共同确认。字段重置保持 `NOT_EXECUTED_NO_RERUN_VARIANT_OR_DELEGATION`。零网络、平台/浏览器/profile/凭据、OCR/付费模型、安装、推送、B 联系、A05题22和书级送交。
