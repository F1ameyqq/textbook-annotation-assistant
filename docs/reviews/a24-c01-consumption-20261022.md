# A24 固定消费者与 B Q16/阅读包离线联调

日期：2026-10-22（Asia/Shanghai）

## 结论

本轮完成了当前 A24 发布树 `c5aefbc8e995c410b3babf74a251f05a7724a1c2` 对固定 B 包的**真实离线消费**：使用复制版 A24 原始 `annotation.contracts.load_bundle(delivery/bundle.json, verify_assets=True)`，成功读取并验证全部资源，返回 `ExchangeBundle`；反序列化后的完整对象与源 `bundle.json` 深度相等。

结果定性为：

`PASS_CURRENT_A24_C01_READ_HOLD_SAVE_SCHEMA_UNBOUND`

这证明当前 A24 C01 消费器能无损读取该包；**不证明 A24 live-save 已适配共享材料、复杂分框或公式诊断结构，也不代表原 A 所有者、独立人工或平台接收。** 本轮没有生成保存 payload 或补丁。

## 固定输入与复制完整性

### A24

- 发布树：`c5aefbc8e995c410b3babf74a251f05a7724a1c2`
- 分支记录：`codex/a24-b-takeover-20261021`
- 本轮自有副本：`work/a24-b-c01-integration-20261022/a24-source`
- 发布 manifest 的 522 个成员逐文件长度和 SHA256 全部匹配。
- 每个成员的 Git blob 和 mode 与固定 `tree.json` 匹配。
- `source_tree_paths` 共 111 个，其中 81 个 Python 文件均以 `ast.PyCF_ONLY_AST` 解析通过。
- `selected` 固定输入共 524 个文件：522 manifest 成员、manifest 自身、`docs/status/a.md`；后者 Git blob 同样与 `tree.json` 匹配。审计运行时产生的解释器 `__pycache__` 不计入发布成员集合，也未改写任何固定成员。

### B 包

- 文件：`B-46007447-Q16-reading-C01-v2-HOLD-2026-10-21.zip`
- SHA256：`4725523ec499a3074b268b12f0282ca795c13ddd98e97350078a50db89f7dc93`
- ZIP 文件项：147。
- manifest 管理成员：146（manifest 自身排除）；逐成员长度和 SHA256 全部匹配，无额外或缺失成员。
- 本轮未使用 ZIP 内旧 A `consumer-a` 或旧 `a-consumer-receipt.json` 代替当前 A24 实测。

## 当前 A24 的实际消费结果

实际入口：

```python
from annotation.contracts import load_bundle
bundle = load_bundle("<copied-package>/delivery/bundle.json", verify_assets=True)
```

实际结果：

| 项目 | 实测 |
|---|---:|
| artifact | 4：SourceBundle / EvidenceBundle / QuestionGraph / CheckReport |
| 题/任务 | 4 |
| 共享材料 | 1 个稳定 owner，8 个共享片段 |
| 区域 | 37：23 text、3 image、11 formula |
| 语义片段 | 26：8 stem、8 shared_material、10 answer |
| 公式诊断槽 | 11（F1–F11） |
| 题面空格 | 6，全部 `value=null` |
| 答案关系 | 4，全部 `UNRESOLVED` |
| selected 答案片段 | 0 |
| 平台动作 | 0 |

六个 null 空格为：

- `q16-next-leg`
- `q16-next-hypotenuse`
- `q16-third-expression`
- `reading-cfgh-side`
- `reading-triangle-area`
- `reading-cfgh-area`

## 无损与引用核验

本轮不是只让 Pydantic“能解析”，还执行了下列比较：

1. `load_bundle(..., verify_assets=True)` 返回对象 `model_dump(mode="json")` 与原始 `bundle.json` 完整深度相等。
2. `delivery.json` 的 37 个 rich bindings 与 C01 37 个 region 一一覆盖；plain/LaTeX/blank 重组后的文本逐字等于 region `text`，图片区保持 `null`。
3. 11 个 formula binding 的 `expected_latex`、F1–F11 区域和 `fragment_id=null` 全部一致；公式诊断区域不伪造成重复答案片段。
4. 26 个 fragment→region、4 个 question/task→fragment、4 个 relation→question/fragment 引用全部闭合，坏引用为 0。
5. 三个阅读任务共享同一组 8 个 `shared_material` 片段；唯一材料 owner 为 `material-940010e304a65065ce384006`。
6. 除 11 个公式诊断区外，其余 26 个 region 均被且仅被语义 fragment 使用。

因此，`4题/任务、1材料、37区、26片段、11公式槽、6null空` 在当前 A24 C01 读取路径上均未丢失。

## 五区语义

A24 live wire 的五区固定为：

1. `question`
2. `choice`
3. `answer`
4. `analysis`
5. `knowledge_point`

自然旧正文的每道题必须保留完整五区键、`parts`、`question_info`、`rect_ids`、原始记录与哈希；新题只写 question/choice/answer，analysis 与 knowledge_point 仅能在“新题”范围显式置空。对应代码见：

