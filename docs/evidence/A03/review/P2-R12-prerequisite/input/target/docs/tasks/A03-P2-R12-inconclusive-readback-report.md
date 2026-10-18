# A03 P2-R12 异常读回准备期阻断交付

2026-10-18（Asia/Shanghai）。状态：**REVIEW_PREPARATION_BLOCKED**。静态核对发现指定 normal UNKNOWN 建立流程与当前 native CheckReport 合同不兼容，按任务的准备期停止规则未启动 U1；U2–U5 同样未执行。产品、合同、pins 和历史原件未改。本轮没有 init/PRE/dispatch/UNKNOWN/reconcile 调用，不把静态分析完成记为五项功能通过，A03/I01 未释放。

## 固定输入与停止依据

- 唯一 base：`cc5966dc58c62017a27266c40ca0cedc5c68485c`；接单时 clean HEAD 精确一致。
- workflow：`7593f880ebec191ed55e03b2d3893d68b00ab0ca`；工作树：`C:/Users/ASUS/.codex/worktrees/a03-runtime-recovery/1800`；分支：`codex/a03-runtime-recovery`。
- [确切任务原件](../evidence/A03/execution/P2-R12-inconclusive-readback/inputs/A03-P2-R12-inconclusive-readback-validation.md) raw SHA256=`15c4f65a698a86ffeb0bbde8a6c97465905bcb0fb5f9bfc1856aec522161f1df`。其明确要求“入口不支持或准则冲突时记录具体位置并停止，不写产品或改标准”，且五例都必须先经正常支持流程建立正式 UNKNOWN。
- [R11 调度结论原件](../evidence/A03/execution/P2-R12-inconclusive-readback/inputs/A03-P2-R11-crash-cuts-coordinator-decision.md) 仅作历史范围引用，旧场景未重跑，原缺件限制及所有失败原件保留。
- 最终 exact commit 是本报告与 R12 新文件所在 clean HEAD，见交付消息/Git 日志，避免提交自引用。

仅新增 [R12 静态核对入口](../../tests/test_a03_p2_r12_inconclusive_readback.py)、[归档工具目录](../../examples/a03/P2-R12-inconclusive-readback)、本报告和 R12 execution 证据。没有合并调度分支或复制历史归档全集。

## 明确的前置冲突

当前公开 fault 接缝确实列出 partial、duplicate、contradictory、truncated、unavailable。问题发生在它们恢复之前的 formal UNKNOWN 投影：

1. 单动作 partial 会按现有 `apply_synthetic_action` 去掉两片段中的最后一片。完整执行读回既不满足全部 frames MATCH，也不是零帧且与 before 相同的 ABSENT，因此共享比较器返回 CONFLICT/outcome UNKNOWN。
2. [RuntimeStore.commit_action_result](../../src/annotation/runtime/storage/__init__.py):693–740 正常提交 UNKNOWN fact/未决 intent 后调用 project_plan。新鲜单动作的 fact 已存在、结果 UNKNOWN，因此 `_project_plan_locked` 中 unknown/issue 列表非空；此前没有可复用 receipt。
3. 同文件:790–802 的 `if issues` 分支在 :793 自动构造旧形状的 POST_APPLY CheckReport，带 snapshot/coverage/checks/reason。这个副作用属于 project，不需要显式调用 publish_quality，因此不能通过“本轮不发布 POST/Batch”避开。
4. `_new_artifact` 只包裹原 payload 并继承 plan 的 native schema_version，不转换该诊断结构。NativeRuntimeStore 没有覆盖它；[native.py](../../src/annotation/runtime/storage/native.py):291–298 的 `_append` 在落库前直接验证合并后的包。
5. 当前 [native exchange Schema](../../src/annotation/contracts/a03_native/data/schemas/exchange.json) 的 artifacts union 只选择 AmendedCheckReport 等 native 定义。其 POST_APPLY 分支要求下列字段集合，additionalProperties=false，没有兼容这个旧诊断 POST 的分支。

