# A03 P2-R4：桥接接口与登记样例独立复核

2026-10-17。继续原验收对话 `01a145aa-8d59-7c70-8d81-731712103a9a`，保留用户当前思考设置，续发省略 thinking/model，不依据旧记录改档。

## 冻结边界

- 只读交付工作树：`C:/Users/ASUS/.codex/worktrees/a03-runtime-recovery/1800`。
- base `87606b73e0754fa670491d9fb958a416c26bfe88`；交付 `e608b54b973b14ff55dd2c4530153f5fe7c931f4`；执行 workflow `ef1d2f4a20971b416afae500889aa5c090dfe89b`。
- 目标提交报告 `docs/tasks/A03-P2-R4-bridge-registration-delivery.md`，SHA256 `95cf2746bb9ceb5a1857f3e8babca04892d8481c74c11d3ee256d5eeb26055f9`。
- 目标清单 `docs/evidence/A03/execution/P2-R4-bridge-registration/sha256-manifest.json`，SHA256 `5c5823f1b146574202fbfd00e066aafc1697d017e40c12cab66b9330cb75d28e`。
- 目标接口表 `examples/a03/P2-R4-bridge-registration/bridge-interface-proposal.json`，SHA256 `b57d0af5d72a03c4b16e6eeedc267bda50f1dfcf022728b1f107f5b158a22207`。
- [执行任务](A03-P2-R4-bridge-registration-preparation.md)、[R3 调度收口](A03-P2-R3-evidence-closure-coordinator-decision.md)、[本次前检](../evidence/coordinator/heartbeat-20261017-0944/A03-R4-delivery-preflight.json)。本次审阅 workflow 由派发消息给精确 SHA，不能合浮动主树。

调度前检核对 110 清单项与清单自身共 111 新文件的磁盘/raw Git 字节、28,002 旧 Git 路径不变、6 workflow 文档/12 产品文本/15 静态输入/5 资源共 38 原始输入。工作树干净，完成 turn `01a1491e-d32b-71d0-a7a7-9c1224a76169`；7 个自有同步运行退出 0/1/1/0/0/1/0，失败真实保留，没有当前 OS/profile 扫描。前检未运行交付代码，不是独立功能验收。

## 只复核两项

1. **桥接接口方案。** 对照固定任务与实际基线源码，只作文本/AST 检查：19 个现有入口的签名/输入输出/版本限制是否准确；新增私有 PRE 接纳边界及 BridgeContext 等类型是否明确为提案；contracts、targetcheck、planner、persistent mock、runtime 的 exact refs、观察凭据、版本/pins 与当前资格责任是否足以制定下一份有界实现任务。检查单题 INITIAL→TARGET→计划→UNKNOWN→恢复头→晚到 receipt→POST/Batch 链的接口一致性，区分真实可达证明与未执行的方案。不能批准版本改标、宽泛白名单、删 UNKNOWN/登记历史、旧 stub 或恢复旧尾；计划算法与事实比较语义保持。若仍有实现前必须决定的缺口，给少量明确的接口/字段/责任选择，不展开新实现或大候选。原生、oracle、公共合同与 B 采用依然未批准。

2. **登记分支正包和三个直接控制。** 通过 raw Git 隔离必要冻结输入，先读四包及其总入口加载器。允许把固定输入/输出根定向到独立审阅目录，但不得改变 Package/Schema/判定语义；保存实际加载源码 SHA 与定向方式。只重现四个完整包各一次，不运行 prepare.py 重新生成作者产物，不跑旧 36 矩阵。独立核对 Artifact/Resource/event 摘要、exact refs、完整 prefix、合法 typed frame 及 Source/Snapshot/登记 scope/target 一致性，不能只看错误码相同。

作者报告：正包 `registration-positive` 在 `FRAME_REGISTRATION_BINDING` 失败；Source 与 Snapshot 负控在实际消费者层拒绝；target 负控有语义不一致，但同样错误被全局扫描 book=None 遮蔽，尚未证明 target 校验有效。请独立区分“样例自身不合法”和“合法样例被无上下文全局遍历错误拒绝”，核对继承 R2 check.py 的登记谓词与全局 evidence 扫描、R3 覆盖层、实际最短路径。全包正例失败与仅局部谓词成立不能混称分支通过。

不修改 checker、不绕开全局扫描或换 Resource 放置路径追求通过、不先修正后再测 target。当前只确认有无已观察的确定缺口与被遮蔽部分，给最小局部修复范围；若确需修复由调度另派。保留此前 R3 消费者闭包、SESSION-02/CONVERSION-07 的有限静态接受，不把它们扩张成登记分支或整体功能通过。

## 输出及停止

给出两项分别结论：接口方案是否达到有限设计接纳条件，以及登记分支 ACCEPTED_STATIC_LIMITED / REWORK / BLOCKED 与确切依据。总体不得把当前失败正包记 ACCEPTED。执行者遵守停止条件而未修规则本身不是越权或交付缺陷。确认本轮直接缺口后冻结，不无限搜索未授权边界、不自行启动下一轮。

只新增 `D:/1800/docs/tasks/A03-P2-R4-bridge-registration-review-report.md` 与 `D:/1800/docs/evidence/A03/review/P2-R4-bridge-registration/`。保存必要输入 raw Git 索引、实际加载源码/pins、四包独立结果、stdout/stderr/argv/cwd/PID/限时/退出、报告及全清单（自身除外）；旧归档与工作树保持原字节。报告提供最短只读复现方式，区分作者运行错误、审阅错误与语义失败，完成后释放自有运行并结束。

禁止产品/planner/DB/native session 运行、修改任意产品或旧材料、浏览器/平台/profile/凭据/OCR/模型/收费 API、安装依赖、提交/推送/集成、联系执行者/B/其他任务。产品/native/oracle/I01 不释放。字段重置专项保持 `NOT_EXECUTED_NO_RERUN_VARIANT_OR_DELEGATION`，不复跑、不变形、不委派、不建议再测。
