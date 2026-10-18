# A03-T3：同次 native 完整验证去重与 M 有界复验

2026-10-18。调度已接受固定诊断，采用本轮最小产品修复；续派现有 T3 执行对话 `01a14ccf-afa4-7260-a2a2-a47633772ae5`，xhigh、model 沿用。独立验收仍为 `01a14ccf-b8c3-7941-a80f-73594e7859a5`，等固定交付并释放后再续派。不开新对话、不委派、不唤醒原 A03 两个退役对话。

## 固定依据

- 唯一工作目录 `D:/1800-worktrees/a03-t3`，分支 `codex/a03-t3-closure`；起点 **F=`7b9245eaa55bad1699ee40baf71be09dd6df8371`**，开始核对 HEAD/clean，不 reset 或覆盖他人改动。
- 产品 C=`c73070884476dc2edcb952d88e4f6ed356b74ae8`、诊断候选 D=`ae2e71f9262dd7654d99ad11f916b71b2461bf58`。C→F 产品/固定输入/capture/根依赖未变，现有失败证据保持原样。
- [独立诊断复核](A03-T3-M1-diagnostic-review-report.md)，raw SHA256=`94d7295563993163e4a705a3f97d58ee4c36f95c7647e917cff355d7091b7244`；[调度接受](A03-T3-M1-diagnostic-coordinator-acceptance.md)。结论仅 `ACCEPTED_DIAGNOSTIC_ONLY`，产品 M/A03 仍 REWORK，I01 未释放。
- 原 [D-M 实现任务](A03-T3-M-implementation-handoff.md)、已接受 T3 计划 C1–C4、D-CONV=LEGACY_INITIAL_ONLY 和 fresh-native-only 继续适用。原 M1 与本次诊断合计两起点、实际四 dispatch/四 effect；不核销、不重封、不复跑旧现场。诊断 pending=1、paused=true 永久保留证据用途。

本轮确定重复链为 RuntimeStore._validate 先由 bridge_for/_issue_context 做一遍 _validate_value，再由 validate_recovery_bundle/validate_native_bundle 做第二遍。仅消除此同次内部重复。当前计时足以采用该修复，但不保证消除所有热点或45秒通过；不先追加诊断或基准。

## 产品改动白名单及不变量

只允许四个产品文件：

1. `src/annotation/contracts/a03_native/__init__.py`：私有完整验证一次并发行 context/NativeBundle 的路径，来自同次稳定输入副本、实际 resource manifest 和真实 registry。内部名称自定，不提供 already_validated/skip_validation 开关，不接收调用者自报已验证元组。
2. `src/annotation/runtime/storage/native.py`：NativeRuntimeStore._validate 专用覆盖消费上述私有结果，保留 NativeRegistry 的实际身份和 root 登记。不要改 legacy 基类或把已有 NativeBundle 当先前通过凭证。
3. `src/annotation/contracts/a03_native/data/profile.json`：只更新这两个实现的真实 implementation pins。
4. 同目录 `adoption.json`：同步实际 profile 摘要，版本/范围不扩张，不迁移旧 DB。

每次调用仍用新的 reader 完整执行原 _validate_value 一次，保留实际资源 bytes/摘要、StaticPackage、恢复闭包、逐消费者 book/scope/声明、时间、intent/resolution、issue 归属、receipt/progress、C01 投影及 reports。发行/返回仍核对当前 select_native_codec pins、_REGISTRIES/_CONTEXTS 真实身份、严格 root、一致 data 摘要与 manifest。不得全局或跨调用缓存 PASS。

公开 validate_native_bundle、bridge/derive、prepared/计划消费者继续重验；NativeRegistry._current/_pre_lease、owner/generation/head/pending/hold/fence、intent/permit、期限和效果前检查保持。native._append 中 self._validate 仍完整调用，不以父类持久化替代验证。只读入口/hold/final CAS 的原 M 语义不变。

支持改动仅限现有 `examples/a03/T3-closure/run.py`、`tests/test_a03_t3_closure.py`，本轮新报告 `docs/tasks/A03-T3-M-validation-R1-report.md` 及新证据目录 `docs/evidence/A03/T3/execution/M-validation-R1/`。沿用唯一驱动及固定输入；不新增通用工具或驱动体系。新报告兼作本轮采用/复现记录，不逐 helper 拆单。公共 C01、planner/mock/targetcheck/native_quality、schema/oracle/接口文档、根依赖、已接受 capture、旧证据/旧报告均只读。白名单不足时给具体静态反例和最小额外路径，停止依赖部分，不扩大重构。

