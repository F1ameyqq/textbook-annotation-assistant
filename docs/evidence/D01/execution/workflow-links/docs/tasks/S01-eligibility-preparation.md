# S01 来源完整性门禁准备

日期：2026-10-16。状态：**DRAFT_WAITING_A02**。这是 A03/I01 前的 A 内部合同准备，不是新开发阶段、实现、验收或 B 确认。A02 仍按冻结旧合同完成独立验收；当前不改公共模型或固定样例。

依据：[A01 正式验收的 S01](A01-review-final-report.md)、[固定交付反例](../evidence/A01/review/formal/primary-confirmation/S01-fixed-delivery-gate.json)、[C01 公开实现](../contracts-implementation-v1.md)、[A03 准备](A03-preparation.md)。核对的公共实现来自根提交 `402170b7361e4a47c12e5726cc73f684340a4f6d`；本轮仅阅读既有反例，没有重跑测试。

## 已确认的缺口

A01 原 SourceBundle 的内容摘要 `1b662ac5c9ac56b4a0c2e9826ff4cc2c512365c58ca2fafda36df110f9cfc32d` 保持不变、附属说明仍标记 coverage_eligible=false / denominator UNKNOWN，追加合成图谱和 PRE_APPLY PASS 后，旧公共加载器仍接受。当前模型只有非空 scope_manifest 与 basis 文字，无法对独立分母的资格作机器校验。此反例没有平台计划或写入，不是实际质量 PASS。

## 最小字段提案

优先在 SourceBundle 中增加声明，不新增独立 artifact，避免下游 CheckReport 自行升级来源状态。具体字段名与版本号由合同负责人在正式派发前冻结：

| 字段 | 候选值与含义 |
|---|---|
| scope_manifest | list[QuestionId] 或 null；null 是独立分母未知，空列表是已经独立核准零题 |
| scope_integrity.status | UNKNOWN / REFERENCE_ONLY / INDEPENDENT_COMPLETE / SYNTHETIC_COMPLETE |
| scope_integrity.basis | UNKNOWN / METADATA / HISTORICAL_REFERENCE / PLATFORM_RECORDS / INDEPENDENT_SCOPE_REVIEW / INDEPENDENT_SCOPE_SCAN / FIXTURE |
| scope_integrity.proof | 复用 Resource 的相对路径、media_type 和 SHA256；未知/参考状态可为空，完整状态必须提供可解析的版本化清单 |

proof 清单至少绑定 book、scope、明确预期页面、原图 ID/尺寸/摘要、逐页检查结果、题目清单和独立检查依据；公共加载器实际解析并交叉核对。proof 不反向引用待检查 QuestionGraph，也不把 SourceBundle 自身摘要写入造成循环。参考候选保留在原历史资源；迁移不会删除旧清单或原件。

## 六条门禁与最小反例

| 门禁 | 接受/拒绝边界及必要反例 |
|---|---|
| 状态 | UNKNOWN、REFERENCE_ONLY、缺字段不能支撑 PRE_APPLY 的 coverage PASS 或整份 PASS；planner/执行资格入口再核对同一条件。正常可读取诊断包，不等于可自动执行 |
| 范围与证据 | INDEPENDENT_COMPLETE 必须由独立检查依据支持，书/范围/页面/图像绑定/逐页结果/题清单一致；缺图、漏检页、错摘要、错书或清单矛盾均阻断；有限范围不外推全书 |
| 模拟隔离 | SYNTHETIC_COMPLETE 仅支持 FIXTURE、全合成资产与证据链、SIMULATED 执行；含 ORIGINAL 图像的来源不能套用。原固定 A01 来源追加合成 PASS 必须被拒 |
| 版本隔离 | 旧 schema/exchange 仅走明确的归档读取/复现入口，新自动入口默认拒绝旧版本资格；旧版可解析不代表新版本可执行，未知版本失败关闭 |
| 显式迁移 | 新 SourceBundle 修订/摘要及下游引用必须重新生成；旧对象/样例/反例字节保留。普通旧来源默认 UNKNOWN 或 REFERENCE_ONLY；旧合成样例只有经显式转换才能成为 SYNTHETIC_COMPLETE |
| 零题 | null 与 [] 不混用；完整且核准零题时无题目动作、无虚构题目，覆盖显示“已检查、零题、无执行动作”，不计算0/0为100% |

A04 目录题节点、平台已保存框、元数据页数只是已存在记录或参考资料，不能作为全部内容的独立题目分母。批次对未知分母应明确报告未知，不能只数成功题。零题来源可保存检查结果，现有要求非空图谱/计划的消费者需明确返回无动作结果；不以该提案隐含扩大题型或执行能力。

## 证明边界与落地顺序

结构、枚举、摘要及引用一致不证明“实际没有漏题”。INDEPENDENT_COMPLETE 与 OBSERVED 标签都不能替代真实独立检查流程和可审查证据。B 提供的检查算法及语义检查由 B 自行开发；本提案不代替其验收、不新增身份认证系统、不宣布共同合同已确认。

1. A02 原版本验收及本地集成结束后，协调唯一合同写入者；S01 与 A03 恢复扩展共同评估版本边界，仍属于已约定路线的依赖准备。
2. 先固定字段、proof 小型 schema、公共校验入口及迁移说明，再实施；明确 A01/A04 SourceBundle、A02 planner/targetcheck 与 BatchReport 的消费者影响。
3. 保存并回归原 S01 固定反例，以及上表的正反例；新合成样例只能证明模拟资格，真实自动资格另需来源与质量证据。旧版本原样复现和新入口拒绝旧资格两项分别记录。
4. 新版本未经独立验收和调度集成不得释放 I01 的真实来源自动资格；B 的接口采用仍待双方确认。

未解决事项：proof 的具体版本/schema、独立检查生产者和审查证据标准、空范围在批次中的公开表示、兼容入口/API命名。Pillow 根依赖声明和干净环境安装验证是独立的 D01 集成项，本文不把它视为已解决。
