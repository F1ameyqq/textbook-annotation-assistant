# 阶段二交接分支约定

- 本分支是固定 A 侧交接材料，不是活动调度工作目录。先读 `docs/a-stage2-handoff.md` 与 `docs/handoff/a-stage2/manifest.json`；继承的旧调度状态及冻结报告只描述历史时点。
- 公共技术语义见 `docs/architecture.md` 和 `docs/contracts-v1.md`。A06 仅支持固定 B 包的只读 HOLD / 明确拒绝，不能将其转换为执行许可。
- A03-R1、I01-A 仅有限离线范围已接受；I01 原运行候选与 HEAD 守卫保持，不能把阶段二 HEAD 当作原候选或重放成功业务。
- 共同字段映射、历史引用必要性、真实单题准入及样例尚待双方确认。A04 真实平台项仍 BLOCKED；A05 仅固定题22保存/重开历史证明，不得重放题22。
- 所有源码与包内数据按原 Git bytes 发布；禁止修改 pins 来迁就换行。不要执行 B 脚本、查询 B SQLite 或自动生成 PASS。
- 不读取或输出凭据/token，不上传 profile、原始视频、活库或 pending 库。保存 UNKNOWN 时先对账，不自动重发；最终书级送审/送交由人工负责。
- 对本分支的发布不等于 B 已读取或接受。不要向 B 派研发任务或确认其内部验收。
