# PREFIX-01 独立静态子审

日期：2026-10-17。确切最终提交 `940a5de33a24b1a3a9ded6e69ade1dd0609ed83a`，设计提交 `a250a76dc0b3f13b9dee3bcd2c3d7414032b9768`。本子审未发现 PREFIX-01 仍需返工的缺口；这只是 P1 事件前缀范围的静态意见，总结论由主验收报告给出。

输入为主验收从确切 Git 选择性导出的 `D:/1800/.local/stages/A03-review-P1-R2/940a5de33a24b1a3a9ded6e69ade1dd0609ed83a/`。独立脚本没有导入作者 checker、生成器或业务实现，没有读取 expected_code/expected_static 作为判断。阅读 R2 proposal、API、README、prefix_rules 和既有严格前提后，另写事件内容核对和 canonical JSON/hash 复算。映射表仅选取15项受影响集合，其结果由实际字节决定。

实际静态结果：

- 主例 `partial-with-complete-absent` 的1..13序号、全事件 canonical hash、逐项前驱、最后头、完整接受动作摘要及预留相符。A/B各有唯一 intent→许可发放→消费→DISPATCH_STARTED→结果；intent正文的序号、前驱、目标/owner/generation及义务公式、fact正文与事件结果一致。C basis在13头，C fact14前驱恰为13头，C无intent/义务/resolution/许可/派发。receipt/progress的A/B/C结果为APPLIED/UNKNOWN/NOT_APPLIED；ledger中的B义务与暂停保留。
- 主例未独立存储 C event14 Resource。使用其已存C fact、第二读时间及公共事件信封独立重构C14后，事件hash恰等于ledger/progress14头，结果存入 `independently_derived_C14_event`。这是下游序列内部一致性核对，不是实际提交证据，C准入prefix保持1..13。
- `original-unknown-preserved`、`recovered-report-binding` 的A UNKNOWN前缀1..8、B只读事实9、C前缀1..9及事实10均相符。独立后缀10/11确实从9头延续，11的既有reconciliation精确绑定原A intent/义务/原receipt/resolution与观察，终局头11及暂停投影一致；原receipt/fact仍UNKNOWN。前者本来没有ExecutionProgress，未臆造其存在。
- 15项受影响案例中的真实basis前缀均另行走读通过。此项仅确认它们共用的正确背景图，不把旧generation、重复事实、错动作等请求扰动当作准入成功。
- 作者3邻例的实际candidate_prefix均被独立语义核对拒绝，未读取其expected标签。另从主例自行删除首个PLAN_ACCEPTED、DISPATCH_STARTED、DISPATCH_PERMIT_CONSUMED，重排序号、重算全部hash并加complete=true；3项仍分别因必经事件/阶段缺失拒绝，且均无HASH_BROKEN，排除了只靠旧断链拒绝的解释。最小静态输入见 `independent-mutants.json`。

实际复现：

```powershell
python -B D:/1800/docs/evidence/A03/review/P1-R2/prefix-agent/run_audit.py
```

cwd为`D:/1800`，退出0。精确解释器/argv/cwd/脚本摘要/标准输出/标准错误见 `command-run.json`；结果及38份实际读取JSON的字节SHA256见 `independent-results.json`。本子审的预备命令/审查脚本失败如实保留在 `preliminary-failures.json`；可选Progress假定与文件名猜测已纠正，没有改候选原件。统一归档由主验收负责。

限制：没有完整JSON Schema标准认证；普通引用/跨版本/混合环由同轮专门独立审计负责，本脚本不替代它。SQLite、实际当前库跨scope扫描、原子接受/预留、观察真实性/新鲜度、权限/锁/并发、崩溃恢复、实际准入拒绝和平台效果均 `NOT_EXECUTED`。P2/I01未释放；S01/D01/B确认边界保持。

本子审零网络、浏览器、平台、凭据/profile、OCR和业务模型API，未实现或调用恢复功能，未对其他任务/执行者/B发消息。只写本`prefix-agent/`目录，未改旧证据、代码、公共合同、依赖或调度状态。全部exec命令同步完成；唯一自行启动的子进程是run_audit内同步Python，returncode=0，未创建后台子进程或持久session，遗留自有进程/会话为0。此声明不冒称操作系统全进程扫描。
