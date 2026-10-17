# A03 P1 主调度设计收口

日期：2026-10-17。结论：**P1_DESIGN_ACCEPTED**，仅接受设计并批准同一任务进入 P2 实现。A03 功能仍未验收、未集成，I01 不释放。

被接受的最终版本为 `940a5de33a24b1a3a9ded6e69ade1dd0609ed83a`，设计提交为 `a250a76dc0b3f13b9dee3bcd2c3d7414032b9768`。采用该版本的原 P1 D01–D08 决策、P1-R1 专用只读未尝试事实入口与逐消费者引用闭包、P1-R2 完整事件前缀及其派生绑定。正式候选选择采用 R2 profile 和七份 Schema 摘要，不能只凭重复的顶层版本字符串选包。

[独立验收报告](A03-P1-R2-review-report.md) SHA256 为 `7a3d02a07042efb8a3f1854ae297b231e3dc8362805144760ee72e46d371eb36`；[验收清单](../evidence/A03/review/P1-R2/sha256-manifest.json) SHA256 为 `f9db0d7e3e0a77416c945d1483e95f589e61fb9573fec5d288e3ec23c1ccbb75`。原 P1/P1-R1 的 REWORK 及原失败证据保留，接受不溯及旧版本。

主调度读取具体语义与独立脚本，在固定原始 Git 导出上复跑四个正例、三个作者负例及三个重新编号/重算链的独立负例；26 个实际输入逐一与确切 Git blob 核对。命令 `python -B docs/evidence/A03/coordinator/P1-R2-acceptance/reproduce.py` 退出 0，结果见 [主调度复现](../evidence/A03/coordinator/P1-R2-acceptance/coordinator-check.json)。这是对独立静态审计的复现，没有运行恢复实现。事件14由静态重建验证头摘要，不是实际事务提交证明。

批准 D08 的离线默认值：每 intent 每次恢复调用最多3次读；单读2秒、单 intent 8秒、整调用60秒、SQLite busy 1秒、效果闸/测试屏障各5秒、lease 10秒、续期2秒。采用 monotonic 最早期限，尝试预先持久登记；重启不能重置同 call_id 额度，耗尽保留暂停。确定性结构/引用错误立即拒绝。退出码按已冻结 P1 第8节，不授权自动循环恢复调用或旧动作重发。

设计完整性可收口；P2 的事务、真实本地 intent、独立目标效果、进程重启/抢占、超时及全合成准入拒绝仍须实际证明。S01 来源完整性、D01/Pillow、B 共同合同、真实平台恢复/识别/成本均保持未解决。P2 明确范围见 [续派任务](A03-P2-dispatch.md)。所有收口与派发仅本地归档，未推送或共享给 B。
