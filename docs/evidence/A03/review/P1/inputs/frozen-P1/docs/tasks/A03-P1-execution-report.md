# A03-P1 设计执行报告

日期：2026-10-17（Asia/Shanghai）。交付状态：**P1 REVIEW**。只交付候选设计，未申请或取得设计通过/功能 ACCEPTED/INTEGRATED；P2 未开始，不释放 I01。

## 1. 确切版本与范围

| 项 | 值 |
|---|---|
| code base | `ec1b4defbfa3ec0f181d291106fb53313983e493` |
| workflow / 派发 HEAD | `a354f95f1d0b40a8f0847b57fa3978cac999e7a2` |
| A02 被接受交付 | `38aca9dcc8d027409b95193e9cc142c2336b76d3` |
| A02 被接受实现 | `13ddf83083224ffafc17a4f57cf2c1a1a1ae02b2`（已核对为 code base 祖先） |
| 工作树 | `C:/Users/ASUS/.codex/worktrees/a03-runtime-recovery/1800` |
| 分支 | `codex/a03-runtime-recovery` |
| 设计交付提交 | `6ac0256f05169570605fcb921a773ff2ae0f4aef` |
| 实现提交 | 无；P1 禁止实现，未修改 `src/`、`tests/` 或根依赖 |
| 最终交付提交 | 包含本报告和统一清单的最终提交；完整 40 位 SHA 在最终回复返回。报告不能包含其自身所属提交的自引用 hash；在冻结工作树运行 `git rev-parse HEAD` 可准确定位 |

所有命令均在指定独立工作树运行；主目录未写文件、未切分支。未改公共合同文档、调度状态、旧样例及既有执行/验收证据。原 tracked 文件共 **7,993** 个，按 workflow 基线记录字节数/SHA256 并在最终包装检查复核。

## 2. 设计交付

- [恢复合同提案](../a03-recovery-contract-v1-proposal.md)：D01–D08 的具体选择、版本/迁移矩阵、三个产物、完整书级账本、部分计划与报告、来源准入、所有权和有限核对。
- [P1 说明](../../examples/a03/P1/README.md)、[完整候选交换 Schema](../../examples/a03/P1/recovery-exchange.schema.json)、[账本 Schema](../../examples/a03/P1/ledger-export.schema.json)、[逐动作事实资源 Schema](../../examples/a03/P1/action-fact.schema.json)、[设计 case wrapper](../../examples/a03/P1/case-file.schema.json)。逐动作事实是资源及 journal 事件，不新增第四种 Artifact。
- [四组 API 提案](../../examples/a03/P1/api-proposal.json)：现有入口/确切源文件行号、建议签名、输入输出/失败码、责任、兼容影响、精确 P2 白名单；附公开 RuntimeAuthority、全新观察绑定桥和正常逐动作收口。
- [案例清单](../../examples/a03/P1/case-manifest.json)：**42** 个完整 JSON 案例，覆盖正常/MATCH/ABSENT、无 receipt、多动作充分/不足 ABSENT、跨 scope 未决、旧无 intent UNKNOWN、错版本/摘要/身份、分叉/环、旧观察复用、真实/OBSERVED 拒绝及 owner/目录/额度反例。预期层和语义错误码全部标为 EXPECTED_NOT_EXECUTED。
- [迁移映射](../../examples/a03/P1/migration-map.json)：显式生成新版本设计输入；原 normal/UNKNOWN 及引用资产按字节归档，不迁移旧执行结果为新资格，不补造历史 intent。

候选版本：schema `1.1.0-a-recovery-proposal`、exchange `a03-exchange-1`、runtime `a03-runtime-db-1`、target `a03-mock-state-1`、账本 `a03-ledger-export-1`、比较器 `a02-facts-1`。

## 3. 已冻结的关键选择

| 项 | 候选规则 |
|---|---|
| 新 intent | 真实本地 SQLite 提交及不可变文件索引才构成资格；P1 JSON 不是提交证明。逐动作 prepared_before 与计划初始快照分别绑定 |
| 旧 UNKNOWN | 旧无 intent 保持 LEGACY_UNRECORDED；只归档，不允许改版本重封签、迁移补默认值或过滤历史解锁 |
| 部分计划 | 完整动作 progress；有充分 ABSENT 才可 NOT_APPLIED + NOT_ATTEMPTED。正常逐动作 ACTION_RESULT_COMMITTED 在完整 receipt 前收口；无 tail 证据不拼回执 |
| 引用/新观察 | 普通引用继续同 book/scope，版本不混用；resolution 绑精确 intent/obligation、原 UNKNOWN 及合法单链。实际新读产生新 ID/时间/read_sequence，业务状态版本可以不变 |
| 书账本/占有权 | 稳定 target_key 三元组，全 run/scope 当前事务扫描；唯一 anchor/store 身份、owner/generation、共同效果闸与 CLAIMING→fence→ACTIVE；自报账本不授许可 |
| 固定 target session | 每书固定 SourceBundle/scope；不支持的切换拒绝，不能 register 清历史；其他 scope 未决即使当前不能读也保持阻断 |
| 继续规则 | 首发 permit 单次事务消费；重启或中断旧计划及 tail 不续发。MATCH/ABSENT 均不重发旧动作，重新检查规划；终局后目标变化形成可用新只读检查解除的 TARGET_DRIFT_HOLD |
| 全合成/S01 | 整包及资源来源闭包必须 SYNTHETIC/FIXTURE/SIMULATED；ORIGINAL/OBSERVED/真实来源拒绝。真实 S01 完整性生产者仍未完成 |
| 有界核对 | 每 intent 每恢复调用最多 3 次；单读 2s、单 intent 8s、整调用 60s、busy 1s、效果闸/屏障各 5s；到限暂停，不重发 |
| 内容/提交 | PENDING / NOT_SUBMITTED，绝不输出 COMPLETED；分母未知/零题保留诊断，不虚构完整批次报告 |

