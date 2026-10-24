# A30 合成10有限独立审查

结论：**REWORK_BATCH_PLAN_INTERSECTS_OWN_CONSUMED_ROI_GUARD**。本次不接受19区域公式批处理首次实际激活；已接受的09恢复、四题实际结果及图框/来源支持结论保持各自原范围。`CUSTOMER_READY=false`，`1800-a PAUSED`。

## 唯一阻断发现

**[P1] 批计划包含会被自身已消耗ROI保护拒绝的相交区域。** 固定计划中，第6、7、8项均为印刷Q8答案、同一原图的三个相邻数学行：

| 批次序号 | 原图bbox | 与前项相交 |
| --- | --- | --- |
| 6 | `[71,1399,540,1422]` | — |
| 7 | `[69,1416,540,1442]` | `[71,1416,540,1422]`，高6像素 |
| 8 | `[69,1437,343,1462]` | `[69,1437,343,1442]`，高5像素 |

源SHA-256：`a231f0247cd0444cc34ed699c4cca99245d2ac6cfda5ef10a38ca3f8164510be`。对应evidence refs为`page-04837b81019a5c9907fd6924/line/144`、`/line/146`、`/line/147`。

`formula_batch.plan`第14–21行直接收集明确数学行，没有在开始调用前消解同源相交；`formula_batch.run`第41–46行逐项调用并保留结果。`formula_runtime.obtain_region`第78–90行扫描已持久化的ROI，并拒绝同源几何相交。

因此，**若前6项均成功完成并留存，第7项会在调用worker前被上述保护拒绝**，批次写为`FAILED_NO_RETRY`，其余12项为`NOT_RUN`，再次启动亦被原批次失败记录阻断。这是冻结代码与当前固定输入之间可确定的冲突；没有执行真实模型，也没有把条件推演称为实际发生。

最小修正：程序应在任何首次模型调用前消解或显式分流本批相交区域，保留已消耗ROI防重跑保护；重新冻结修正代码和程序生成的有限计划。具体可按可核对的来源范围组织，但不能靠客户写JSON、外部agent逐项修计划，或简单放宽已消耗区域保护。这里只要求核对明确的批内冲突，不要求无限扫描未知历史。普通UI后head变化时从原任务重新生成计划即可，无需重建workspace。

## 已完成的有限核验

- 固定manifest `c49e5d036dd6d0905e42fda02f23db5d15a8e1bf2f02a473baf8710cedf84495`，report `b8ae12b3308cf53f277df234b14efb3c26d7577c22f784f7d7b1f99389261148`。234程序＋12证据＋3metadata，共249件复制到独立隔离；249件协调端冻结副本原字节亦核验一致。
- 相对09：205件原字节相同、11件修改、18件新增、0删除。existing_fill、source、recognition_cache、retained_readback原字节相同；reconcile、compare_readback、send_window_bounds及执行选择/计划检查等指定函数AST相同。
- 与已接受支持候选相比，figure_proposals、review_features、quality、orphan_groups、formula_roi_cache原字节相同；审校assign/bind/save/confirm、生产produce、计划make_plan及客户main/wizard指定函数AST相同。新增公式结果以独立待审记录接入，静态路径没有自动内容确认或自动应用。
- 只从此前独立封存的实际副本取出head `982965f8ed0010e2f4eb3503bc7217748e6879f912d5dccaf1c3fa8ec6040ca8`及其graph/evidence三个原blob，执行纯计划投影，与计划SHA `5640a3590d8db83de38a51fbe050fad69a6160f23372803f83eb7b7e874ec534`的内容完全相同：19明确数学行、22混排区域；已完成1/5/10/11不在其中。
- 7个已知旧消耗区域与明确原记录字段相符，普通OCR均为`tex_cache=false`；19＋22与这7个旧区域重叠0。独立新增的批内相交检查发现上述2对冲突。未把“旧区域重叠0”推断成“批次内互不相交”。

## 失败与后继状态

`static_verify.py`首次运行在批内相交断言失败，退出码1；原脚本、stdout/stderr、static-result保留，不改写为通过。随后只解析固定JSON与AST记录具体冲突，不重跑产品计划或模型。此失败属于实际代码/计划兼容缺陷，不是辅助工具误报。

后继运行时身份计算、新缓存/运行时检查、新批处理失败检查和新受控UI检查均`NOT_RUN`。作者已有9项Python及1组UI结果只作为冻结作者记录，不重跑、不替代尚未完成的独立接受。作者此前worker validate-only记录亦保留，未据此扩大为模型推理已验证。

本审查新浏览器/平台/模型/OCR调用0；真实workspace、profile、ledger变更0；未修改产品、原authority、协调状态或旧成功材料。私有详情见`D:/1800-private/a30-union10-independent-20261024-01/failure-detail.json`。
