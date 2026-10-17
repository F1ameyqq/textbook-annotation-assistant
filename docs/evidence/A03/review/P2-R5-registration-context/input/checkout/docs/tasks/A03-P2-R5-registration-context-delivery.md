# A03 P2-R5 登记上下文局部修复交付

状态：**REVIEW_WITH_CONTROL_RESIDUAL**。原正包与六项指定语义结果已记录；混合环的干净输入证明仍未闭合。允许的一轮局部修正已使用，按停止条件冻结，不再追加修复或 Package 调用。执行者没有自行记为接受。

base `e608b54b973b14ff55dd2c4530153f5fe7c931f4`，workflow `5fcb2e0084c92c20092cac19e33619128ad86d54`；工作树 `C:/Users/ASUS/.codex/worktrees/a03-runtime-recovery/1800`，分支 `codex/a03-runtime-recovery`。[任务原文](../evidence/A03/execution/P2-R5-registration-context/inputs/workflow/docs/tasks/A03-P2-R5-registration-context-rework.md) SHA256 `64026a73b55c904090544b92c3202208d68189c1c98953affc034b87d716bc69`。保留用户当前思考设置，没有猜测档位、改档、委派或合浮动主树。

## 实现与输入

[新统一入口及说明](../../examples/a03/P2-R5-registration-context/README.md) 将全局无上下文遍历与实际消费者绑定分开，补登记 target/观察对应字段比较。覆盖层 [registration.py](../../examples/a03/P2-R5-registration-context/registration.py) SHA256 `3f0281c5cfc9aeec99b11fa2de30ba40e9984a19dd0e651b747d99ebe29772ba`；[源码差异](../evidence/A03/execution/P2-R5-registration-context/source-difference.patch) 和 [执行前静态核对](../evidence/A03/execution/P2-R5-registration-context/pre-execution-static-audit.json) 固定代码及输入。全局不跳过 EvidenceRecord/Resource、正式 ID、typed frame、声明或混合 DAG，不将 None 当通配符。

R3 固定类 AST 未改，仍负责正式证据消费者闭包；R2 的完整 DAG、消费者声明/book/scope、Artifact hash/PRE 尾段仍执行。加载只移除旧模块输出初始化，不修改基类方法、Schema、版本选择或旧 pins。当前实现是静态覆盖层，不是产品 ABI、R17/PRE/native 接纳。

[raw Git 输入索引](../evidence/A03/execution/P2-R5-registration-context/input-index.json) 固定 68 项必要输入；[一次修正的补充输入](../evidence/A03/execution/P2-R5-registration-context/repair-input-index.json) 再固定 2 项。9 份 workflow 文档按 raw Git 保存；四个 R4 bundle/case/资源与 base 原件逐字节绑定；原 R3 未声明正式证据反例保持原字节。没有复制历史全集或产品源码。[原七例索引](../../examples/a03/P2-R5-registration-context/case-index.json) 和 [唯一修正版索引](../../examples/a03/P2-R5-registration-context/repair-case-index.json) 分开保存。

## 实际验证

先完成代码/输入静态检查，再逐例运行七个完整 `registration.Package.validate`。一轮后只复测混合环，总计 **8 次**；没有旧 36 矩阵、其他新用例、checker 修后全矩阵或产品调用。

| 场景 | 首轮实际结果 | 实际层与限制 |
| --- | --- | --- |
| 原 R4 registration-positive | STATIC_ACCEPTED | 完整入口返回；已到 DAG、声明/book/scope、Artifact hash、固定尾段返回。真实消费者 16，全局 frame 6，虚构 None-book 消费者 0。 |
| 原 R4 source-binding-negative | FRAME_REGISTRATION_BINDING | 实际登记消费者 source/snapshot scope 不一致，路径 r4-static/source-binding-negative/prefix.json。 |
| 原 R4 snapshot-binding-negative | FRAME_REGISTRATION_BINDING | 实际登记消费者 snapshot/source scope 不一致，路径 r4-static/snapshot-binding-negative/prefix.json。 |
| 原 R4 target-tuple-negative | FRAME_REGISTRATION_TARGET | Source/Snapshot kind/book/scope 均通过，Snapshot.target_id 与 canonical target_id 不同；路径 r4-static/target-tuple-negative/prefix.json/registration/target。 |
| 原 R3 R2-SCOPE-EVIDENCE-ID-01 | UNDECLARED_REFERENCE | origin-a-SourceBundle 的正式证据嵌套 ordinary ref 未声明；原消费者闭包保留。 |
| global-resource-hash-corruption | RESOURCE_HASH | r5-static/global-only-proof.txt；实际读入异常 trace 的真实消费者上下文数为 0。 |
| artifact-resource-frame-mixed-cycle | SHAPE_oneOf | 首轮控制构造错误：legacy PLAN_ACCEPTED 的封闭 payload 不允许新增 evidence 字段。输入和退出 1 原样保存。 |

