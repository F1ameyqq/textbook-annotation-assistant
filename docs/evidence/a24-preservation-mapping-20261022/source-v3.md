# A24 当前平台目录与导出预检观察（2026-10-22，v3）

## 结论

本轮在同一 USense 标签页完成了新的只读 DOM 原件保存。当前书号仍为 `46007447`；当前渲染的目录树中共有 143 行 `treeitem`，其中顶层章节 8 个、可见“插题”节点 22 个（标签 1–22）。目标叶目录“2 一定是直角三角形吗”及其可见子题“22 插题”均在原始快照中。

这 143 个节点只能证明**当前已渲染 DOM 树**，不能当作服务器端完整目录或题目分母；快照也不含每个节点的稳定后台 ID。

## “导出试题”结果已从 UNKNOWN 收敛为可见预检失败

v2 的单次“导出试题”点击当时因为控制会话超时，只能记为 UNKNOWN。本轮保存的同一标签页 DOM 已明确出现对话框“导出试题预检未通过”，显示错误 9、警告 0：

| `importShitiID` | 可见错误 |
|---|---|
| 1 | 选择/多选题的 `choice` 必填 |
| 2 | 选择/多选题的 `choice` 必填 |
| 7 | `question` 为空、`answer` 为空、选择/多选题的 `choice` 必填 |
| 19 | `question` 为空、`answer` 为空 |
| 22 | `question` 为空、`answer` 为空 |

因此可以确认：此前这次“导出试题”没有通过平台可见预检，当前导出文件仍未取得。这里收敛的是**可见 UI 结果**；没有 HTTP 回执、下载事件回执或实际文件路径，不能把它扩大为网络层结论。

## ID 证据边界

- `46007447`：当前页面可见的书号。
- `dir-1792063578574-g0n3ulsni`：v1 已取到的目标目录 DOM `data-key`，只按会话 DOM 键使用。
- `1792148510557`：v1 已取到的第 22 题树节点 DOM `data-key`，只按会话 DOM 键使用。
- `importShitiID=1/2/7/19/22`：本轮预检对话框明确可见的导入题号字段。
- 上述 DOM `data-key`、显示题号和 `importShitiID` 均**没有证据证明等同于服务器稳定 `question_id`**；稳定题目 ID 映射仍为 `NOT ESTABLISHED`。

## 有界读取停止点

在保存原始 DOM 后，尝试以精确可见名称“22 插题”进行一次只读选择。选择器计数在执行前超时；随后唯一一次选择点击使浏览器控制工具被强制终止，未得到完成回执。本轮没有再次尝试，也没有打开“预览”。

没有重点击 v1 的“导出整套书籍JSON”或 v2 的“导出试题”，没有点击其它相似导出项。

## v3 证据原件

| 文件 | 字节 | SHA-256 | 表示 | 时序（Asia/Shanghai） | 完整性边界 |
|---|---:|---|---|---|---|
| `private/A24-current-platform-20261022/10-v3-current-selected-book-dom-snapshot.txt` | 20,487 | `07d7defe1fb2ce093aaa1793a86a4f9b10f53f1d4fa8fcbb5e5a69351a52b315` | DOM 原始文本 | 15:14:05 | 当前已渲染 DOM；含目录树与预检对话框；含账号标签，保持私有 |
| `private/A24-current-platform-20261022/11-v3-readonly-selection-attempt.json` | 1,085 | `75f7fa01b2dc0db353c7062e11ba340d608a47705919d2158bd14889b6206beb` | 工具尝试回执 | 15:17:06 | 仅记录有界尝试；工具终止后没有新的 UI 观察 |

## 仍未取得与恢复入口

仍未取得：服务器稳定 `question_id`、服务器端完整目录/题目分母、当前整书原始 JSON，以及 HTTP 状态/响应体。

可恢复入口只有以下三类：

1. 平台原生导出通过预检并返回一个可核验的当前文件路径，再记录字节数和 SHA-256；
2. 页面出现明确标注为不可变 `question_id` 的只读字段，并能与原始页资产身份、尺寸和哈希绑定；
3. 用户提供经授权的当前原始服务器导出文件，无需调用隐藏接口或页面内 `fetch`。

本轮没有编辑、保存、提交、上传或重复导出；没有读取 Cookie、Token、凭据、浏览器 Profile 或隐藏 store；没有页面内 `fetch` 或原始 CDP。

最终状态：`VISIBLE_EXPORT_PRECHECK_FAILED; CURRENT_RENDERED_DIRECTORY_CAPTURED; STABLE_QUESTION_ID_AND_SERVER_DENOMINATORS_UNOBSERVED; HOLD`
