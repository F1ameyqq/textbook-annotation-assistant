# I01-A 固定交付独立验收派发

2026-10-18。沿用 [独立验收任务](I01-A-independent-review.md) 的有限范围，不新增业务标准。调度完成固定交付与释放预检后，将本单发送已登记验收对话 `01a14e1c-1d38-7fb3-83f2-015b0380ea56`；本单本身不是 ACCEPTED。

## 固定对象

- 组合基线：`a1c3c3b2d452ecbdf5c57a8b7372e7d53de0f8d8`。
- 最终交付：`3fdc5d37e221fc73410f197605f5d7b8878182d5`。
- 实际业务运行候选：`be68b8d7c645de556d601458d1d493258f063721`；首次静态冻结 `3a7b5430659918d015a23fa2da722bfe3cec44af` 与打包纠正历史保留，不恢复纠正额度。
- 作者仓库：`D:/1800-worktrees/i01-a`，只作为固定 Git 对象来源，不在其工作树或业务状态上运行。
- 原字节报告：上述最终交付的 `docs/tasks/I01-A-execution-report.md`；SHA256 `59a3d4990162ba4ea798cafb2989e2df2714a757a637eb3d7bc2192f0569b3d9`。
- 原字节清单：同提交 `docs/evidence/I01-A/execution/manifest.json`；SHA256 `e55f241b6e1c85eec5ed4c09d50361ef7a9a4f1db8aa7bed9045f87d67a187aa`，665 成员，自身排除。
- 释放：同提交 `docs/evidence/I01-A/execution/release.json`；SHA256 `cdb007faa3653719ec058c41a7d209fe98b3437f9d8b52b762841667d4eb685e`。作者已结束，21 个原进程均有退出记录；PID 36852 后被更晚创建的 conhost 复用，不操作复用者。
- 调度预检记录：`docs/evidence/coordinator/heartbeat-20261018-0839/I01-A-delivery-preflight.json`。

## 独立复现与边界

从固定 Git raw blobs 建自己的新隔离运行视图，Git 一律 `-c core.longpaths=true`、`GIT_NO_LAZY_FETCH=1`；本地缺件即报告，不联网补件。产品、pins 和依赖不变，不复制作者数据库作为正向起点。

实际业务入口为 `python -X utf8 -B examples/i01/run.py --candidate be68b8d7c645de556d601458d1d493258f063721`。先读固定驱动与报告，核对 HEAD/路径守卫，不能拿最终交付 HEAD 冒充运行候选。按独立验收任务固定自己的隔离路由、状态、输入身份和顺序；保持业务语义及既有守卫，不替换业务函数或修改候选。只读检查与必要的外部记录不另设设计审批。

本次实际运行只包括 A01 两个公共入口及 N/E/U：每侧最多 3 fresh targets、3 dispatch；N 一次正常执行，E 旧候选 TARGET_CHANGED 且 0 dispatch 后全新链执行一次，U 真实效果后 UNKNOWN、原进程退出、新 PID 一次 MATCH 且 0 重发。E 使用任务已允许的前置拒绝纠正，不要求额外制造 hold。保留 PENDING 内容与 NOT_SUBMITTED，A01 真实归档和 native 合成样例分别判断。

子 worker 180 秒/每阶段父 240 秒及原内层期限不变，不重跑旧 A03/M/L/G/F，不新增路径，不因静态归档修正追加业务。作者三路径已成功，独立运行只用自己的有限三路径。任何业务失败保留并停止依赖步骤，不能自行修后重跑。首轮打包字节问题、归档重复计数与 PID 复用静态误判均保留，不能改成无失败历史。

输出仅新增主目录 `docs/tasks/I01-A-review-report.md` 与 `docs/evidence/I01-A/review/`，附确切版本、真实命令/进程/原始流、关键产物、计数、摘要及释放证明；不改产品、作者文件、state、索引或提交。禁止平台、profile、凭据、网络、模型、安装、推送、B 消息、旧 pending 恢复。有限 ACCEPTED/REWORK/BLOCKED 由实际证据决定，I01-A 不关闭 B 的接收或联合业务状态。
