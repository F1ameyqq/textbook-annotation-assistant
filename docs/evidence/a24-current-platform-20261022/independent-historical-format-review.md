# A24 历史下载 JSONL 独立审计

## 结论

`HISTORICAL_EXPORT_FORMAT_CONFIRMED_CURRENT_DENOMINATOR_AND_CODEC_HOLD`

已确认普通 Downloads 中存在一份字节固定的历史 JSONL：11,625 bytes，SHA-256 为 `02a8aaae2bc907649a03f3676806a02da103e0b487fb43f7e187b29a67fc7a8c`。私有复制与原文件逐字节一致，`discovery.json` 记录的源文件时间为 2026-10-16；因此它能证明历史实际格式和19条历史记录存在，不能证明2026-10-22本次导出成功、当前平台状态或当前完整分母。

本报告只发布结构统计和摘要，不复制任何题干、选项、答案、提示或其他正文。

## 原件与解析

| 项目 | 结果 |
|---|---|
| 历史 JSONL | 11,625 bytes；SHA-256 `02a8aaae2bc907649a03f3676806a02da103e0b487fb43f7e187b29a67fc7a8c` |
| 私有复制 | 与普通 Downloads 原件字节一致 |
| `discovery.json` | SHA-256 `48bd3388838b39ca71688dffd763a8504035cf22ff3b2fe447d6d7bfface1766` |
| 编码/换行 | UTF-8，无 BOM；18个 LF，无末尾换行 |
| 记录 | 19个非空物理行；19条均为 object/dict |
| JSON 键 | 无行内重复键；19条具有完全相同的19个顶层键 |
| 重复 | 无重复整条记录；无重复 `tixu` 或 `tixu+tihao` 组合 |

19个顶层键为：`analysis`、`answer`、`city`、`comment`、`district`、`doc_id`、`grade`、`option`、`paper_type`、`province`、`question`、`step`、`subject`、`term`、`tihao`、`tishi`、`title`、`tixu`、`year`。

## 记录身份与重复边界

- `doc_id`：19条均存在，但19条全空。
- `tihao`：19条均存在，但19条全空。
- `tixu`：19个唯一整数，恰为1–19；无重复。
- 没有 `platform_question_id`，也没有当前目录/catalog 对 `tixu` 的绑定。

因此可以用“原始行 SHA-256 + 文件 SHA-256 + 行号”固定这19条历史记录的字节身份，也可以确认不存在整行重复；但不能把 `tixu` 1–19升级成平台稳定题 ID，不能把行号或题序当作跨快照身份。机器回执保存了19个逐行 SHA-256，没有公开正文。

## 五区与 extra 的可保全范围

历史字段能提供候选映射，但目前只证明结构，不证明业务语义：

| 目标区 | 历史字段候选 | 结构观察 | 当前结论 |
|---|---|---|---|
| question | `question` | 19条均为非空字符串 | 原始值可由冻结原件保全 |
| choice | `option` | 19条均为 list；5条非空、14条空；共18个字符串元素 | 是否对应 choice 及空列表是否业务完整均未资格化 |
| answer | `answer` | 19条均为非空字符串 | 原始值可由冻结原件保全 |
| analysis | `analysis` | 19条均为空字符串 | 字段存在，但不能证明解析正文完整 |
| knowledge_point | `tishi` | 19条均为非空字符串 | `tishi` 是否等同知识点没有证据绑定 |

冻结的原始11,625字节可以逐字保全全部19个顶层字段。除五区候选外，还有14个字段必须作为原始业务字段保留。当前 natural codec 解码结果只保存投影字段和 `raw_record_hash`，不会自动携带所有原始 extra 值；若适配器只生成哈希而未保留 raw record/extra，不能称为无损旧题保全。

## wire natural codec 准入

只读测试绑定到 `wire.py` SHA-256 `64885d7ac5d91d5351231a803ffeab4badb1b55528057a6abde1c03ac6131116`。

当前 `A24NaturalExportCodec/v1` 要求六类投影字段：`platform_question_id`、`question_type`、`parts`、`wire_zones`、`question_info`、`rect_ids`。历史19键中这六个直接字段全部不存在。

