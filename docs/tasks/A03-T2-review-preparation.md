# A03-T2 独立验收准备

2026-10-18。状态：`PREPARATION_ONLY_WAITING_FOR_FIXED_TARGET_AND_ACCEPTED_T1`。本轮仅阅读约定及任务边界；未执行产品静态审查、导入、C、H1、SQL或业务调用，不产生功能验收结论。A03整体仍REWORK，I01未释放。

| 固定输入 | 确切版本 |
| --- | --- |
| 冻结workflow | `f7084b2e8f2e9a1fcf758f9cba56ec9c9fb1f304` |
| 共同产品基线 | `1330047dd29890dea0e433ff01b991f615bf78f4`；尚未独立接受其归属修复 |
| 原执行最终交接 | `6b61ac9d623e76cbe6311f64d012fd04e2e03c21`；作为历史引用，不是本任务target |
| T2完整target / T1已接受工具提交 | 均未提供；等待调度固定 |

已读主目录AGENTS、[架构](../architecture.md)、[公共合同](../contracts-v1.md)、[A侧调度](../coordination.md)、[开发计划](../development-plan.md)；任务规则读取上述workflow中的[拆分约定](A03-redispatch-2026-10-18.md)、[T2任务](A03-T2-history-and-report.md)、[R12-R2语义要求](A03-P2-R12-R2-issue-ownership-repair.md)及[原验收交接](A03-original-reviewer-handoff-2026-10-18.md)。这些任务链接仅作导航，版本以上述workflow为准。新拆分优先于旧“原对话续派”；不联系旧对话、B或委派子代理。

## 四文件责任边界

以下是任务单规定的待验边界，不是对当前实现的审查结果。T2执行者为唯一新产品写入者；本验收者不修改产品。

| 文件 | 后续固定target的审查重点 |
| --- | --- |
| `src/annotation/runtime/storage/__init__.py` | 共享纯派生归属规则形成receipt/issue绑定；fact→receipt→progress顺序；保留native报告策略及legacy默认行为。 |
| `src/annotation/contracts/recovery.py` | 从每份receipt自己的真实不可变fact验证历史归属，派生完整Issue及稳定ID；私有native→C01证明绑定确切receipt。 |
| `src/annotation/contracts/a03_native/__init__.py` | native闭包中的归属证明、验证顺序及历史consumer闭合，不能用late fact或新receipt替换旧fact引用。 |
| `src/annotation/contracts/validation.py` | 必要的内部C01语义消费；公开`validate_bundle`继续拒绝悬空引用，私有桥不能接受任意ID白名单或伪造CheckReport。 |

对应四项implementation pins及adoption的`profile_sha256`仅随实际改动同步；其他产品、schema、发布器和根依赖只读。无产品改动时沿用1330047d，最终采用情况等待交付确认。

## 正式验收启动与上限

调度须先提供固定完整target（候选代码及最终证据提交）、T1已接受工具的确切提交和允许集成范围、执行报告/实际diff及pins、适用原件清单与进程释放证明。收到后才在`D:/1800/.local/A03-T2-independent-review`建立全新隔离副本，审查四文件改动及所有受影响历史consumer；不读取浮动执行工作树、不复制T1浮动文件、不另造取证器、不轮询作者。

- C最多12个纯合同具名用例、一次批次、最多60秒；运行前冻结输入、数量与目标错误层，继承R12-R2的合法归属及ID/身份/引用/Resource反例、私有权限与公开C01拒绝控制。不创建业务库或消耗报告观察。
- H1仅一次：全新单题两片段、一次dispatch，以applied效果及unavailable执行观察形成真实UNKNOWN receipt；正常释放后新进程一次`max_attempts=1`完整reconcile得到MATCH/RESOLVED_APPLIED，原UNKNOWN fact/receipt/issue仍可验证。一次显式现有`publish_native_quality`独立新鲜读回，正式POST/Batch绑定原receipt/intent及当前resolution，`native_report_reads`恰为1，CONTENT_PENDING/HOLD及NOT_SUBMITTED保持；不追加dispatch、重发或第二次报告读取。
- H1业务子进程45秒、父watchdog90秒，观察2秒、屏障5秒、lease10秒；保存建立前、UNKNOWN建立/释放后、reconcile前后、正式报告前后的适用双库原字节、正式产物、命令/导入、退出和释放。逐库捕获须说明业务/keeper写入静止边界，不称跨库原子快照；SQL仅操作自有immutable副本，不能用最终库重建中间阶段。
- 不重跑T1六场景或全套测试；四文件影响它们时交影响清单，由调度安排。首次非预期失败保留现场并停止后继；只有明确属于本任务新增驱动错误时，按拆分约定允许一次有界纠正及失败项/未运行后继重跑，保留首错；产品错误交最小反例，不改预期。第二次失败停止交付。

## 历史、输出与停止点

按冻结交接事实保留：原C/L1/U1仅作者检查；U2在UNKNOWN建立后采集失败，恢复及U3–U5/H1未运行；不补造U2失败阶段、瞬时journal或R11作者F2/F3历史缺件，不重启原库。旧证据按确切提交引用，不复制历史全集；raw Git字节和checkout字节分开记录。

本轮仅新增此专属文件，由调度保存；不操作主目录Git索引/提交、coordination-state.json、公共任务单或执行者worktree。后续必要报告/证据仅写`docs/tasks/A03-T2-review-report.md`及`docs/evidence/A03/T2/review/`，自有隔离副本与运行输出仅用上述`.local`目录。每条Git及Git子进程显式`-c core.longpaths=true`，Python使用`-X utf8`。

全部离线；无网络、平台、浏览器/profile/凭据、安装、付费模型、OCR、推送、书级提交或A05题22操作。field reset维持`NOT_EXECUTED_NO_RERUN_VARIANT_OR_DELEGATION`。后续即便有限ACCEPTED，也仅关闭本轮归属/历史报告链，不替代T3、I01、平台或B共同确认。本轮无新功能进程/会话待释放；准备完成后结束等待，不重复静态审查。