唯一修正版仅复测第七项：复用冻结 R2 原本已有 Resource 字段的 event 分支，保留其 event_version 值，新增独立 Source/正式 EvidenceRecord/prefix/返回 Resource，得到 **MIXED_CYCLE**，进入继承 DAG 层。覆盖层源码未改，原六个场景未复跑。[实际结果汇总](../evidence/A03/execution/P2-R5-registration-context/results-summary.json) 连接全部八次结果及原始 stdout/stderr。

## 仍未闭合的控制残余

归档前核对修正版发现 `r5-static/cycle-prefix.json` 的 READONLY_ABSENCE_STARTED（sequence 8）内部 `initial_event_head` 没有随事件重链更新：

- 声明 sequence 7 hash：`87f8f86767e923c8fe7eb351c45eb57df3d6d4ebfdf855249fc7f5be025bbf84`。
- 实际 sequence 7 hash：`28ef8b468d67a04e9ba75fe3e41a45fb96f280deb95ddcef4cdc2097d6c195f9`。

Artifact、Resource、event 原始摘要及 frame exact ref 声明正确；上述内部头绑定仍不一致。它没有成为这次拒绝的更早原因，实际 MIXED_CYCLE 层已到达，但不能据此宣称控制的其余引用全部自洽。详见 [最短残余证据](../evidence/A03/execution/P2-R5-registration-context/control-residual.json)。八次实际错误码中最终七个场景均符合目标代码，场景输入证明只有六项闭合，混合环保持残余。

任务只允许一轮本范围修正，该轮已经使用；这里不做第二轮修复、再次复测、版本/预期放宽或另造替代控制。R5 整体仍交 REVIEW，由原独立验收决定下一步。

## 归档、保全与复现

[旧路径索引](../evidence/A03/execution/P2-R5-registration-context/old-preservation.jsonl) 和 [原 Git tree](../evidence/A03/execution/P2-R5-registration-context/old-tree.raw) 固定 28,113 个旧文件的 path/mode/type/blob、工作区字节摘要及 symlink 状态。封存前逐项核对，旧 R2/R3/R4、产品 src/tests、依赖、公共合同和 state 保持不变；新增仅在本任务三个授权路径。最终暂存/提交 raw Git blob 与清单核对，确切提交 SHA 在交付消息中给出。

[归档核对](../evidence/A03/execution/P2-R5-registration-context/archive-verification.json)、[完整新增清单](../evidence/A03/execution/P2-R5-registration-context/sha256-manifest.json)（仅排除自身）与 [自有进程释放](../evidence/A03/execution/P2-R5-registration-context/process-release.json) 一同封存。所有登记子进程均先保存脚本/输入索引 SHA、argv/cwd、限时和原始流，随后记 PID、退出/超时/alive；失败不覆盖。封存核对只读现有结果和文件，不再导入 checker。

最短只读文件复现，不调用 Package：

```powershell
Set-Location C:/Users/ASUS/.codex/worktrees/a03-runtime-recovery/1800
python -X utf8 -B docs/evidence/A03/execution/P2-R5-registration-context/archive.py --check
```

独立审阅可用说明中的 `run_case.py ... --readonly` 命令复现完整入口；这些命令在本轮封存阶段没有再执行。退出 0 表示结果与该输入预期代码一致，不代表控制输入完整合格或已获独立验收。

产品/planner/DB/native/网络/浏览器/平台/profile/凭据/OCR/模型/收费 API/安装/推送/B 或验收者联系均未发生。当前 profile、oracle、公用/B 合同采用和 I01 均未释放。字段重置专项仍为 **NOT_EXECUTED_NO_RERUN_VARIANT_OR_DELEGATION**，未复跑、变形、委派或建议再测。
