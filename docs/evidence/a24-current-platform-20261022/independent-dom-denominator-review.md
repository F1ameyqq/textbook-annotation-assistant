# A24 当前 DOM 观察：旧题保全与分母独立核查

## 结论

`PARTIAL_VISIBLE_DOM_CONFIRMED_FULL_DENOMINATOR_HOLD`

本次真实当前私有 DOM 能确认：页面中可见书号 `46007447`、状态“标注中”、当前页面 URL、一个可见章节键、选中目录标识，以及界面当前可见的题号标签 1–22。

它不能证明整书或章节共有22题，也不能证明历史68框仍是当前完整框分母。现有证据是渲染后 DOM 文本/结构化值，不是原始 HTTP response body；题号标签也不是平台 `platform_question_id`。因此全旧题、全框、五区正文、info/meta、extra 字段和保存前后保全仍全部 HOLD，写资格不变。

## 私有来源与固定身份

| 私有来源 | 字节数 | SHA-256 | 表示 |
|---|---:|---|---|
| `01-home-dom-snapshot.txt` | 767 | `f902276f8b6c047811a071a7e503bfd9438250100e5b9833afc9894c723ebbac` | UTF-8 渲染后 DOM 文本抽取 |
| `02-book-picker-dom-snapshot.txt` | 1326 | `3285ff730249bb554cb35f09abd7bbe5ad953fc2f2b1c955003efabaa46d6014` | UTF-8 渲染后 DOM 文本抽取 |
| `03-selected-book-directory-observation.json` | 1783 | `23a5e681ed9541acac4aa68ae1eda9829466a2cb17b8e6f86f82993fdf844e9b` | `DOM_EXTRACTED_STRUCTURED_VALUES` |

两份 TXT 均可严格 UTF-8 解码，但不是 HTML 文档、JSON 文档或带 HTTP headers 的响应记录。第三份观察明确写明 `http_status=UNKNOWN`，并自我限定为“Visible expanded DOM only”。因此这些 SHA 只绑定 DOM 派生文件本身，不能转述为服务器原始响应字节 SHA。

私有 DOM 中的账户/标注者信息没有复制到本报告或机器回执；原 DOM 继续留在来源成员私有目录。

## 当前可证明的事实

- 可见书号：`46007447`。
- 可见状态：`标注中`。
- 当前观察 URL：`https://www.usense.com/qieti/annotateUnified`。
- 可见章节键：`dir-1792063578574-ug3232apl`。
- 选中可见目录 ID/tree key：`dir-1792063578574-g0n3ulsni`。
- 当前展开 DOM 提取到9个结构条目。
- 当前界面可见题号标签是连续的1–22，分布显示为1–21和22。

“9个结构条目”只描述此次可见 DOM 提取结果，不等于9个权威目录；“1–22”只描述可见标签，不等于22个唯一平台题 ID，更不等于整书或章节的完整题量。

## 当前不能证明的分母

### 题与目录

- 没有每题的 `platform_question_id`，只有界面显示序号。
- 没有权威的整书/章节 catalog、总数或“已完整加载”标志。
- 页面可能存在折叠、懒加载、虚拟列表、分页或仅当前选择范围；DOM 可见范围不能排除这些情况。
- 没有完整目录原始 JSON，无法证明目录总数、父子关系、当前目录是否终端叶节点。
- 当前 Chapter 1 Q9 旧汇总仍是 `question_id=null`；可见标签9不能补成平台题 ID。

### 框与正文

- 没有当前 full-frame 原始响应，不能建立 frame ID 集合、题关联、type、bbox、page/save_page、image path。
- 没有依据把历史“68框”当作当前完整框分母。
- 没有任何题的五区 `question/choice/answer/analysis/knowledge_point` 全量正文。
- 没有 `question_info`、其他 metadata 或未知 extra 业务字段的完整原始记录。
- 因而不能运行 raw-extra 保全、catalog/state binding 或保存前后 delta。

### 表示与时效

早先公开 baseline 文件在本次读取时 SHA 为 `7cf233878e785c91aa5ad8e46c1601f852472d36d08d95b4fd2519acd473cc4e`，仍记录 `LIVE_NOT_CONNECTED`。它不是本次 `01`/`02` DOM 原文或稍后 `03` 派生观察的汇总，而只是历史对照；不得作为当前平台事实、当前连接状态、当前分母或本次 fixed manifest 的证据。

该历史 baseline 中列出的 book/directory/frames/natural-export 长度或哈希没有对应原始正文，且标记 `raw_body_available_here=false`；这些历史摘要不能替代本次当前原件。截至本报告封存时，本次来源仅有私有目录中的 `01`、`02` 两个 DOM 文本抽取和 `03` 派生观察，尚无本次新的最终汇总。

## 继续实测所缺的具体输入

1. 当前 book 原始响应正文，以及 native 请求/响应来源、HTTP 状态、精确字节长度和 SHA-256。
2. 当前完整 directory 原始 JSON，并有权威层级与完整性依据。
3. 当前完整 full-frame 原始响应，含每个 frame ID、题关联、类型、bbox、page/save_page 和 image path。
4. 当前 natural-export 原始响应，含每题五区、info/meta、所有 extra 字段和路线资格。
5. 同一次采集的 manifest：逐文件绑定路径、长度、SHA、表示类型、route/query keys、HTTP status、request identity、session 与时间。
6. 把 book、directory、question、frame、export 成员关系连到同一当前状态的 catalog/state binding。
7. 在上述原件冻结后生成 adapter observation，并逐字段比较 raw→projection 损失；任何缺项、别名或 extra 丢失继续 HOLD。

收到这些原 JSON 后才能实测现有 schema-readiness 门；当前不猜接口、不自填 metadata、不使用可见22题或历史68框补全。

## 最终边界

- `write_allowed=false`
- `successors=NOT_RUN`
- 全旧题/框/五区/extra：`UNPROVEN`
- 浏览器、网络、API、模型、live authority 调用（本审查成员）：0
- 共享 B 编辑：0
