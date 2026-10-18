# A03 P2-R12-R1 UNKNOWN 投影候选交付

2026-10-18（Asia/Shanghai）。交付状态 **REVIEW**；本轮功能结论 **REWORK**。执行者不自行验收。A03 整体仍为 REWORK，I01 未释放。

候选代码提交：`7694490ef25539d131b863bdcb2b21531c69dfae`。唯一 base：`394fe51f5ed14c5ed312073a20faac0f5cbb9990`。workflow：`05ba526cbd8575edc778016cf25cee13661a65c6`。最终证据提交为此候选之后仅新增本证据目录和本报告的交付提交；其确切 ID 随交付消息提供，避免提交自引用。

工作目录 `C:/Users/ASUS/.codex/worktrees/a03-runtime-recovery/1800`，分支 `codex/a03-runtime-recovery`。派发键 `A03:execution:P2-R12-R1-unknown-projection:394fe51f5ed14c5ed312073a20faac0f5cbb9990`。任务原文、原 R12 和独立静态复核的 raw Git 字节见[preflight 来源](../evidence/A03/execution/P2-R12-R1-unknown-projection/preflight/raw-git/05ba526cbd8575edc778016cf25cee13661a65c6/docs/tasks/)。三份原文摘要均与派发相符；任务 SHA256 为 `ec269e977ed67276e5b4d1901c32c28acd75ba44870094fa0eb5fecf0cdc0076`。

## 候选改动与 pin

基类增加 `_project_unknown_diagnostic_post()`，默认 `True`，只在旧 `if issues` 分支追加该策略条件；native 覆盖为 `False`。没有复制投影状态机，没有改 UNKNOWN issue 构造、receipt/progress 字段、pending、fact、intent、permit 或报告发布入口。现有文件仅以下四个发生变化：

| 文件 | 原始 SHA256 | 候选 SHA256 / 改动 |
| --- | --- | --- |
| `src/annotation/runtime/storage/__init__.py` | `93cb82da040346cfba95a312f3615b8bfc5c47edee01ba69584ac338882cfa3a` | `d4d9882add415d93b8bc779a2873727f1f1ee4ce8ef41e77461d4bc05df48200`，默认策略及条件 |
| `src/annotation/runtime/storage/native.py` | `c3e2f01ccbfb7b64c49a5272eb51ffbe2f6af8c8abb5a51c4c9c6965166b902a` | `a9b039a9989ffb3afc954c87b6adbf512cf1e4ba4833cbb9e07984735b35db9b`，覆盖策略 |
| `src/annotation/contracts/a03_native/data/profile.json` | `741cadbfaaa622f2e24610026dcbfd6d68fd214dd1e4e1a1fb042df44b97445c` | `33cb93c20fadb74a3e72b55b688413b78a269daab3d7d0e6d292335ef9273bff`，仅上述两项 implementation pins |
| `src/annotation/contracts/a03_native/data/adoption.json` | 见 raw baseline 与 manifest | 仅 `profile_sha256` 同步上述 profile |

四文件完整差异可用 `git -c core.longpaths=true diff 394fe51f5ed14c5ed312073a20faac0f5cbb9990 7694490ef25539d131b863bdcb2b21531c69dfae -- src/annotation/runtime/storage/__init__.py src/annotation/runtime/storage/native.py src/annotation/contracts/a03_native/data/profile.json src/annotation/contracts/a03_native/data/adoption.json` 查看。[静态冻结证明](../evidence/A03/execution/P2-R12-R1-unknown-projection/preflight/static-stage-proof.json)核对了 33,028 项受保护历史 tree entries、40 个候选文件的 staged raw 字节；其他 profile/adoption 字段和 pins 保持原样。109 项[输入及源码索引](../../examples/a03/P2-R12-R1-unknown-projection/inputs.json)在功能开始前冻结，UTF-8 严格解码和 compile 检查完成。新 legacy 输入通过公开显式转换器由全新未执行单题输入生成，输入闭包已校验。

## 首次功能结果

| 组 | 实际执行 | 结果 |
| --- | --- | --- |
| L1 | 新单动作 legacy；一次 partial dispatch、正常完整读回 | 作者断言通过；真实 UNKNOWN fact、合法原诊断 POST/HOLD、receipt/progress、一个 unresolved issue、PENDING/暂停及 `replay_allowed=false` 保留 |
| U1 | 新单题双片段 native；一次 partial dispatch、正常完整读回 | **建立阶段失败**：receipt append 时 `MISSING_REFERENCE`；未形成正式 receipt/progress，未启动 reconcile |
| U2 | 未运行 | 首错停止 |
| U3 | 未运行 | 首错停止 |
| U4 | 未运行 | 首错停止 |
| U5 | 未运行 | 首错停止 |

完整[实际矩阵](../evidence/A03/execution/P2-R12-R1-unknown-projection/validation/author-01/matrix.json)、[L1 真实 UNKNOWN 证明](../evidence/A03/execution/P2-R12-R1-unknown-projection/validation/author-01/cases/L1/unknown-proof.json)及[U1 原始 stderr](../evidence/A03/execution/P2-R12-R1-unknown-projection/validation/author-01/processes/U1-execute/stderr.txt)均保留。L1 只证明本次受影响的有限 legacy 默认路径；没有动态重发旧动作来试探拒绝，不外推为其他 legacy 场景通过。

