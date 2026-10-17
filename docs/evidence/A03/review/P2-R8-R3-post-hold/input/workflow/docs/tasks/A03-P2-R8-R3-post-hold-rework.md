# A03 P2-R8-R3：POST_HOLD 只读预检入口与接纳衔接

2026-10-18（Asia/Shanghai）。继续原执行对话 `01a145aa-2fea-7942-97f9-ad260acf4e30`，工作树 `C:/Users/ASUS/.codex/worktrees/a03-runtime-recovery/1800`，唯一 base `58d8a64734271d15654bb00b03d760f0f3eccd10`。保留用户当前 model/thinking，不委派、不合浮动主树、不改根调度 state、不推送。

依据：[R8-R2 独立报告](A03-P2-R8-R2-projection-review-report.md)，SHA256 `0cd36afd8409ec75ef04be9baf1602dc089d85a0bc5e187b393aece17a519565`；[调度结论](A03-P2-R8-R2-projection-coordinator-decision.md)。该 target 的尝试分类投影及固定合成 N1 完整链已有限 ACCEPTED，不再重做其设计。A03 整体与 I01 未通过。

## 一个已确认的接口缺口

N2 正常受控目录变化产生 hold 后，`begin_native_pre(kind='POST_HOLD')` 在 native.py:318 的普通 `_lease` 调用即报 TARGET_DRIFT_HOLD，无法创建新的 POST_HOLD run。静态检查同一链路还见 `NativeRegistry._current` :76 和 `admit_pre` 提交事务内 :137 同样的 hold 门禁。这两处尚未动态运行失败，但属于本次同一 POST_HOLD 只读 PRE 的启动、当前性和接纳衔接范围，应一次检查解决，不能只修首个调用。

为合法当前 owner/generation 下的 POST_HOLD 只读预检取得并持续校验 exact hold 上下文；它仍是只读核验资格，不直接解除 hold 或授予普通写入。完整保留 ACTIVE lease、当前 PID/instance、owner/generation、pending obligations、exact hold/head、注册/session、观察、源/目标、五检查、预算与时限校验。事务提交前重复校验必要当前性，不能用宽松参数绕掉 pending 或错 hold。

## 允许改动

- 产品只限 `src/annotation/runtime/storage/native.py` 的 `begin_native_pre`、`NativeRegistry._current`、`_dispatch` 中 `admit_pre` 的上述衔接，以及同文件必要的小型私有辅助。明确解释每个改动如何保持普通写入和 INITIAL 禁令。
- 不修改共享 `_lease` 的默认或行为，不清空 SQL hold/资格/头，不改投影修复、producer、合同守卫、Schema、版本语义、根依赖或其他状态机。若该范围确实不能实现，先交具体原因，不擅自扩大。
- 仅更新 `src/annotation/contracts/a03_native/data/profile.json` 和 `adoption.json` 中受确切实现字节影响的 pins。
- 新测试/驱动/夹具用 `a03_r8_r3` 或新 `P2-R8-R3-post-hold` 目录。旧驱动、报告、证据、失败字节不改。
- 新交付 `docs/tasks/A03-P2-R8-R3-post-hold-report.md` 与 `docs/evidence/A03/execution/P2-R8-R3-post-hold/`。保全历史采用 raw Git 差分，不复制历史全集。

## 有界验证及停止条件

1. 先静态检查上述三个 lease 衔接点及事务复查，再做必要的局部检查。覆盖 exact current hold 正常入口，以及 INITIAL、无 hold 的 POST_HOLD、旧 owner/generation、未解决 pending 仍拒绝；使用正常 API 形成状态，不 SQL 伪造资格，不扩大控制矩阵。
2. 最终候选全新目录/双库运行原 N1 一次，作为 N2 所需的真实正常前序，同时验证共享 native 修改没有破坏已接受链。不能复制或继续任何旧成功/失败库。保留 N1 原完整标准、正式 receipt/progress 绑定、实际子进程与屏障、效果一次、UNKNOWN 和 null 原回执、独立 POST/Batch。
3. 在该新场景执行 **N2 POST_HOLD 生命周期一轮**：正常目标漂移生成 hold；旧 INITIAL 被拒绝；新 POST_HOLD 正常真实读取、五项语义比较、正式接纳，所绑定 hold/head/观察正确。依原生命周期验证旧 hold run 与正常推进后的旧证明失效。记录确切拒绝 code 和原始输出，不能只用 `assertRaises(Exception)` 当作语义证明。核验期间不得偷偷清 hold 或产生新目标效果，普通写入禁令须保留到正常资格流程确实允许。
4. N2 通过后继续原 [R8 任务](A03-P2-R8-native-bridge-implementation.md) N3–N7 各一轮：五检查语义不匹配、缺少/他属运行、旧版本/角色、创建输入/UNKNOWN 历史、新双库生命周期。标准不减，不将已经失败的旧库继续当成功前缀。
5. 最终源码的 C01 `test_contracts*.py`、A02 `test_a02*.py`、R7 `test_a03_r7_readonly_codec.py` 各一轮，记录实际导入及产品摘要；不扩张为旧全矩阵。

本轮限这一个已明确的 POST_HOLD 接口修复。出现新的独立产品阻断时保留最短真实失败、准确到达边界，停止依赖组并冻结；不要同轮修第二类问题、反复尝试或扩大候选。正常记录脚本错误可纠正，但首次输出保留，不借此重跑已失败产品路径。未达条目标 NOT_RUN。

原 P2 V01–V10/R01–R18 未被自动替代或豁免；交付列明已覆盖/未覆盖映射供验收核定。字段重置专项始终 `NOT_EXECUTED_NO_RERUN_VARIANT_OR_DELEGATION`，不复跑、不变形、不委派、不建议重测。

## 冻结交付

提交 exact 产品和最终 commit、最小 diff、运行命令/实际导入、pins、新双库及真实 Resource/正式 SQL 登记绑定、每组实际到达点和限制。父/子进程预登记 argv/cwd、脚本/输入摘要、PID、超时上限，保留原 stdout/stderr 与退出/timeout/alive。所有自有进程 wait/退出后给释放证明。

manifest 覆盖本轮改动/新增及原始输出，只排除自身；旧原件不变，工作树干净后冻结 REVIEW。不得自行记 ACCEPTED/INTEGRATED 或释放 I01。零网络、浏览器、平台、凭据/profile、OCR、付费模型、A05 题22重放或书级送交；不联系 B/验收者。B 包只读/HOLD 准备独立，双方映射确认仍保留。
