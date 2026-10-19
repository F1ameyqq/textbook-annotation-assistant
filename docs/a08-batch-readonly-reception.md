# A08 固定批次只读接收器

`annotation.source.b_batch` 只接收 B `a76e5a925fec76f20818dfdefa4145aa132ec8a8` 的固定 stage ZIP。版本 `a08-fixed-stage-readonly/0.1`。报告表示结构接收诊断，四例业务结论始终 HOLD。

支持的原件 SHA256 为 `b646fad9008e03e79a3dddfb4ead912d7ceadefbcee331c2e2af2415abf6f673`（1,440,149 bytes）。版本、身份、HOLD、结构检查先于最终固定 bytes 门；重封负例可以到达对应检查，任何变体都不能成功接收。成功必须同时满足成员原字节、原件 ZIP 及语义/结构门。

实际 ZIP 共 **24 成员**；外层清单 23 条，不含自身；内层清单 9 条，不含自身。任务正文的“23成员”与实际 ZIP 项数不同，输入登记的 24 项 raw 清单与原件一致。

## 公共入口

从本任务工作目录运行，使用现有 Python/Pillow，无需安装依赖：

```powershell
$env:GIT_NO_LAZY_FETCH='1'
$env:PYTHONPATH=(Join-Path (Get-Location) 'src')
$env:PYTHONIOENCODING='utf-8'
$env:PYTHONDONTWRITEBYTECODE='1'
python -m annotation.source.b_batch D:/1800/.local/stages/a08-inputs/B-46007447-Q4-Q9-Q16-next-batch-HOLD-2026-10-19.zip --priority-case q4-first-lesson --report examples/a08/new-reception.json
```

`--report` 只新建 UTF-8 JSON 文件，拒绝覆盖已有文件或输入。省略该参数时只写 UTF-8 stdout。退出码：0 为 `RECEIVED_READONLY_HOLD`，2 为拒收，3 为报告写入拒绝；参数语法错误由 argparse 返回 2。输出含实际 `layer/code/path/detail`。

```python
from annotation.source.b_batch import BatchReceptionError, receive_package

try:
    report = receive_package(package_path, priority_case="q4-first-lesson")
except BatchReceptionError as error:
    rejection = error.as_dict()
```

API 只读 ZIP，不写文件，不接收任何审批或 Q1 政策参数。返回独立的 JSON-compatible 字典。优先案例只支持 `q4-first-lesson`。报告保留完整 `source_snapshot`，其中 `selected_answer_id` 是 **B 原声明**；A 诊断的关系状态为 `B_DECLARED_CANDIDATE_ONLY`，`a_selected_relation_created=false`。

## 字段及支持范围

| 对象 | 接收范围 | 未取得的资格 |
|---|---|---|
| 外层包 | `b-complex-batch-evidence-package/0.1`；大小、路径、覆盖、摘要 | 通用 B 包支持 |
| 批次 | 无 payload 包装的 `ComplexCaseBatchProposal` / `b-complex-batch-proposal/0.1` | 完整 G0.8/Check0.8/plan0.3 消费 |
| 案例 | 无独立 schema 字段；固定 4 身份/章节/课时 | 新 C01 或执行准入 |
| 第一课时 Q4 | 固定题答候选、原题干/4片段、`13`/`4.13`/[2,4) 原来源、5处原框（4题片段+1答案区） | 13 正确性、图形边界、内容/区域/逐题政策核准 |
| 小专题 Q4 | 3原片段、1 LaTeX run、裁边前后及 B 像素声明原值 | 题 ID/题答关系、重新裁图或像素证明 |
| Q9 | 33原片段、15呈现区、10个文字顺序、23个图像覆盖片段、跨页声明及未解决标志 | 题身份、未知 viewer 映射、内容/空间间隔核准 |
| Q16 | 17原片段、3行内容、11个 LaTeX runs 与原 run 索引 | 题身份、公式解析/语义/逐字核准 |

