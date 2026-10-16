# C01 执行交付报告

日期：2026-10-16（Asia/Shanghai）。执行状态：**REVIEW**，提交供独立验收；执行者不作 ACCEPTED 结论。

## 确切版本与范围

- 工作目录：`C:\Users\ASUS\.codex\worktrees\c01-contracts\1800`。
- 分支：`codex/c01-contracts`。
- base_commit / workflow_commit：均为 `30bc00cbaa3e40d78fd8d5cac98e81bd354763b2`。
- implementation_head_commit：`4660e8e4120af1b8550c2e0ee3dd02593aa38aac`（81 个新增任务文件）。本报告以随后独立的文档提交归档，交付 HEAD 由最终回执给出；该文档提交只增加本报告，代码/样例被验版本固定为此 implementation commit。报告不能自包含其自身 Git commit hash。
- 合同：`1.0.0-a-proposal`；交换：`c01-exchange-1`；样例：`c01-fixtures-1`。
- 修改仅为 `src/annotation/contracts/`、`src/annotation/__init__.py`、`pyproject.toml`、`tests/test_contracts.py`、`tests/fixtures/contracts/`、`examples/contracts/`、`config/policies/`、[实现说明](../contracts-implementation-v1.md)及本报告。样例目录内 `.gitattributes` 保留 SHA-256 绑定资源的精确字节。
- 未改 AGENTS、架构/原合同、coordination/coordination-state、B 模块、原研究工具和证据；所有源码与 Git 操作均显式使用指定 worktree，未切换或修改 `D:\1800` 主工作区。

## 交付与最短复现

九类公共 Python 类型、单一结构权威生成 JSON Schema、完整 bundle 级依赖/语义校验、最小 CLI、四组固定样例、只用公共 API 的跨目录消费者、政策提案及失败测试已提交。实现取舍和 B 消费入口见 [contracts-implementation-v1](../contracts-implementation-v1.md)，示例见 [examples](../../examples/contracts/README.md)。

实际环境：Windows / PowerShell，Python **3.9.13**（MSC v.1929 64 bit AMD64），Pydantic **2.12.5**，setuptools **82.0.0**。根配置固定 Pydantic 2.12.5，测试只用 unittest。实际安装使用既有依赖，无需浏览器或模型：

```powershell
Set-Location 'C:\Users\ASUS\.codex\worktrees\c01-contracts\1800'
python -m pip install -e . --no-build-isolation
python -m annotation.contracts validate tests/fixtures/contracts/normal/input.json
python examples/contracts/consume.py tests/fixtures/contracts/normal
python examples/contracts/consume.py tests/fixtures/contracts/exception
python examples/contracts/consume.py tests/fixtures/contracts/unknown
python examples/contracts/consume.py tests/fixtures/contracts/choice-assumption
python -m unittest discover -s tests -p 'test_contracts*.py' -v
python -m annotation.contracts schema
```

最后一次完整测试使用 `-q`，实际输出及退出码：

```text
----------------------------------------------------------------------
Ran 54 tests in 6.926s

OK
exit=0; skipped=0
```

具体负例独立复现（测试退出 0 表示观察到了预期拒绝）：

```powershell
python -m unittest discover -s tests -p 'test_contracts*.py' -k only_one_pass -v
python -m unittest discover -s tests -p 'test_contracts*.py' -k current_target_change -v
python -m unittest discover -s tests -p 'test_contracts*.py' -k unknown -v
python -m unittest discover -s tests -p 'test_contracts*.py' -k patch -v
python -m unittest discover -s tests -p 'test_contracts*.py' -k resource_paths -v
python -m unittest discover -s tests -p 'test_contracts*.py' -k cli_rejects -v
```

另实际在临时 JSON 将 region[0].box.bbox.x2 从 65 改为 81（原图宽 80），运行 `python -m annotation.contracts validate <temporary-invalid.json> --structure-only`，进程退出 **1**，stderr 为：

```json
{"valid":false,"issues":[{"path":"$.artifacts[1].EvidenceBundle.payload.regions[0].box","code":"SCHEMA","message":"Value error, bbox must have positive area within bound original image"}]}
```

该错误来自几何结构层，未被未重算的摘要抢先遮蔽。其他引用/状态负例测试会重新封签并传播合法依赖摘要，避免只验证“hash 被改了”。

## 实际样例与验证结果

所有样例的图像、题目、质量断言、能力和回执均 **SYNTHETIC**，每组 12 个产物，包含九种类型、PRE_APPLY/TARGET/POST_APPLY 三份报告及 patch 前后两个图谱修订。没有调用识别/组题/平台 executor。

| 样例 | 实际消费者结果 | 关键状态 |
|---|---|---|
| normal | EXACT_MATCH | 3 题；模拟 APPLIED；READY_FOR_SUBMISSION / NOT_SUBMITTED / VERIFIED |
| exception | EXACT_MATCH | 4 题分母含 SKIPPED 漏题；EXCEPTION；PLAN_BLOCKED；NOT_EXECUTED / NEEDS_REVIEW |
| unknown | EXACT_MATCH | 3 题；UNKNOWN / RECONCILE；BOOK_WRITE_PAUSED；NEEDS_RECONCILIATION / PENDING |
| choice-assumption | EXACT_MATCH | 3 题；普通选择题仅在 SYNTHETIC_ASSUMPTION、SYNTHETIC_ONLY、SIMULATED 假设下通过 |

