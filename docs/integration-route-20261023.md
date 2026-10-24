# 固定分支集成路线与交付入口

核查日期：2026-10-23，Asia/Shanghai。实现基线 `ee463c800bef1ec5010ee5950662b9726d474e42`；本轮在独立 clone 中读 Git 对象、运行 `merge-tree` 和离线回归，没有真实 merge、远端 push、base 修改或平台操作。代码/文档入口见[运行索引](run-index.md)。

## GitHub 为什么只有 PR #3 带有最新闭环

本轮 `gh api` 成功读取分支、全部 3 个 PR 和 Actions 元数据；初次及后续留存尝试曾被本机 socket 权限阻断，保留该限制，不把失败请求写成新的远端确认。成功读取的固定 SHA 与本地对象逐一一致，摘要及原命令见[核查记录](../evaluation/integration-checks-20261023.json)。

| 对象 | 已核实状态 | 对集成的含义 |
|---|---|---|
| `main` | `561ca5a2fa11026f6667e1c7a897782dd3a205f4` | 架构分支的祖先，落后 27 个提交；相对最新 B 落后 86 个提交 |
| `codex/automation-architecture` | `aac335bcee72005dcebf02fe9131db8a0d463e37` | 接收了 PR #1/#2；是现有 PR #3 的 base |
| `b-side/readonly-book-46007447` | `ee463c800bef1ec5010ee5950662b9726d474e42` | 带有 17 题真实闭环源码与脱敏证据；本轮实现基线 |
| [PR #1](https://github.com/F1ameyqq/textbook-annotation-assistant/pull/1) | CLOSED，2026-10-16 19:35:15 +08:00 合并 | base 为架构分支；合并提交 `d9b20230d66caec150c76c85183433b35cd85f66` |
| [PR #2](https://github.com/F1ameyqq/textbook-annotation-assistant/pull/2) | CLOSED，2026-10-17 11:04:49 +08:00 合并 | base 仍为架构分支；合并提交 `aac335bcee72005dcebf02fe9131db8a0d463e37` |
| [PR #3](https://github.com/F1ameyqq/textbook-annotation-assistant/pull/3) | OPEN，head 为 `ee463c8`，base 为 `aac335b` | `merged_at=null`；最新闭环还未进入架构分支及 main |
| GitHub Actions | `total_count=0` | 没有远端 CI 运行证据；本地回归需随交付留存 |

因此 main 落后的可证原因是这些交付的合并目标一直是架构分支，PR #3 尚未合并。仓库元数据不能说明当初为何选择该流程，不推测负责人意图。PR #3 的 `merge_commit_sha` 是 GitHub 试合成值，不能据此当作已经合并。

最新真实流程由 B 后续提交 `885f7366`（可移植已有题保存/读回）、`d0eada3`（补图、修订与批次核验）、`ee463c8`（Q7 两阶段拆分与课时收口）交付。它们存在于 B 分支；远端旧 A 分支没有因此自动获得这些模块。

## A 交付的实际位置与消费范围

远端 A handoff 是一条发布链：stage1 → stage2 → A07 → A08/A09 → A24。五者均不是当前 B head 的祖先；接收报告或固定代码包消费与 Git 分支合并分别记录。

| 固定 A 分支 / SHA | 已消费的可核查结果 | 本轮可确认的交付形态与限制 |
|---|---|---|
| `codex/a-stage1-handoff` / `a15301ef3532aca25dcd527aae1c680c1e220e9f` | `1994b77` 与 `a15301e` 是 A 发布链内的准备/发布记录；本轮未找到 B 对 stage1 单独的消费者验收 | 这两个提交不是当前 B 的祖先，不能当成 B 已消费；后续 stage2 有独立接收证据，按其范围解释 |
| `codex/a-stage2-handoff` / `37089f9e0229da76ae1c45461b7e63929590be56` | [B 实际接收](reviews/a-stage2-37089f9-b-reception.md)：A06 读回固定 B 包，完整 stdout 与封存字节相同，5 项窄测试及 3 个静态 C01 消费通过 | 接收证据 ZIP 与机器回执已经跟踪入 B；生产 A 模块未直接混入 B `src`。结论是只读 HOLD，不是新模拟执行或平台通过 |
| `codex/a07-q1-handoff` / `e37606d74d7e538052c563d02df11c6c961b742f` | [固定 Q1 采用](reviews/a07-q1-e37606d-b-adoption.md)：六组映射/规范及模拟回执获得限定技术采用；[六框重放入口](a24-current-q1-sixframe-20261022.md)实际提取固定 A07 源码执行 | 固定包、引用和 B 重放入口已入库；模拟空目标不能证明真实全旧题保全，不能将历史答案/计划套用到当前 Q1 |
| `codex/a08-a09-q4-handoff` / `edf125961be9cdc1642652c038d99872b1c8cdc7` | [Q4 限定采用](reviews/a08-a09-q4-edf12596-b-adoption.md)及[Q16/三阅读包](b-q16-reading-fixed-delivery-20261021.md)的 C01 完整读取有记录 | 固定消费者源码以包内副本消费；不能把固定 Q4 或四任务可读推广为所有外部图谱/复杂框真实执行通过 |
| `codex/a24-b-takeover-20261021` / `c5aefbc8e995c410b3babf74a251f05a7724a1c2` | [当前 A24 C01 消费](reviews/a24-c01-consumption-20261022.md)实际保留四任务完整对象；[21 项重建包](a24-offline-replay-20261022.md)及[56 项保全 v3 包](a24-runtime-preservation-20261022.md)已入 B | 远端 A24 原提交未被覆盖；后续 B 修复存在于公开 ZIP/patch 和固定提取入口中，不能只 checkout A24 原分支就宣称取得这些修复 |

B 当前生产树是 `prebox/`、`recognition/` 和 `runtime/usense_live/`；A 分支还有独立的 `contracts/`、`delivery/`、`geometry/`、`quality/`、`source/` 和其 runtime。直接拼装两个同名 `annotation` 包需要导入和公共合同验证；没有文本冲突的文件也不能视为接口已经兼容。

**仍只在私有运行/归档中的材料**包括历史 concrete owner/launcher 的本机配置与原运行证据、原始响应、源图、OCR 原输出、审校文件、profile 和真实 intent ledger。本轮没有把这些复制进仓库，也没有重新验证私人运行数据。公开 A24 v3 包仅含选取的运行源码/资源及合成夹具，不能当作其私有 live launcher。`0f83d5a` 的“公开包缺 launcher”是 10 月 22 日历史缺口；后续 `885f7366` 起已提供当前 `tools/run_usense_live.py` 与独立 writer，不能继续据旧缺口说全项目没有可运行保存代码。

## 已实测的合成结果

以本轮成功核对的固定 refs 在独立 clone 执行 `git merge-tree --write-tree --name-only <目标SHA> ee463c800bef1ec5010ee5950662b9726d474e42`。该命令只生成 Git 对象，不改变分支、工作树或索引。

| 合成对象 | left/right 提交数 | 冲突与文件树 |
|---|---|---|
| main 与 B | 0 / 86 | exit 0、0 冲突，结果与 B tree 相同 |
| 架构分支与 B | 2 / 61 | exit 0、0 冲突，结果与 B tree 相同 |
| A stage1 与 B | 78 / 85 | exit 1、4 个冲突路径 |
| A stage2 与 B | 79 / 85 | exit 1、4 个冲突路径 |
| A07 与 B | 80 / 85 | exit 1、4 个冲突路径 |
| A08/A09 与 B | 81 / 85 | exit 1、4 个冲突路径 |
| A24 与 B | 82 / 85 | exit 1、4 个冲突路径 |

main/B 与架构/B 的合成树都是 `ad2d4ad75306fe2540d2cf9243504b50b24f7252`，等于 B 当前树。架构独有的两个提交恰好是 PR #1/#2 的合并记录；B 已带有两次 PR 的内容祖先，因此出现分叉但没有文件差异。

五个 A 分支的 4 个冲突路径相同：`.gitattributes`、`AGENTS.md`、`README.md`、`docs/status/a.md`。此结果仅为文本冲突预检，不能据“只有 4 处”批准整体导入 A。尤其不能选择 ours/theirs 批量覆盖 A 状态或协作规则。

## 给总控的最小集成顺序

1. 在总控自己的集成副本确认 GitHub head/base 仍为表中 SHA，检查其他三线交付的父提交与差量；本分支相对 `ee463c8` 只交文档入口和核查摘要，可单独 cherry-pick 本地交付提交。各线提交 SHA 以各自 `handoff.json` 为准，不能从会话名推定已集成。
2. 在最终 B 集成候选上重跑本文最低回归、入口帮助与文档链接检查。保留现有 PR #3 的 base 为架构分支；不在本轮更换 base、push 或 merge。后续由总控按既有授权发布候选并等待 review。
3. 审查通过后，经 PR #3 把 B 候选合入架构分支以保留两个已关闭 PR 的历史；再为架构分支 → main 准备单独可审查交付。固定 refs 下两个阶段均无文本冲突，第一阶段文件树应等于被审查 B 候选。若 main 没有新增提交，第二阶段满足 ancestry 条件；main 分支保护/允许合并方式还需总控在实际发布时核对，本文不声称已通过。
4. A 历史分支保持固定来源。需要复用 A 能力时，先复用已经校验的隔离包和消费入口，再按一个具体缺口提取最小模块/适配及正反例。不要把 A24 原分支整体合入当成“补齐当前真实流程”。

备选的 B → main 合成也已测得同树无冲突，但它会绕开现有架构集成线和 PR #3 审查关系；除非总控明确改变发布策略，本次不推荐改走该路。上述是可审查的后续方案，本轮未创建合并提交。

## 最小回归和后续验收清单

```powershell
$env:PYTHONPATH = Join-Path (Get-Location) 'src'
python -B -m unittest discover -s tests -p 'test_usense_live*.py'
python -B -m unittest discover -s tests/usense_live -p 'test_*.py'
python tools/run_usense_live.py --help
python tools/run_usense_live.py --writer --help
python tools/run_usense_live.py --insert-writer --help
python tools/run_usense_live.py --finalize-writer --help
git diff --check
```

本轮实际 143 + 51 项通过；首次受限执行为 142 通过 / 1 环境错误，沙箱外复核 143 全通过，原失败保留。另从新目录运行 A24 保全入口，5 组共 56 项合成回归通过。没有跑完整历史全套，也没有重新进行真实保存。若后续改动 A24 保全包，重跑 `python tools/replay_a24_runtime_preservation.py --out data/runs/a24-regression-new`；若导入 A 合同/消费者，另在独立命名空间跑其固定完整对象接受与拒绝用例，不能只检查 import 成功。

- [ ] 最终集成 SHA、源码/输入摘要、各线交付消费回执及受影响回归齐备；本轮通过不自动覆盖其他线后续修改。
- [ ] 接收方环境实际安装/启动检查，确认 Python、Edge 和 Playwright API；本轮只复用既有离线运行时。
- [ ] 当前完整来源/稳定身份/原生题序和第 2 课时目录冲突已明确处置；旧批次及 Q7 计划不重放。
- [ ] 后续新范围保存由唯一平台操作者执行，独立新进程完整读回、其他题/未知字段保全、实际导出/图片、退出释放逐层核验；UNKNOWN 不自动重发。
- [ ] 正式平台业务复审、独立人工内容验收、A 所有者接收分别由实际负责人记录；完整章节分母、独立留出与跨书能力继续开放。
