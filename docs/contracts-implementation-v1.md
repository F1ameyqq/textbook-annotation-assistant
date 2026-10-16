# C01 合同实现 v1 提案

合同版本 `1.0.0-a-proposal`，交换文件版本 `c01-exchange-1`，固定样例版本 `c01-fixtures-1`。这是 A 内部实现提案，交付等待独立验收及双方接口确认。语义来源：[contracts-v1](contracts-v1.md)、[architecture](architecture.md)、[C01 任务单](tasks/C01-contracts-implementation.md)。本文不改变上述设计文件，不声称 B 已采用。

## 安装与最短运行

在本 checkout 根目录执行（已实测 Python 3.9.13）：

```powershell
python -m pip install -e . --no-build-isolation
python -m annotation.contracts validate tests/fixtures/contracts/normal/input.json
python examples/contracts/consume.py tests/fixtures/contracts/normal
python -m unittest discover -s tests -p 'test_contracts*.py' -v
```

运行依赖固定为 Pydantic 2.12.5；其核心轮子已支持本次 Python 3.9.13 环境。打包使用 setuptools，测试使用标准库 unittest，不需 pytest、浏览器、数据库或模型。安装需要依赖已存在或可取得依赖；离线运行本身不访问网络。`--no-build-isolation` 使用当前 Python 的 setuptools。需要隔离环境时可先 `python -m venv .venv`，再用该环境 Python 安装。

`python -m annotation.contracts schema` 向 stdout 输出从类型自动生成的 JSON Schema；没有第二份手写 schema。Windows PowerShell 5 重定向可能产生 UTF-16，保存 schema 时可用 Python 捕获 stdout 并以 UTF-8 写出。JSON Schema 定义结构，完整引用/摘要/安全状态仍须通过公共验证入口。

## 单一权威与公共 API

唯一结构定义为 [models.py](../src/annotation/contracts/models.py)，公共入口为 [annotation.contracts](../src/annotation/contracts/__init__.py)。九类产物均为公共 Python 类型，`ExchangeBundle` 持有产物、政策和证据注册表。用 discriminator `kind` 选择 payload 类型，未知字段被拒绝；运行状态仅在 BatchReport 的 runtime 汇总视图表达，不靠给算法 payload 填写一个 status 驱动执行。

```python
from pathlib import Path
from annotation.contracts import (
    load_bundle, validate_bundle, artifact_ref, assert_plan_ready,
    assert_patch_base, write_bundle, schema, seal_artifact, seal_policy,
)

bundle = load_bundle(Path("copied-fixture/input.json"))
plan = next(a for a in bundle.artifacts if a.kind == "ApplyPlan")
snapshot = next(a for a in bundle.artifacts if a.kind == "PlatformSnapshot")
# Checks an explicit snapshot; does not execute or grant platform write authority.
eligible = assert_plan_ready(bundle, artifact_ref(plan), artifact_ref(snapshot))
write_bundle(bundle, Path("copied-fixture/new-input.json"))  # same resources; exclusive create
```

`load_bundle` 默认验证资源存在、SHA-256 和原图头部尺寸，路径相对交换文件父目录解析，与 cwd 无关。`validate_bundle(data, asset_root=...)` 接受 dict 或模型并返回重新校验的模型；`asset_root=None` 只跳过文件字节检查，仍校验全部引用和语义。CLI 的 `--structure-only` 对应此行为，输出明确 `resources_verified=false`，不得作为资源完整性证据。

`seal_artifact`/`seal_policy` 只对结构合法的单个对象规范化并计算摘要，**不证明整个依赖闭合或计划资格**。直接实例化某个模型也只保证结构。消费者交接必须调用 `load_bundle` 或 `validate_bundle`。`ContractError.issues` 含 `path/code/message`；CLI 合法退出 0，非法退出 1，错误输出到 stderr。`write_bundle` 校验后以 `x` 模式新建文件，不创建父目录、不复制资源；示例消费者演示自包含资源复制。

模型冻结字段赋值，但 Python 嵌套 list/dict 本身仍可变；公开语义校验入口会重新序列化并解析，捕获未重新封签的嵌套修改。不要把模型对象用作跨模块共享可变状态。修改应创建新版本。

## 摘要与引用

规则命名为 C01 canonical-json-1，具体代码只有 [integrity.py](../src/annotation/contracts/integrity.py) 一处：

