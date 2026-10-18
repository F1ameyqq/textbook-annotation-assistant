# A06：B 原生离线包只读接收与可导入交接

2026-10-18。将用户转来的 `PENDING_A` 落实为 A 侧接收工作；与 I01-A 固定桩集成并行，二者不能互相代替。依据[既有接收记录](../b-handoff-receipt-2026-10-17.md)、[最小交接清单](../b-minimal-integration-handoff-2026-10-17.md)；独立验收见 [A06-independent-review](A06-independent-review.md)。本任务不安排或验收 B 的内部研发，不把 A 的接口实现写成双方共同确认。

## 固定基线、输入与写入范围

- A 集成基线：`a1c3c3b2d452ecbdf5c57a8b7372e7d53de0f8d8`，调度已固定并释放执行；执行者不得自行取浮动 HEAD。独立分支使用 `codex/` 前缀，执行目录 `D:/1800-worktrees/a06`。
- B 包提交：`0e5434f0ecf57152ec03f66bd7d0cf48b7c0700f`；包说明中的代码基线 `c3cc2df7a0be24c125c83681c0499c0d328d78f6`。本任务只使用已存在的本地包，不 fetch、拉取或借最新分支补对象。
- 输入：`D:/1800/.local/stages/coordinator/b-handoff-0e5434f/B-46007447-Q16-offline-HOLD-2026-10-17.zip`；SHA256 `b2bed674f87cde7fb2df4fdf31dec9ede08f494fc6190f654abda51dd4dae89d`，11,681,712 bytes。内含 104 成员，即 103 清单文件与 manifest；manifest SHA256 `3952a42e5ea966a0ec039564c71dc1db242c061af807aa730ac1f7f015e8189f`。
- 包格式 `b-handoff-package-trial/0.1`，固定 run `pipeline-run-0a2c03e193694ef88953f3ca08b8cde2`。保留原 ZIP 原字节，只在自有新副本生成测试变体；不以重新导出或重建 B 流水线替换输入。
- 唯一产品写入范围：新建 `src/annotation/source/b_handoff/`、`examples/a06/`、`tests/test_a06*.py`、`tests/fixtures/a06/`；报告 `docs/tasks/A06-execution-report.md`，证据 `docs/evidence/A06/`。可移植 API/消费说明放 `examples/a06/README.md`，不扩大文档白名单。
- 公共 contracts、native、delivery、runtime、pins、根依赖以及其他现有实现只读；不得改父包入口来绕过范围。使用既有依赖，不安装、不调用网络或模型。所有 Git 命令带 `-c core.longpaths=true`，并禁用 partial-clone 的惰性联网取对象；本地对象缺失则报告，不联网补齐。

只消费 JSON、清单和资源字节，不导入或执行包内/B 侧脚本，不打开或查询任何 SQLite。不得访问平台、profile、凭据，不能向 B/其他任务发消息、推送或书级送审。原包内数据库和脚本可以作为清单成员核对字节，不能据此声称其内部语义已核验。

## 接收能力与明确拒绝

提供可导入的 `annotation.source.b_handoff` 公共入口及调用它的固定 CLI/消费者；入口、参数、输出结构和错误码写入说明。输出为 A 的只读诊断与接收回执，包含输入身份、采用版本、可定位问题和支持边界；不输出 C01 可执行交换包、ApplyPlan、PASS 或平台资格。

| 输入版本/位置 | 本轮处理 |
|---|---|
| 当前 Evidence `b-evidence-trial/0.3`，Graph `b-graph-trial/0.7`，Check `b-check-trial/0.7` | 仅固定包的当前关系可只读诊断；保持 `HOLD`、`business_acceptance=false`、未核准内容及实际范围。 |
| Graph/Check 0.4、0.5，处于已绑定历史 archive | `ARCHIVE_ONLY`；保留原身份、引用、未选候选和历史语义，不提升为当前检查或运行依据。 |
| Graph/Check 0.4、0.5 被当作当前顶层输入 | 明确拒绝，诊断 `ARCHIVE_ONLY_NOT_CURRENT`；不能因为内部对象可读而接受为当前版本。 |
| Graph/Check 0.6 | 当前收到的包没有完整 G06/Check06 正样例；`UNSUPPORTED_VERSION`，不猜测字段兼容、不声称支持或已验收。 |
| 其他未注册版本或不支持的入口形状 | 明确拒绝，返回版本和路径；不按字段相似度降级为 0.5/0.7。 |

现存历史未解析引用必须原样呈现：`artifact_id=b-evidence-18e2d1ee2a22288f585513f0`、revision `1`、content_hash `a2e53e1fc5ddee5ed0eaa57102af074a9b20b7815aa065116464446b9be7a8da`。对应输出同时标记 `UNRESOLVED_HISTORY_REFERENCE` 与 `UNCONFIRMED_REQUIREDNESS`。不能默认它可选、伪造 envelope/kind 或共同确认；诊断读取可以返回当前可解释材料及 HOLD，但完整语义闭包、公共格式资格仍不成立。此已知缺口不要求 B 重做或执行者自行补造对象。

## 主入口必须实际核对的内容

