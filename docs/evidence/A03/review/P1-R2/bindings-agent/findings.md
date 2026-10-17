# P1-R2 独立下游绑定与消费者闭包审查

结论：本子范围未发现要求返修的静态设计缺陷。最终提交为 `940a5de33a24b1a3a9ded6e69ade1dd0609ed83a`，设计提交为 `a250a76dc0b3f13b9dee3bcd2c3d7414032b9768`，R2 基线为 `ca4fba4f505467228a8164c3999e0cecc54ffc4e`。这不是 A03 功能通过或 P2/I01 放行决定。

所有判断来自确切 Git 导出中的实际 JSON、原提案的规范摘要公式和 R2 的明确序列约定。独立脚本仅使用 Python 标准库，不导入作者检查器或恢复实现，不使用作者 expected 字段判断。89 个实际读取输入逐件用 `git cat-file blob <final>:<path>` 核对导出原字节，详细长度和 SHA256 见 `independent-results-final.json` 的 `exact_git_input_index`。

| 受影响正例 | 单独检查的消费产物 | 各消费者递归资源消费数之和 | 实际绑定 |
|---|---:|---:|---|
| unattempted-absence-commit | 14 | 48 | A fact8、B UNKNOWN fact13；C 前缀13、CAS13、fact14、ledger/progress14 |
| partial-with-complete-absent | 14 | 48 | 同上；B 原 UNKNOWN、义务、pending 和 SAVE_UNKNOWN 暂停保留 |
| original-unknown-preserved | 14 | 37 | A UNKNOWN fact8；B 前缀8/fact9；C 前缀9/fact10；独立后缀10/11，终局仅绑定原 A reconciliation |
| recovered-report-binding | 17 | 58 | 同上；progress A 有效 APPLIED 来自原精确 resolution，原 fact/receipt A 仍 UNKNOWN；批报告 PENDING/NOT_SUBMITTED |

每一消费产物分别递归读取其直接 Resource、嵌套 Resource、正式 evidence_refs 对应 EvidenceRecord 的 Resource，要求其中每一个普通引用出现在该消费者自己的 input_refs。逐件核对四元组、资源原字节摘要、artifact canonical 内容摘要、版本、书/scope 和完整有向依赖图。遍历普通引用时不把另一个 Artifact 的 payload 错并入当前消费者的声明义务。重复资源只在当前消费者内去重，不能借全局缓存跳过声明或 scope 检查。

四例的 intent/ref/action_digest、plan_dependency_digest 和 obligation_id 均独立重算；fact 与原 action、receipt result、basis/CAS、前驱事件头、两次合成观察身份/递增序号/时间、固定 source/scope/store/session 绑定一致。未尝试项保持 intent/obligation/resolution/result.intent_ref 全为 null，没有给 C 补造调用或旧 tail 续发。两终局例仅以既有 `RECONCILIATION_COMMITTED11` 精确解释 A 的解除；其 C10 ABSENT 不解除 A UNKNOWN。静态合成观察无法证明未来运行时新读已发生。

主例并未另存 C14 提交事件的单独 Resource。本审查从 C fact、其前驱13、独立合成 readback 时间及已文档化 UNATTEMPTED 事件编码重建 C14 的序列化，得到 `7ce6ce7a124473cc2975f2368301dac1cb2889f88adaa3ba9ac6f437c6e37012`，与 ledger/progress14 精确一致。重建完整对象保存在最终结果，明确标注为静态重建，不能称为已提交事件或运行证据。两终局例实际序列化的后缀 head11 为 `f169e7d3cf477e4b07e9921a6bd15481cd90ba5976fdf0c8611394a6f2d1f328`，其前驱9、C10、A11 的原始链及 resolution/receipt 绑定均一致。

另独立检查两个闭包正控和十二个既有拒绝邻例。两个正控闭包无错；实际观察到的拒绝诊断为：缺直接/证据间接声明→UNDECLARED_RESOURCE_REFERENCE，跨书/scope→REFERENCE_SCOPE_MISMATCH，错普通摘要→REFERENCE_EXACT_TUPLE_MISMATCH，错资源字节→RESOURCE_HASH_MISMATCH，资源/混合环→DEPENDENCY_CYCLE（并可能同时具有摘要错误），不便携路径→RESOURCE_PATH_OR_MISSING，三类 OBSERVED 来源→SYNTHETIC_ONLY。循环例由于摘要也可能不闭合，结果只表示静态拒绝及图循环诊断，不宣称未来 runtime 最先返回的具体错误码。完整诊断含定位和被引用对象，保存在最终结果。

R2 四组 API 的全部 group 内容与确切 R1 Git 原件相同。`refusal_boundaries`、`initial_dispatch_authority`、`normal_action_result_protocol`、`unattempted_absence_protocol`、`resource_reference_closure_protocol`、`runtime_authority_protocol`、`two_stage_gate` 也逐值相同。候选 R2 profile 的七份 Schema 实际字节 SHA256 全部吻合。相同顶层版本字符串没有被当作混用许可；当前审查仍固定最终/设计 Git、R2 profile 与七份 Schema 摘要。

复现命令（PowerShell，cwd 为 `D:/1800`）：

```powershell
python -B D:/1800/docs/evidence/A03/review/P1-R2/bindings-agent/independent_bindings.py --source D:/1800/.local/stages/A03-review-P1-R2/940a5de33a24b1a3a9ded6e69ade1dd0609ed83a --git-root D:/1800 --output D:/1800/docs/evidence/A03/review/P1-R2/bindings-agent/new-independent-results.json
```

实际执行记录为 `run-02.command.json`、`run-02.stdout.log`、`run-02.stderr.log`，有限子进程退出码为 0。复现应选择新的输出文件，保留本轮冻结证据。首轮工具脚本及输出完整保存在 `independent_bindings-v1.py`、`independent-results.json` 和 `run-01.*`；首轮未抛异常、退出码0，但两个负例文件名选择错误，且把历史邻例 ledger 当作当前投影检查。最终脚本改用实际文件名，将当前 ledger 绑定检查限定为四个受影响正例，并在摘要已拒绝的普通引用上保留身份图边，补充混合环诊断。两轮均没有对正式候选作任何修改；差异是验收工具的范围和诊断修正。

首次预读曾对未存在的主目录 `D:/1800/docs/a03-recovery-contract-v1-r2-proposal.md` 调用 Get-Content，返回 Cannot find path；随后始终使用确切隔离 Git 导出中的该提案，没有从缺失路径取得任何内容，也没有以浮动作者目录作判断。

限制：这是局部静态审查，不是完整 JSON Schema 标准认证。原69例映射、完整事件状态转换邻例与作者检查器复现由主验收合并审查。本子范围未访问网络、浏览器、平台、凭据/profile、OCR、模型 API 或数据库；运行时恢复/提交/dispatch、新实际观察、超时/并发/崩溃行为、P2/I01 均为 NOT_EXECUTED。所有自有子进程均为同步有限命令且已返回；没有创建后台进程或持续会话，遗留自有进程/会话为0。这不是对他人进程的全系统扫描。
