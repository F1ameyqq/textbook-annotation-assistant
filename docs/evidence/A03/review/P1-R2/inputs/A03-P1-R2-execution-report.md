# A03 P1-R2 执行报告

日期：2026-10-17（Asia/Shanghai）。状态：**P1 REVIEW**，等待原独立验收对话复验及主调度决定。只交付 PREFIX-01 的有界静态设计修订；未记为 ACCEPTED/INTEGRATED，P2 未开始，I01 未释放。

## 1. 固定边界与提交

| 项 | 确切值 |
|---|---|
| R2 基线 | `ca4fba4f505467228a8164c3999e0cecc54ffc4e` |
| R1 设计 | `095ed4aa18a56100ce3aabc4a0d6885ad37ab520` |
| workflow | `a354f95f1d0b40a8f0847b57fa3978cac999e7a2` |
| A02 代码基线 | `ec1b4defbfa3ec0f181d291106fb53313983e493` |
| 工作树 | `C:/Users/ASUS/.codex/worktrees/a03-runtime-recovery/1800` |
| 分支 | `codex/a03-runtime-recovery` |
| R2 设计及样例提交 | `a250a76dc0b3f13b9dee3bcd2c3d7414032b9768` |
| 实现提交 | 无；本轮不授权实现 |
| 最终交付提交 | 包含本报告及统一清单的最终提交，完整 SHA 在最终回复返回；冻结后 `git rev-parse HEAD` 定位，避免自身摘要循环 |

权威输入逐原始字节核对并保留：[R2任务](../evidence/A03/execution/P1-R2/inputs/A03-P1-rework-R2.md)，SHA256 `7415a8e74b92e5ee92a52433343e0e92ed910a779b375f89cdc65c71f594ff1e`；[R1独立复验](../evidence/A03/execution/P1-R2/inputs/A03-P1-R1-review-report.md)，SHA256 `788de983f08c401de4e045ccd990b090aecd868bbe9148a3615446e59539c318`；[主调度静态反例](../evidence/A03/execution/P1-R2/inputs/coordinator-check.json)。原 API-01/REF-01 已有独立确认结论保留，本轮不重新记作功能通过。

## 2. 唯一修订与候选选择

[R2提案](../a03-recovery-contract-v1-r2-proposal.md) 和 [可搬运样例说明](../../examples/a03/P1-R2/README.md) 明确事件编码及 hash：只排除顶层 event_hash，UTF-8、键排序、紧凑 JSON、Unicode 不转义、拒绝非有限数；逐事件重算链和真实内容，不信任 complete=true。

主成功链补齐 PLAN_ACCEPTED、原子动作预留绑定、预留索引、开始、A/B 各自 intent→许可发放→消费→DISPATCH_STARTED→结果，共13事件。A APPLIED、B UNKNOWN，C 的 basis/CAS 头13、只读 fact14；C 无 intent/obligation/resolution，B 义务及整书暂停保留，旧计划 INTERRUPTED、旧 tail 不派发。同步重算 intent/义务、prepared/观察递归资源、fact、receipt/progress、ledger、每个消费者 input_refs 和下游摘要。

另两条保留原终局 reconciliation 的旧例，B/C 未尝试事实为9/10，C 的准入前缀只到9。既有终局 resolution 以独立 RECONCILIATION_COMMITTED 事件11及后缀 Resource 解释 ledger/progress 最终头11；原 A UNKNOWN receipt/fact 保留，解除来自该原有终局语义，不来自只读尾部事实。

原69例逐 SHA/主要扰动对照见 [映射](../../examples/a03/P1-R2/data/r1-case-mapping.json)：54例在新包中逐字节复制，15例只重建相关前缀及派生图。每项原 expected_layer/code/static 保持；主要结构/引用反例仍按原先更早层拒绝，不假定其旧前缀有效。三个新邻例使用独立实际候选前缀，正确 basis 图保留作背景；前两类删除事件后重新编号/重算链，第三类单独断 hash。

候选顶层版本仍为 `1.1.0-a-recovery-proposal / a03-exchange-1`，由本报告确切设计提交、[API/profile](../../examples/a03/P1-R2/api-proposal.json) 的 A03-P1-R2 修订及7份 Schema SHA锁定；source_git_commit 仅绑定冻结R1输入。API SHA256 `e2b0865fc1a25206181f3094155b059a6d34eb851afc750e813f0c2e89960f85`。46个原 API 签名未变，不按相同顶层字符串自动选择“最新”。

## 3. 实际静态验证

五项统一命令的实际 argv、退出码及 stdout/stderr 见 [命令记录](../evidence/A03/execution/P1-R2/final-static/command-results.json)；profile 单独记录于 [profile命令](../evidence/A03/execution/P1-R2/final-static/profile-command.json)。全部恢复/资格/事务/拒绝行为 actual 仍为 **NOT_EXECUTED**。

