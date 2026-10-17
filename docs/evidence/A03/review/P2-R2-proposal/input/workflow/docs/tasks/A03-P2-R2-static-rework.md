# A03 P2-R2：按调度决定收口静态候选

2026-10-17。继续原执行对话，明确 `xhigh`。base=`7fdbde8f16569fd3bc399013115e13269d5d33fa`，原工作目录 `C:/Users/ASUS/.codex/worktrees/a03-runtime-recovery/1800`，分支 `codex/a03-runtime-recovery`。workflow 是包含本任务的调度提交，消息给出确切 SHA，不合并浮动主树。

输入为[独立审阅](A03-P2-R1-proposal-review-report.md)及[主调度设计决定](A03-P2-R1-proposal-coordinator-decision.md)。本次只批准一次有界静态修订；产品/DB实现、公共合同采用与 I01 均未放行。

## 唯一改动范围

只新增 `examples/a03/P2-R2-proposal/`、`docs/evidence/A03/execution/P2-R2-proposal/`、`docs/tasks/A03-P2-R2-proposal-delivery.md`。旧 candidate-v2、旧检查器、旧 Schema/API/profile、任何报告或失败证据逐字节不变。新纯静态检查器可使用标准库和已有依赖，不 import 产品，不运行旧功能场景或 DB，不安装包。仅导出必要冻结输入，不复制历史全集或重复生成大量无关包。

## 本轮必须闭合的三个缺口

1. **全包跨 scope 递归消费者**：按选定的 typed frame 边界实现静态验证。提供同书两 scope、不同计划、含嵌套 Resource 的完整静态包，经唯一总入口检查成功；普通非 frame 引用仍同 scope。错误 scope、漏声明、他书、伪装 frame 和 Artifact/Resource 混合环分别在明确层拒绝。不能只调用 prefix_check 绕过外层消费者。
2. **session 与 H0→Hfinal 一致性**：冻结 API/Schema 语义和静态检查，应拒绝审阅归档中的会话不一致与初始头不在链两项诊断；同时有符合三读/计数/owner/fence/登记/target/唯一fact规则的最小完整正值。读序列及 session 窗口外事件拒绝要有可定位结果。静态校验不声称真实锁、读取或 CAS 已通过。
3. **初始类型与完整转换候选**：消除新 Source 在 Schema 允许、语义却不注册的矛盾，明确受支持的新初始 Source/Graph/Snapshot/PRE 等类型。给出完整静态目标、旧新映射及摘要闭合；不可转换的旧派生 PRE/plan 明列仅归档及原因，新派生对象另列来源，不假造等价映射。按决定区分 INITIAL/POST_HOLD，并表示 COMMITTED 唯一接纳点与各中断状态。完整候选依然是 STATIC/UNIMPLEMENTED，没有 native registry/run 资格。

## 规范收口与运行证据分层

将主调度决定中的预算、逻辑 session/lease、已知DB profile-meta+event接纳及旧已打开 writer 的排他条件、R17单头原生路径与多头值层角色、oracle候选和证据保全逐项写入新规范。提供一个简短“决定编号→规范位置→样例/检查→未来功能证据”表。

oracle 必须有可审阅的固定来源与五项独立预期，给 exact 输入摘要、判据及纯静态 verifier 草案摘要。不能靠同一 producer 的输出自证、graph hash 相等或自己给 PASS 来替代五项比较。没有真实调用/接纳的地方保持 NOT_EXECUTED/UNIMPLEMENTED；可列静态比较结果，但不能生成原生 PASS 资格。

R17一动作计划需说明由未改A02 planner可生成的输入与动作依据；本轮不执行产品 planner。给清晰的后续最短可达场景；若无法静态说明其可达性，明确阻断并冻结，不裁剪旧计划、不续旧尾、不跨计划/scope聚合。

本轮不要求实现所有未来功能，也不扩大到新算法或一般迁移框架。上述限定模型若仍不自洽，给最小证据和具体剩余选择后结束，不自行放宽规则或追加无限轮次。

## 交付

给 exact 新 profile/完整 pins/API 摘要、唯一候选选择规则、改动和消费者影响、最小正反包、静态检查命令和原始 stdout/stderr/退出记录。新运行从启动即写持久日志；保留失败、预登记与进程退出。清单覆盖所有实际产物并排除自身；核对旧 Git 原件未改，工作树干净，冻结确切提交、报告、清单后交 REVIEW。主调度再安排同一独立审阅者。

全部离线。禁止产品/DB/原生session/网络/平台/浏览器/profile/凭据/OCR/模型调用；不推送、不联系B或验收者，不改调度state。既有自动安全审查拒绝的字段重置专项继续 **NOT_EXECUTED_NO_RERUN_VARIANT_OR_DELEGATION**，不复跑、变形、委派或列入后续测试请求。
