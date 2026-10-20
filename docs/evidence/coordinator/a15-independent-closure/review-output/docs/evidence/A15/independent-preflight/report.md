# A15 固定候选正式独立预检

结论：`ACCEPTED_OFFLINE_ONLY`。仅接受本固定候选的有限批准门禁与静态预检资格；本对话已停止 REVIEW 并释放。live 未激活，必须由调度另行核证和固定派发。

产品 `bef0204541eedd86e1fab849e8002a83f432cd7b`，作者新 final `7432122b9fd5602785ebfb2b3f24e407fdf76eda`，候选清单 SHA256 `78382e0b484ad46ab497217683fa3022440a1f570589f538c3d355670d552652`。独立正式对话 `01a157fe-5cc9-7d91-8bbe-73b376cbe2a5`。机器报告 `report.json` 可供后续调度绑定摘要。

独立唯一一次 E1–E4：**4/4 PASS，32ms，退出码 0**；E1 固定 10 个拒绝变体及默认严格校验，E2 固定 29 个绑定/额度/时间/摘要/JSON 拒绝变体，E3 一次匹配合成领取，E4 重复拒绝且原标记 bytes 不变。合成标记 SHA256 `607ed11663d9fe379b6dbf60e45e10406f0d53db19f8a81551bcb83c02cf330b`。stdout 原 bytes 保留，stderr 0 bytes；八类资源入口计数全 0。独立额度已用 1、剩余 0，不补跑。

| 层级 | 本次独立结论 |
| --- | --- |
| 固定交付 | 47 raw 与新 final 固定 Git blob 相符；原失败 final 的 31,243 旧成员 mode/type/blob 保全，仅新增 16；原基线 31,212 亦保全；22 个候选成员未变。运行前后 47 输入及 R1 对照、先前静态封存全部原 bytes 保全。 |
| 权威语义 | 从固定用户决定、提案和执行任务推导任务/候选/调度/target/profile/输出/额度/期限绑定，独立静态确认显式开关与摘要门禁先于真实资源动作；默认严格证书校验，CLI 不替代固定激活字段。 |
| 守卫/生命周期 | 21 个关键 R1 函数/类 raw 比较通过（DOM 观察和最终化只改认证枚举）；逐跳方法/WS/子 target、DOM 后最终判定保持。各进程本地 monotonic 截止无跨进程时基混用；精确保留句柄、OS 退出观测、Job 计数和 wrapper UNKNOWN 边界，仅静态审查。详见先前独立静态报告。 |
| 原打包失败 | 23,514-byte raw diff 可独立精确重建，17 处均为上下文空行。原单项退出码 null、PS 继续 commit、失败/NOT_RUN 原件保持；未重跑原检查或改记 PASS。显式处置只启用原未用一次作者差量，无新候选或追加 suite。 |
| 真实资源 | 本 suite 仅执行纯函数和本轮合成目录。0 产品子进程/browser/network/native API/profile/实际占用，0 登录提交/业务/书级送交/B 消息；未触发任何真实证书例外。 |

复现命令（仅记录已发生的一次调用，**不授权重跑**）：

```text
python -B tools/a15_cert_exception_gate_delta.py --candidate-sha256 78382e0b484ad46ab497217683fa3022440a1f570589f538c3d355670d552652 --output docs/evidence/A15/certificate-exception/first-independent-delta
```

`independent-command-result.json`、`independent-delta-stdout.txt`、`independent-delta-stderr.txt` 保存原始命令/输出/退出；唯一差量原始结果在 `../certificate-exception/first-independent-delta/`。`fixed-input-preservation.json` 保存运行后的输入复核，`independent-release.json` 记录本次释放；`manifest.json` 绑定本报告、差量原始输出与先前静态封存。

本次没有执行旧 N1–N3、D1–D8，没有实际网络/DOM/证书/占用/Job 超时释放证明，也没有认证或书籍保存证明。A14-TIMING-01 通用截止守卫仍不接受，A13 wrapper OS 退出 UNKNOWN 保留。首题保存读回仍 NOT_RUN，其他三例 HOLD、Q22 不重放。准备工具及这次差量解释器是同步本地进程；不把资源计数 0 夸大为整个准备过程无进程，也不声称已测量 shell/报告进程自身 OS 身份。

下一依赖：调度核固定报告/清单/释放，再绑定实际独立报告 SHA、候选、用户决定、profile 指纹、唯一输出及 UTC 窗口后，另行派发执行对话至多一次新观测。本离线结论不自动激活 live，也不授权题目写入。