1. 按 Pydantic 模型转成 JSON 值（包括浮点坐标规范化）；只排除**当前对象顶层** `content_hash`，嵌套引用摘要仍参与计算。
2. `json.dumps(..., ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)`，UTF-8 编码，无 BOM，无尾换行，再计算 SHA-256 小写十六进制。
3. 对象键排序，列表顺序保留；不进行 Unicode NFC 归一化、时区字符串重写或资源路径重写。数值使用已实测 Python 3.9 的 JSON 浮点表示（例如坐标 `5` 规范化为 `5.0`）。这不是声称符合 RFC 8785 的跨语言数字规范；非 Python 消费者须用固定样例对照相同字节规则。
4. 原图/证据资源摘要针对文件原始字节。改动依赖摘要、时间、配置或政策都会改变产物摘要；不存在 content_hash 自指。

ArtifactRef 固定包含 `artifact_id/revision/kind/content_hash`；PolicyRef 包含 `policy_id/revision/content_hash`。索引按 ID+revision，重复不可变版本被拒绝；同 ID 不得改变 kind/book/scope。payload 中每个产物引用都必须列在 `input_refs`，每个政策引用都必须列在 `producer.policy_versions`；缺失、错 hash、错 kind、跨书/跨范围和循环依赖均拒绝。旧修订可与新修订共存，不按“最大 revision”暗中替换引用。

同一组交换产物允许不同 run_id，以支持旧回执/人工修改来源；book/scope 必须一致。跨范围共享/跨书关联尚需新提案，当前应拆包，不能绕过 scope 约束。

## 身份、原图与证据

内部 ID 为以字母起始的稳定字符串，印刷题号与平台题序仅放 `Question.external_refs`。book/target 是外部标识，允许如 `46007447` 的数字字符串。格式不能从数学上证明 ID 稳定，生产者仍须维护实体身份；本实现检查重复、错引用和父子循环，固定样例证明重复印刷“1”不冲突。

每个 bbox 保存 `ImageBinding(asset_id,width,height,sha256)`，必须精确匹配被依赖 SourceBundle 的资产。坐标为原图像素 `[x1,y1,x2,y2]` 半开范围；有限数值、正面积和图像边界在结构层校验。不会静默裁边。历史异常原数据可作为带质量标记的 `history.resource` 保留，不能冒充合法通用框。

`crop_transform` 保存缩放、偏移、旋转、补边和处理图尺寸，并带 invertible 标记；C01 保存合同，不计算几何回投或证明变换准确。示例给出可手工核算的缩放/偏移关系；几何实现属于后续任务。EvidenceBundle 的全文页线索独立列出 ASSIGNED/EXCLUDED/UNASSIGNED、依据和来源，来源可标共享识别证据，不会冒充独立识别成绩。

SourceBundle 的 acquired 列表必须等于实际资产清单，并为 expected 子集；metadata_page_count 不表示已取得页数。独立 `scope_manifest` 可包含未进入图谱的题目，BatchReport 必须保留该清单及异常/跳过项。PASS 覆盖不能省略已检查页的任何线索，不能含未归属线索或把未入图谱区域标为已归属。

资源仅接受 POSIX 相对路径，拒绝绝对路径、盘符、UNC、反斜杠、`..`、空/`.` 分量、Windows ADS/保留设备名和特殊字符；实际解析后检查 symlink/junction 是否越出包根。PNG/JPEG/PGM 验证头部尺寸，非完整图像解码器；摘要绑定实际字节。样例目录的 `.gitattributes` 对 assets 禁用文本换行转换，避免 Windows core.autocrlf 改动 PGM/证据文本而破坏摘要。证据注册表为交换包伴随索引，含资源摘要及 SYNTHETIC/OBSERVED，观察产物不得引用模拟证据或模拟依赖。凭据/profile 没有合同字段，不能通过额外顶层字段传入；文本内容是否含敏感信息仍由生产者脱敏。

## 检查、政策与计划

CheckReport 必须保存 stage、subject、精确 graph/policy/snapshot/receipt 引用、范围、逐项结果和理由。PRE_APPLY 必需 `source_integrity/structure/answer_matching/coverage/policy`；TARGET 必需 `target_version/authorized_scope/capabilities/policy`；POST_APPLY 必需 `frame_structure/final_content`。PASS 要求所有所列检查 PASS、覆盖闭合且无阻断问题。检查结论的业务真实性由 quality/独立验收负责，合同无法从一段理由文字证明内容正确。

