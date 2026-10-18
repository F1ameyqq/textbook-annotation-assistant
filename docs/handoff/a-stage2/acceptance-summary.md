# 有限接受摘要

2026-10-18。此文将当前接受结论与历史原件分开。所有档案的来源路径、原 blob 和 SHA256 见[发布清单](manifest.json)。

| 阶段 | 固定来源 / 集成 | 已证明范围 |
|---|---|---|
| A06 | 最终交付 `d78737815279965f660057bea0a572b426098aaa`；实现 `43ebdd21f2dc6803ae322b95776806e167884749`；集成 `61695306a97e90ea2d69b21c9dfe096f8a641081` | 固定 B 包只读 HOLD / 明确拒绝、既定有限版本分派、独立结果 kind/schema 门 |
| A03-R1 | 交付 `19ab03c849bfab3dcde2dc86be37c59f3add1ebe`；集成 `a1c3c3b2d452ecbdf5c57a8b7372e7d53de0f8d8` | 原有限离线持久化、UNKNOWN 对账、防重复与报告范围 |
| I01-A | 交付 `3fdc5d37e221fc73410f197605f5d7b8878182d5`；运行候选 `be68b8d7c645de556d601458d1d493258f063721`；集成 `f356dde53bf9cc852eb35fc3710c884c397ce6c5` | A01 公共离线消费与 N/E/U synthetic 三路径 |
| D01 | 集成 `c78c8a123437e6c53096e0c48f1dd14aad10c2c3` | 历史 Windows CPython 3.9.13 / Pillow 11.3.0 的有限清洁安装证据 |

A06 第二最终独立检查原包 HOLD 和未知中间结果版本拒绝各一次；F01 已关闭。155 成员的原独立清单已由调度核对，首轮 507 成员保全，7 PID 已释放。本地集成恰好新增122路径，原主线保全，3项窄字段检查通过。这些是已封存历史结果，本次发布没有重跑业务。

I01-A 独立三路径累计3目标/3 dispatch，U 一次 MATCH、零重发，19进程释放。A03-R1 集成时70合同、3 native、62 A02兼容检查通过。以上数量不能代表真实平台、OCR、B 算法或任意规模稳定性。

当前源码、消费者和依赖声明完整提供；未重新做清洁安装或 wheel 验收。公共 C01、A01、A02 继承已发布第一阶段范围。

## 随包原件

- [A06 最终独立报告](records/A06-second-final-review-report.md.txt)、[调度接受](records/A06-coordinator-acceptance.md.txt)、[本地集成](records/A06-local-integration.md.txt)
- [A06 原件接收 stdout](records/original.stdout.txt.txt)、[结果版本拒绝 stdout](records/unknown-stage-result.stdout.txt.txt)、[释放记录](records/release.json.txt)
- [A06 完整证据索引原件](records/review-manifest.json.txt)：索引的大部分成员留在本地，不包含在本交接包内
- [A03-R1 最终调度接受](records/A03-R1-final-coordinator-acceptance.md.txt)、[本地集成](records/A03-R1-local-integration.md.txt)
- [I01-A 独立报告](records/I01-A-review-report.md.txt)、[调度接受](records/I01-A-coordinator-acceptance.md.txt)、[本地集成](records/I01-A-local-integration.md.txt)
- [D01 调度接受](records/D01-coordinator-acceptance.md.txt)

原件包含记录当时的“未推送”“REVIEW”及历史路径；这些描述不覆盖阶段二发布状态。保留原件 SHA，未改写历史证据。

## 尚未闭合

B 共同字段映射、历史引用必要性、执行准入、合格真实单题，以及真实 B→A 正向业务仍未确认。A06 HOLD + I01 synthetic 不能合成正向联合通过。A04 真实平台仍阻断，A05 仅题22历史成功。发布分支可获取不等于 B 已确认合同或验收。
