# A02：计划、目标检查与模拟执行

日期：2026-10-16。状态：**READY / 批准派发**；接到正式派发消息后开工，实际状态见调度记录。

## 基线、依赖与交付边界

- 代码基线：`见调度状态与正式派发消息`；workflow_commit、独立 worktree、分支及执行/验收对话 ID 由正式[调度状态](../coordination-state.json)提供，接单前记录实际值。
- C01 R1 已独立 ACCEPTED，交付提交 `4e42668ab28eda37a37285285d2f6c595d3bba12`；主调度已本地集成于 `223b0b3d9ae0bd50ef2ac045219a41ad41611856`，本任务起点以正式调度记录为准。
- 依据：[项目开发约定](../../AGENTS.md)、[A 侧调度](../coordination.md)、[开发计划](../development-plan.md)、[公共合同](../contracts-v1.md)、[C01 公共 API](../contracts-implementation-v1.md)。
- 使用 `1.0.0-a-proposal` / `c01-exchange-1` / `c01-fixtures-1`；A 内部接受不代表 B 已确认合同。
- 目标：固定 QuestionGraph → 自行计算 TARGET 检查 → 实际生成 ApplyPlan → 改变模拟目标 → 根据独立读回生成 ExecutionReceipt。
- 不等待 B 的识别或组题实现；PRE_APPLY 使用明确标注的合同桩，不把其 PASS 当成独立算法质量证据。

## 独占改动范围

- `src/annotation/delivery/planner/`、`src/annotation/delivery/mock/`、`src/annotation/quality/targetcheck/`。
- 专属 `tests/test_a02*.py`、`tests/fixtures/a02/`、`examples/a02/`、`docs/evidence/A02/execution/` 和 `docs/tasks/A02-execution-report.md`。
- 不改 contracts、C01 样例、公共政策、根依赖、父目录入口、source、geometry、B 的 precheck/coverage 或 runtime；不得覆盖他人改动。
- 包入口只在本任务独占子目录内建立；确需公共变更时交最小失败输入及提案，由调度指定整合者。
- 不新增依赖；使用已接受的公共 API，不复制类型定义或直接导入合同私有实现。

## 实现要求

