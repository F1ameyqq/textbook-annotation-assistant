# A01 集成修订 R1：固定历史快照与常规回归解耦

日期：2026-10-17。授权原 A01 执行对话进行一次有界修订。原 R3 有界离线独立验收和主调度复现保持历史事实；**本地集成未通过，A04 未释放**。不扩充来源、几何、OCR 或平台能力。

## 确切基线与失败

- A01 冻结基线：`180bb1e86fb2a7eb1546be85af70f466f069daf5`；继续原工作树 `C:/Users/ASUS/.codex/worktrees/a01-source-geometry/1800`。
- 主目录合并前基线：`4946b8ab307f88bdc25c14ace5ead774e3119fc5`。调度正常合并上述 A01 到未提交状态，414 个暂存路径均与 A01 Git blob 一致，无冲突。
- [集成回执](../evidence/A01/coordinator/integration/checks.json)：A01 49 项中 47 通过、1 权限跳过、1 失败；C01 70、A02 52、登录 8 均通过。
- 失败为 `PreservationR3Tests.test_fixed_baseline_has_only_explicit_twenty_five_variants`：在当前整个 `ROOT` 运行历史 971 项保全检查。主目录合法更新的 `docs/coordination-state.json`、`docs/coordination.md` 必然不同；18 个新合入文本为默认 checkout 的精确 LF→CRLF 表示，而非该历史清单允许的候选。[逐项诊断](../evidence/A01/coordinator/integration/fixed-reference-diagnostic.json)及[分类](../evidence/A01/coordinator/integration/mismatch-classification.json)保留原摘要，没有规范化输入或放宽规则。
- 已正常撤回未提交合并，主目录仍为上述基线；原始失败日志和回执不可覆盖。不是线上故障，也没有证据显示来源/几何算法失效。

## 目标与允许范围

常规测试应能在持续演进的集成仓库运行，固定发行快照仍须严格按其原始参照验收。修订必须同时保留这两种保证，不能通过跳过、吞错、重写期望摘要或删除损坏负例制造成功。

允许修改既有 `tests/test_a01_rework_r3.py`，允许新增 `tests/test_a01_integration_r1.py`、`tests/fixtures/a01/integration-R1/`、`examples/a01/integration-R1/`、`docs/evidence/A01/execution/integration-R1/`、`docs/tasks/A01-integration-R1-execution-report.md`。不要修改实现、原 geometry、公共合同、根依赖、根属性、调度文档、旧输入/报告/失败证据或原 R3 固定参照/verify。需要额外既有文件变更时交付最小提案及失败证据，不自行扩范围。

1. 先独立复现两类集成差异，设计最小测试调整。常规回归不应要求当前调度文档保持历史字节；原固定参照仍检查其明确绑定的不可变输入。保留 971 条及 25 个明确候选的政策检查，并用固定输入而非当前文件生成期望。损坏、混合换行、未允许表示仍须拒绝。
2. 不为一般 checkout 任意追加换行候选，不改全局 Git 设置，不把全仓库文件规范化。原 R3 verify 继续只针对它绑定的冻结版本；不能声称旧 verify 接受改过测试文件的新提交。新版本给出清晰的常规回归/冻结归档验证入口，避免消费者混用。
3. 用临时、隔离的本地集成副本重演“固定主目录基线加 A01 及本修订”，不得在 D:/1800 开发或合并浮动分支。副本须记录确切两个父版本与本补丁身份，保全受审代码。用当前默认 checkout 和无 Git 原始字节副本验证新常规入口；调度文件合法改变不应使来源功能回归失败，真实源/输入损坏仍由对应门禁拒绝。
4. 受影响 A01、C01、A02、登录回归应全部符合预期（已有 symlink 权限跳过如实保留）。独立 URL 和搬运消费复用必要固定样例；不重复构建无关大型证据全集，不重新运行原 630 项几何矩阵。

## 交付与边界

提供确切补丁/最终提交、范围清单、精确命令与环境、原失败和修后结果、独立副本的父版本、文件表示及已知限制。原件保持不变，仅允许指定旧测试的受审修改；新清单不覆盖或更新旧 R3 清单。工作树干净冻结后转 REVIEW，由原独立验收对话复验，再由主调度重新集成。

全程离线；不访问网络、平台、浏览器、凭据/profile、OCR 或付费模型，不推送，不标 INTEGRATED，不释放 A04。D01 仍待 A01 集成完成后由主调度处理；S01、N15、B 确认等限制不变。当前仅授权这一轮有界修订，不无限重试或扩张任务。