| 方向 | 具体字段 |
| --- | --- |
| 旧构造缺少的6个 native 必需字段 | `action_bindings`, `content_check_status`, `frame_structure`, `report_observation`, `report_snapshot_ref`, `submission_status` |
| native POST 不允许的4个旧字段 | `checks`, `coverage`, `reason`, `snapshot` |

Schema pointer=`/$defs/AmendedCheckReport/properties/payload/oneOf/2`。此外 [native 合同](../../src/annotation/contracts/a03_native/__init__.py):211 起的 `_reports` 也直接消费 report_snapshot_ref/action_bindings/report_observation；不能仅给旧 payload 换个版本或放宽字段检查。

完整字面字段、Schema required/properties、条件链、源码行号和原摘要见 [静态前提审计](../evidence/A03/execution/P2-R12-inconclusive-readback/preflight/static-prerequisite-conflict.json)；精确 RuntimeStore 类方法及 transaction 包装源码见 [调用链补充](../evidence/A03/execution/P2-R12-inconclusive-readback/preflight/source-chain-supplement.json)。所有必要原源码/Schema raw Git blobs 在 inputs/base 保存。

这是读取固定源码和 Schema 得出的输出集合冲突，**没有动态运行或捕获产品异常**，没有宣称实际返回了某个外层错误码。当前事务包装也已静态保留，未按猜测的错误字符串判失败。其他更早的动态依赖是否另有阻断并未验证。

## 五例实际/未执行状态

| 组 | 实际状态 | 仅供后续准备的源级预期，未验证 |
| --- | --- | --- |
| U1 部分生效 | NOT_EXECUTED_STATIC_PREREQUISITE_CONFLICT | partial 保留一部分 frame；正常完整新读回应为 CONFLICT/UNKNOWN，保持未决 |
| U2 重复身份 | NOT_EXECUTED_AFTER_PREPARATION_STOP | 新 applied case 执行读回 unavailable 形成 UNKNOWN；恢复 duplicate 必须出现真实重复身份，不能降级为空表 |
| U3 矛盾 | NOT_EXECUTED_AFTER_PREPARATION_STOP | CONTRADICTORY 应为 INDETERMINATE/UNKNOWN，不能解除暂停 |
| U4 截断 | NOT_EXECUTED_AFTER_PREPARATION_STOP | TRUNCATED/incomplete scope 不能形成终局解决 |
| U5 不可用 | NOT_EXECUTED_AFTER_PREPARATION_STOP | UNAVAILABLE 的 sequence/hash/version/null、无 snapshot 按实际保留，不补造终局结果 |

上述预期来自公开接缝、比较器及恢复源码，仅是准备依据，不是 admission/capture/commit/paused 结果。没有运行后将未捕获错误改写为“仍暂停即成功”。U2–U5 仍共享“先完成正式 UNKNOWN”这一必要前提，本轮在顺序首项准备阻断后停止，不绕过它继续。

## 数据库与实际过程边界

没有创建任何 case、runtime/target 数据库或业务进程。四个要求阶段（建立前、UNKNOWN 建立/释放后、reconcile 前、reconcile 后）的二进制 capture 均为 **NOT_APPLICABLE / NOT_CREATED**。这里没有执行后漏存的阶段，不用最终库重建中间库，不把不存在数据库的效果/行数填为0；效果数量标为未观察。

没有正式运行产物的 plan/intent/receipt/resolution/attempt 四元组，没有新观察、Resource、事件、keeper 或业务 owner 可释放。已有示例只作为代码/Schema 读取，没有回放数据库或结果。当前静态审计退出0只表示固定字段冲突被核对出来，不是五例功能测试成功。

唯一登记的子进程为静态审计：PID54248，exit0、timeout=false、alive=false。真实 executable=`C:/Users/ASUS/AppData/Local/Programs/Python/Python39/python.exe`；argv/cwd、输入/脚本摘要、源码快照、原 stdout/stderr 和退出记录见 [preregistration](../evidence/A03/execution/P2-R12-inconclusive-readback/runs/static-prerequisite/preregistered.json) 与 [completion](../evidence/A03/execution/P2-R12-inconclusive-readback/runs/static-prerequisite/completed.json)。程序仅导入标准库，严格 UTF-8 解码、compile 和 AST/JSON 字段检查；不导入或调用 annotation 产品，不将 AST 裁剪后执行。

