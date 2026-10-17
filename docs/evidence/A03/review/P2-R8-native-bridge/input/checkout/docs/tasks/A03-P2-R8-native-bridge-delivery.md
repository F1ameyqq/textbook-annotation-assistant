# A03 P2-R8 原生桥接冻结交付

状态：**REVIEW，N1 未闭合**。本轮唯一局部修复已使用；随后出现独立的 producer/schema 合同阻断，停止修改产品和执行后续组。没有自记 ACCEPTED、INTEGRATED 或释放 I01。

base `8ad45dd07214ae406a3fab28d76a4b5abd6eef03`，workflow `873d8151000430fc79e63b312ccd21978fc15f79`。工作树 `C:/Users/ASUS/.codex/worktrees/a03-runtime-recovery/1800`，分支 `codex/a03-runtime-recovery`。未委派、未合浮动主树、未更改用户的 model/thinking。

- 合同/显式桥接先提交：`352b1475fff85a034b839a712ee499ba4c1ec5e6`。
- runtime/producer/链路候选及冻结残余：`334577d922d224789191a8b4d7127513692ada95`。
- 本报告与原始证据随后单独提交；最终交付 tip 由交付消息给出，包含上述两个提交和全部证据。

[固定任务原字节](../evidence/A03/execution/P2-R8-native-bridge/inputs/task.md) SHA256 `b7dbf94ff06d8ba272b1bd20bf61afbe09fa1dd99c501dcb70f865ab36737721`；[输入核对索引](../evidence/A03/execution/P2-R8-native-bridge/inputs.json) 记录逐项核对的 89 个输入。旧内容保全见[Git blob 差分](../evidence/A03/execution/P2-R8-native-bridge/preservation.json)。

## 最短实际失败

第二次 N1 的真实子进程 PID `23008` 退出 `1`，父测试 PID `63432` 退出 `1`，均未 timeout，未到效果屏障。原始[子进程 stderr](../evidence/A03/execution/P2-R8-native-bridge/validation/bounded-02/processes/n1-child/stderr.txt) 和[父测试 stderr](../evidence/A03/execution/P2-R8-native-bridge/runs/N1-local-fix/stderr.txt) 保留不覆盖。

实际链停在：

`produce_a03_pre_run -> make_artifact -> seal_native_artifact -> NativeSchemas.check -> CheckReport.payload: SHAPE_oneOf`。

静态对照定位：`synthetic_precheck.py:122` 把 `coverage_for(bundle, graph)` 的完整返回值直接作为 `payload.coverage`；`targetcheck/__init__.py:109` 返回 `(coverage, complete)`，而 PRE schema 要求 coverage 对象。因此封签时形成数组，不能匹配 PRE payload 分支。没有继续修复或重跑，也没有补造 PRE/接纳值。

第一次 N1 更早在私有 C01 语义投影处报 `HASH_MISMATCH`：整数坐标进入 C01 类型模型后规范化为浮点，投影封签前后的摘要不一致。本轮唯一修复仅在该私有投影内先通过 C01 类型规范化，再计算投影摘要。原生 1.4 输入、引用和资源原字节不变，投影不导出为 CURRENT。首次[原始失败](../evidence/A03/execution/P2-R8-native-bridge/runs/N1-initial/stderr.txt)、对应脚本和产品快照完整保留。修复后仅复跑 N1，推进到了上面的独立 PRE producer 合同阻断。

## 实际执行边界

第二次执行正常创建了两个新合成 SQLite 库、一个书籍登记、owner/fence 和一次真实独立目标观察。新的完整 PGM 已读取，五项比较在新 run resource 中均记录 PASS；这只是**已计算、未接纳**的 producer 产物，不能作为质量通过或写入资格。

[只读数据库回看及组状态](../evidence/A03/execution/P2-R8-native-bridge/bounded-outcome.json) 记录：runtime 中 `native_pre_runs=1`、`status=OBSERVED`、`reads=1`、`pre_ref=null`、`run_sha=null`；target 中 `observations=1`、`effects=0`。两个库的原字节摘要在只读查询前后相同。