建议策略为固定策略 ID 加次数/成本上限，不接收浏览器脚本或自由文本执行指令。RETRY 至少需要一个仍有次数的自动补救策略；UNKNOWN 的策略只能交给 reconcile 流程处理，不能因 RETRY 枚举就重发保存。

READY 计划必须绑定不同 stage 的 PRE_APPLY/TARGET 两份 PASS，同图谱同政策，目标检查与计划快照一致。检查资格时调用者还须传入**当前**快照；当前 revision/hash 变化使旧计划失效。能力需 VERIFIED、有证据、适用于同一个 snapshot.platform_version；frame_readback 始终必需，PERSISTENT 还需 persistent_draft，同会话方案需 same_session_handoff。该新增能力及 platform_version 字段是具体实现提案。

诊断 `BLOCKED` 计划必须引用具体未通过检查和 issue，actions 为空；其回执只能 NOT_EXECUTED。它方便异常组也保存完整链，不代表 planner 已运行或可执行。Action 仅支持 CREATE_FRAMES/UPDATE_FRAMES；不包含最终提交动作，`final_submission=HUMAN_ONLY`。动作来源必须属于目标题的片段/共享材料/选定答案闭包，不能使用别题实体。UPDATE 必须引用同图谱旧修订的 ExecutionReceipt、对应题有 APPLIED 基线，且 frame_update 能力已验证；实际差量能力和操作投影仍待 delivery 实现。

默认 [Usense 政策](../config/policies/usense-v1-proposal.json) 保持普通选择题 W 独立/合并 UNRESOLVED；受影响题目不能输出前置/目标 PASS 或 READY。角色与平台映射位于政策层，通用角色只含 stem/option/answer/explanation/shared_material。A05 框保存/读回记录 `BOUNDED_A05_OBSERVED`，OCR 为 UNVERIFIED，不能互相代替。未涉及 option 的 free_response/combination 模拟样例可继续检查。

额外普通选择题样例只使用 [synthetic-choice-separate](../config/policies/synthetic-choice-separate.json) 的 SYNTHETIC_ASSUMPTION，限定 SYNTHETIC_ONLY+SIMULATED。SEPARATE 是人为假设，不能变成平台写入资格或业务定论。平台模式还要求 JOINT_CONFIRMED 政策及 OBSERVED 链，C01 没有创建这种真实执行产物。

## 回执、批次与 patch

动作回执一一覆盖计划动作。APPLIED 需要 MATCH、后置证据、读回资源和平台 ID，next_step=POSTCHECK；NOT_APPLIED 需要 ABSENT、明确读回证据，next_step=RECHECK_TARGET；UNKNOWN 必须 INDETERMINATE/RECONCILE，整份回执 PAUSE_RECONCILE，保留未决 issue。三者均 `replay_allowed=false`，即使明确未生效也先重查目标。这里验证证据存在和状态一致，不实施写入前 intent 持久化、平台证据比对或去重数据库。

存在同书 UNKNOWN 回执时 `assert_plan_ready` 拒绝任何计划（包括换 action ID），BatchReport 必须 NEEDS_RECONCILIATION，所有 UNKNOWN 动作对应题都保持 UNKNOWN，不能标内容 VERIFIED。NOT_APPLIED 对应题也不能 VERIFIED。C01 不实现 ReconciliationResult、解暂停或恢复状态机；未知历史未被解决前资格检查会保持关闭，后续 A03 应增加显式解决证据而不是删记录解锁。依赖包只能约束所提供事实，调用者不得省略真实未决日志来伪造闭包；跨进程锁与实时完整性属于 runtime。

`COMPLETED` 必须提交 CONFIRMED（另有观察证据）、内容 VERIFIED、框检查 PASS、POST_APPLY PASS、全部范围题 VERIFIED、无未决事项。READY_FOR_SUBMISSION 同样要求全部质量检查通过但 submission_status=NOT_SUBMITTED。CONTENT_PENDING 与 AWAITING_HUMAN_SUBMIT_FOR_OCR 保持内容 PENDING，后者仍 NOT_SUBMITTED；unknown/异常不从分母删除。未知账单金额用 null，不能填零。固定样例的模型调用/费用确为 0，但真实模型质量、费用和人工效率未测。