所有内容投影/续接/图形引用只保留已提供快照。报告 `external_objects.status=DECLARED_ONLY_EXTERNAL_NOT_LOADED`，完整 G/Check/plan 未读；不取得 Q15 原包，不执行 B 工具、DeepSeek 记录或历史测试，不借用其结果作为 A 验证。

逐资产原图按 SHA/尺寸解码核对，坐标按所属资产界限检查。`viewer-173` 是 resource index172、1148×1621；`resource-173` 是另一图、1145×1620、viewer 页码 null。图像整体存在不扩大 Q9 内容前缀范围。结构化 `latex_runs=0` 只说明 `content_fragments[].runs` 的指标为 0，Q9 `pieces` 等其他数学原文保持。

N01–N08 的 `support_matrix` 明确区分固定 stage 已做部分与 PENDING：N01 路由/版本、N02 证据模式、N03 顺序/几何保留、N04 runs/图形数据保留、N05 几何修订记录保留、N08 有限拒绝诊断；N06 核准与完整 Check、N07 PRE_APPLY/TARGET/计划/模拟均待后续任务。没有笼统全版本 SUPPORTED。

## 拒绝层及有限复现

| layer | 主要 code | 边界 |
|---|---|---|
| ZIP / JSON | UNSAFE_PATH / UNSUPPORTED_MEMBER / INVALID_JSON | 有界读取、无解包；重复键/非有限数拒绝 |
| MANIFEST | MEMBER_SIZE / MEMBER_DIGEST / MEMBER_COVERAGE | 内外覆盖、字节数、摘要 |
| VERSION | UNSUPPORTED_OUTER_SCHEMA / UNSUPPORTED_BATCH_VERSION | 实际声明 schema/kind |
| IDENTITY | CROSS_SCOPE_OR_CASE_IDENTITY / FABRICATED_QUESTION_OR_RELATION | 同号跨章节替换、无题案例造题 |
| SOURCE | ASSET_IDENTITY_CONFLICT / ASSET_DIGEST / ASSET_DIMENSIONS / BOX_OUTSIDE_ASSET | 独立 viewer/resource 身份与原图几何 |
| AUTHORIZATION | CASE_APPROVAL_ESCALATION | HOLD、UNVERIFIED、审批/排除转移及外加批准标记 |
| STRUCTURE | FIXED_COUNT_MISMATCH / MISSING_CONTINUATION / SOURCE_COVERAGE | 固定片段/呈现区/runs/续接库存 |
| SNAPSHOT_BINDING / BINDING | FROZEN_SNAPSHOT_CHANGED / CASE_BATCH_MISMATCH | 固定完整快照与批次/单例一致性 |
| FIXED_INPUT | RAW_MEMBER_BINDING / PACKAGE_BINDING | 所有前门后仍要求固定原件 bytes |

新字段/未支持形状也拒收，报告真实层；未声称对每个 helper 做了单独负测。业务 flags 如 `complete=true` 和结构续接解决声明按 B 原值保留，不能升级业务接受。

冻结候选后只运行有限 R0–R7：

```powershell
python tests/test_a08_reception.py --package D:/1800/.local/stages/a08-inputs/B-46007447-Q4-Q9-Q16-next-batch-HOLD-2026-10-19.zip --candidate 1 --evidence-dir docs/evidence/A08/execution/candidate-1
```

每候选原包一次、固定负例每个一次。驱动重封单例/批次/receipt/两层清单，不改产品 pins；R2 故意保留坏成员摘要。首次非预期失败保留，后续 NOT_RUN，最多两冻结候选。已有证据目录不能重用；独立验收在自己的固定检出和输出下复验。

所有报告都有 `actions` 八项零值；无目标、计划、新执行对象或模拟回执。接收不转移 Q1 审批，不恢复旧业务额度，不证明平台资格。作者只交付 `REVIEW_READY`，独立及调度结论另行形成。
