# A24 当前平台只读观察（2026-10-22，v1）

## 结论

已对当前 USense 页面完成一个可复核的只读小闭环，并保留原始 DOM、结构化框层和当前视口截图。确认目标书籍为 `46007447`，目标目录叶为 `dir-1792063578574-g0n3ulsni`（“2 一定是直角三角形吗”），其当前可见既有子题为题号 `22`，树节点 `data-key=1792148510557`。

当前第 22 题页面显示题目页 `14`、答案页 `173`、题号 `22 / 22`。DOM 框层中可见：

- 题目侧：1 个 `question-type history-rect locked` 框，标签为 `22`，`data-rect-index=0`。
- 答案侧：答案页 173 上共有 24 个 `answer-type history-rect locked` 框，其中标签 `22` 的框为 `data-rect-index=7`。
- 这 24 个答案框是答案页 173 上所有可见历史答案框，不能说成全部都属于第 22 题。
- 右侧编辑面板同时显示“当前题目 23”“暂无可编辑内容”，且题目框/答案/选项/解析/知识点均为 0。这里的 0 属于新编辑槽 23，不能拿来覆盖第 22 题已有历史框层。

因此，当前证据支持“第 22 题确有可见历史题框和答案框”，不支持“第 22 题五区完整结构已经取得”或“全章/全书分母已经确认”。

## JSON 与导出结果

“更多操作”菜单实际可见“导出整套书籍JSON”。已尝试一次平台原生下载等待，但控制会话在等待期间超时重置，未得到可证明与该点击对应的下载事件或新文件；恢复后菜单仍处于展开状态。本轮没有重复触发导出。

普通 `Downloads` 目录中未找到本次新生成的匹配文件。只发现 2026-10-16 的旧文件 `46007447_paper_questions.jsonl`（11,625 字节，SHA-256 `02a8aaae2bc907649a03f3676806a02da103e0b487fb43f7e187b29a67fc7a8c`），它与历史摘要一致，已明确排除，不能当作本次新下载。

平台 `/qieti/jsonPreview` 页面也已实际打开。页面只有“JSON文件预览”和“点击或拖拽 JSON 文件”的本地上传面板，没有当前书籍选择器、服务端当前书籍 JSON 或下载控件。本轮没有上传任何文件。

因此，本轮“当前原始 JSON/JSONL 导出”状态为：**未取得；下载结果 UNKNOWN**。

## 证据清单

| 文件 | 字节 | SHA-256 | 采集方式 | 时序（Asia/Shanghai） | 完整性边界 |
|---|---:|---|---|---|---|
| `private/A24-current-platform-20261022/01-home-dom-snapshot.txt` | 767 | `f902276f8b6c047811a071a7e503bfd9438250100e5b9833afc9894c723ebbac` | DOM 原始文本 | 13:57:29 | 仅可见主页 DOM |
| `private/A24-current-platform-20261022/02-book-picker-dom-snapshot.txt` | 1,326 | `3285ff730249bb554cb35f09abd7bbe5ad953fc2f2b1c955003efabaa46d6014` | DOM 原始文本 | 13:57:29 | 仅可见选书弹窗 DOM |
| `private/A24-current-platform-20261022/03-selected-book-directory-observation.json` | 1,783 | `23a5e681ed9541acac4aa68ae1eda9829466a2cb17b8e6f86f82993fdf844e9b` | DOM 人工派生结构值 | 13:59:45 | 早先目录状态的同刻原始 DOM 未留存；不能用 03 自证原 DOM |
| `private/A24-current-platform-20261022/04-q22-selected-dom-snapshot.txt` | 20,404 | `41769485628f1b2ae8f0b8a24adcc30fd9bcdc835553cb0ab48b010f5883350c` | DOM 原始文本 | 14:12:33 | 后续第 22 题选中且“更多操作”展开状态，不追认 03 的早先时刻 |
| `private/A24-current-platform-20261022/04-q22-selected-dom-snapshot.meta.json` | 1,088 | `76f11664a9666ee3ebe7f31d4fee196f9b46516af248899f216bcdc7e1572f0e` | 04 元数据侧车 | 14:16:38 | 仅描述 04 |
| `private/A24-current-platform-20261022/05-q22-selected-platform-view.png` | 186,996 | `2afe0dfca6e2649072ed25c5bf2a8e0d35d34b668d6e318fbe1e23d268f36e42` | 浏览器当前视口截图 | 14:11:46 | 仅当前视口；含账号标签，保持私有 |
| `private/A24-current-platform-20261022/06-q22-visible-rects-dom-extract.json` | 13,121 | `4e9f7718124c12489923c6fcc841ece990edba4ae1afb90d71e21666edbf9b8c` | DOM 结构化提取 | 14:12:33 | 仅当前两页可见 DOM 框层 |
| `private/A24-current-platform-20261022/07-json-preview-dom-snapshot.txt` | 193 | `cc59c6e32adf4e559eabf4c20ef1ac5cbb63aece2a14258e88640b607451aee9` | DOM 原始文本 | 14:13:21 | 仅 JSON 预览上传页可见 DOM |
| `private/A24-current-platform-20261022/07-json-preview-dom-snapshot.meta.json` | 725 | `729fa339029e05ef810c19fc73ab0f69c5d0287ac78f3d84d8639dd6b772f39b` | 07 元数据侧车 | 14:16:38 | 仅描述 07 |

## 网络与安全边界

- 所有 DOM 观察的 HTTP 状态均为 `UNKNOWN`；没有网络日志可证明 200 或其它状态。
- 本轮没有受控调用四条固定业务 GET；页面导航和 UI 可能自动产生后台请求，但数量、路由和状态均未观测。
- 没有取得任何原始 HTTP 响应体。
- 没有保存、提交或修改标注；没有上传文件；没有读取凭据、Cookie、Token 或浏览器 Profile；没有读取隐藏 store；没有在页面中执行 `fetch`；没有使用原始 CDP。
- 公开报告已移除账号姓名；含账号标签的截图和原始内容只保留在 `private/`。

## 当前判定

`PARTIAL_CURRENT_UI_EVIDENCE; FRESH_RAW_JSON_EXPORT_NOT_OBTAINED`

本报告是新的当前观察文件，没有覆盖此前 `A24-46007447-current-platform-readonly-baseline-20261022.*` 历史基线。
