# A03 P2-R8-R1：修复 PRE coverage 接线并核验实际恢复链

2026-10-17。继续原执行对话 `01a145aa-2fea-7942-97f9-ad260acf4e30`，原工作树 `C:/Users/ASUS/.codex/worktrees/a03-runtime-recovery/1800`，唯一 base 为 `fa6edeb7e9dd0c9502781747e5fce012931d9441`。保留用户的 model/thinking 设置；不委派、不合浮动主树。

依据：[R8 独立报告](A03-P2-R8-native-bridge-review-report.md)，报告 SHA256 `66690c0e259635d770cc44d2265b979e813c7e72494c1cf9b87257ed5c8e5555`。调度已核对完整 373 项审阅清单及文件集合；R8 结论为 REWORK。R7 只读通过范围保留，A03 功能和 I01 尚未接受。

## 唯一已确认产品缺口

`synthetic_precheck.py` 将 `coverage_for(bundle, graph)` 返回的 `(coverage_dict, complete_bool)` 整体交给 PRE 的对象字段 `coverage`。实际第二次 N1 因 `SHAPE_oneOf` 停在 PRE 封签前；plans/intents/permits/effects 均为零。此前私有投影的整数/浮点摘要问题已做局部修改，本轮不得无理由重做。

在 producer 调用处显式解包，PRE 仅接收 coverage 对象，并使 complete 的处理与既有 coverage 比较及 PASS/HOLD 语义一致。保留公共 helper 返回约定和 Schema，不放宽验证、不把五个已计算 PASS 当成 runtime 接纳。

## 允许改动

- 产品仅 `src/annotation/quality/synthetic_precheck.py`，以及新 native profile/adoption 中受本次 producer 变化影响的确切身份 pins；不改其他算法、Schema、旧 API、R7 产品或根依赖。
- 新增本轮测试/夹具/驱动辅助文件，命名带 `a03_r8_r1` 或放在独立 `P2-R8-R1-producer` 目录；旧测试、驱动、报告、证据和原始失败字节不改。
- 新增 `docs/evidence/A03/execution/P2-R8-R1-producer/` 与 `docs/tasks/A03-P2-R8-R1-producer-report.md`。不改根调度 state/AGENTS，不推送。

## 执行顺序与停止条件

1. 先静态核对相关 helper 的真实返回约定及 producer 调用；只修上述确认缺口，更新精确 pins。新增最小检查证明 coverage 对象形状，以及完整/不完整输入对应的既有决策语义；不得合成成功数据库行或跳过真实资源读取。
2. 使用新运行目录、全新合成双库，以原 N1 标准真实运行一次。证据先证明 PRE 封签及 runtime 实际接纳，再证明实际计划、单次 permit、目标效果后崩溃/丢响应、UNKNOWN、只读对账、迟到回执及独立 POST/Batch。目标效果必须恰好一次，保留原 UNKNOWN 和完整 creation anchor。不得沿用失败库或历史成功前缀。
3. 若 N1 成功，执行原任务 N2–N7 各一轮，不改其标准或扩大矩阵；相互独立的离线组可继续，但依赖未满足的组标明 NOT_RUN。若出现新的独立产品阻断，保留最短实际失败和冻结交付，不自行修第二个问题或发明下一轮。
4. 对最终候选执行 C01 `test_contracts*.py`、A02 `test_a02*.py`、R7 `test_a03_r7_readonly_codec.py` 各一轮并记录实际源码身份。不得将上轮修复前结果计作本轮回归。

本任务授权一次具体产品修正；发现新的独立阻断后不重复运行同一失败、不更换大量候选。执行器如遇本轮记录脚本自身错误，保留失败后只修记录脚本，不借此重跑已失败产品路径。任何出界必需改动均交具体路径与理由，等待调度重新划定范围。

原 [R8 任务](A03-P2-R8-native-bridge-implementation.md) 的 N1–N7、真实子进程/屏障、身份、权限和历史保全标准继续有效；原 P2 V01–V10/R01–R18 未被豁免。字段重置专项维持 `NOT_EXECUTED_NO_RERUN_VARIANT_OR_DELEGATION`，不复跑、变形、委派或建议重测。零网络、浏览器、平台、凭据/profile、OCR、付费模型或 A05 题22重放。

## 冻结交付与验收

交 exact commit、实际命令与导入路径、真实产物/效果数、每组到达的边界、首个残余、相关兼容结果及限制。原始父/子进程 argv/cwd、输入/脚本摘要、PID、限时、stdout/stderr、退出/timeout/alive 均保留；所有自有进程 wait/退出后交释放记录。清单覆盖本轮交付且只排除自身，旧证据用 raw Git blob 差分保全，不复制历史全集。

工作树干净后冻结为 REVIEW，由调度核对版本和释放证明，再交原独立验收对话。执行者不得自行记 ACCEPTED/INTEGRATED 或释放 I01。B 原生包只读/HOLD 接收是独立路线，不以本轮通过代替跨侧映射确认。
