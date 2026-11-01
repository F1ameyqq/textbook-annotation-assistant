# A24 当前 DOM 实际输入适配核查

## 结论

**HOLD_DOM_FACTS_ONLY_CURRENT_SCHEMA_UNBOUND**

两份本次不可变 DOM 文本和一份随后存在的目录观察，已经足以确认当前页面上可见的书籍身份与状态，但不足以绑定 A24 的真实 HTTP/JSON schema。

保持：

- `schema_profile=None`
- `write_allowed=false`
- `successors=NOT_RUN`
- `complete` 未知
- export/route qualification 未执行
- B 固定版本 `29099c0` 未修改

没有把 DOM 抽取包装成 HTTP 200 响应，没有生成四响应集合，没有创建 profile、codec 或写入 proof。

## 本次实际输入

| 输入 | 字节 | SHA-256 | 表示与边界 |
|---|---:|---|---|
| `01-home-dom-snapshot.txt` | 767 | `f902276f8b6c047811a071a7e503bfd9438250100e5b9833afc9894c723ebbac` | 源声明 `DOM_SNAPSHOT_TEXT`；UTF-8 strict；无 BOM；28 行；`http_status=UNKNOWN` |
| `02-book-picker-dom-snapshot.txt` | 1326 | `3285ff730249bb554cb35f09abd7bbe5ad953fc2f2b1c955003efabaa46d6014` | 源声明 `DOM_SNAPSHOT_TEXT`；UTF-8 strict；无 BOM；41 行；`http_status=UNKNOWN` |
| `03-selected-book-directory-observation.json` | 1783 | `23a5e681ed9541acac4aa68ae1eda9829466a2cb17b8e6f86f82993fdf844e9b` | 源声明 `DOM_EXTRACTED_STRUCTURED_VALUES`；UTF-8 JSON；45 行；不是原 DOM/HTTP body |

前两份 DOM 的路径为：

`C:\Users\LIHAOYANG\Documents\Codex\2026-10-17\chapter1-source-sol56\private\A24-current-platform-20261022`

目录观察位于同一目录。本次证据集只包含这三个文件。

来源成员更正指出，`outputs/A24-46007447-current-platform-readonly-baseline-20261022.json` 是早先 `LIVE_NOT_CONNECTED` 的历史报告，不是本次汇总或待追加记录。本报告不将它纳入当前证据、不覆盖它，也不从中继承任何当前事实。

## 可以直接验证的当前事实

### 书籍与页面身份

由 book picker DOM 和目录观察交叉确认：

- 可见书号：`46007447`
- 可见书名：`0917-136-9787555396581-名校课堂八年级数学上册`
- 可见状态：`标注中`
- 可见标注人：`[REDACTED]`
- 可见团队：`[REDACTED]`

picker DOM 还单独显示：

- 上传时间：`2026-10-10 23:21`
- 认领时间：`2026-10-15 23:10`
- 当前对话框结果：`共 1 条`

这里的“共 1 条”仅是当时 picker 对话框结果，不证明平台全局只有一本书。

home DOM 确认页面标题 `QT-Platform`、当前可见账户文案 `[REDACTED]`，以及通用标注、书籍信息、JSON 预览入口的可见路由。

### 当前可见目录状态

目录观察直接记录：

- 章节文案：`第一章 勾股定理`
- 叶目录文案：`2 一定是直角三角形吗`
- 可见章节 DOM data key：`dir-1792063578574-ug3232apl`
- 可见叶 DOM data-node-id / tree data key：`dir-1792063578574-g0n3ulsni`
- 可见子项标签：`22`
- 可见子项 data key：`1792148510557`
- 当前展开 DOM 中可见题号：1–22
- 可见分布：`第1课时 探索勾股定理` 下 1–21，`2 一定是直角三角形吗` 下 22

这些值只能称为可见 DOM 标识/标签：

- `dir-...` 不能在没有服务器 JSON 的情况下命名为权威 `directory_id`；
- `1792148510557` 不能命名为原始 `question_id`；
- 可见标签 `22` 不能命名为题 ID，也不能证明完整书/章分母；
- picker 未选择时背景页的“0”计数明确不是书籍或章节分母。

## A24 真实格式接入现在能做到哪里

### 可安全做到

1. 建立只读 DOM 证据，证明当前可见书号、书名、状态、标注人、团队及目录文案。
2. 把 `46007447` 作为“当前可见表格单元格值”做人工/DOM 层交叉检查。
3. 把章节/叶目录的 DOM data key 作为原样证据保存，等待原 JSON 后再判断它们与服务器 ID 的关系。
4. 保持 schema capture/profile/qualification 全部 UNBOUND。

### 现在不能做到

1. 不能定义 `book_id` 的 JSON 字段路径；DOM 只有可见值，没有原响应字段名。
2. 不能把“标注中”映射成 `complete=false`、`read_status` 或任何内部枚举。
3. 不能证明目录成员全集、题目全集或 authoritative count。
4. 不能获得原始 `question_id`、`frame_id/rect_id`、坐标/bbox、页码、框类型和 frame→question 关联。
5. 不能获得五区正文、`parts`、`question_info`、unknown extra、原始记录哈希。
6. 不能绑定 export `state_version/state_binding`、服务器版本或本次 catalog。
7. 不能满足四个 HTTP route body、HTTP status、请求参数和同次捕获关系的证明要求。
8. 不能覆盖保存回执与保存后回读，因此不能生成可写 profile 或解除 HOLD。

## 下一份真正有用的输入

若来源成员随后取得明确的原 JSON，应原样提供：

- 文件字节、SHA-256、字节数、捕获时间、route、query keys、HTTP status；
- book 行的原字段名和值；
- directory 树的原始节点对象及父子关系；
- frame/rect 的原 ID、question 关联、bbox/页码/类型；
- export 的完整题记录、五区、parts、question_info、rect_ids；
- 能证明同次 catalog/version 的状态字段。

只有这些证据到齐后，才能从 DOM 可见身份继续到真实 JSON 字段路径核验；仍需逐门验证，不能由 DOM 值反推字段。
