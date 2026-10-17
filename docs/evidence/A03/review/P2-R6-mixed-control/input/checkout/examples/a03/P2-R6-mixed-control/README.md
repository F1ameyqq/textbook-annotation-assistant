# A03 P2-R6 单一混合环控制头修正

状态：**REVIEW**，等待原独立验收。仅制作一个候选，先完成独立数据检查，再使用完全不变的 R5 `registration.Package.validate` 完整调用一次。实际在继承 MIXED_DAG 层得到 MIXED_CYCLE；不表示恢复功能或 I01 已接受。

## 唯一数据变化

来源为 base `323013c4f0dbae75368e56db60147a8057368d1f` 中的 R5 mixed-cycle repair-01。书籍、scope、版本、Schema、声明、旧证据、历史事件及 Artifact 全部保留。只修第 8 条 READONLY_ABSENCE_STARTED 的 initial_event_head.hash，使其等于实际第 7 条 event_hash：`28ef8b468d67a04e9ba75fe3e41a45fb96f280deb95ddcef4cdc2097d6c195f9`。

随之必须更新第 8—14 条的 7 个 event_hash、第 9—14 条的 6 个 previous_hash、expected_book_head.hash；加上内部头共 **15 处 prefix 叶字段变化**。accepted_anchor 位于第 5 条，因此不变。prefix Resource 原始 SHA 变化后，bundle 仅更新 `evidence[1].resource.sha256`。16 个 Artifact 的内容与 hash、普通 ArtifactRef、return Resource 均未改变；新 case/index 固定新文件 SHA。

- bundle SHA256：`6a39c873de02dab04d3efd831cb1032b87ba8323c35bfd2a7a31f0b2e48dabd2`。
- prefix SHA256：`d946006863bac1a8862ba2b3652f0b62e0914c36625541d463c342721e508e5f`。

## 先行检查与真实入口

[precheck.json](../../../docs/evidence/A03/execution/P2-R6-mixed-control/precheck.json) 在任何 Package 调用前落盘。`data_check.py` 只用标准库读取数据及确切 Schema 字段位置，不导入校验器/产品，不调用 schema helper、session 或 conversion。它独立核对 16 个 Artifact hash、18 个 Resource 原始 SHA、全部普通四元组引用、两个 prefix 的 14 条事件摘要/前驱链、所有 initial_event_head、accepted_anchor/expected_book_head、已有 basis 头引用，以及 frame/外层各自的声明和书籍/scope。

正式 EvidenceRecord 字段仅从固定 Schema 的 string-array/ID-pattern 属性定位，opaque JSON 同名字符串不充当正式 ID。全局读池只做数据引用检查，frame 数据用明确的 canonical book/scope 核对，不形成 runtime 当前资格。完整旧包和新 Source 的混合环仍为 Source → 正式 EvidenceRecord → prefix Resource → frame → return Resource → 同 Source。

[实际结果](../../../docs/evidence/A03/execution/P2-R6-mixed-control/entry-result.json) 记录 R5/R3/R2 的实际调用 trace 各为 1，R3 类计数 0→1；64 个图节点、44 个真实消费者、None-book 真实消费者 0，consumer_failures=[]。先行检查给出的五条环边均在实际 Package 图中存在。实际拒绝路径为 `A:760b541bec881e9d98abb75f38bc7e34a75d2ed047edbc8ac657091c70fdc320`。

首次驱动启动因 trace 条件漏空格，在 Python 解析阶段 SyntaxError 退出，Package 调用为 0。失败原脚本/流/退出保留；只补该空格，经 AST 检查后执行尚未发生的唯一完整调用。候选、固定 R5/加载器及加载语义未变，没有执行后修包重测。详见 [driver-syntax-check.json](../../../docs/evidence/A03/execution/P2-R6-mixed-control/driver-syntax-check.json)。

## 只读复现

供独立审阅使用；本轮封存阶段没有再执行：

```powershell
Set-Location C:/Users/ASUS/.codex/worktrees/a03-runtime-recovery/1800
# 唯一候选，经不变 R5 完整入口；输出 stdout，不写结果或旧路径。
python -X utf8 -B examples/a03/P2-R6-mixed-control/entry.py --readonly
# 仅核对归档/旧文件/计数，不导入 checker 或再运行数据检查。
python -X utf8 -B docs/evidence/A03/execution/P2-R6-mixed-control/archive.py --check
```

R5 六项静态结果不重跑，旧矩阵、产品/SQLite/native/PRE ABI/planner、网络/平台/模型均未运行。字段重置专项仍为 `NOT_EXECUTED_NO_RERUN_VARIANT_OR_DELEGATION`。执行者只交 REVIEW，未宣布独立接受。
