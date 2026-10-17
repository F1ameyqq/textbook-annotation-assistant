# A03 P2-R5 登记上下文静态覆盖层

状态为 **REVIEW_WITH_CONTROL_RESIDUAL**，等待独立验收。原 R4 正包完整接受，Source/Snapshot/target 三个负控及正式证据声明、全局 Resource 摘要两个防回归控制到达预期层。混合环修正版实际在 MIXED_CYCLE 拒绝，但内部 initial_event_head 未随重链更新，仍不能记为干净的防回归证明。一轮局部修正已使用，现停止。

## 代码差异

[registration.py](registration.py) SHA256 `3f0281c5cfc9aeec99b11fa2de30ba40e9984a19dd0e651b747d99ebe29772ba`。这是新静态入口 `Package.validate`，继承固定 R3 正式 EvidenceRecord 消费者闭包及 R2 完整 validate 尾段，没有复制产品或修改旧文件。逐段对照见 [source-difference.patch](../../../docs/evidence/A03/execution/P2-R5-registration-context/source-difference.patch)，仅用于评审，不是向旧路径应用的补丁。

- 实际 Artifact/frame 消费使用 R3 的 contexts、formal ID catalog、独立 found/declared、active consumer 防递归与混合图。合法外层 Source scope A 和 frame scope B 保持独立。
- 没有真实消费者的全局遍历继续读取每条 EvidenceRecord Resource、检查原始 SHA、确切 ArtifactRef、typed prefix 结构/根位置及 frame 声明，并保留所有图边。正式 ID 列表仍由固定 Schema 定位；全局还解析这些 ID，但不创建 book=None 的消费者。无跨上下文通过缓存，None 不作通配符。
- 登记 Source/Snapshot 仍为 exact 四元组、正确 kind、同书/同 scope，并绑定实际消费者 book。canonical prefix.target_key 与 event、观察、观察业务值及 baseline 中已有对应 target 字段比较；Snapshot 只比较现有 target_id/authorized_scope_id，没有捏造 platform_namespace 字段。观察的 source/snapshot/scope/registration/store/session 与登记 payload 对应。
- `load_static.py` 固定 R3 源码和 R2 pins 文件 SHA，只重定向未使用的输出变量并去掉模块级 mkdir。原 R3 Package 类 AST 含位置保持完全一致；没有调用 main、oracle comparison、session 或 conversion 函数。这样只读复现也不会在旧目录创建输出。

正包经过真实消费及全局两次 prefix 遍历，记录 16 个真实消费者、6 个全局 frame、26 个图节点；book=None 的真实消费者为 0。源码只读 trace 确认已到混合 DAG、消费者声明/book/scope、Artifact hash 和固定 R2 返回尾段。静态接受不产生当前写入资格。

## 有界输入与实际运行

[case-index.json](case-index.json) 固定最初七例，四个 R4 bundle、原 case 与资源逐字节对应 base。前三个防回归输入中的原 R3 反例直接复用冻结原件；全局 hash 控制仅追加一个未消费的独立 EvidenceRecord，故损坏在无真实消费者的全局读入发生。

第七例首次错误地向不含 evidence 字段的 legacy PLAN_ACCEPTED payload 加字段，在 SHAPE_oneOf 拒绝，结果和输入原样保留。唯一一轮修正复用已经具有 Resource 字段的冻结 R2 event 分支，事件版本值、Schema、旧样例位置/pins 全未改动；修正版见 [repair-case-index.json](repair-case-index.json)。它用新增 Source A → 正式 EvidenceRecord → 新 prefix Resource → frame A → 返回 Resource → 同 Source A 构造图环，Artifact/Resource/event 原始摘要与 frame 引用声明均正确。

归档前输入审计发现修正版 READONLY_ABSENCE_STARTED（sequence 8）的 initial_event_head 仍是原前驱值，和重链后的 sequence 7 摘要不同。详见 [control-residual.json](../../../docs/evidence/A03/execution/P2-R5-registration-context/control-residual.json)。这是控制构造残余；MIXED_CYCLE 实际拒绝并不消除该问题。本轮不进行第二轮修正、第二次混合环复测或其他边界搜索。

总计八次完整入口调用：七例首轮，混合环一例复测。覆盖层源码在八次调用间未改。原 36 矩阵、产品/DB/native/planner/网络/平台/模型均未运行。字段重置专项为 `NOT_EXECUTED_NO_RERUN_VARIANT_OR_DELEGATION`。

## 只读复现

以下命令提供给独立审阅，本轮封存阶段没有再次调用 Package：

```powershell
Set-Location C:/Users/ASUS/.codex/worktrees/a03-runtime-recovery/1800
# 正包完整入口，仅读取输入并向 stdout 输出结果。
python -X utf8 -B examples/a03/P2-R5-registration-context/run_case.py registration-positive --readonly
# target 应在 FRAME_REGISTRATION_TARGET 拒绝。
python -X utf8 -B examples/a03/P2-R5-registration-context/run_case.py target-tuple-negative --readonly
# 仅核对归档、输入和旧文件；不导入 checker 或产品。
python -X utf8 -B docs/evidence/A03/execution/P2-R5-registration-context/archive.py --check
```

`run_case.py` 退出 0 仅表示实际错误码与该输入的预期相符，不表示场景已被独立接受；混合环控制仍有上述残余。所有产出型入口使用 xb 防止覆盖，不能据此再次执行本轮已结束的七例。
