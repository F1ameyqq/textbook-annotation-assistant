# A03-T3 M1 诊断：固定证据独立复核

2026-10-18。续派现有独立验收对话 `01a14ccf-b8c3-7941-a80f-73594e7859a5`，xhigh、model 沿用。执行者已 completed/idle，最终提交和工作树干净，原件及新现场释放经调度入审核对。**只集中复核这一次诊断是否足以确定最小修复，不重跑诊断，不审 M 整体，不增加新标准。**

## 固定输入

- 采用范围：workflow `c077c2c77901d1df754ffeee4a0004162323a579` 中 [M1 诊断任务](A03-T3-M1-diagnostic-handoff.md)，raw SHA256 `fdab7e670e7ea62645bd1790fb152183ef632e9dcead75a7be59a981bd4f25a8`。
- 本次最终交付 **F=`7b9245eaa55bad1699ee40baf71be09dd6df8371`**，位于 `D:/1800-worktrees/a03-t3`。诊断候选 D=`ae2e71f9262dd7654d99ad11f916b71b2461bf58`，起点 T=`3f39a117b1b98e85c5a449a07f13b3490ef77e18`，产品 C=`c73070884476dc2edcb952d88e4f6ed356b74ae8`。
- F 内 `docs/tasks/A03-T3-M1-diagnostic-report.md` raw SHA256 **`27441a9b7059bb5f4f9d29f7abfa70e6093f983e756f69c1e8d13cdaa707b5f3`**。
- F 内 `docs/evidence/A03/T3/execution/M1-diagnostic/index.json` raw SHA256 **`33fe3cbb728089abbddc3e7914fb985cb7581f460770e0017b8e8ff20565c79c`**，233成员。
- [调度入审记录](../evidence/coordinator/heartbeat-20261018-0522/diagnostic-delivery-preflight.json)已批量核对本轮233个 raw blobs、白名单、受保护路径不变、D后驱动/产品不变、四个已登记Python进程结束、owner释放证明和pending保留。原263成员只检查Git无改动，未重封。无需再逐项重哈希233或复制整份证据。

## 需要一次回答的事项

1. **探针是否保持原语义与预算。** 只审 T→D 的 `run.py` 与 `diagnostic_release.py` 差异及本次命令：没有改产品/输入/pins/capture、跳过guard、monkeypatch、增加目标观察/重试或期限；新增1起点、实际2次DISPATCH_STARTED/2effect，第三dispatch方法ENTER不等于第三实际效果。45秒子超时后保全、最多一次正常open/claim/release，保留pending=1、paused和第三ISSUED permit；父54.797秒exit0仅为诊断/清理完成。
2. **用已有原始日志复算主要结论。** 从79行 `calls.jsonl` 复算已完成区间、累计wall/主线程CPU及最后ENTER，核对七组 `stacks.txt` 中关键帧和固定源码。区分第三prepare/intent/permit已返回与第三dispatch内部未定位；最后栈仍在intent、dump时间仅名义偏移，不能补造kill瞬间栈。评估主线程约42.234/44.015秒CPU与重复校验栈是否足以把优化范围固定在重复全量验证链。不要把栈采样当独占profile，不要求再跑基准或第二次诊断来补齐占比。
3. **判断最小修复是否保持合同。** 作者建议仅在同一次 native `_validate` 内完整验证一次，并私有返回已验证数据/resource manifest/context给 `NativeRuntimeStore._validate`；每次调用仍重查实际bytes/pins/root/registry，公开bridge/context消费者仍重验，不跨调用缓存“通过”。集中审查这条重复路径是否真实，以及如何避免遗漏逐消费者book/scope/声明/资源闭包、owner/head/fence或native._append验证。给确切最小文件/接口与有限负控范围，注明尚未实测的性能效果。无需代作者写产品或重新设计整套合同。
4. **明确可释放的下一步。** 若固定证据及建议足够，结论 `ACCEPTED_DIAGNOSTIC_ONLY`，推荐调度采用具体有界产品修复；M1/M/A03保持REWORK，I01未释放。若有直接影响诊断有效性或修复安全的缺口，给 `REWORK` 与已有材料可补的最小条目。不要把旧缺失包装日志、原崩溃journal没有SQL、没有细分独占profile等已明确限制变成无限补证；不要为优化收益作保证。

优先使用F内 `facts.json`、`call-summary.json`、`stack-map.json`、原始calls/stacks、`run/release/` 前后public与原件索引、清理后SQL导出和进程完成文件。只读取现有JSON/导出和固定Git源码；零产品导入、SQLite连接、脚本重跑、新业务/目标/dispatch/reconcile/publisher。不要打开/恢复原诊断DB或旧失败现场。该诊断现场pending永久保持证据用途，不能为了验证修复而继续它。

## 输出与停止边界

仅新增根仓库 `D:/1800/docs/tasks/A03-T3-M1-diagnostic-review-report.md`，如有必要再加 `D:/1800/docs/evidence/A03/T3/review-M1-diagnostic/` 中一个小型复算/引用记录。报告包含固定身份、探针/计数/释放核对、根因支持强度、具体修复边界及有限复验建议。记录实际只读命令和自有进程退出；无需大型审计器、额外manifest或自引用封存。不要写协调JSON、产品、作者工作树、Git索引或提交。

沿用T1/T2有限接受；不复审原28项、不推进L/G/F或I01，不新增业务起点，不代调度派产品修复。所有 Git 显式 `-c core.longpaths=true`，Python `-X utf8`。field reset=`NOT_EXECUTED_NO_RERUN_VARIANT_OR_DELEGATION`。无网络、平台/profile/凭据、安装、费用模型、OCR、原视频、推送、A05题22或书级提交，不联系B或退役原A03，不另行委派。完成一次明确判定后结束等待。
