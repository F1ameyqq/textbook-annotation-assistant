# A03 P1-R2 静态设计包

状态为 DESIGN_ONLY / P1 REVIEW。正式候选是 `data/`、本目录 API/profile、7 份 Schema 和静态检查脚本。恢复、观察、提交、权限、锁、SQLite、平台效果及未来拒绝全部 **NOT_EXECUTED**。源 Git 固定为 `ca4fba4f505467228a8164c3999e0cecc54ffc4e`；本包的新设计/最终提交由执行证据选择，避免在自身 JSON 内形成 Git 自引用。

从仓库根执行：

```powershell
python -B examples/a03/P1-R2/check_design.py --root examples/a03/P1-R2/data
```

把本目录原样搬运后，从目录内执行 `python -B check_design.py --root data` 即可；不需要旧仓库、网络或第三方包。检查器只导入本包的标准库静态函数，不导入业务、数据库或恢复实现。局部 Schema 检查不宣称完整 JSON Schema 标准认证。

原 69 例保持语义层、错误码和历史静态分类，另加 3 个邻例，共 72 例。`data/r1-case-mapping.json` 含每例旧/新 SHA256、54 例逐字节保全以及 15 例实际原扰动字段对照。检查器根据当前 JSON 重新抽取扰动与映射核对；不把 `semantic_trigger_retained=true` 当证明。旧 42 例映射仍保留原 P1/R1 摘要，增加独立 R2 摘要列。

15 个相关案例重建完整事件前缀及派生意图、义务、事实、CAS、receipt/progress 和每个消费者自己的递归引用声明。主要成功例 C 的前缀为 seq1 接受与原子预留绑定、seq2 预留索引投影、seq3 开始、A seq4–8 的意图/许可/消费/派发/结果、B seq9–13 同流程后 UNKNOWN。C 无 intent/obligation/resolution，basis 绑定 head13，候选只读事实为 seq14；B 保持未决和暂停，旧计划 INTERRUPTED。

`original-unknown-preserved` 与 `recovered-report-binding` 的 A 原 UNKNOWN fact/receipt 保留，B/C 未尝试事实为 seq9/10。原有 A 终局结果在 seq11 `RECONCILIATION_COMMITTED`，由 `runtime_claim.post_prefix_events` 的独立后缀 Resource 绑定，解释 ledger/progress 最终 head11；不把后缀塞入 C 的 precommit prefix。

新邻例的 `candidate_prefix_role=PRE_ADMISSION_INPUT` 表示 `candidate_uncalled_prefix` 是实际受测输入。正确 basis 图保留作上下文，隔离被删除的接受事件、被删除的 A 派发事件和被改坏的 hash；前两者重新编号、重新计算 hash，第三者保留断链。独立函数从实际字节计算错误，未来运行时是否拒绝仍未执行。旧 `unattempted-incomplete-prefix` 保留历史结构 PASS，并另列实际缺接受的候选前缀结果。

事件 hash 为除自身顶层 `event_hash` 外全部成员的 SHA256：UTF-8、键排序、紧凑 JSON、Unicode 不转义、拒绝非有限数。genesis 为 64 个零；逐事件前驱和序号连贯。静态检查同时核对完整 plan/action 摘要、意图前驱/序号/义务、事件中的事实资源与正文、basis CAS、后缀终局及消费者声明。`complete=true` 不参与准入。

本次内部制作曾遇 Schema `uniqueItems` 检查缺项、prepared 递归资源仍引用旧 A fact，以及缺少终局 event11 的中间版本；其日志与输入保留于 `attempts/`，不能当作正式候选。一次清理组合命令在进程启动前被自动审批拒绝，原文为 `CreateProcess rejected: blocked by policy`。未重试删除；两份中间数据通过原生 PowerShell 保全移动到该目录，详见 `attempts/policy-denial.json`。

仅需复现转换时，给一个本目录内尚不存在的输出路径；转换只读冻结 R1 的 197 个静态输入，不运行旧生成器：

```powershell
python -B examples/a03/P1-R2/build_r2_fixtures.py --output examples/a03/P1-R2/new-reproduction
```

本轮不改变原 API/REF 修订结论、公共合同、源码、测试或依赖。P1 自检不等于独立验收通过；P2、I01、S01、D01、B 确认及真实恢复边界保持。