- `src/annotation/delivery/live_pilot/wire.py:25`
- `src/annotation/delivery/live_pilot/wire.py:311-365`
- `src/annotation/delivery/live_pilot/wire.py:377-432`

## C01 能读与 live-save 能保存之间的实际缺口

| 层面 | 当前 C01 结果 | A24 live-save 实际合同 | 结论 |
|---|---|---|---|
| 题型 | 4 个 `free_response` 可读 | 只准单个 `ordinary_choice` | 不兼容 |
| 分框 | 37 区、26 片段可读 | 精确六框 `Q/W/W/W/W/A`、六个非空 text 片段 | 不兼容 |
| 共享材料 | 1 owner + 8 shared fragments 可读 | 明确拒绝 `shared_fragment_ids` 与 `parent_question_id` | 不兼容 |
| 跨页/复杂结构 | C01 合同可表达 | live admission 拒绝 `cross_page` | 未绑定 |
| 公式 | 11 诊断区可读且不重复成 fragment | live-save 无这组诊断槽的保存映射 | 未绑定 |
| 答案选择 | 4 relation 均 UNRESOLVED，selected=0 | live admission 要唯一 SELECTED 答案 | 不满足 |
| 平台身份 | platform id/order 均未造 | 保存要求当前身份、新题性和合法 append | 未证明 |
| 五区旧正文 | 本 B 包不含真实 natural export | 必须有完整当前五区与 authoritative route qualification | 不可推导 |
| savepage | 来源资产可验证 | viewer/source/save 三者及保存页映射必须另有当前证明 | 未证明 |

A24 的限制是显式代码行为，不是报告推测：

- `quality/live_pilot.py:158-177` 要求普通单选、无共享/父子/跨页、精确六框和唯一选择。
- `wire.py:342-365` 要求 natural export 具备完整 catalog、全部业务字段、五区、state binding 和 evidence refs。
- `wire.py:395-421` 将六框固定映射到 question、四个 choice、answer，并拒绝空区范围不明。
- `runtime/live_pilot/owner.py:434,491-494` 在 schema 未绑定时明确 `write_allowed=false`，终态 `PREWRITE_BLOCKED_NO_EFFECT`。
- `runtime/live_pilot/authority.py:87-89` 只把既有 savepage 状态视为需要 post-save proof 的提案，不是已证明映射。

## A24 首题目标与本 B 包不是同一范围

A24 首题目标仍是原先的单道普通单选保存候选；本轮 Q16/阅读包是四个 `free_response` 题/任务及一个共享材料。后者只用于验证当前 A24 公共 C01 消费能力，**不能替代 A24 首题候选，也不能把其来源页或结构套入首题 savepage/append 计划。**

## 为什么没有生成最小补丁或保存候选

委派明确指出的以下本机私有输入实际均不存在：

- directory snapshot
- frames snapshot
- natural export snapshot
- reviewed candidate
- request draft
- 六裁图目录

此外，book 原响应本来就仅保存长度和哈希，没有保留 body。由此不能从 SHA 反推 natural schema、metadata、profile、selected 关系、旧五区正文、合法 append 或 savepage。现在改 live wire 或构造保存请求会把未知字段伪造成已绑定事实，所以正确结果是：

- C01 读取：通过；
- 保存 schema：`CURRENT_SCHEMA_UNBOUND`；
- 真实 save / refresh / independent reopen：`NOT_RUN`；
- 最小补丁：不生成。

## 运行环境与边界

指定运行时实测：

- Python 3.12.14
- Pydantic 2.14.1
- Pillow 12.3.0

A24 原环境/冻结声明为 Python 3.9.13、Pydantic 2.12.5、Pillow 11.3.0，环境并不相同。因此本轮结论准确表述为“当前指定本机运行时上的兼容消费通过”，不冒充原 A 环境重放。

本轮：平台调用 0、OCR/模型调用 0、旧 live 重放 0、保存/refresh/reopen 0；未编辑共享 A/B 仓库。

核验结束时，共享 B 仓库 HEAD 为新增接管记录 `1cd363a050bfd14cfe9b7af8d3d97d9aaeb952ec`，固定 ZIP 哈希未变。共享工作树当时可见其他任务的未提交变化 `tools/prepare_complex_batch_b.py` 与 `tests/test_complex_batch_staging.py`；本轮只读观察，未修改或清理它们。

## 交付文件

- `a24-b-c01-machine-record.json`：机器可读审计记录。
- `REPORT.md`：本报告。
- `work/a24-b-c01-integration-20261022/audit_a24_b_c01.py`：可复现离线审计脚本。
- `work/a24-b-c01-integration-20261022/a24-source/`：固定 A24 本地副本。
- `work/a24-b-c01-integration-20261022/b-package/`：固定 B 包解压副本。

机器结果和本报告都只表示本次离线兼容性与缺口审计，不表示独立人工验收、原 A 所有者接收、平台保存或业务完成。
