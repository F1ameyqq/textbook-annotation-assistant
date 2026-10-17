# A03 P1-R1 执行报告

日期：2026-10-17（Asia/Shanghai）。状态：**P1 REVIEW**。本轮为有界设计修订交付，待原独立验收复审。未标设计通过/功能 ACCEPTED/INTEGRATED，P2 未开始，I01 未释放。

## 1. 基线、授权与提交

| 项 | 确切值 |
|---|---|
| R1 基线 | `2d5ae2a53945a7fa20ef60a6b61e7b31c91dbea9` |
| 原 P1 设计 | `6ac0256f05169570605fcb921a773ff2ae0f4aef` |
| workflow | `a354f95f1d0b40a8f0847b57fa3978cac999e7a2` |
| A02 代码基线 | `ec1b4defbfa3ec0f181d291106fb53313983e493` |
| 工作树 | `C:/Users/ASUS/.codex/worktrees/a03-runtime-recovery/1800` |
| 分支 | `codex/a03-runtime-recovery` |
| R1 设计提交 | `095ed4aa18a56100ce3aabc4a0d6885ad37ab520` |
| 实现提交 | 无，P1-R1 不授权实现 |
| 最终交付提交 | 包含本报告和完整清单的最终提交，其完整 SHA 在最终回复返回；冻结后 `git rev-parse HEAD` 可定位。避免让报告/清单自引用其所属提交摘要 |

本轮恢复上次 usage limit 前的断点：当时仅有未完成 `build_r1_examples.py` 和五份权威输入副本，没有新设计/报告/冻结提交。已保留原脚本副本及其 SHA，从现有内容继续；没有绕过用量/费用限制。所有命令/写入均在指定工作树执行，不合并浮动主分支，不在 D:/1800 写文件。

本地权威副本：[R1任务](../evidence/A03/execution/P1-R1/inputs/A03-P1-rework-R1.md)、[独立 REWORK](../evidence/A03/execution/P1-R1/inputs/A03-P1-review-report.md)，实际 SHA256 分别核对为 `5e868e4b84fc1c138ff96806a4ae205522c465b09d238999d43070f5ee610dab`、`df3faccf4be93335517a3f319fc356f3d568db44202e56a6a35e5153f54f2b8b`。

## 2. 两项有界修订

详见 [R1提案](../a03-recovery-contract-v1-r1-proposal.md)、[新样例说明](../../examples/a03/P1-R1/README.md) 和 [新 API](../../examples/a03/P1-R1/api-proposal.json)。所有 Schema/API/状态都是候选未实施设计。

| 问题 | 修订内容 | 仍未实测 |
|---|---|---|
| A03-P1-API-01 | 新增 `commit_unattempted_absence`：只接受当前受控库的 INTERRUPTED、完整未调用前缀且无 intent/obligation 的动作；当前 owner/generation 和同书闸内两次真实新观察，专用只读 prepared/独立 ABSENT；先文件后索引和事件头 CAS，提交 UNATTEMPTED_ABSENCE_COMMITTED。新增 fact origin/basis，重复/冲突明确拒绝 | 未提交任何本地事实、未读取目标、未运行拒绝/暂停/聚合行为 |
| A03-P1-REF-01 | 每个消费者递归展开 Resource 及正式 evidence_refs 的资源；普通引用必须精确、同书/scope且由本消费者声明。重算新资源/产物/下游摘要；检查消费者缓存、资源和混合环，新增邻近反例 | 未运行新 contracts 或恢复资格门；静态结果只证明候选声明/字节一致性 |

C 不补造 intent/obligation/resolution、不续发旧 tail、不解除 B UNKNOWN 或其他未决；完整回执可聚合 A/B/C 的真实类别，含 B UNKNOWN 时保留 NEEDS_RECONCILIATION、PENDING、NOT_SUBMITTED。缺充分 ABSENT 仅输出完整动作 progress。迁移身份只澄清 namespace+book/scope/id/revision 的含义，与新映射一致，未记为第三项功能缺陷。

顶层候选字符串仍为 `1.1.0-a-recovery-proposal / a03-exchange-1`；本 R1 由确切提交、proposal profile 和新 Schema SHA 固定，不混用旧候选或自动推断最新版。S01/根 Pillow 依赖/B 确认保持未解决。

## 3. 新集合、修前证据与实际静态结果

原 42 案例覆盖在新 `data/case-mapping.json` 一一保留；R1 新增案例单列，合计 **69** 个。新集合独立携带 Schema、归档、assets、API 和检查器；原 P1 提案/样例/脚本/报告/证据没有覆盖。

