# A03 P2-R8-R4 调度结论

2026-10-18（Asia/Shanghai）。target `435aaee2d140e82d3237ce8902d594a1aee70aad` 的 **N6 完整历史重算、一个 PRE 依赖缺失控制，以及 N7 的一个 runtime 初始化中断分支有限 ACCEPTED**。新 N1 必要前序通过。产品相对 `d9ed692db9ab8e9277f8ffd09e040451e8b8f65f` 未变，本轮关闭验证缺口，没有新的产品修复。A03 整体仍为 REWORK；native 产品尚未整体集成，I01 未释放。

依据：[独立报告](A03-P2-R8-R4-remaining-review-report.md)，SHA256 `4666400a3bc1f9227601bcc1d47b4335e33a8ebf427a3dc72872221dda4d5945`；[调度复核](../evidence/coordinator/heartbeat-20261018-0459/review-audit.json)。独立对话 `01a145aa-8d59-7c70-8d81-731712103a9a` 的 turn `01a14b92-b51a-7381-a112-e5d37da18cad` 已完成，cursor `abdea222-4697-4046-86b1-a5dc48889fac:45`。

## 已接受范围

N6 向 verifier 提供完整20项正式历史，保留原 UNKNOWN、晚到回执、解决结果和 POST/Batch；产品从已登记的创建输入 anchor 实际重算一次，完整计划和动作一致，6项递归 Resource 实体与摘要一致。仅移除一个由 PRE source_integrity 明确引用的 EvidenceRecord 后，闭包层以 EVIDENCE_ID_MISSING 定位拒绝。双库前后字节不变，permit/effect 无新增。

N7 通过现有 before_completion 钩子产生一次同进程受控异常，原异常传播；runtime 有表但没有完成标记和 anchor，随后正常 open 一次拒绝。目标库未创建。这不是进程崩溃或目标初始化全部故障点的证明。原 R3 N7 FAILED 和“新增外层诊断断言过严”的分类永久保留，未重跑或改写为 PASS。

调度核验660条清单及清单自身，共661个文件；409份 raw Git 输入和76份隔离种子逐字节对应固定提交。14个父进程与4个子进程的登记、原输出和退出记录吻合；产品三组各一次。审阅者两个元数据脚本失败原样保留。

调度另建三个自有 immutable 数据库副本，核对独立 N1 双库和 N7 中间库：20项正式 artifact、唯一效果、4次观察、原 UNKNOWN、正式 receipt/progress/fact/intent 和新 POST/Batch 绑定成立，内容 PENDING、NOT_SUBMITTED。N6 保存的实际返回、SQL anchor、完整历史和递归资源闭包交叉吻合。没有连接原库、导入产品或重跑功能。

调度自己的首次元数据断言漏遍历嵌套 JSON Resource，并将 ImageAsset 附加字段与四字段 Resource 直接比较；已保留首轮脚本与失败输出，修正后只复核字节/SQL/引用，没有重跑产品。一次只读路径查询误猜模块路径，后续由文件列表纠正；不把查询错误算作产品失败。

## 下一有界范围

原 P2 要求的三条可搬运演示中，单题“已生效后丢回执”已在 R8/R4 得到证据。现在继续原执行对话完成[正常与明确未生效演示](A03-P2-R9-minimal-demos.md)，保留 A03 用户自选 model/thinking。

当前 synthetic_precheck 明确只接受固定32×32、单题、两片段语言。下一轮不把两题夹具当作现成支持，也不暗改 oracle/版本/pins。正常多动作、混合尾段及充分/不足 ABSENT、跨 scope/run/书未决、竞争者、其他故障切点、版本/身份/资格负例、归档转换、报告/分母/次数边界继续按原覆盖表保留。后续多动作能力须有明确的有限实现与采用范围，不让当前单题演示替代它。

这是本地证据归档与范围接受，不是产品集成、远端推送或 B 共同确认。B 只读/HOLD 包的版本映射仍待双方确认。字段重置专项始终 `NOT_EXECUTED_NO_RERUN_VARIANT_OR_DELEGATION`；零平台、浏览器、凭据、OCR、付费模型、A05题22及书级送交操作。
