# A30 launch03-r1 实际收口补充：比较器离线重建

- 收口报告：`receipt.json`（`9b6a05a5d1eaff1c656139aa094891c1a47b03e7147c8297efa98f13ccd8b258`，未改写）
- 补充报告：本文件与 `addendum-receipt.json`（`19fe0c6f282d5ba0d7d80424d58e7b01c01030f694da1f60e0f2ba618cdc0a5e`）
- 结论不变：**ACCEPTED_FIXED_FAILURE_AND_OWN_RELEASE_ONLY**
- 复核自身 0 平台调用、0 工作区写入、0 profile 读取

## 为什么有这一份

原收口只证明“实际运行按固定失败+自有释放收口”，没有证明“失败原因就是四个先存尾节点”。复核者随后用九个保留只读分片独立重建合并读回，仅移除 orders 39–42 的四个节点及其 15 个题框，用冻结产品源码的 `native_plan.compare_readback` 重新比较。

## 结果

- 未清理：第 256 行 `Hold("读回题数或书籍不一致。")`，42 ≠ 37+1；book_id 两侧均为 46007447。
- 清理后：`validate_current` PASS、`compare_readback` PASS；`old_questions_preserved=37`、`old_frames_preserved=125`、`new_node_id=1792848391723`、`new_info_id=2113985491617890305`、`readback_hash=cceb4298fb93bb8b4afd01c489bf4cdf7284bc52834594bb92dfc7a38094d449`、`runtime_actor_and_send_window_checked=true`。
- 根此前独立完成的同类重建（`D:/1800-private/a30-root-20261025/preexisting-q13-16-report.json`）得到**完全相同**的 readback_hash 与全部字段——两次独立重建逐字段一致。
- 复核脚本经根扫描：无 transport/网络/浏览器/子进程引用。

## 边界

- Q12 仍为 `UNKNOWN_NO_RETRY`；本补充不授权重发、补对账或新运行。
- Q13–16 归因仍 `UNKNOWN`，永不重发或覆盖。
- full16 导出/展示仍未运行；`customer_ready=false`；1800-a PAUSED。

## 记录缺陷

`decision-addendum.json` 的 `results.uncleaned_compare_at_line_256.message` 字段是乱码（仅该 JSON 字段的编码问题）；同一 Hold 文本在收口报告、output blob `521de423…` 与公开 `REVIEW.md` 中均正确。无实质影响。