| 项目 | 本轮结果 |
|---|---|
| N1 | 两次实际运行；唯一修复后停在 PRE 封签前，未接纳 |
| N2–N7 | `NOT_RUN_AFTER_INDEPENDENT_BLOCKER`，只有候选测试代码 |
| TARGET / create_plan / PreparedAction | 尚未到达，不宣称功能通过 |
| intent / permit / dispatch / UNKNOWN 恢复 / 晚到 receipt / POST / Batch | 尚未到达，不存在成功链产物 |
| 独立目标效果次数 | **0**，没有把设计要求的 1 次当成实际结果 |
| C01 `test_contracts*.py` | 一轮 70 项通过 |
| A02 `test_a02*.py` | 一轮 52 项通过 |
| R7 `test_a03_r7_readonly_codec.py` | 一轮 13 项通过 |

三组兼容性运行均在上述 native-only 投影修复前完成，之后遵守“各一轮”限制没有重复执行。它们没有证明最终候选的 N1–N7，也没有替代原独立验收。没有运行旧 36 静态矩阵、旧 P2 全矩阵、旧 examples main/session/conversion/oracle 驱动。

字段重置专项：`NOT_EXECUTED_NO_RERUN_VARIANT_OR_DELEGATION`。没有变体、重跑或委派。

## 交付的产品候选

正常导入路径为 `annotation.contracts.a03_native`、`annotation.quality.synthetic_precheck`、`annotation.runtime.storage.native`、`annotation.runtime.storage.native_target` 和原 planner/targetcheck/mock/reconciler 入口；实际子进程从本工作树的 `src/annotation` 导入。产品没有依赖 examples/docs/Git 或 AST/exec 加载候选。examples 下的准备脚本只用于本轮源码/输入生成和证据编排。

| 范围 | 候选实现与验证限度 |
|---|---|
| 新合同 | `1.4.0-a03-native-proposal` / `a03-exchange-4-proposal` / `a03-native-synthetic-1-PROPOSAL`，独立 package-data；R7 产品/数据及旧 schema/profile/API 原字节不变 |
| 显式桥接 | [19 个实际签名](../evidence/A03/execution/P2-R8-native-bridge/contract-signatures.json) 均含 keyword-only `bridge_context`；旧默认分支保留；不是 19 项功能验收 |
| 闭包与业务检查 | 新命名空间派生 R7 的 exact refs、正式 EvidenceRecord、typed frame 和 mixed DAG 检查；另保留 1.1 的来源、intent、resolution、fact/progress 及私有 C01 业务规则；只证明本次走到的前缀 |
| 五检查 | 固定 32×32 P2 PGM 全像素、结构、答案关系、覆盖分母、policy；Source/Evidence/Graph/Policy 明确唯一，无同 kind 最后覆盖；未执行五个 N3 负控 |
| PRE 私有接纳 | quality 产物计算与 runtime durable row/当前性/私有 proof 分离；quality 不写 SQL、不发 permit；**实际尚未接纳成功** |
| 当前资格 | 沿用真实登记、owner/generation/fence、全书 pending/hold、intent 和单次 permit 路径；后段未执行，不宣称已验证不可绕过 |
| creation anchor | 已写完整创建输入 canonical bytes、原始 Resource 清单及同算法重算候选；N6 未运行 |
| 两库格式 | 新 application/user version、profile/adoption/completion 元数据及独立入口；实际创建/观察前缀已发生，严格 reopen、旧库拒绝和中断控制的 N7 未执行；迁移仍 `NOT_IMPLEMENTED_BLOCKED` |
| hold、晚到 receipt、独立报告 | 已提交候选桥接代码和固定测试入口，全部未到达；不声明这些路径闭合 |

R8 fixture 新生成 PGM、完整独立页/题枚举证明和新的 Source/Evidence/Graph/Snapshot 身份；没有把旧 PRE stub 或旧 fixture plan 改名作为新运行或新计划。历史 oracle 的 CANDIDATE/false 原件保留；新采用只限固定合成比较语言，不能代表 B、OCR 或真实内容质量。

