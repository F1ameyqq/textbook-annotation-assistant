# Schema/案例独立静态核对

输入只读目录：`D:/1800/.local/stages/A03-review-P1/2d5ae2a53945a7fa20ef60a6b61e7b31c91dbea9/`。最终提交 `2d5ae2a53945a7fa20ef60a6b61e7b31c91dbea9`，设计提交 `6ac0256f05169570605fcb921a773ff2ae0f4aef`。这是子审查证据，正式结论由主验收报告给出。

## 已确认的 P1 不一致

**正例资源引用未由消费产物声明（P1-02/P1-07）**。提案 `docs/a03-recovery-contract-v1-proposal.md:106` 明确要求资源内部普通引用同书同 scope、摘要一致并由消费产物声明；`examples/a03/P1/api-proposal.json:984` 同样规定资源嵌套引用遵守声明规则。

最小现成对照来自 `examples/a03/P1/cases/normal.json:3156` 的 ExecutionReceipt：它的 input_refs 仅为 plan 和三个 intent；引用的 `assets/action-fact-normal-1.json:27` 另含 snapshot-action-result-1 的精确普通引用，该快照未声明。第二、第三 fact 也分别漏 snapshot-action-result-2/3。同案例 ExecutionProgress 的 input_refs（normal.json:3320）也缺这三项。

作者 `check_design.py:265` 至 `273` 检查 fact 内资源摘要和普通引用可解析/精确相等，却不将它们与消费产物 input_refs 比较。只运行该静态读取/比较函数，normal 的现有输入仍 PASS；独立读取同一输入得到 UNDECLARED_INPUT。此项针对冻结设计与正例的闭合，不声称运行过恢复功能。

独立静态递归展开资源引用后，受影响正例共五个：normal、partial-without-absent、partial-with-complete-absent、original-unknown-preserved、recovered-report-binding。精确 consumer/resource/missing_ref 对照见 audit-summary.json；minimal-normal-resource-ref.json 保存最小引用片段和完整第一条 fact。原件未更改。

## 需澄清项

API `api-proposal.json:702` 要求显式转换生成 new identities/digests；提案第 26 行要求不可变 ID/revision 不允许同身份不同摘要。然而 migration-map.json 的七对映射均保持相同 artifact_id/revision/kind、改变 content_hash。第 28 行/版本矩阵未显式声明 schema 版本是否构成存储身份命名空间。完整对照保存在 audit-summary.json 的 migration_identity_pairs。因为正式任务明确要求新文件/摘要/映射，不能仅凭跨版本复用 ID 推定功能失败；需作者明确身份含义或使样例与 API 表述一致。

## 通过的静态项目及限制

独立 stdlib 局部 Schema 断言评估覆盖全部 42 个 wrapper（包括非空账本）及所有被 receipt/progress 引用的 action-fact：形状结果与作者声明的 STRUCTURE_FAIL/PASS 预期全部相符，所引用 fact 的形状全部接受。该评估独立于作者 SchemaChecker，不声称完整 JSON Schema 标准符合性。

Python39/311/312 均没有 jsonschema；完整标准验证器复核为 NOT_RUN，未安装依赖、未联网。首轮人工摘要脚本曾错误假定 QuestionStatus 有 frame_check_status，产生 KeyError；这是审查脚本字段假设错误，不是交付缺陷，已在 exploration-history.log 保留并通过只读纠正查询完成相关字段核对。最终 audit_static.py 首次归档运行退出 0。

复现（PowerShell，Python stdlib）：

```powershell
& 'C:/Users/ASUS/AppData/Local/Programs/Python/Python39/python.exe' -B 'D:/1800/docs/evidence/A03/review/P1/schema-agent/audit_static.py' --stage 'D:/1800/.local/stages/A03-review-P1/2d5ae2a53945a7fa20ef60a6b61e7b31c91dbea9/' --out 'D:/1800/docs/evidence/A03/review/P1/schema-agent/'
```

脚本只读取冻结目录，在本子证据目录写输出；没有导入业务模块或运行 main/生成器。仅为证明局部 checker 限制，导入已人工检查的冻结 check_design.py，并直接调用其 references/design_action_facts 静态函数。-B 与 sys.dont_write_bytecode 禁止写入冻结目录的 pycache。

业务恢复、目标效果、SQLite intent、重启/竞争、来源资格与解除暂停全部 NOT_RUN。网络、浏览器、平台、凭据/profile、OCR、模型 API、B 任务均零操作。全部有限前台子进程已退出，无自有后台进程或会话。此证据不释放 I01，不表示 B 已确认。
