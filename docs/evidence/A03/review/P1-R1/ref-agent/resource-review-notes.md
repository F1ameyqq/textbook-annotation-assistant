# A03 P1-R1 独立资源闭包子审

审查对象严格限定最终提交 `ca4fba4f505467228a8164c3999e0cecc54ffc4e` 的指定 Git 导出；设计提交为 `095ed4aa18a56100ce3aabc4a0d6885ad37ab520`。本子审没有读取执行工作树浮动输出。导出完整性与正式 P1-R1 结论由主验收者负责。

结论：**在本子审的 REF-01 静态闭包范围内，未发现新的阻断项。** 这不是整个 P1 的验收结论，不表示 API、事务、事件前缀、恢复行为或 P2 已通过。

## 独立检查结果

- 直接读取新提案、README、候选 checker 与实际 JSON/资源字节后，另写标准库审计器。自己的遍历与判定不导入作者 checker；最后单独导入其 `audit_closure`，只对独立构造输入做差分对照。
- 扫描全部 **69** 案例的每个消费者、各自 `input_refs`、任意深度 JSON Resource、正式 evidence ID 对应 Resource、路径、资源字节 SHA256、普通精确四元引用、同书同 scope/候选 schema namespace 与 Artifact/Resource 依赖环。作者 `expected_static=PASS` 的 **47** 案均未发现本范围错误。其余含结构/字段层失败，不能用闭包扫描替代该层检查。
- 原 **42** 案映射为双射；逐项核对旧路径、旧文件 SHA256、新路径、新文件 SHA256、case ID、来源 ID、预期语义层、预期语义码和 `EXPECTED_NOT_EXECUTED`，全部一致。这证明映射与静态声明保全，不证明相应未来语义已发生。
- 正常例 receipt 找到/声明普通引用 **8/8**，progress **9/9**；`partial-with-complete-absent` receipt **6/6**、progress **7/7**；`partial-without-absent` progress **5/5**。未通过删除事实或快照来消除原漏声明。
- 独立构造 **9** 个邻近输入，其中 **8** 个负例和 **1** 个正对照；全部独立预期吻合，作者静态差分结果也一致。输入及新增资源均保存在本目录 `counterexamples/`，未修改原件。

|独立输入|独立结果|作者静态差分|
|---|---|---|
|只从 receipt 自身声明删去第二个结果快照|UNDECLARED_RESOURCE_REFERENCE|REFERENCE_FAIL，同原因|
|只从 progress 自身声明删去第二个结果快照|UNDECLARED_RESOURCE_REFERENCE|REFERENCE_FAIL，同原因|
|正式 before_evidence_refs → 四层通用 JSON Resource → 未声明快照|UNDECLARED_RESOURCE_REFERENCE|REFERENCE_FAIL，同原因|
|同一四层资源，补当前 receipt 自身声明|PASS|PASS|
|资源内部普通引用摘要错误|REFERENCE_HASH_OR_IDENTITY_MISMATCH|REFERENCE_HASH_MISMATCH|
|资源字节摘要错误|RESOURCE_HASH_MISMATCH|RESOURCE_HASH_MISMATCH|
|资源内部普通引用跨书|REFERENCE_SCOPE_MISMATCH|REFERENCE_SCOPE_MISMATCH book|
|资源内部普通引用跨 scope|REFERENCE_SCOPE_MISMATCH|REFERENCE_SCOPE_MISMATCH scope|
|receipt → evidence Resource → receipt 身份混合自环|REFERENCE_CYCLE，另报不可一致摘要|REFERENCE_CYCLE|

作者已有 `shared-resource-second-consumer-missing`、`nested-prepared-missing-declaration`、`evidence-id-resource-missing-declaration` 也被独立审计识别为各消费者自己的漏声明。独立正对照证明递归规则不限于 action-fact/prepared 的特定字段。

## 边界与复现

独立审计器并非完整 JSON Schema 验证器；不检查全部 action-fact/basis 语义，也不替代主验收者的 API/事件前缀检查。未被任何消费者正式引用的 bundle evidence 诊断项由主验收者另核。资源环的有效 SHA256 固定点没有构造；作者 `nested-resource-cycle` 实际在资源摘要门拒绝，本子审没有把它写成已走到资源环分支。混合环按产物身份图识别，故不会被不可形成一致摘要的循环掩盖。

复现命令（当前目录 `D:/1800`）：

```powershell
python -B D:/1800/docs/evidence/A03/review/P1-R1/ref-agent/independent_resource_audit.py --frozen-root D:/1800/.local/stages/A03-review-P1-R1/ca4fba4f505467228a8164c3999e0cecc54ffc4e
```

正式执行记录为 `run-02.command.json`、`run-02.stdout.log`、`run-02.stderr.log`，Python 退出码 **0**。`run-01.*` 保留首轮输出，首轮命令链末尾是日志读取，独立 Python 退出码未在该轮单独固化；不把该轮 shell 退出码替代 Python 退出码。第二轮补入输入 SHA256 并确切捕获退出码，故以第二轮为可复现记录。

详细可机读结果：`resource-audit-results.json`；摘要：`resource-audit-summary.json`。本子审新增的脚本、日志、反例及其复制资源交主验收者统一清单纳入；未自行改正式报告或旧 P1 证据。

全程零网络、浏览器、平台、凭据/profile、OCR、模型 API、数据库和恢复实现调用；未来观察、提交、拒绝、锁和事务均为 **NOT_EXECUTED**。没有创建聊天、没有向执行者或 B 发消息。所有工具命令同步结束，没有启动后台进程；本子审自有活动会话和遗留进程为 **0**。
