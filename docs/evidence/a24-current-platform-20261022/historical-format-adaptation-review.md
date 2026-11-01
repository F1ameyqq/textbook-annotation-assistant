# A24 历史真实 JSONL 格式核查（DOM 核查增量 v2）

## 结论

**HISTORICAL_FORMAT_OBSERVED / CURRENT_COMPLETENESS_UNBOUND / HOLD**

`46007447_paper_questions.jsonl` 是真实历史导出字节，但不是 2026-10-22 的 fresh capture。它精确匹配旧 export 摘要：

- 字节数：11625
- SHA-256：`02a8aaae2bc907649a03f3676806a02da103e0b487fb43f7e187b29a67fc7a8c`
- 原 Downloads 文件 ctime：2026-10-16 20:26:03.825364 +08:00
- 原 Downloads 文件 mtime：2026-10-16 20:26:04.769535 +08:00
- 证据副本：UTF-8 strict、无 BOM、19 个物理行、无空行、无末尾换行
- discovery：`fresh_capture_proven=false`

正文没有进入报告或机器记录；只保存字段、类型、计数和源哈希。

## 严格解析结果

19 行均严格解析为 JSON object：

- 每条恰有 19 个同序字段；
- 所有记录字段集合完全一致；
- 拒绝重复 JSON key 和 NaN/Infinity 的严格解析通过；
- 所有 361 个顶层字段值均不是 JSON `null`；
- 但有 266 个空字符串和 14 个空数组，不能把“非 null”误写成“有内容”。

字段顺序：

`doc_id, title, province, city, district, grade, subject, year, term, paper_type, tixu, tihao, question, option, answer, analysis, tishi, comment, step`

## 字段、类型与空值

| 字段 | 19 条中的类型 | null | 空值/结构 | 唯一值数 | 可支持的事实 |
|---|---|---:|---|---:|---|
| `doc_id` | string ×19 | 0 | 空字符串 ×19 | 1 | 键存在，但没有任何可用 ID |
| `title` | string ×19 | 0 | 空字符串 ×19 | 1 | 无标题值 |
| `province` | string ×19 | 0 | 空字符串 ×19 | 1 | 无值 |
| `city` | string ×19 | 0 | 空字符串 ×19 | 1 | 无值 |
| `district` | string ×19 | 0 | 空字符串 ×19 | 1 | 无值 |
| `grade` | string ×19 | 0 | 空字符串 ×19 | 1 | 无值 |
| `subject` | string ×19 | 0 | 空字符串 ×19 | 1 | 无值 |
| `year` | string ×19 | 0 | 空字符串 ×19 | 1 | 无值 |
| `term` | string ×19 | 0 | 空字符串 ×19 | 1 | 无值 |
| `paper_type` | string ×19 | 0 | 空字符串 ×19 | 1 | 无值 |
| `tixu` | integer ×19 | 0 | 1–19，连续且不重复 | 19 | 观察到的历史行序号；不是已证明的 canonical ID |
| `tihao` | string ×19 | 0 | 空字符串 ×19 | 1 | 没有可用题号 |
| `question` | string ×19 | 0 | 全部非空；长度 50–304 | 19 | 历史题面文本；含 HTML/TeX |
| `option` | array ×19 | 0 | 空数组 ×14；非空 ×5 | 6 | 5 条含选项数组；无 question_type 证明 |
| `answer` | string ×19 | 0 | 全部非空；长度 1–579 | 16 | 历史答案文本；含 HTML/TeX |
| `analysis` | string ×19 | 0 | 空字符串 ×19 | 1 | 无解析正文 |
| `tishi` | string ×19 | 0 | 全部非空；长度 5–8 | 3 | 历史字符串字段；语义不向 knowledge_point 映射 |
| `comment` | string ×19 | 0 | 空字符串 ×19 | 1 | 无值 |
| `step` | string ×19 | 0 | 空字符串 ×19 | 1 | 无值 |

`option` 的精确结构：

- 数组长度分布：0 项 ×14、2 项 ×1、4 项 ×4；
- 共 18 个元素，全部是非空 string；
- 选项字符串中没有 HTML tag 或图片 tag；
- 观察到 TeX command token，但不据此推断题型。

## 身份与唯一性

### 已证实

- `tixu` 是整数，恰好连续覆盖 1–19，且本文件内不重复。
- `question` 文本 19 条均不同。
- 文件名和 discovery 将该历史文件标记为书 `46007447` 的 export。

### 未证实

- `doc_id` 19 条全部为空，不能承担平台题 ID；
- `tihao` 19 条全部为空；
- 文件正文中字符串 `46007447` 出现 0 次，记录本身不是自描述 book binding；
- `tixu` 只是观察到的连续整数，不能自动改名为 `platform_question_id`；
- 没有 `frame_id/rect_id` 或 frame→question 关系。

因此本文件没有可直接采用的非空 canonical question ID，也无法与当前 DOM 节点逐条稳定 join。

## HTML、图片与公式承载

跨 `question/option/answer`：

- 17/19 条记录至少含一个 HTML tag；
- 13/19 条记录至少含一个反斜杠 TeX command token；
- 共观察到 128 个反斜杠命令 token；
- HTML tag occurrence：`br` 81、`div` 2、`img` 1；
- 仅 1 条记录含图片 tag。

分字段：

- `question`：17 条含 HTML，1 个 `img`，10 条含已识别的常用公式命令；
- `answer`：3 条含 HTML，6 条含已识别的常用公式命令；
- `option`：18 个字符串元素中无 HTML/图片，合计 4 个反斜杠命令 token。

