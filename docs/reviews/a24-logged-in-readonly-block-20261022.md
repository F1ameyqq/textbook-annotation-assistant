# A24 当前平台只读采集尝试

日期：2026-10-22（Asia/Shanghai）

## 结论

- 用户已在独立 Edge 标签 `1199071973` 完成登录；浏览器状态清单显示该标签从 `/qieti/login` 转到 `https://www.usense.com/qieti/home`。
- 本轮没有取得 book、directory、fullframes 或 natural export 的任何业务正文，也没有产生可保存的原始响应文件。
- 原因不是平台登录失败，而是两个受支持控制通道均在业务读取前被阻断：
  1. 浏览器 DOM 绑定返回 `Debugger unattached`；
  2. Windows 原生窗口回退被安全策略强制终止：`could not determine the current browser URL on Windows with enough confidence to enforce policy`。
- 按 computer-use 技能的强制停止规则，已停止所有网页动作。没有改用 Cookie、token、CDP、shell HTTP 或猜测端点绕过。

## 实际动作与效果

| 项目 | 结果 |
|---|---|
| 登录后标签存在性与 URL 清单 | 已确认：`1199071973` / `/qieti/home` |
| 绑定目标标签 | 失败：`Debugger unattached` |
| 原生 Edge 窗口读取 | 安全策略强制停止 |
| book/directory/fullframes/export GET | 0 |
| 网站标注编辑、保存、提交 | 0 |
| 凭据、Cookie、profile、锁操作 | 0 |

因此，“已登录”只能证明页面重定向完成，不能表述成“当前平台数据已采集”。

## 本机只读能力核查

只读检查了 `C:/Users/LIHAOYANG/Documents/Codex/2026-10-16/ni/work/a24-takeover-20261022/source`；该目录不是 Git checkout。固定代码仍只允许四个已知 GET：

1. `/qieti/api/claim_book/books`，必须使用页面上下文导出的官方查询；
2. `/qieti/api/annotate_ocr/directory/get?file_id=46007447`；
3. `/qieti/api/annotate_pic/get_manual_annotations_unified/46007447`；
4. `/qieti/api/annotate_ocr/export-paper-questions/46007447`。

代码中的 `acquire_current_schema` 会把 directory、frames、export 的 UTF-8 响应体另存为私有 `.bin`；book 在旧实现中只记录长度和哈希。本轮未运行该代码、未发请求，也没有把代码中的旧规则伪装成当前响应。

本机文件 SHA256：

- `owner.py`: `fb5bcd815d075f425d97845da13b64c2e06f62ecb990f41924377dadea8aeaaf`
- `usense.py`: `6e5c6ae1fa08588ee675193a3054588c1b537083098ab169b4646cc1ddc3e277`
- `current_readonly/policy.py`: `a1c2dfbdf04e368a9beca6e998783196347d71d0d36d024ec9e309e607c0b89d`

## 恢复条件

无需重新登录或创建新标签。只需恢复 Codex 浏览器集成对现有标签 `1199071973` 的调试连接，使 `getTab` 不再返回 `Debugger unattached`；然后在新的安全可识别回合中仅对上述四个 GET 做只读采集。若工具仍无法可信识别 URL，应继续保持阻断，不能降级到直接 HTTP。

机器可读回执：`outputs/A24-current-platform-readonly-attempt-20261022.json`。