## exact pins

[profile](../../src/annotation/contracts/a03_native/data/profile.json) SHA256 `29e9d78190dd702fb944d99d74bd9c40426618b477ed16088422b9b89c45219b`；[adoption](../../src/annotation/contracts/a03_native/data/adoption.json) SHA256 `f0e793d635b5072b7955259f15cc7b389e99c02adbbae4bb98e21a966b1eb6b7`。profile 列出全部六份 schema 和产品源码 pins，包括共享桥接、producer 与 runtime 实现。

- API：`20a65c9fd62de9b04a8e8a9661b4884d662361e87d91a6c29b83c45065bdeb15`。
- R4 接口表：`b57d0af5d72a03c4b16e6eeedc267bda50f1dfcf022728b1f107f5b158a22207`。
- 采用 oracle：`659a715bd293026e28ec50f6bccbe1cecdf6511d168afc9f98d9ab05f6e8efb9`。
- 历史纯比较 verifier：`6667659ccc71cf1c0769d2ca7c684021140046a71a2ca73e40699aa354afac2d`，没有执行/导入该历史模块。
- 新 producer：`ffdfc0f73d969c19b489aa9342dae6b73aa3f8d80df5382dba57ee07a25606b0`。
- 实际计算、未接纳 run resource：`6845ce79b980ff45dd5d03fb1cf8d0625d03bc3e527aa728ca6c868577452d58`。

源码 pins 绑定本轮实际文件字节，随运行保存的快照用于核对；未做 wheel/外目录安装验收，也没有承诺任意 CRLF checkout 可自动采用。新 profile 中的 CURRENT 只描述候选角色，不是本任务或跨侧合同已被接受的标记。

## 已执行命令与证据

以下为本轮实际 argv，cwd 均为上述 worktree；runner 拒绝覆盖已有 run id。列出用于核对与复现，不在本轮继续运行。

```powershell
python -B examples/a03/P2-R8-native-bridge/audit.py run C01 python -B examples/a03/P2-R8-native-bridge/compat.py C01 test_contracts*.py
python -X utf8 -B examples/a03/P2-R8-native-bridge/audit.py run A02 python -X utf8 -B examples/a03/P2-R8-native-bridge/compat.py A02 test_a02*.py
python -X utf8 -B examples/a03/P2-R8-native-bridge/audit.py run R7 python -X utf8 -B examples/a03/P2-R8-native-bridge/compat.py R7 test_a03_r7_readonly_codec.py
python -X utf8 -B examples/a03/P2-R8-native-bridge/audit.py run N1-initial python -X utf8 -B tests/test_a03_r8_native_bridge.py R8NativeBridgeTests.test_N1 -v
$env:A03_R8_RUN_ID='bounded-02'
python -X utf8 -B examples/a03/P2-R8-native-bridge/audit.py run N1-local-fix python -X utf8 -B tests/test_a03_r8_native_bridge.py R8NativeBridgeTests.test_N1 -v
```

每次测试及实际子进程的 preregistration、argv/cwd、脚本/输入及产品源码摘要、raw stdout/stderr、PID、退出/timeout/alive 状态均在证据目录；失败前产品与脚本快照也已保存。[进程释放记录](../evidence/A03/execution/P2-R8-native-bridge/process-release.json) 记录 28 个自有进程均已结束；没有为解锁或补证据重新调用产品。Git 证据清单覆盖本轮新增/修改源码、输入、报告、日志及两个失败运行目录，排除清单自身。旧 28,750 个 tree entries 中，除明确允许修改的 12 个共享路径外，28,738 个原条目的 mode/type/blob 保持一致。

没有网络、浏览器、真实平台、凭据/profile、OCR、模型、付费 API、A05 题22重放、书级提交、push、B/验收者消息或调度 state 修改。I01、真实平台恢复和完整 A03 接受边界继续关闭。