1. 读取自包含交换包，通过 `load_bundle` / `validate_bundle` 验证；新产物使用 `seal_artifact`、精确引用和公共写出入口，保留资产相对路径及摘要。
2. targetcheck 自行比较当前目标、授权范围、政策及能力，输出 stage=TARGET 的逐项报告与具体 issue；不抄输入报告的 PASS。
3. planner 是纯计算模块，只读取图谱、两阶段报告、政策及当前快照，生成动作和预期效果；quality 不改目标，mock 才执行模拟变更。
4. 仅 PRE_APPLY 与 TARGET 两份不同阶段 PASS、同图谱/政策、当前快照与授权一致时生成 READY；缺报告、错误阶段、错版本、未决政策或能力未验证都阻断。
5. 普通选择题采用 SYNTHETIC_ASSUMPTION 时仅可模拟；不得把 W 独立/合并或组合题投影写成已确认政策。不支持的投影明确异常。
6. 计划和执行前均以显式当前快照调用 `assert_plan_ready`；记录图谱、报告、政策、目标与能力适用版本，旧目标快照不能继续执行。
7. 根据片段归属、选定答案闭包及政策生成框动作，保留原图绑定与平台表示分界；不得用题号、平台顺序或 bbox 充当内部动作/题目身份。
8. 每动作保留相关事实的 expected_before / expected_after 和依赖顺序；先前本程序造成的预期变化不能被误判为外部目标冲突。
9. 空快照的新题与非空快照中未映射的新题均允许 null 平台题目 ID；不得根据相同印刷题号猜测已有题归属。
10. 已映射题必须核对快照内真实 ID、平台目录引用及已有平台题序，动作目标与图谱映射一致；不直接比较内部目录 ID 和平台目录 ID。空字符串、缺失 ID、错映射、null 替换已有映射均拒绝。
11. UPDATE_FRAMES 只有公共合同要求的旧 APPLIED 基线、旧回执及 frame_update 能力齐全才可支持；未实现的差量形态显式阻断，不能降级为重复新建。
12. 模拟器提供可单独读取的目标状态和追加动作日志，执行函数响应、目标读回与证据比较分离；实际计算回执，不能返回预制 expected.json。
13. 至少支持正常生效、明确未生效、已生效但响应丢失三条故障路径；超时、读回失败或矛盾不足以确认效果时必须 UNKNOWN。
14. APPLIED 需读回匹配及模拟平台 ID；NOT_APPLIED 需明确 ABSENT 证据；UNKNOWN 为 INDETERMINATE / RECONCILE，整份回执 PAUSE_RECONCILE。
15. 三种结果均 replay_allowed=false；NOT_APPLIED 需重查目标并重新规划，不自动重放旧动作。UNKNOWN 暂停同书后续写入。
16. 模拟会话保留完整未决回执与同书阻断依据；换 action_id、run_id、另一题或另一 scope 不能解除该书暂停，其他书仍可独立模拟。
17. 本任务只验证当前模拟会话的阻断，不实现跨进程持久化、重启恢复或正式解除流程。缺少 ReconciliationResult 时报告接口缺口，禁止删 UNKNOWN 历史或私造字段解锁。
18. 演示汇总消费独立 scope_manifest，保留异常、跳过、未入图谱项和各题状态；分母不得只取可执行图谱或成功题。
19. 框保存、内容校验与最终提交分别记录；未验证内容保持 PENDING / CONTENT_PENDING，未提交保持 NOT_SUBMITTED，不得包装为 COMPLETED。
20. 所有输入/证据标明 SYNTHETIC，计划及执行回执标明 SIMULATED；仅诊断阻断链使用合同的 NOT_EXECUTED。模拟通过不构成真实平台或算法验收。

## 必交正反例与可观察结果

| 用例组 | 必须观察到的结果 |
|---|---|
| 正常多题；两章节同印刷题号；跨页/共享片段固定图谱 | 按内部身份生成不同动作，来源闭包正确；真正改变模拟目标，读回与预期效果可比较 |
| 两阶段检查缺失/非 PASS/错阶段；政策或图谱变更 | 无可执行动作，报告可定位原因，模拟状态未变 |
| 目标版本变化、授权错书/错范围、能力 UNKNOWN/错平台版本 | 计划生成或执行被拒绝；旧计划不得盲执行 |
| 空快照/非空快照新题；合法已有映射；缺失/错序/空字符串映射 | 合法路径通过；非法映射失败，不能猜测或绕过已有身份 |
| 正常 APPLIED、明确 NOT_APPLIED、保存后丢响应、读回矛盾 | 相应结果及证据正确；未知结果保持同书阻断且不重复建框 |
| UNKNOWN 后换运行/动作/题/范围；另一书 | 同书继续阻断；完整历史仍在；另一书不被无依据全局暂停 |
| 异常/跳过/未入图谱项；框已保存但内容未可读 | 分母和题级状态完整；内容 PENDING、提交 NOT_SUBMITTED，不生成完整完成结论 |

## 交付与验收

- 交付确切 head_commit、base_commit、workflow_commit、合同/样例版本、环境、最短运行命令、完整输入输出、故障注入命令与实际报告；命令必须在交付提交上可复现。
- 报告逐条列通过/失败/未执行及原因，说明 mock 范围、投影支持范围、UNKNOWN 的内存边界及 A03 接口缺口；模型调用/费用和平台动作均为 0，算法精度及真实运行成本未测。
- [独立验收](A02-independent-review.md)读取冻结提交并另造反例；执行者交付仅进入 REVIEW，不能自行标 ACCEPTED 或释放 A03。
- 禁止登录、联网调用平台、OCR、书级送审/送交、付费模型和原始视频上传；A05 题 22 不重放。真实测试书授权不扩展本离线任务。