ReviewPatch 指向精确 QuestionGraph 基线，变更保存 old/new 值及操作者/理由，result_revision 必须为基线+1，requires_recheck=true；拒绝不存在实体或 before 不匹配。`assert_patch_base` 额外核对调用者当前基线。C01 提案只支持 role、printed_number、selected_fragment_ids 三类变更，不提供 patch 应用/冲突迁移执行器；引用 patch 的结果图谱必须精确等于基线加声明变更，不能静默丢弃或夹带其他修改。重识别和 patch 混合派生需以后显式冲突合同，当前拒绝。样例手工构造旧图谱+patch+新图谱依赖链，再对新版本重新检查。不能复用旧图谱的检查或回执。

## 固定样例和失败复现

四组均自包含 `input.json/expected.json/assets/README.md`，所有业务输入及效果证据均为 SYNTHETIC。每组 12 产物：九种类型、三份阶段 CheckReport、两份不可变图谱修订。

| 样例 | 精确预期 | 覆盖的边界 |
|---|---|---|
| [normal](../tests/fixtures/contracts/normal/README.md) | 两份前置 PASS，模拟 APPLIED，READY_FOR_SUBMISSION / NOT_SUBMITTED / VERIFIED | 重复题号、跨页、多框、共享材料、裁片变换、patch后重查 |
| [exception](../tests/fixtures/contracts/exception/README.md) | EXCEPTION，BLOCKED，NOT_EXECUTED，NEEDS_REVIEW | W 未决、整题未进候选、UNASSIGNED全页线索、SKIPPED计入4题分母 |
| [unknown](../tests/fixtures/contracts/unknown/README.md) | UNKNOWN，RECONCILE，NEEDS_RECONCILIATION / PENDING | 模拟响应超时，效果可能已生效，禁止重播 |
| [choice-assumption](../tests/fixtures/contracts/choice-assumption/README.md) | 模拟选择题 PASS，NOT_SUBMITTED | 显式模拟政策假设，不构成 W 规则确认 |

从其他目录也可运行：先用 `Copy-Item -Recurse <checkout>/tests/fixtures/contracts/normal <destination>/normal`，再用安装本包的 Python 执行 `python <checkout>/examples/contracts/consume.py <destination>/normal --roundtrip <destination>/output/input.json`。消费者只读取公共 API，不读取 recognition/assembly 等私有结构。所有固定值与摘要精确比较；没有算法成绩或真实平台成绩。

生成样例：`python examples/contracts/build_fixtures.py`，固定时间和资源字节保证重生成可重复。此显式生成器只重建指定样例文件，业务 writer 保持不可覆盖。失败用例全部由 unittest 临时构造，不污染固定输入；最短失败复现例如：

```powershell
python -m unittest discover -s tests -p 'test_contracts*.py' -k only_one_pass -v
python -m unittest discover -s tests -p 'test_contracts*.py' -k current_target_change -v
python -m unittest discover -s tests -p 'test_contracts*.py' -k unknown -v
python -m unittest discover -s tests -p 'test_contracts*.py' -k resource_paths -v
```

这些命令退出 0 表示测试观察到预期拒绝。CLI 非零失败及定位输出由 `test_cli_rejects_invalid_exchange_with_nonzero_exit_and_location` 实测。

## 待双方确认及后续边界

- 本版本信封补充 ExchangeBundle 证据注册表、政策精确引用、scope_manifest 独立清单、subject分阶段指向和必需检查集合；采用前须共同确认必填字段、跨范围依赖及迁移规则。
- canonical-json-1 的跨语言数字/Unicode规则、内部 ID 生成与重识别对应策略待确认；消费者先以固定样例校验兼容性。
- W 独立/合并继续未决，七选五/组合选项投影、父子与平台分组、裁片回投准确性需后续合同和算法联调。
- BLOCKED/NOT_EXECUTED 诊断链、PLATFORM 资格门、同会话能力、新增platform_version、patch允许字段、空范围是否需要零分母报告及 reconciliation 产物均为实现提案；当前 scope 至少一题。
- 原图头部解析不代替完整图像可读性检查，报告理由不代替独立内容核验；固定样例不测试 OCR、真实 executor、原子持久化、登录、恢复、B算法或自动标注完整产品。

B 可通过 `annotation.contracts` 的类型与 load/validate/seal/schema API 消费这份提案；先提供产物版本、错误位置和固定输入进行接口反馈。A 内部测试通过与 B 是否确认采用分别记录，未收到 B 确认时保持待共同确认。
