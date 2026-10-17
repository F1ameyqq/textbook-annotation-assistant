# A03 P2-R8-R4 独立验收交接

2026-10-18（Asia/Shanghai）。继续原独立验收对话 `01a145aa-8d59-7c70-8d81-731712103a9a`，保留用户当前 model/thinking；不委派、不联系执行者或 B。执行者已完成并释放本轮自有进程。根工作树 `D:/1800` 只写本轮 review 目录和报告，不改产品、调度 state、旧报告或证据。

## 确切冻结输入

- 执行工作树：`C:/Users/ASUS/.codex/worktrees/a03-runtime-recovery/1800`；base/未变产品 `d9ed692db9ab8e9277f8ffd09e040451e8b8f65f`；唯一 target `435aaee2d140e82d3237ce8902d594a1aee70aad`，已核对 clean HEAD。
- 执行任务：workflow `cb9c8f76e9eae40a8fda042c196705d7258b5107` 的 `docs/tasks/A03-P2-R8-R4-remaining-validation.md`，SHA256 `5a93ea9012ad8d9d2f69e622235051cbf1ced23922e1e6fc021c4443657e184b`。
- target 报告 `docs/tasks/A03-P2-R8-R4-remaining-report.md`，SHA256 `eaba2a007216999ca70e506609a50a049e89b48b86b4c39af0e51dfa50e9e324`。
- target evidence 根 `docs/evidence/A03/execution/P2-R8-R4-remaining/`；**清单名是 `manifest.json`**，SHA256 `337ba0aa1ce0fd8a70032a6b2580797752f0e4ea5b0216b56913dae2ebd91f4c`；314 条加自身共315新文件。
- `process-release.json` SHA256 `31f77b464ff08fbca8c79b4fec0e1e6500a07f9773056f541e96d03318bab6b7`。四个父测试/只读回查及四个嵌套进程均有 wait/exit 记录；N1 效果 child 60488 在真实屏障后 exit87，其余0。
- R4 主驱动 `tests/test_a03_r8_r4_remaining.py` SHA256 `27d1969548011b044c21b77a121c53b5bef90d4aa0b19aef95f65b8d692f9a3d`。R3 主驱动 `02acb22f395f380528130166ca8ae4637e3303c73f6496d9da4166b5050a1467` 正常 import；只重定向测试模块 EVIDENCE/BASE_EVIDENCE，原方法与 child 不改。
- [调度交付核对](../evidence/coordinator/heartbeat-20261018-0429/delivery-preflight.json) 已核验315份 raw Git、6份 workflow 文档、31,167个旧 tree 条目原样及进程记录，未运行产品/测试/SQL；这不是独立功能接受。
- 已有 [R3 独立报告](A03-P2-R8-R3-post-hold-review-report.md) 和 [R3 调度决定](A03-P2-R8-R3-post-hold-coordinator-decision.md) 均在上述 workflow；R3 报告 SHA256 `a39afab68c15837122a34fb0f75dca7cae339dd2ba1be13dde007971b99b9a17`。

## 验收范围

1. 从确切 target/workflow 用 raw Git blob 导出必要输入，登记 commit/path/bytes/SHA；核对整套新增清单、产品/历史 tree 保全、实际 import/驱动快照及进程注册/启动/退出/原日志。无需复制历史全集，旧 root review 文件保持原字节。记录固定合成逻辑标签沿用与真实 run/观察/intent/receipt 新身份的区别。
2. 在 `docs/evidence/A03/review/P2-R8-R4-remaining/isolation/` 内建立全新独立 workspace 和输出；只放必要产品/驱动/夹具及清楚来源的输入索引，不能复制作者成功/失败数据库作为起点。产品/驱动原始字节不改，正常 import，不用 AST/exec 裁剪或产品 monkeypatch。实际 module.__file__/SHA 必须来自该隔离树。执行 **新 N1 一次 → N6 一次，及 N7 初始化一次**；只用原 R4 范围，不跑 local/N2–N5、兼容套件、原 N7 旧 target 入口或其变体。需准备索引/路由时使用审阅者包装脚本，保留与原文差异；不得修改产品/业务输入使其通过。
3. N1 作为 N6 的必要前序，仍须真实 child 屏障、恰好一次效果、原 UNKNOWN/null 回执、正式晚到 receipt/intent/fact/material progress 对齐、新独立 POST/Batch，内容 PENDING、NOT_SUBMITTED。用自有 immutable/query_only 数据库副本和正式 Resource/SQL/current bundle 交叉检查；不得调用作者库中的产品 API，也不补发写入。
4. N6 确认传入 verifier 的完整正式历史保留 UNKNOWN 及后续 receipt/resolution/POST/Batch；产品从真实 creation anchor 验证资源并实际重算相同 plan 四元组和全部 action。检查 sys.setprofile 仅捕获本次正常调用的真实 return，无输入/输出替换或第二次 planner 调用；anchor canonical SHA、SQL input_sha、原件、消费资源清单及实际实体一致。负控缺少的是 checks[0] 正式消费的 PRE EvidenceRecord，原 anchor/资源未变，拒绝定位准确，前后双库及 permit/effect 不增加。它证明一个正式依赖控制，不扩张成全部资源损坏矩阵。
5. N7 仅核对既有 before_completion 钩子调用一次、原异常传播、无完成标记/anchor、正常 open 一次 fail closed；存在的 runtime 表计划/intent/permit 为0，未创建的 target/effects 记 NOT_CREATED。前后摘要不变，不恢复初始化再尝试成功。这是同进程受控异常，不能声称真实崩溃或所有目标库初始化点通过。
6. 原 R3 N7 FAILED 永久保留；先前“精确外层错误码断言过严”的分类不变，不要求修改 persistent.py，不重跑该失败调用。原 N1–N7 和 P2 V01–V10/R01–R18 的覆盖映射逐项区分有限接受/本轮复核/未覆盖；不能以本轮三项通过自动豁免整体矩阵、接受整个 A03 或放行 I01。不同 hold/合格清 hold、多动作/ABSENT、其他崩溃点等只整理剩余范围，不在本轮扩测。

每组一次，父 watchdog 上限60秒，子进程沿用原限定；不要因输出记录错误反复运行产品。新的产品语义失败保存首次原输出、停止依赖组，交 REWORK，不修产品、不复跑。审阅元数据脚本错误可更正，但保留首次记录并解释没有额外产品调用。所有实际进程提前登记 argv/cwd、脚本/输入摘要与限时，保存 stdout/stderr、PID、退出/timeout/alive，结束后 wait/释放；无需全系统进程扫描。

字段重置专项保持 `NOT_EXECUTED_NO_RERUN_VARIANT_OR_DELEGATION`，本任务不授权其任何变体、重试或委派。零网络、平台、浏览器、凭据/profile、OCR、付费模型、A05题22重放、书级送交、推送和 B 联系。

## 输出

仅新增 `docs/tasks/A03-P2-R8-R4-remaining-review-report.md` 和 `docs/evidence/A03/review/P2-R8-R4-remaining/`。报告给 exact target、逐项证据与限制、有限 ACCEPTED/REWORK、原始失败保全和剩余标准，不自行 INTEGRATED。最终 manifest 覆盖本次全部文件及报告，仅排除自身；附进程释放证明、实际导入身份、独立新产物/SQL绑定、原字节保全摘要。全部自有进程结束并封存后交调度。