| 实际检查 | 实际结果 |
|---|---|
| 可搬运 check_design | 退出0；72/72静态预期相符，69映射当前内容/主要扰动匹配，归档字节匹配；[输出](../evidence/A03/execution/P1-R2/final-static/design.stdout.json) |
| 三个新邻例 | 缺接受：PREFIX_ACCEPTANCE_MISSING（另报预留/状态连带错误）；缺派发：PREFIX_DISPATCH_MISSING；断链：PREFIX_HASH_BROKEN，均由实际内容计算，静态层 PREFIX_FAIL |
| 独立 prefix/fact/intent/ledger 绑定审计 | 退出0；4例最终头14/14/11/11，逐事件、原义务/结果、终局/暂停投影及下游绑定无错误；[输出](../evidence/A03/execution/P1-R2/final-static/bindings.stdout.json) |
| 修前回放及 complete 标志邻接检查 | 退出0；保留的两个原前缀实际检出缺接受/断链等错误；三个新邻例在内存附加 complete=true 后仍检出对应错误，未写回资源；[输出](../evidence/A03/execution/P1-R2/final-static/before-regression.stdout.json) |
| 独立69例字节映射审计 | 退出0；直接读取冻结R1和新文件，旧/新SHA与分类一致，54逐字节保留、15派生；[输出](../evidence/A03/execution/P1-R2/final-static/mapping-bytes.stdout.json) |
| 独立递归 Resource/普通引用审计 | 退出0；4例59消费者，逐消费者声明及混合依赖环检查违规0，不导入作者checker；[输出](../evidence/A03/execution/P1-R2/final-static/resource-closure.stdout.json) |
| profile/Schema/API 签名 | 退出0；7个实际Schema字节摘要匹配，46个原签名相同；[输出](../evidence/A03/execution/P1-R2/final-static/profile.stdout.json) |
| Git 空白检查 | 默认检查实际退出2：原样保留的CRLF日志/快照被报尾部CR；单命令保留全部默认空白规则并添加 cr-at-eol 后退出0。未转换证据字节、未改全局设置；[实际输出记录](../evidence/A03/execution/P1-R2/final-static/diff-check-results.json) |

最短复现（cwd见第1节；Python 3.9.13、标准库、`-B`）：

```powershell
python -B examples/a03/P1-R2/check_design.py --root examples/a03/P1-R2/data
python -B docs/evidence/A03/execution/P1-R2/audit_prefix_bindings.py
python -B docs/evidence/A03/execution/P1-R2/package_r2.py verify
git -c core.whitespace=blank-at-eol,blank-at-eof,space-before-tab,cr-at-eol diff --check ca4fba4f505467228a8164c3999e0cecc54ffc4e HEAD
git status --porcelain=v1
```

样例目录本身可搬运后执行 `python -B check_design.py --root data`，不需要旧仓库/网络/第三方依赖。局部 Schema 评估不宣称完整 JSON Schema 标准认证。独立绑定/映射审计使用本冻结仓库中的输入；不将该内部辅助复核当作原独立验收结论。没有重跑未变功能套件、P2 V01–V10、崩溃/并发/平台测试。

## 4. 保全、制作失败与停止状态

[修前清单](../evidence/A03/execution/P1-R2/before/P1-R1/before-manifest.json) 保存两个原成功例及递归所需的33个文件。新正式 data 为218文件；完整样例711文件，包含本轮中间输入/失败日志。初次 Schema uniqueItems 支持缺项、prepared 仍引用旧 A fact，以及终局头遗漏均保留于新 attempts；修正未放宽原规则。根辅助审计曾因一例没有可选 progress 而 StopIteration，修前脚本及失败摘要保留于 [root-01](../evidence/A03/execution/P1-R2/attempts/root-01/failure.json)。早期 PowerShell 引号解析错误同目录记明；摘要记录明确标注非原始工具转录，不伪装完整日志。

清理本轮可再生中间目录的组合命令在进程启动前被自动审批拒绝，原文 `CreateProcess rejected: blocked by policy`；未执行删除，未重试。改为以原生 PowerShell 保全移动，两个中间包仍在新 attempts 内；[拒绝记录](../../examples/a03/P1-R2/attempts/policy-denial.json)。

以 exact R2 基线捕获的8,923个旧跟踪文件逐字节核对，四个允许路径之外不得改动；实际结论见 [保全/范围/链接审计](../evidence/A03/execution/P1-R2/preservation-audit.json)。原R1清单780项的SHA仍为 `c882542e9aefe1f413533b1350f6b81d20202f0bc37dd44b829d1eeb39f946b5`。新增内容全部由 [统一SHA256清单](../evidence/A03/execution/P1-R2/sha256-manifest.json) 覆盖，含日志、失败现场和Git忽略项；仅清单自身排除。最终提交后另作只读清单核对及 Git raw blob 对比，其实际退出、文件数和清单自身SHA在最终回复给出，避免把所属最终提交摘要写回自身。

未写 D:/1800，未改 src/tests/公共合同/根依赖/调度文件，未推送/集成。S01真实完整性、D01/Pillow、B确认、真实恢复、真实质量/成本与I01保持未完成。网络、浏览器、平台、凭据/profile、OCR、业务模型API/费用、数据库/恢复实现均为0。同步静态子进程已等待退出，没有后台服务或平台会话；内部辅助执行者也已结束，遗留自有进程/会话为0。停在 **P1 REVIEW**。