`input.json` 原始文件 SHA-256（UTF-8 LF，资源摘要另列在文件中）：

| 样例 | SHA-256 |
|---|---|
| normal | `b437be9cd68b04f3c72cadad6a78af8dc2edfeb6f7302c6904f553efebdbabf4` |
| exception | `8af3599838dcf397050cbe6d39048bcf5d454ec050c20c3bcb0788ea11b4c94d` |
| unknown | `6fa1e9a76d9b0062603651544e9474994ca56af9e0354eb6fd41545a22a00406` |
| choice-assumption | `0f63d06f9fdfe6fcea30097a6d8c136d91c3a7cd33e220c70643ee7fe29caacb` |

跨目录实测：四组复制到系统临时目录，以另一个 cwd 运行绝对路径消费者，移除子进程 PYTHONPATH 后使用已安装包；写出新目录、重读和 expected 精确比较，**4/4 EXACT_MATCH**。测试还覆盖含空格路径及写出后再次消费。

确定性实测：固定生成器重建后全部 67 个样例/政策文件 SHA-256 不变；随后增加目录 `.gitattributes` 并将 README 写为显式 UTF-8 LF，资源/input/expected 摘要不变。最终从 Git index 用 `checkout-index` 导出 **65 个样例文件**（含 attributes），在 `core.autocrlf=true` 的实际环境重新验证四组资源，全部 VALID，避免只在作者现有目录通过。

执行侧逐项结果：

| 条款 | 实际结果 |
|---|---|
| 单一类型、JSON Schema、包导入、CLI | 通过；schema 与公开 API 输出相同，未手写第二权威 |
| 摘要自指、依赖版本/摘要/kind、缺失实体/资产 | 通过；修改引用后重封签仍能拒绝错引用 |
| 原图尺寸/摘要绑定、边界/NaN/±Infinity | 通过；未裁边，非有限值报具体字段位置 |
| PRE_APPLY+TARGET 两份 PASS、政策及当前目标快照 | 通过；一份 PASS、错 stage、版本变化、未验证/过期能力均拒绝 |
| UNKNOWN/NOT_APPLIED/APPLIED 和完成组合 | 通过；合法 NOT_APPLIED 与合法已提交 COMPLETED 为正例，对应伪装成功为负例 |
| 换动作 ID 绕过 UNKNOWN | 通过；同书资格门 BOOK_WRITE_PAUSED；每个未决动作对应题都 UNKNOWN |
| 题目归属与整页遗漏 | 通过；跨题动作来源拒绝；PASS 不准漏 scope manifest 题，孤儿片段不算题目归属 |
| Patch 基线/派生/新修订 | 通过；错基线、旧字段不符、丢 after、夹带改动拒绝；旧版保留 |
| 旧回执/差量引用 | 通过；错误类型/同版基线拒绝；UPDATE 需 frame_update VERIFIED 和对应 APPLIED 旧目标 |
| 分母、提交/内容独立字段、账单未知 | 通过；异常/跳过不能删；未知费用为 null，不能为 0 |
| 路径和跨 cwd | 通过；绝对/盘符/UNC/遍历/ADS/设备名均拒绝；symlink 权限不足时用 Windows junction 实测 PATH_ESCAPE，无跳过 |
| 编译、文档本地链接、Git 差异 | compileall 通过；7 个说明文档本地链接无断链；git diff --cached --check 通过 |

开发侧只读风险扫描发现五处漏口后已修复，并加入独立变异回归，不是把扫描意见当验收结论。最终 54 项包含这些负例及正例对照。

## 未决语义与未测试层

以下保持显式提案/未测，详细影响见实现说明：

- B 的接口采用和合同共同确认未取得，不能称已冻结。新增 scope_manifest、证据注册表、必需检查集合、BLOCKED/NOT_EXECUTED 诊断链、platform_version、same_session_handoff/frame_update 能力及 patch 字段子集都需共同确认。
- W 独立/合并继续 UNRESOLVED；默认政策只记录 A05 有界框保存/读回，OCR UNVERIFIED。普通选择题正常组额外样例使用模拟假设，不决定业务规则。
- canonical-json-1 是明确的 Python JSON 数值规则，未声称 RFC 8785 跨语言数字一致。跨语言消费者需以固定样例核对。
- C01 不实现 recognition、assembly、真正 planner/executor、intent/receipt 原子持久化、实时锁、reconciliation 解暂停、重启恢复、复杂工作台或 patch 应用/冲突迁移执行器。UNKNOWN 解决证据留给 A03 后续合同；不能删旧记录解锁。
- 资源验证读取图像头部尺寸及文件摘要，不做完整图像解码或几何回投算法；报告中的 PASS 理由无法证明算法内容真实正确。纯 patch 派生不允许混入重识别修改，未来需显式冲突处理合同。
- 完全离线：未启动浏览器、未读取凭据/profile、未运行 A05 写入或重放题 22、未触及真实平台、未最终提交、未测试真实 OCR/B算法准确率或恢复能力。模型调用 **0**，付费调用/花费 **0**；真实模型成本和人工效率未测。

交付后源代码与样例保持 `4660e8e4120af1b8550c2e0ee3dd02593aa38aac` 不变，仅归档本报告；停止修改被验工作树，等待主调度独立验收和必要定向修复。未推送远端、未合并主工作区、未创建自动化、未向其他对话发消息或管理 B。
