# A24 当前平台“导出试题”增量观察（2026-10-22，v2）

## 结论

在同一 USense 标签页重新只读选择了书籍 `46007447`，打开“更多操作”菜单，并确认精确名称为“导出试题”的 `menuitem` 只有 1 个。

按照有界尝试要求，实际调用顺序如下：

1. 调用 `waitForEvent('download', {timeoutMs: 55000})` 并把返回的 Promise 赋值；该操作在 click 调用之前。
2. 调用并等待精确匹配菜单项的 `click({timeoutMs: 10000})`。
3. 代码原计划在 click 返回后等待下载 Promise，再调用 `download.path()`。

65 秒外层工具调用到时后控制会话重置，没有输出中间阶段回执。因此只能确认“下载等待器先创建、click 调用随后被发起”；不能确认 click Promise 是否已经返回、下载事件是否已经解析，也不能确认代码是否进入 `download.path()`。恢复后菜单已关闭，说明页面处理了这次点击，但这不是下载成功证明。本轮没有重复点击，也没有点击“导出整套书籍JSON”“导出试卷试题”等其它相似项。

恢复后只读观察到：

- 当前书号 `46007447` 仍可见；
- “更多操作”菜单已关闭，说明该次单击被页面处理；
- 页面没有可见成功或失败提示；
- 普通 `Downloads` 目录未出现本次时间对应的新 JSON、JSONL、ZIP 或 TXT 文件；
- 只有 2026-10-16 的旧文件 `46007447_paper_questions.jsonl`，其 11,625 字节及 SHA-256 `02a8aaae2bc907649a03f3676806a02da103e0b487fb43f7e187b29a67fc7a8c` 与历史摘要一致，明确排除。

因此最终判定为：**等待器先注册，单次 click 调用已发起且页面菜单随后关闭；click 返回、下载事件解析和 `path()` 阶段均无回执。没有新文件或页面提示能够证明本次导出完成；结果保持 UNKNOWN，不再重试或扩展范围。**

## 增量证据

- 私有机器记录：`private/A24-current-platform-20261022/08-export-questions-attempt.json`
- 本报告补充而不覆盖 v1：`outputs/A24-current-platform-observations-20261022-v1.*`
- 所有 HTTP 状态仍为 `UNKNOWN`；后台请求未观测；没有取得原始 HTTP 响应体。

## 安全边界

- 没有编辑、保存或提交标注。
- 没有上传文件。
- 没有读取 Cookie、Token、凭据、浏览器 Profile 或隐藏 store。
- 没有在页面中执行 `fetch`，没有使用原始 CDP。
- 公开报告不含账号姓名。

最终状态：`WAITER_REGISTERED_THEN_SINGLE_CLICK_INVOKED; CLICK_RETURN_AND_DOWNLOAD_EVENT_UNOBSERVED; FRESH_DOWNLOAD_NOT_PROVEN; RESULT_UNKNOWN`