唯一的 `img` 使用未加引号的 `src`，值长度为 4，属于 relative/other 形态；它不是已验证可解析的 HTTP(S)、data URL 或受控图片资源。不能据 tag 存在声称图片完整可用。

未观察到 MathML tag、MathJax/KaTeX class、`\(...\)`/`\[...\]` 或 `$$...$$` 分隔符；主要承载是普通字符串中的反斜杠 TeX 命令。这里仅统计语法标记，不验证公式渲染正确性。

## 现有 A24 codec 可消费程度

### JSONL 语法层：可读取

现有 codec 使用逐行 JSON object 的基本输入形态；本文件的 19 行在语法层面可严格读取。完整原记录可以计算 raw hash。

### Complete codec：不能直接消费

缺少：

- 独立 metadata row；
- `book_id`、`complete`、`question_ids`、五区清单和 `state_version`；
- metadata/question record kind discriminator；
- 可验证的非空题 ID。

不能为适配而合成 metadata 或把历史 19 条声明为 complete。

### Natural codec：不能直接消费

现有 natural codec 所需语义包括：

- 非空 canonical `platform_question_id`；
- `question_type`；
- 非空 object 型 `parts`；
- 五区 `wire_zones`；
- `question_info`；
- `rect_ids`；
- 当前 route 的 authoritative qualification 与 `state_binding`。

本文件不提供这些语义。虽然 `question/option/answer/analysis` 是实际历史字段，但：

- 没有独立 `knowledge_point` 字段；
- 不把 `tishi` 或 `comment` 猜成 `knowledge_point`；
- 不把 `tixu` 猜成 canonical question ID；
- 不把 HTML `img` 猜成 rect/frame；
- 不把 19 行数当 current catalog。

因此结论是：**历史 JSONL 格式已观察，但现有 A24 codec 的直接语义消费为 BLOCKED。**

## 与 2026-10-22 DOM 观察的关系

先前 DOM 核查确认当前展开页面可见标签 1–22；本历史文件有 19 行且 `tixu=1…19`。

这两个数字不能相减得出“漏 3 题”，原因包括：

- 日期不同：历史文件源时间为 2026-10-16，DOM 为 2026-10-22；
- 口径不同：一个是历史 export 行，一个是展开 DOM 可见标签；
- 范围和完整性都未由同次 authoritative catalog 证明；
- 没有非空原始题 ID 可逐条 join；
- DOM 标签也不是已证明的服务器 question ID。

它们只能记录为“19 条历史记录”与“22 个当前可见标签”的跨时间、跨口径观察。

## 2026-10-22 q22 DOM 新来源差量

来源成员已冻结本批次只读 UI 汇总：

- `A24-current-platform-observations-20261022-v1.json`：7181 bytes，SHA-256 `488a9902822f53a1b29f65cd7ee83637cc26fa2b236bb582c523b0ba6e06eeba`；
- `A24-current-platform-observations-20261022-v1.md`：5321 bytes，SHA-256 `5e03f0b12832a6adda1990f5f46b836e43f47980dd81ff24251c1c1927c63ee9`。

新增直接 DOM：

- `04-q22-selected-dom-snapshot.txt`：20404 bytes，SHA-256 `41769485628f1b2ae8f0b8a24adcc30fd9bcdc835553cb0ab48b010f5883350c`；
- 表示为 `DOM_SNAPSHOT_TEXT`，`http_status=UNKNOWN`；
- 可见选择题号 22，题页可见值 14，答案页可见值 173；
- 该 DOM 是稍后的 q22 选择状态，且“更多操作”菜单已展开，不能倒推更早 03 观察时刻。

新增派生结构：

- `06-q22-visible-rects-dom-extract.json`：13121 bytes，SHA-256 `4e9f7718124c12489923c6fcc841ece990edba4ae1afb90d71e21666edbf9b8c`；
- 表示为 `DOM_EXTRACTED_STRUCTURED_VALUES`，不是原 HTTP/JSON；
- 可见 rect layer 共 25：question 1、answer 24、option/analysis/knowledge 各 0；
- 25 个 rect object 的键均为 `class, label, layerRect, rectIndex, style`；
- `layerRect` 均为 4 个有限数值；`style` 含屏幕 CSS 的 left/top/width/height/position/z-index/pointer-events；
- `rectIndex` 25 条中只有 24 个不同值，连 DOM 层也不是全局唯一键。

边界：

- 1 个 question 历史框位于当前可见题页 14；24 个 answer 历史框是答案页 173 当前可见的全部历史答案框，不能断言都属于 q22；
- question rect 和一个 answer rect 的可见 label 都能见到 22，但 label/`rectIndex`/DOM attrs 不是已证实的服务器 `question_id/frame_id/rect_id`；
- `layerRect` 是浏览器可见层的屏幕矩形，CSS `style` 是渲染定位；两者都不是已证实的原图 bbox、页内像素坐标或上传 payload；
- 25 只覆盖当前可见的题页 14 与答案页 173，不是整题、整叶目录或整书的全量 frame 分母；
- 右侧编辑面板显示的是 new slot 23，其五类计数均为 0；这些 0 不能解释成历史 q22 无框。

JSON 预览页仅显示本地文件点击/拖拽控件，没有当前书 selector 或下载控件；一次“导出整套书籍 JSON”操作没有证实新文件落盘，结果继续为 UNKNOWN。历史 19 条文件仍不得提升为当前导出。

## 当前状态

- 真实当前 export：仍待来源成员查找；
- 当前 schema：UNBOUND；
- `write_allowed=false`；
- 未生成 adapter/profile/qualification；
- 历史私有正文未进入 Git 或公开制品；
- 共享 B 与来源原件均未修改。
