# A03 P2-R1 提案：调度决定与下一轮边界

2026-10-17。独立静态审阅为 **REWORK**，主调度确认该结论。提案 `7fdbde8f16569fd3bc399013115e13269d5d33fa` 尚未整体采用，A03 功能未接受，I01 不释放。

[独立报告](A03-P2-R1-proposal-review-report.md) SHA256 `265d5b8a67548b4e6322c105859475a852ca6d82bc8c0c04ec10bf2eedb411f0`；[清单](../evidence/A03/review/P2-R1-proposal/sha256-manifest.json) SHA256 `68b7c8f16f0a5973fa20e962525b8dab12b095b85b2343e95e6373ae38d152ac`。主调度核对309项归档、读取具体校验源码和诊断，并运行只读归档核验，退出0，见[预检](../evidence/coordinator/heartbeat-20261017-0649/A03-review-preflight.json)。没有重跑产品、DB、旧动态场景或被拒的专项。

源码中的外层引用递归与 frame scope 校验相互冲突；两个 session/CAS 静态矛盾未被拒绝；新 Source 类型的结构与语义入口不一致。这些是下一轮明确修复对象。未运行功能与设计缺口分开记录。

## 本调度选定的设计约束

下列决定仅约束 **A 侧离线合成恢复候选**，供下一轮静态修订。不是公共合同发布、B 接受、产品实现授权或真实平台预算。旧七 Schema/API/profile 与全部历史原件保留。

| 事项 | 选定约束 | 仍须证明 |
|---|---|---|
| 新版本 | 采用显式新 profile、完整 pins/API 摘要、按精确版本选择的方向。另立新候选，不覆盖 candidate-v2。 | 结构/语义消费者一致，旧版本只读及拒绝路径；最终 exact pins 仍待独立审阅。 |
| 全书跨 scope | 采用受类型和字节约束的 journal-frame 子消费者边界。只有已识别的 prefix.frames 可终止外层递归；每个 frame 递归声明其普通引用，scope 从确切计划或登记实体推导。planless 且没有 scope 依据时为 null。非 frame 普通引用仍严格同书同 scope，全局混合 DAG 检查仍适用。 | 同书两 scope 完整包通过同一总入口；伪 frame、漏声明、他书、错误 scope 和混合环拒绝。全书原生完整性不能由静态包自证。 |
| 未尝试只读预算 | 选定独立持久计数的最多 **3 次实际读取**，包含最终 currentness 读；每读2秒、entry8秒、parent60秒、busy1秒、gate5秒、lease10秒/续期2秒，均由最早绝对期限截短。retries=0；读前计数，崩溃耗次；同 entry/call 接管或重开不重置。无 intent 不借用 intent 计数，不自动换 call 循环。 | 三读的准确时点、失败/耗尽和永久唯一 fact key；后续功能证明计数及期限，而非值包自报。 |
| 排他与 CAS | 选择有持久记录的 logical readonly session；中间可释放 OS gate。所有受控目标写入口、claim/takeover 均需尊重 active session。最终第三读在短 gate 内，随后只做本地校验和 CAS，不暗加第四次目标业务读。H0 必须是本 session STARTED 前真实头，至 Hfinal 的窗口只能有本 session 许可记账；owner/generation/registration/target/session/read 绑定一致。 | 死亡/过期 session 明确收口，lease 失效即暂停；不得声称新增逻辑锁已实现。若静态协议无法证明所有写入口覆盖，应列具体阻断，不退化成布尔标志。 |
| 已知 DB 接纳 | 选择显式接纳事务中的持久 profile meta 判别 + adoption event，新入口必须校验二者一致，旧严格 meta 比较必须拒绝新库。只接纳 exact 已知合成格式；不接纳未知库。接纳必须先有可核对的排他和旧 writer 退出条件，不能只防重新 open 而忽略已持有连接。 | 明确 meta 键、版本、事务/崩溃状态，跨 runtime/target fence 的顺序及不一致时停止效果；保留旧行/hash。无法在限定模型闭合则阻断接纳，不扩大自动迁移。 |
| R17 | 原 R17 的新 POST/Batch、精确有效结果、新检查、保留 UNKNOWN、拒绝旧报告/直接改 VERIFIED、PENDING/NOT_SUBMITTED 全部保持。下一段原生正向证据选用 **未改 A02 planner 生成的真实最小单动作计划**：UNKNOWN、null 原 receipt、终局 head、晚到完整 receipt、独立 report 读。不剪裁旧计划、不恢复旧尾。 | 单头路径也要证明可达性。多头/不同 snapshot 保留为值层表达与绑定验证，不能算原生恢复通过；在当前首 UNKNOWN 即停模型下不批准伪造多头历史或跨计划聚合。原生多头若未来需要，另立历史模型范围。此分层不豁免原 R17 的可达行为要求。 |
| 合成 PRE | 采用独立固定 oracle + 五项真实比较 + 私有 run 接纳方向；明确 INITIAL 与 POST_HOLD 两种上下文。INITIAL 不制造 hold；POST_HOLD 需确切 hold id/head 及新观察。两者都不能复制旧 PRE stub 改 ID/时间。 | 下一轮提供 exact oracle 输入来源、摘要、五检查判据和纯静态 verifier 草案供独立审阅。此次没有批准任何尚未给出的 oracle/实现 digest；不得冒充 B 质量或原生接纳。 |
| 转换接纳点 | completion manifest 的写入/rename 仅是准备；选择追加的 **COMMITTED 状态记录**为唯一完成接纳点，它引用已落盘 manifest 的摘要。manifest 不回指 COMMITTED，避免自引用。rename 后未 COMMITTED 仍 INCOMPLETE；重开只读，不自动补提交，重做用新目录/新 ID。 | 完整静态目标及可解释的旧/新映射；旧 PRE/plan 的归档与新派生资格分开。新初始类型结构/语义一致；中断点实测留到功能阶段。 |
| 证据保全 | 接收历史 NOT_RETAINED 作为不可修复的已知限制，不把它记为通过或要求重建旧原件。采用新运行预登记、持久目录、原始流、失败 finally、退出及不可覆盖 run id 的保全原则。 | 后续所有新运行必须落实。缺失历史不得成为对未来失败删除证据的理由。 |

所有涉及 Exchange、跨 scope 消费者、Receipt/POST/Batch 的变更仍属待双方确认的接口提案，不改 B 的排期或确认状态。静态样例不取得平台/数据库执行资格。

## 下一步

批准一次[有界静态修订](A03-P2-R2-static-rework.md)，先关闭三个已证实的自洽缺口，并将上述选择落实为可核对的规范和最小样例。**不批准 runtime/公共合同产品修改。** 冻结后由原独立审阅对话复核，再决定是否可派实现；相同核心缺口若仍不能收口，保留具体残余并重新裁定范围，不自动进入无限修订。
