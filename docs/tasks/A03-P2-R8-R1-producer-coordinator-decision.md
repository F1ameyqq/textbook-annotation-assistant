# A03 P2-R8-R1 调度收口

2026-10-18（Asia/Shanghai）。对固定 target `a0c40886f3076f84c46377e03fc2206d2fdc5585`，结论为 **REWORK：coverage 缺口已关闭，原生恢复链尚未通过**。不记录整个 A03 ACCEPTED 或 INTEGRATED，I01 继续等待；R7 已接受的只读范围保持。

[独立报告](A03-P2-R8-R1-producer-review-report.md) SHA256 为 `37ad11cbecefcfc97c2c1487786f66418bd231c79e7b7654bd9d6c7a8fbf9cbf`；[审阅清单](../evidence/A03/review/P2-R8-R1-producer/sha256-manifest.json) SHA256 为 `13406d827e98d1e158ddd78592b00f1efbf328e53a340afa43a9d4c046edba4e`。原验收对话 `01a145aa-8d59-7c70-8d81-731712103a9a` 的本轮已 completed，自有 5 个进程记录均退出。

调度核验了清单的 391 个条目及清单自身、精确文件集合、339 个导出输入与 raw Git blob，以及 5 组登记/PID/输出/退出记录。通过自己的两个 immutable SQLite 副本及原 material fact，再次确认 PRE ADMITTED、permit CONSUMED、目标效果一次、当前正式回执缺失、POST 未生成、原 UNKNOWN 保留。四项守卫仅 attempt_fact 不同：fact 为 MAY_HAVE_BEEN_ATTEMPTED，APPLIED 行触发投影源码的 ATTEMPTED 分支；后一值是静态推导，未生成新 progress。详见[调度核验](../evidence/coordinator/heartbeat-20261018-0057/review-audit.json)及其脚本。

首次调度核验脚本误以为所有导出输入均位于 input/checkout，遇到映射到 input/raw 的长路径资源后停止。已保留首次脚本及失败说明，按已验证 input-index 的 exact commit/path 修正查找后通过；没有修改候选产品、重跑 N1 或打开执行原库。

下一项为[有界投影修复 R8-R2](A03-P2-R8-R2-projection-rework.md)。范围锁定已有 material fact 的尝试分类来源及必要 pins；保持原事实、四项守卫和历史，使用全新合成库验证正式 receipt/progress、独立 POST/Batch。N1 完成后继续原 N2–N7。出现新独立产品阻断则冻结最短失败，不以继续叠加补丁代替审阅。

这次只在本地归档审阅与派发材料，没有推送、平台操作或 B 通知。B 原生输出包的只读/HOLD 最小接收路线独立于 A03，但仍需双方明确映射口径。