完整字段、条件与精确摘要公式见主提案及候选 Schema/API，不能只按此摘要实施。

## 4. 实际检查与复现

环境详见 [environment.json](../evidence/A03/execution/P1/environment.json)：Windows；Python 3.9.13、Pydantic 2.12.5、SQLite library 3.37.2。公开 contracts 模块导入路径已核对位于本工作树。未创建运行库/目标库，未安装依赖；本地无 jsonschema 包，使用交付的离线有限关键字结构检查器，不能将它宣称为完整 JSON Schema 标准认证。

在上述工作树运行以下只读命令：

```powershell
python -B examples/a03/P1/check_design.py
python -B docs/evidence/A03/execution/P1/check_api_design.py
python -B docs/evidence/A03/execution/P1/verify_delivery.py verify-manifest
git diff --check
git status --porcelain=v1
```

| 实际检查 | 结果及证据 |
|---|---|
| JSON/候选 Schema 引用/资源字节/内容摘要/普通引用/DAG | `退出 0；42 例静态预期全部相符；两套旧归档结构、资源和字节摘要核对通过；所有语义 actual=NOT_EXECUTED`；[静态输出](../evidence/A03/execution/P1/static-check.txt) |
| API/Schema 设计字段/当前源文件行范围/authority 协议 | `退出 0；94 JSON、4组适配、14个当前入口行范围、18个组内接口、7个authority方法；errors=[]`；[一致性输出](../evidence/A03/execution/P1/api-check-attempt-01.txt) |
| 原 7,993 文件字节、允许路径、本地链接 | `最终包装审计退出 0；7,993 个原文件零差异、允许路径通过、30 个本地链接；审计/清单的未来自身链接由最终 verify-manifest 再核对`；[包装审计](../evidence/A03/execution/P1/delivery-audit.json) |
| 统一 SHA256 清单核对 | `最终按只读核对命令返回退出 0；实际最终清单 SHA256 在最终回复返回`；[清单](../evidence/A03/execution/P1/sha256-manifest.json)（清单自身排除，最终回复返回其 SHA256） |
| 新恢复分类/真实本地 intent/解除暂停/进程重启/并发/P2 V01–V10 | **未运行**；P1 不授权功能实现或实测 |
| 旧 C01/A02/登录测试与 52+70+8 回归 | **本 P1 未重跑**；这些是主调度既有接受记录，不是新恢复证据 |

完整命令/cwd/退出码索引见 [command-results.json](../evidence/A03/execution/P1/command-results.json)。制作过程中有 Python 3.9 写文件参数、stdin 编码、静态 checker 初次未支持 minProperties/propertyNames 等制作错误，已保留 [制作尝试记录](../evidence/A03/execution/P1/packaging-attempts.json)，后来纠正不覆盖原失败记录；这些没有执行恢复功能。首次包装审计误把自身尚未生成的输出当断链，原失败保存在 delivery-audit-attempt-01.json；修正自身输出链接处理后单独审计退出 0。候选生成器仅制作静态设计数据，交付后不在冻结目录运行 `--replace-draft`。

新增 examples/a03/P1/.gitattributes 仅在候选目录禁用行尾转换，保全原件与资产哈希；132 个设计文件已核对 Git index 与工作文件逐字节相同。

统一清单覆盖本报告、提案、Schema/API、脚本、案例/资源、归档、实际检查输出与日志；仅清单自身和未提交的 ignored `__pycache__` 排除。最早两次 schema 导出命令未带 `-B`，发现五个 ignored import cache，来源未证明；未删除可能既有缓存，也未入提交。源码及全部 tracked 旧文件仍逐字节保全。

## 5. 限制、待批准与会话释放

P1 只完成设计交付和静态包装检查，不能替代正式独立设计验收。D02–D07 与超时数值、恢复版本及最小适配接口须独立设计验收和主调度批准，原执行对话获续派后才可开始 P2。

P2 的 SQLite/文件事务、实际 commit、进程崩溃、双进程竞争、故障注入、来源门和恢复链的功能行为全部未实施/未运行。S01 真实完整性、Pillow 根依赖 D01、B 合同确认继续未解决；未释放 I01，未推送或集成。模拟目标持久化、真实平台 exactly-once、任意外部写入者协调、OCR/最终内容和真实成本均未测。

业务模型调用/费用=0；浏览器、平台、网络、凭据/profile 操作=0。没有启动后台服务、浏览器或长驻自有子进程；所有本次前台命令已退出，**待释放自有进程/会话=0**。最终工作树干净冻结后，仅交回 P1 REVIEW。
