# A 侧第一阶段交接

2026-10-17（Asia/Shanghai）。交接分支：`codex/a-stage1-handoff`。这是已验收的 A 侧基础模块与完整历史证据的阶段快照，供搭档读取接口、消费固定样例和准备联调。B 的开发、排期和内部验收由 B 自行管理。

## 已交付范围

| 模块 | 已验证能力 | 接受版本与实际集成 |
|---|---|---|
| C01 | 类型、引用、资源摘要、合法与异常状态校验；正常、异常和 UNKNOWN 构造样例 | 接受 `4e42668ab28eda37a37285285d2f6c595d3bba12`；集成 `223b0b3d9ae0bd50ef2ac045219a41ad41611856` |
| A01 | 两本书的静态来源包、来源一致性检查、原图绑定与公共几何 | 接受 `5f872150a237b195f73c78e02e13a91d2f4f46a7`；集成 `c6bebdf43eb93f7a6ae21e96ec07ed155686777d` |
| A02 | TARGET 检查、动作计划、内存模拟平台、UNKNOWN 暂停与故障样例 | R1 功能及 portability-R2 已接受；R2 `a1e5be00909172429d792b6c41bdaf384258694e`；集成 `2d1dc8b97713ee06ec5bf35febe0b894ece584b2` |

本次代码基准是主调度提交 `00e6d52b97ef9fddcd534deb81a2ae7244484d9f`。发布准备只增加交接入口和发布核验记录，没有改动已验收的实现、固定样例或历史结果。[发布清单](handoff/a-stage1/manifest.json)绑定导出接口、测试、样例及关键验收文件的 Git blob 和 SHA256。

A03 P2 恢复实现、A04 坐标续作和 D01 清洁安装验证尚未被主调度接受并集成，其在研代码不在这个分支。历史 A03 设计、任务单及 A04 准备材料保留原状态。已有 A05 证据仅证明书 `46007447` 的题 22 的一对 Q/A 框保存与重开；内容仍待验证，不能重放，也不代表通用恢复、OCR 或批量能力通过。

## 搭档从哪里开始

- 合同说明：[合同 v1](contracts-v1.md)、[Python 实现与公共 API](contracts-implementation-v1.md)。版本为 `1.0.0-a-proposal` / `c01-exchange-1`；A 内部通过，双方共同确认仍待完成。
- 来源与几何：[A01 说明](a01-source-geometry.md)，当前固定包为 [旧书 R3](../examples/a01/R3/bundles/46006966/exchange.json) 和 [测试书 R3](../examples/a01/R3/bundles/46007447/exchange.json)。每本书目录必须整体复制，保留原字节和相对资源路径。
- 公共消费：`annotation.contracts.load_bundle` 默认检查资源；`examples/a01/consume.py`还完整解码页图并核对来源。通过类型构造或 JSON Schema 不能替代完整包校验。
- 计划与模拟：[A02 运行说明](../examples/a02/README.md)。PRE_APPLY 为显式合同桩，输出标记 SYNTHETIC / SIMULATED；不代表 B 的算法结果或真实平台保存。
- 后续接口讨论：给出双方确切提交、输入包、错误路径和期望语义。当前未宣称 B 的现有产物已经兼容这些公共合同。

旧书只有 6 张图，新书只有 2 张图；元数据页数分别为 250、214。两包均为 `REFERENCE_ONLY`，`coverage_eligible=false`，不能用于证明全书完整性或充当独立评测分母。

## 最短离线复现

以下为 Windows PowerShell，在本分支仓库根目录执行。使用 Python 3.9；记录中已验证的依赖为 Pydantic 2.12.5、Pillow 11.3.0。先安装到自己的虚拟环境，不需要平台账号、浏览器或模型 API。

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install pydantic==2.12.5 Pillow==11.3.0
$env:PYTHONPATH = (Join-Path $PWD 'src')
.\.venv\Scripts\python.exe -m unittest discover -s tests -p 'test_contracts*.py' -v
.\.venv\Scripts\python.exe -m unittest discover -s tests -p 'test_a01_*.py' -v
.\.venv\Scripts\python.exe -m unittest discover -s tests -p 'test_a02*.py' -v
.\.venv\Scripts\python.exe examples/a01/consume.py examples/a01/R3/bundles/46006966/exchange.json --book-id 46006966
.\.venv\Scripts\python.exe examples/a01/consume.py examples/a01/R3/bundles/46007447/exchange.json --book-id 46007447
.\.venv\Scripts\python.exe examples/a02/run.py --output .local/stage1-normal
.\.venv\Scripts\python.exe examples/a02/run.py --output .local/stage1-unknown --fault lost_response
```

输出目录必须不存在；重复运行时换新目录。上述是源码环境复现说明，**不是 D01 的清洁安装验收**。当前 `pyproject.toml` 尚未声明 Pillow，因此这里显式安装；待 D01 独立验收并集成后再提供其安装结论。历史文档中的 REVIEW、尚未集成或未推送描述保留为当时记录，当前阶段范围以本页和各收口记录为准。

## 验收依据与限制

- [C01 收口](tasks/C01-coordinator-acceptance.md)：70 项合同测试与 8 项离线登录工具测试通过。
- [A01 集成 R2 收口](tasks/A01-integration-R2-coordinator-acceptance.md)、[独立复验](tasks/A01-integration-R2-review-report.md)：静态来源与几何范围已接受。实际集成的 11 个子命令全部退出 0，A01 52 项中 51 通过、1 项因 Windows 文件符号链接权限跳过；该跳过仍是未验证项。
- [A02 R2 收口](tasks/A02-portability-R2-coordinator-acceptance.md)、[独立复验](tasks/A02-portability-R2-review-report.md)：实际集成 62 项通过、零跳过。内存模拟不具备跨进程持久化和真实写入恢复能力。
- [实际集成检查](evidence/A01/coordinator/integration-R2-integration/checks.json)同时记录 C01 70、A02 62、离线登录 8、5 个 URL 反例及 6 次来源消费。发布本身没有重新运行未变化的全套测试，没有增加上述功能验收范围。

本次不发布“完整自动标注已实现”的结论。A03 恢复、A04 通用只读适配、D01 安装、S01 来源完整性、I01 纵向集成、真实跨侧联调、批量质量和成本均有各自未闭合门槛。书级送审/送交仍由人工负责。

## 与远端的关系

本次核对的远端架构分支为 `aac335bcee72005dcebf02fe9131db8a0d463e37`，B 侧分支为 `c3cc2df7a0be24c125c83681c0499c0d328d78f6`。架构分支有 26 个本地调度分支未包含的提交。本交接分支保存 A 的确切接受历史，未合并这些 B 增量，未改写 `main`、架构分支或 B 分支。

后续合并前，需要核对 `.gitattributes`、`.gitignore`、`AGENTS.md`、`README.md`、`docs/development-plan.md` 的双方改动，以及远端新增的 `docs/status/a.md` 入口。它们是路径交集，不表示已执行合并或已确认冲突。公共文档和跨侧合同以双方确认的版本继续推进。

本分支提供的是代码和样例；凭据、浏览器 profile、原始视频不进入发布。授权仍限定既有测试书和操作范围，取得分支不构成新的平台操作授权。