[修前固定副本清单](../evidence/A03/execution/P1-R1/before/before-manifest.json) 保存 36 个原字节文件，包含 normal、partial-with-complete-absent 和递归所需资源及原 API/Schema；独立最小问题输入也保存在 inputs。修前独立资源审计实际退出 **1**，在这两个固定输入检出 **30** 条漏声明。出现次数不是功能失败数。

| 实际静态命令 | 结果/输出 |
|---|---|
| `python -B examples/a03/P1-R1/check_design.py --root examples/a03/P1-R1/data` | 退出 0；69/69 静态预期相符，旧归档结构/资源/字节摘要匹配；所有语义 actual=NOT_EXECUTED；[作者静态输出](../evidence/A03/execution/P1-R1/static-check.json) |
| `python -B docs/evidence/A03/execution/P1-R1/check_r1_design.py` | 退出 0；4组保留、42个旧案例逐SHA映射、165个正式候选JSON语法及Schema/API/basis字段一致；errors=[]；[API/映射输出](../evidence/A03/execution/P1-R1/design-check.json) |
| 独立 `audit_resource_closure.py`，修前固定 normal/partial | 退出1，30条漏声明；[修前输出](../evidence/A03/execution/P1-R1/before-resource-audit.json) |
| 独立 `audit_resource_closure.py`，修后代表正例与新入口正例 | 退出 0；8个代表正例的逐消费者递归资源审计 violation_count=0；未运行业务或作者checker；[修后输出](../evidence/A03/execution/P1-R1/after-resource-audit.json) |
| `package_r1.py audit` | 退出 0；8,142个原文件零差异，允许新增路径通过，21个本地链接有效，R1范围ignored项为空；[原件/范围核对](../evidence/A03/execution/P1-R1/preservation-audit.json) |
| `package_r1.py verify` | 完整 SHA256 清单最终只读核对；实际退出和清单自身摘要在最终回复返回 |

复现 cwd 为第 1 节工作树；具体 argv、输入根、退出码和制作失败由 [命令记录](../evidence/A03/execution/P1-R1/command-results.json) 及新目录 attempts 留存。制作错误不算恢复失败或通过；未删除失败现场。使用 Python 3.9.13、标准库静态工具和 `-B`；未安装依赖，无 `jsonschema` 完整标准实现，局部结构评估不等于标准认证。未导入/调用业务恢复代码。

```powershell
python -B examples/a03/P1-R1/check_design.py --root examples/a03/P1-R1/data
python -B docs/evidence/A03/execution/P1-R1/check_r1_design.py
python -B docs/evidence/A03/execution/P1-R1/package_r1.py verify
git diff --check
git status --porcelain=v1
```

候选生成器只制作新设计数据，最终冻结后不要在交付目录重建。原 42 个恶意/语义输入仍明确区分预期结构/引用拒绝与未来行为；所有恢复/API/事务/资格结果为 EXPECTED_NOT_EXECUTED。没有运行无改动的 C01/A02 功能套件、P2 V01–V10、崩溃或并发试验。

## 4. 原件、清单与限制

本轮以 exact R1 baseline 记录 **8,142** 个原文件字节数/SHA256；最终核对原文件零修改/删除，四个授权新路径之外无新增。范围仅 `docs/a03-recovery-contract-v1-r1-proposal.md`、`examples/a03/P1-R1/`、`docs/evidence/A03/execution/P1-R1/`、本报告。旧 P1 的 148 条统一清单也已只读复核，摘要仍为 `4988c1ce490ef62d0c1a019ac8f746166eb4dc0b595c3b29036bde38a6315950`。

[R1统一清单](../evidence/A03/execution/P1-R1/sha256-manifest.json) 覆盖新提案、完整样例/资源/Schema/API、原脚本断点、失败现场/日志、输入副本、脚本、实际输出及本报告；仅清单自身排除。实际 ignored 项在 preservation-audit 说明，旧 import cache 未修改/删除。新候选目录以局部 `.gitattributes` 保全字节，不改根设置。

P1-R1 静态自报不替代独立复审或主调度批准；新入口及闭包语义的运行行为全部未实施/未执行。S01 真实完整性、根 Pillow 依赖、B 合同确认、真实平台恢复、真实内容/质量/成本和 I01 仍未完成。未推送、未集成、未改调度状态、不释放依赖。

业务模型 API/费用、浏览器、网络、平台、凭据/profile、OCR 操作均为 0。只运行有限前台 Git/PowerShell/Python 静态工具，没有启动后台服务或平台会话；本轮自有待释放进程/会话 **0**。冻结干净工作树后停止在 **P1 REVIEW**。
