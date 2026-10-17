# A03 P2-R8-R1：producer 修复与恢复进度失败的独立复核

2026-10-18（Asia/Shanghai）。继续原验收对话 `01a145aa-8d59-7c70-8d81-731712103a9a`，保留用户 model/thinking；不委派，不修改执行工作树，不联系 B 或执行者。精确 target 为 `a0c40886f3076f84c46377e03fc2206d2fdc5585`，base 为 `fa6edeb7e9dd0c9502781747e5fce012931d9441`，产品修复提交 `613952f170167551b6f935d93cc9f007e6aa7221`。

本轮核验已冻结失败和实际到达边界，不开展新一轮运行。调度已核对 raw Git/disk 507 个 manifest 条目及 manifest 自身，29,201 个旧 tree entries 中仅三个允许产品路径改变，23 个登记进程均有对应 preregistered/started/completed 与原输出，工作树干净、执行 turn completed。见[调度交付前检](../evidence/coordinator/heartbeat-20261018-0005/A03-R8-R1-delivery-preflight.json)。这不是功能接受。

## 固定输入

- 执行任务：workflow `b9889efd29baa364bdd0ce9e356a8cde7054f8d9` 的 `docs/tasks/A03-P2-R8-R1-producer-rework.md`，SHA256 `bc0063986d164bd0ca7caeddfb2ed358439fd14e3d9d80961f2f5c85f932ad7b`。
- 本次报告：target 的 `docs/tasks/A03-P2-R8-R1-producer-report.md`，SHA256 `e9b99a31b5958f184ef9bea63f5b26a9765fac767af9ef21918929673c6df199`。
- 本次证据目录：`docs/evidence/A03/execution/P2-R8-R1-producer/`；`manifest.json` SHA256 `5d5bf3de95c8e6bd335e8ec1e014a627f9346837df2ff243ae1c63c719bd60ad`；`process-release.json` SHA256 `c051dbc4c821874f45c0e5a213391fd3f7c42a4e04ebcca12c8c6ae207031a77`。
- `bounded-outcome.json` SHA256 `734525b4a1a46b3a69e3ae930168eb904610f2d590f91c8cc4d2634202684381`；`attempt-field-binding.json` SHA256 `2c325f6044ae76493da4b6521b6fdf6139eb87d920c8779a32300a95bcf00771`。
- 上轮独立报告 [R8 REWORK](A03-P2-R8-native-bridge-review-report.md) 及其原证据保持冻结，仅作已确认缺口和边界的依据，不重复制历史全集。

## 必须回答的有限问题

1. 三个产品改动是否仅显式解包 coverage/complete、保留完整性失败的 HOLD 语义及更新对应 producer/profile/adoption pins；公共 helper、Schema、其他 runtime、R7 和旧失败字节是否保持。核对最小测试确实读取资源、完整/不完整两种决策及真实 PRE 原件，不能只看作者 PASS。
2. 以冻结日志、屏障记录和必要 SQLite 的自有 immutable 只读副本，核对这次实际前缀：PRE ADMITTED、单动作计划、单次 permit、一次目标效果、子进程 exit87、原 receipt 缺失及 UNKNOWN、terminal RESOLVED_APPLIED 与 original_receipt_ref=null。区分这些实际已落库状态和完整恢复链通过。
3. 以冻结 material fact、保存的 action/intent/plan 数据和实际执行源码核对四个比较字段。作者说明只有 attempt_fact 不同：fact 保留 MAY_HAVE_BEEN_ATTEMPTED，actions.state 为 APPLIED，projection 分支推导 ATTEMPTED。失败 progress 没有持久化，不把静态推导值写成已存在的 Artifact，也不重新生成/封签失败 progress。
4. 核对终局 head/fact 已落库、当前 receipt 仍缺失、POST/Batch 未到达及 N2–N7 未运行。明确后续最小产品修复涉及哪一处状态投影，以及应保留的原事实/历史，不放宽一致性合同、不伪造 ATTEMPTED、不继续使用本轮失败库重放效果。
5. 核对最终候选 C01 70、A02 52、R7 13 的原始结果和实际源码身份；预期拒绝子进程 exit1 与 N1 真失败分开。核对 23 个进程退出和日志摘要；没有当前 OS/profile 扫描。

## 执行边界与交付

不重跑 N1、N2–N7、最小测试、native API 或兼容套件，不修产品、不执行作者审计脚本代替独立判断。只读取冻结 Git blob、静态代码/Schema、JSON、日志及必要 SQLite 的自有 `mode=ro&immutable=1` 副本；数据库读取前后核对原摘要，绝不连接执行原库。没有数据库必要性时可采用经原字节绑定的其他直接产物，说明证明边界。

只导出必要新输入；旧 R8/R7 通过 raw Git mode/type/blob 差分保全，不复制历史全集，不扩大矩阵或新建身份/设计提案。字段重置专项维持 `NOT_EXECUTED_NO_RERUN_VARIANT_OR_DELEGATION`。零网络、平台、浏览器、凭据/profile、付费模型、A05 题22重放或提交。

报告新增 `docs/tasks/A03-P2-R8-R1-producer-review-report.md`，证据新增 `docs/evidence/A03/review/P2-R8-R1-producer/`；不得改旧文件和调度 state。记录 exact inputs、实际检查、必要自有进程限时/输出/退出及清单。结论区分 producer 缺口是否关闭、N1 当前真实剩余和整个 A03 状态；完整链未通过即不释放 I01。完成后冻结、释放自有进程，由调度据明确结论制定下一次有界修复。
