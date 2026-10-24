# Q16 来源复核修订（2026-10-17）

本增量把第二课时 Q16 的有来源修订实际送入既有 14 阶段，改进当前三行正文、11 处分式及外围符号。内容成员提交 revision 5；质量成员对照原图发现“60，61”的逗号无像素/OCR 支持，总控另建 revision 6 改为“60 61”。两版均保留，当前是 **MODEL_DRAFT / HOLD**，不代表独立人工核准。

## 当前可消费版本

- 完整计划：`tests/fixtures/book46007447/q16-source-revision-plan-v2.json`，内部 revision 6；操作快照为同目录 `q16-source-revision-operations-v2.json`。计划 SHA-256 `64127c99a28178d13a4ad3bae6868ec41e4137437934cb0d8c67a1dbdc9f00cd`。
- 计划引用：`content-revision-plan-70c5d835c849ff68047554f9` / `540f9f7fa03e5e7619033060a445d58023e55a02f7f125d2d4dd7510dce04a56`。八个操作保留既有 Q9 七项和 Q16 一项，完整归档 revision 5 及更早历史。
- 当前 G07：`content-graph-2761436bca06fe2cd4f33e36` / `43db5fa9d0becf97d37f9465d524ed4c81b66b22e1e812606cbaebae0c1604c4`。
- 当前 Check07：`content-check-acef084b0cc35a112c5122fd` / `a367b50031820abc9bddb065e6e4679cb9ad25304e129ff1843714a64130e9f7`。
- 真实导出位于不入库的 `data/runs/46007447-q16-source-revision-master-v1/`；`pipeline-history/` 保留旧/新阶段对象和运行记录。可移植固定输入与评估随仓库提交。

原资产为 `viewer-173`，SHA `a231f0247cd0444cc34ed699c4cca99245d2ac6cfda5ef10a38ca3f8164510be`，1148×1621，区域 `[579,263,1084,367]`；准备器实际检查原图、尺寸及 RGB 裁片 SHA `4fa6dac45f65e9f50351edcbf0a87427b9a8283bcee2c8e89cb4957d4bd8dcb7`。它不是 Q9 续页 `resource-173`。

![Q16 固定来源裁片](../tests/fixtures/book46007447/recovery-assets/unit2-q16.png)

## 实际内容改进与剩余核对

当前正文修正连写的“6061”、杂字“ira”、错误拼接“.a+(”、F2 的错误指数、F3/F5 漏四次幂、F11 漏平方，以及因果符号、括号和外围平方。11 槽从已有观察/同源派生候选中显式选择，没有新模型调用，也不把派生组合冒充整式观察。选择身份表见 `evaluation/book-46007447-q16-source-selections.json`；正文完整投影见总控评估。

17 个原片段仍按 7/3/7 对应三行；原 OCR、44 条整式观察、298 条派生组合及失败完整保留。独立质量成员的模型目视复核发现并促成上述标点修正；它仍不是人审签核。全部三行、11 公式槽及原始字体符号仍待按 `docs/q16-independent-review.md` 独立人工逐项核对。

## 验证

总控以固定旧包和干净 Git 导出的生产代码重放 revision 5：12 前序缓存、两内容阶段重建，最终引用与成员独立运行一致；恢复旧计划和再次应用 revision 5 都是 14 缓存。随后 revision 6 再次仅重建末两阶段，暖运行全 14 缓存，审计 accepted，业务 HOLD。沿用本机 Python 依赖，进程禁止模型导入和网络连接；不称为新安装的依赖环境。

总控另逐对象比较：全部问题和配答不变；印刷题号4的六个答案对象逐字段不变；Q9正文、33原片段、来源行和15呈现区语义不变，只有由谱系生成的区域/内容片段 ID 可重签。当前仍34题、66答、127检查问题和19未归属，问题数不作为内容准确率。

成员的错误参数调用及失败回执不撤销：首次把 adjacent manifest 传给原图参数得到 FAILED/HOLD，正确使用 resource-173 原图后重跑；另有一次误写测试类名失败后修正。总控的原包重放初次也误把ZIP作为inline manifest，随后通过正式准备器生成正确 JSON。各失败与收口分别记录，没有计作成功。

证据：`evaluation/book-46007447-q16-source-revision-member.json` 保留成员原报告；`book-46007447-q16-source-revision-prepare-v2.json` 为总控原图准备回执；`book-46007447-q16-master-integration.json` 为增量重放/恢复与防退化结果。第一章来源、Q4/Q9余下错误、19条身份、人工验收和A接收均未因此关闭。
