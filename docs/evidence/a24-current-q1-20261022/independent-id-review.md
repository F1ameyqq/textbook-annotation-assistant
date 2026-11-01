# A24 当前 Q1 长 ID 跨源关联证据结论

日期：2026-10-22（Asia/Shanghai）

## 结论

`1792064001811` 可升级为 **同书、同目录节点、跨日跨源强一致的目录节点 ID 候选**，足以支持只读分析中把当前活动树节点与归档解析目录节点关联起来；目前仍不能称为平台 canonical `question_id`，也不能据此开放写入。

## 两侧证据

### 归档解析侧

- 文件：`docs/evidence/A24/revisions/current-context-r1/live-delivery/raw/current-state.json`
- 232,913 bytes；SHA-256 `640aaabe023c1e96e24ac3b1b002c8b9e7c045ed7b075a8777377a8ae9ba5775`
- 运行时间：2026-10-21 16:06:13 至 16:06:27（北京时间）。
- scope：`CURRENT_OFFICIAL_CONTEXT_SOURCE_AND_FIRST_SAVE_PREPARATION_READONLY`
- source plan：`LEGACY_DB`、`EXPLICIT_SOURCE_FIELD`；书籍绑定为 `46007447`，returned file ID 标记为匹配目标。
- `/target/questions/0/id`：`1792064001811`
- 同一节点 `raw_node_fields`：`id=1792064001811`、`isQuestion=true`、`label=1`、`order_in_level=1`
- 边界：`READONLY_REVIEW_WITH_GAPS`、inventory `PARTIAL`、content `UNKNOWN`、production/write eligible 均为 false、business writes 为 0；`raw_directory_tree_is_full_response_body=false`。

### 当前 DOM 侧

- 文件：`20-v6-current-q1-tree-dom-attrs.json`
- 340 bytes；SHA-256 `ddf4251950bc3ef076416e3a677a18d378890dd251a94d33f062a431d838a770`
- collectedAt：`2026-10-22 Asia/Shanghai`，源文件没有更精确的采集时刻。
- 活动节点：class 含 `is-current`，文本 `1插题`，`dataKey=1792064001811`。
- v6 公共绑定文件同时记录：book `46007447`、visible sequence `1/22`、活动标签 `1 插题`；其自身仍声明该 `data-key` 尚未证明为 canonical question ID。

## 能证明什么

1. 两份独立来源在同一书籍 `46007447` 上，把长 ID `1792064001811` 指向标签/顺序为 1 的目录题节点。
2. 当前 DOM 键不是由 printed label、`importShitiID`、行号或内容哈希推导出来；它与前一日归档解析出的节点 `id` 逐字相同，因此排除了单纯“同号 1”误连。
3. 在只读证据图中，可建立：`current active DOM tree node` → `archived parsed directory question node` 的强候选关联。

## 不能证明什么

1. 不能证明该字段就是写接口接受的 canonical `question_id`；尚无写接口 schema、成功保存或保存后回读。
2. 不能证明当前结构化 question/option/answer 已由服务器按此 ID 返回；当前 preview 仍为 `UNREAD`，像素转写不是 server raw。
3. 不能把 2026-10-21 的 `current-state.json` 当作 2026-10-22 的 fresh HTTP 响应；它是固定归档证据，且自报存在 gaps。
4. 不能证明此 ID 在其他书籍、其他版本或未来长期保持全局唯一和永久稳定。
5. 不能把短标签 `1`、历史 `importShitiID=1` 或当前编辑槽位 `23` 等同于该长 ID。

## 建议状态

`DIRECTORY_NODE_ID_CROSS_SOURCE_CORROBORATED / CANONICAL_QUESTION_ID_UNPROVEN / WRITE_HOLD`

本次没有读取 authentication 内容、没有公开凭据字段、没有调用任何端点，也没有执行平台写入。