- 用实际未资格化 route 状态测试：拒绝，错误码 `NATURAL_EXPORT_AUTHORITY_UNBOUND`。
- 为了越过第一道门、仅检查结构，使用明确标记为非权威的合成 qualification 和合成 inventory：仍拒绝，错误码 `EXPORT_QUESTION_COVERAGE`。

第二项只是负向结构探针，不是资格材料。不能借合成 metadata、合成 ID 或字段猜测把历史文件提升为自然 codec 已准入。

## 为什么19条不能与当前可见22标签相减

历史 JSONL 来自2026-10-16；当前 DOM 观察来自2026-10-22。前者没有平台稳定题 ID，后者只有界面可见标签1–22，也没有 `platform_question_id`。两者没有同状态 catalog、成员集合或逐题身份绑定。

所以 `22 - 19 = 3` 只是算术差，不能推出“漏了3题”。差异也可能来自新增、历史导出不完整、目录/选择范围不同、折叠或加载范围、重新编号等。没有当前原始导出和权威 catalog 前，19与22都不能充当当前完整分母。

## 最终边界

- 历史实际格式与19条记录：`CONFIRMED`
- 当前导出成功：`UNPROVEN`
- 当前题目完整分母：`UNPROVEN`
- 五区完整性与 extra 无损 codec 投影：`UNPROVEN`
- natural codec 准入：`DENIED`
- `write_allowed=false`
- `successors=NOT_RUN`
- 审查成员浏览器、网络、API、模型、live authority 调用：0
- 共享 B 编辑：0

## 封存追加：当前 UI `04`/`06` 差量核查

新的当前观察汇总已固定为：

- `A24-current-platform-observations-20261022-v1.json`：7,181 bytes，SHA-256 `488a9902822f53a1b29f65cd7ee83637cc26fa2b236bb582c523b0ba6e06eeba`。
- `A24-current-platform-observations-20261022-v1.md`：5,321 bytes，SHA-256 `5e03f0b12832a6adda1990f5f46b836e43f47980dd81ff24251c1c1927c63ee9`。

它们是本次新的当前观察汇总；早先 `LIVE_NOT_CONNECTED` baseline 仍只作历史对照。

原始输入边界：

- `04-q22-selected-dom-snapshot.txt`：20,404 bytes，SHA-256 `41769485628f1b2ae8f0b8a24adcc30fd9bcdc835553cb0ab48b010f5883350c`，表示为后续选中第22题且菜单展开时的 DOM 文本；HTTP 状态未知，也不是 `03` 的同刻原始 DOM。
- `06-q22-visible-rects-dom-extract.json`：13,121 bytes，SHA-256 `4e9f7718124c12489923c6fcc841ece990edba4ae1afb90d71e21666edbf9b8c`，表示为当前两页可见 DOM 框层的结构化派生值。

独立核查支持以下有限事实：当前可见第22题位于题目页14、答案页173；题目侧有1个标签22的 `question-type history-rect locked` 层，答案页173上有24个可见历史答案层，其中 `rectIndex=7` 的层标签为22。

必须保留以下否定边界：

- 24个答案层是答案页173当前可见的全部历史答案层，不能说成24个都属于第22题。
- 右侧“当前题目23”的题目框、答案、选项、解析、知识点计数均为0，只描述新编辑槽23，不能推出旧题22无框。
- `layerRect` 和 CSS `left/top/width/height` 是浏览器可见层几何，不是绑定原始图像资产与尺寸的原图 bbox。
- DOM `data-key`、`rectIndex` 是当前界面标识，未证明为 canonical server ID。
- `1 + 24 = 25` 只是当前题目页14与答案页173的可见 DOM 层总数，不是第22题完整框分母，更不是整书框分母。
- `/qieti/jsonPreview` 只显示本地文件上传面板；没有上传文件，也没有可见的服务端当前书籍 JSON。
- “导出整套书籍JSON”只尝试一次，等待结果因控制会话超时而未知；未发现 fresh 匹配下载，也未重复触发。历史19条 JSONL 继续只证明历史字节，不能替代本次 fresh 导出。

差量结论：`04`/`06` 将“第22题有可见历史题框及标签22答案框”从未知提升为当前 UI 可见事实，但不提升原图坐标、canonical ID、全题/全书框分母、五区正文、extra 无损投影或 fresh 导出。原结论与 `write_allowed=false` 均不变。