## 一次修复包内的验证

先完成实现、真实 pins、有限控制和驱动接线自检，在首次业务前固定候选提交与实际运行字节。输入从该候选 raw Git blobs 构建，避免 CRLF 改变 pins；所有 Git 显式 `-c core.longpaths=true`，Python `-X utf8`，不安装依赖。

前置控制不新建业务目标、不 dispatch。用既有合格 native 值/registry 夹具确认新私有结果 data/manifest/context/root 与原严格入口一致，公开消费继续核对；静态确认同次路径仅一次完整 _validate_value。最多八个具名差量负控：缺嵌套正式引用、第二 consumer 借声明、错书、错 scope、成功后实际资源 bytes 变化、成功后 implementation pin 变化、错误 root、伪造/未登记 registry/context。实际 bytes/pin 变更仅在专属可丢弃夹具/运行副本，不能污染候选或旧证据。新路径须实际拒绝；不得用旧公开入口的早拒冒充新路径闭包验证。资源变化同时核对再次调用及旧 context 公开消费仍拒绝；可合并同一控制中的断言，不扩为旧全集。

前置通过后，授权以下原 M 五例的本轮 fresh 验证，上限共 **5 起点、11 实际 dispatch**；历史计数另列。每个命名场景一次，不为凑数运行：

| 顺序 | 场景与必要证据 | 上限 |
| --- | --- | --- |
| 1 | M1：三动作正常、正式 receipt/progress、单次新鲜报告、查询/重开/旧计划拒绝，同一新起点 | 1 起点 / 3 dispatch |
| 2 | M2-sufficient：A APPLIED、B UNKNOWN、C NOT_ATTEMPTED 无 intent/permit/dispatch；充分 ABSENT 才有专用 NOT_APPLIED fact/混合 receipt，B UNKNOWN 保留 | 1 / 2 |
| 3 | M2-insufficient：同样前两动作，不足只 progress/暂停，不能凑 receipt/Batch | 1 / 2 |
| 4 | M3-new-plan：原单题 UNKNOWN→一次完整 ABSENT→hold 只读候选→final read/CAS 清除→新 INITIAL/PRE/TARGET/planner/plan 才能执行；不用旧 POST_HOLD/旧尾 | 1 / 2 |
| 5 | M3-final-drift：最后实际读有变，保持 hold 和写禁令 | 1 / 2 |

业务子45秒、父90秒及原内层预算不变；readonly entry 最多3读（含最终读）、每读2秒、entry8秒、原parent60秒、gate5秒、lease10秒/renew2秒等不延长、不省略。M1 未通过则其余四例 NOT_RUN。产品缺陷或业务超时立即保全并停止本轮后继；不再追加诊断/基准/第二个同名业务起点，不降低预期。新驱动的纯接线错误沿用原任务单最多一次有界纠正规则，保留原失败、只纠正失败及未运行后继，不能绕过5/11总上限；已耗完的场景预算不能换名重启。第二次驱动错误停止。field reset=`NOT_EXECUTED_NO_RERUN_VARIANT_OR_DELEGATION`。

## 固定交付与退出

沿用已接受 capture 的同步边界及既有进程记录器，记录候选/实际 imports/输入摘要、执行命令、PID、timeout/exit/wait、stdout/stderr、实际 starts/dispatch/effects/reads/PRE、receipt/fact/progress/报告和相应原件/SQL。只选对本轮不变量有意义的边界，不机械增加阶段或全量重封。若超时，先 kill/wait 业务进程，保留当时原 DB 和存在的 journal/WAL，再按既有正常释放路径处理自有 owner/keeper，pending/UNKNOWN/hold 保留；不要恢复旧诊断 DB，不伪称崩溃 SQL/双库原子快照。

输出固定候选及最终提交、确切差异、本轮报告与非自引用证据索引、控制结果及业务逐项 PASS/FAIL/NOT_RUN、未验证限制、所有自有进程/keeper/owner 释放和干净工作树。完成后只报 REVIEW/REWORK 并等待。调度核对后才续派独立验收，不自行写 ACCEPTED/INTEGRATED。

不跑 T1/T2、旧28项全集、L/G/F、I01；无网络、平台/browser/profile/凭据、付费模型/OCR、原视频、推送、书级提交、A05题22。当前无需用户决定或 B 确认即可做本轮 A 侧离线修复；不得把它当共同合同通过。