U1 首错发生在 `commit_action_result → project_plan → _project_plan_locked → NativeRuntimeStore._append(receipt) → native bridge → recovery._legacy_projection → validate_bundle`，早于策略分支。实际错误：

```text
$.artifacts[10].payload.unresolved_issue_ids[0]: [MISSING_REFERENCE]
unknown reference issue-save-unknown-1c539a7e21cad8405cbf61cb958992af
```

当前不变的 `validation.py:661` 仅从 CheckReport 的 `issues` 构造 `all_issues`，`:682` 检查 receipt 的 unresolved issue 引用；native 的语义投影仍调用该校验（`recovery.py:800`）。receipt 在逐件 `_append` 时尚无承载该 issue 的报告，故本次窄策略不足以形成合法 native receipt。执行证据没有到达原先预测的旧 POST 字段冲突，也没有动态验证 native 跳过 POST 后的成功路径。解决此缺口须先由调度确认如何在保留 unresolved issue 绑定、独立观察报告职责和既有闭包校验的条件下组织投影；本轮未扩改合同、校验器或发布器。

U1 [首错双库 SQL](../evidence/A03/execution/P2-R12-R1-unknown-projection/validation/author-01/cases/U1/captures/first-failure/SQL.json)表明：action 的 UNKNOWN fact 已单独提交，intent 为 PENDING、receipt 为 null、permit 为 CONSUMED、plan 为 INTERRUPTED；target 有且仅有一次真实效果及两片段中的一片。没有持久化 ExecutionReceipt、ExecutionProgress、POST_APPLY 或 BatchReport；`native_report_reads` 仍为 0。这些是失败现场事实，不是“保持暂停所以通过”。

## 现场、退出与归档

L1 留存建立前、UNKNOWN 建立后、释放后三组双库原件；U1 留存建立前、首错现场、释放后三组双库原件，共 12 份实际二进制。每组都含 capture 记录及只读 SQL；SQL 仅打开自有 `mode=ro&immutable=1` 副本，复制和审计前后核对原库摘要，逐库记录 keeper/writer 状态，未宣称跨库原子快照。U1 未到达正式 UNKNOWN 建立及 reconcile 各阶段，明确不补造这些中间证据。

两例均正常停止 keeper、释放 owner；释放后 owner 为 null、phase 为 RELEASED。L1 和 U1 的 watch/业务进程及 U1 PRE 原观察子进程共 5 个功能 Popen 均保留 preregistration/start/completion、原始 stdout/stderr；全部已 wait/reap，无 timeout。U1 业务进程和其 watchdog 实际 exit=1；其余 exit=0。实际导入路径由正常退出时的被动记录保存，源码摘要保持冻结。详见[失败与现场摘要](../evidence/A03/execution/P2-R12-R1-unknown-projection/failure-summary.json)、[进程释放证明](../evidence/A03/execution/P2-R12-R1-unknown-projection/sealing/process-release-proof.json)；新证据目录另含 `sealing/final-file-audit.json` 和统一 `manifest.json`。

本轮没有功能重跑、变体或产品/驱动修补。归档只做静态检查。所有被正式引用的 JSON、Resource、事件、原件及 raw Git 来源都在新证据目录或冻结源码输入中保留。manifest 覆盖四个改动既有文件、全部新样例/驱动/输入/测试/证据及本报告，仅排除 manifest 自身；旧大包通过原提交及 mode/type/blob 对照保全。

静态汇总首次把 ledger `files.path` 误当作 cwd 相对路径，发生 FileNotFoundError，见新证据目录 `first-archive-error.txt`。保留首错后仅进行一次新元数据纠正：按实际 runtime 目录解析这些相对路径，并完成摘要与事件链核对；未改冻结代码、驱动、输入或业务预期，未重开业务流程。纠正记录为 `metadata-correction.json`。

## 搬运与边界

以下是本轮已执行的一次入口，须以冻结候选和现有兼容 Python 环境为基础；每次入口要求全新输出目录，不覆盖现场。这里记录复现命令，不安排本轮再次执行。

```powershell
$env:PYTHONPATH = "$((Get-Location).Path)/src;$((Get-Location).Path)/examples/a03/P2-R12-R1-unknown-projection"
$env:PYTHONDONTWRITEBYTECODE = '1'
python -X utf8 -B examples/a03/P2-R12-R1-unknown-projection/run.py --output docs/evidence/A03/execution/P2-R12-R1-unknown-projection/validation/author-01
```

父 watchdog 90 秒/例、业务子进程 45 秒、原观察 2 秒、屏障 5 秒、lease 10 秒和恢复 `max_attempts=1` 均冻结；U1 恢复未启动。没有调用显式 native quality 发布。其模块及发布职责仅通过不变源码摘要静态确认，不能算新的动态发布验收。

没有运行旧全套、旧成功组、N7，未委派、改 model/thinking、合并浮动分支、推送或联系 B；没有网络、平台、浏览器、profile/凭据、安装、OCR、付费模型、A05题22或书级送交。字段重置保持 `NOT_EXECUTED_NO_RERUN_VARIANT_OR_DELEGATION`。本交付不关闭投影缺陷或原 V03/R05 五项，不外推其他 A03 条目、本地集成、B 接受或 I01 完成。
