# Agent token 用量实测（本会话）

> 统计方式：解压 DSH 会话日志（`session.v4.jsonl.zstd`，Node 24 `zstdDecompressSync`），
> 汇总 `assistant/message` 记录里的 `data.usage`。

| 指标 | 数值 |
|---|---|
| assistant 计费调用 | 451 次 |
| 输入 tokens 合计 | **2,257,088** |
| 输出 tokens 合计 | **359,648** |
| 输入+输出 | **2,616,736** |
| 最后一次累计 totalTokens | 559,712 |
| 缓存读峰值 | 558,592 |
| 会话时间跨度 | 26.5 小时 |

## 对比：交付工具运行时的 token 成本

| 路径 | 单页 token |
|---|---|
| Agent 全程驱动（本会话口径） | 约 260 万 / 26.5 小时（含大量探索与试错） |
| **交付包运行**（A 链路 + 我们的 bat） | **0**（无 LLM 参与：ego 点击 + Python 算像素 + Node 校验） |

结论：交付包的价值不只是"快"，更是**把 agent 的试错成本一次性摊掉**——
客户日常运行不烧 token，只在首次安装和 spec 起草时可能需要人（或我们）介入。