## 原件、命令与最小所需范围

[输入登记](../evidence/A03/execution/P2-R12-inconclusive-readback/inputs.json) 包含4份确切 workflow 原文和10份最小源输入；10份 raw Git 与工作树字节均相同。冻结前对全部执行入口严格 UTF-8 解码并 compile，见 [驱动登记](../evidence/A03/execution/P2-R12-inconclusive-readback/driver-preregistered.json)：

| 文件 | SHA256 |
| --- | --- |
| `tests/test_a03_p2_r12_inconclusive_readback.py` | `c1873f0d2d8e8fcc88cffff617c178a8e12c8b41537f156e4f36289e50b434a8` |
| `examples/a03/P2-R12-inconclusive-readback/audit_a03_p2_r12.py` | `f52722f3de8476098efe559a66061a10a1828a951c8637f963473fbc06343f80` |
| `examples/a03/P2-R12-inconclusive-readback/prepare_a03_p2_r12.py` | `64305d7cf3f081a40a53fa1d50f1551eb7801ab1caa2f6c9751f87c0e58f2257` |

实际命令均从仓库根目录运行，无个人绝对路径参数；已有输出 exclusive，不覆盖：

```powershell
python -X utf8 -B examples/a03/P2-R12-inconclusive-readback/prepare_a03_p2_r12.py
python -X utf8 -B examples/a03/P2-R12-inconclusive-readback/audit_a03_p2_r12.py
```

直接静态入口为 `python -X utf8 -B tests/test_a03_p2_r12_inconclusive_readback.py --output-root docs/evidence/A03/execution/P2-R12-inconclusive-readback/<new-static-directory>`。它不提供未执行的 U1–U5 业务演示，不能用它的退出码代替功能验收。

最小需要处理的位置是 `RuntimeStore._project_plan_locked` 的 native UNKNOWN 诊断分支：使其实际输出与 native 合同一致，同时保留原 UNKNOWN fact/正式 receipt/progress、pending/paused 和旧版行为。不应在本轮通过改 Schema/pins、丢历史、补造独立报告观察、换旧版本或绕过正常 project 来取得资格。若需产品修复，应由调度另发这一有界范围及受影响的 pins/合同责任；**本轮未实施任何修复，也未证明后续只有这一处问题。**

[范围结果](../evidence/A03/execution/P2-R12-inconclusive-readback/bounded-outcome.json) 与 [覆盖/未达映射](../evidence/A03/execution/P2-R12-inconclusive-readback/coverage-map.json) 明确五例仍未动态覆盖。[进程释放清单](../evidence/A03/execution/P2-R12-inconclusive-readback/process-release.json) 保留所有已登记自有进程 wait/退出；[系统 PID 只读核对](../evidence/A03/execution/P2-R12-inconclusive-readback/process-os-readback.json) 只查本轮登记 PID，不触碰其他任务。

最终 raw Git mode/type/blob 逐项比较 base32993个条目，所有旧文件无例外保持；产品 source index 与 base 相同。manifest 覆盖完整本轮新交付、报告、原文/源码、审计输出、脚本和释放证明，只排除自身；入库后再核对 raw blobs，clean status 冻结。文件复核入口为 `python -X utf8 -B examples/a03/P2-R12-inconclusive-readback/seal_a03_p2_r12.py check`，不执行产品。

保留用户 model/thinking，不委派、不改 coordination-state、不推送、不自记 ACCEPTED/INTEGRATED。字段重置始终 `NOT_EXECUTED_NO_RERUN_VARIANT_OR_DELEGATION`。零网络、平台/浏览器/profile/凭据、OCR/模型、安装、B联系、A05题22和书级送交；旧接受组、旧失败及全套矩阵均未重跑。A03/I01 和 B 版本映射边界继续保留。