1. 包和清单身份、成员路径/重复、长度与 SHA；解包或读取限制在自有包根，不能跟随路径越界。使用资源时核对其声明身份、SHA、尺寸和实际可解码性；原图与裁片、viewer173 与 resource173 分开，不凭相同数字合并。
2. wrapper 与 `payload.result` 各自的版本和身份；文件 SHA 与 B 格式规范化 JSON 的 content_hash 分别独立核对，不能只验证 manifest 或执行 B helper 就称接收通过。引用按真实形状区分产物、资产、裁片及嵌入记录，不补造 C01 ArtifactRef 必填字段。
3. 当前 E/G/Check、pipeline final outputs 与实际 wrapper/result 精确绑定，Check 指向当前 Graph；保留真实 run 绑定方法和各层 scope。包的五页范围与 graph 的相邻答案前缀不能被统一覆盖，不把 PARTIAL/FAILED 或旧 Check 当当前依据。
4. 来源层、活动 `content_fragments`、plain/LaTeX runs、`render_regions`、`content_fragment_ids` 和 typed 答案区域分别消费。保留有 `source_region` 而旧 `source_fragment_ids` 为空的 REGION_DRAFT；按 Unicode 码点、左闭右开解释字符区间，不套 UTF-16 下标。不能按 OCR/裁片数量推平台框，不新增或核准文字。
5. 保留 0.4 的混合历史区域表示、0.5 的候选/风险和原 core/检查复用依据；它们只作为档案读取。当前 0.7 的活动内容与未选历史候选分开，不用“旧 core 不变”覆盖当前修订语义。不能无损解释的字段/关系必须列为不支持或未确认，不静默丢弃后宣称兼容。
6. 正常包的 34 题候选、66 答案候选、127 项问题用于固定输入核对，不是功能测试数或质量成绩。READY 仅为流水线阶段状态，HOLD 和未核准标记持续有效。

不新增 B 算法/内容准确率、整章覆盖、人工签核、任意规模性能、平台/OCR 或联合业务标准。A03 接受与 I01-A 的合成三路径不改变本任务的接收边界。

## 四个完整入口样例与版本矩阵

只要求以下四个固定主入口样例，以及上述明确版本分派的窄测试；全部由 A 入口处理，不能以 helper 自测代替。

| 样例 | 实际预期 |
|---|---|
| 原 ZIP | 可返回只读诊断与 HOLD；已知历史引用两项状态明确保留，C01 执行资格为 false。 |
| 坏资源 TEST_VARIANT | 确定性变体经完整入口到达资源核验并拒绝，定位文件及具体原因。 |
| 陈旧 Check TEST_VARIANT | 同一固定输入的当前 Graph/Check 绑定不一致，完整入口拒绝陈旧关系，不借旧检查放行。 |
| 未知版本 TEST_VARIANT | 完整入口到达版本分派并明确拒绝，不能按旧格式解释。 |

变体在新目录生成，保留配方、变动路径、前后身份及预期到达层。重算不属于故意破坏点的 ZIP/manifest 成员摘要、对象自摘要及必要外层绑定，使三个变体分别命中资源、当前引用、版本门；不能都停在同一个最外层 hash 错误。原 ZIP 与原 B 产物永不改写。测试变体只称 `TEST_VARIANT`，不能伪装成 B 的真实产物。0.4/0.5 顶层拒绝、archive-only 区分和 0.6 `UNSUPPORTED_VERSION` 另列分派结果，不要求为这些版本新造真实业务正包或执行旧流水线。

## 可导入交接与交付

`examples/a06/README.md` 给出确切 A 基线/候选、包身份、依赖、最短导入与完整消费者命令、支持/拒绝矩阵、输出字段、正常诊断和失败回执。路径以显式输入参数及包内相对路径工作，不依赖作者个人目录或 B 本机 UI/head。记录实际 Python 版本、公共模块 `__file__` 与源码摘要，证明调用的是固定 A 代码。

说明同时给出已有公共合同 `annotation.contracts` 的实际导入和 `load_bundle/validate_bundle/schema/ContractError` 入口，以及 `examples/contracts/consume.py` 的正常/异常/UNKNOWN 固定样例调用、确切版本和限制；只引用/使用现有文件，不修改它们。明确 `1.0.0-a-proposal`/`c01-exchange-1` 公共消费者与本次 B 原生诊断消费者的区别，不把本地可导入当作 B 已取得、已兼容或共同采用。

报告和 SHA/长度清单覆盖代码、配方、输入身份、四个入口原始 argv/cwd/退出码/stdout/stderr、版本分派结果、输出/限制及自有进程释放；大原包按固定本地路径与摘要引用，不复制凭据或改旧证据。交付确切提交，不自行记 ACCEPTED/INTEGRATED，不修改主目录 state/Git 索引；主调度核对后送独立验收。

最多两个冻结实现候选。首候选失败保留现场和已运行记录；仅在调度续派后允许一次有界纠正为第二、最终候选。第二候选失败固定交接，不改后重跑，不新增第三包或借新任务名恢复额度。不得通过放宽上述预期、改输入身份或扩大标准处理失败。

建议将 `PENDING_A` 细分记录为公共 API 已提供、包字节已核验、原生诊断实现/独立验收待定、版本拒绝已验证与否、历史引用必要性未确认、共同映射未确认、联合业务未验收；具体状态由调度填写。有限只读/HOLD 接收通过不能直接改为 B 可执行接入、联合业务通过或材料已发送给 B。
