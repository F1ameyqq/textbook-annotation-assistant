# I01-A 本地集成记录

2026-10-18。经[调度有限接受](I01-A-coordinator-acceptance.md)，作者固定交付 `3fdc5d37e221fc73410f197605f5d7b8878182d5` 已正常合入本地主线，集成提交 **`f356dde53bf9cc852eb35fc3710c884c397ce6c5`**。状态 **INTEGRATED** 仅指任务定义的离线范围，未推送或共享B。

集成前主线为 `d16ead51b2fe73f17c8857b8d21c7a47cbf13554`，共同基线 `a1c3c3b2d452ecbdf5c57a8b7372e7d53de0f8d8`。两侧路径无交集，正常三方合并；纳入666个新增文件：11个examples/i01、25个固定夹具、1个静态测试、628个作者证据文件、1个作者报告。没有既有产品、公共合同、pins、依赖或其他任务文件的修改。独立报告与678成员证据已在先前调度归档提交中固定。

调度逐一比较666个新增路径的来源raw Git blob、合并索引与实际工作树bytes，最终全匹配。首次静态比较在audit.py发现checkout换行转换即停止；仅将11个此次新合入的脚本恢复为来源raw bytes，没有改来源提交、pins或他人文件，原因及前后摘要保留在 [integration-bytes](../evidence/coordinator/heartbeat-20261018-0854/i01-integration-bytes.json)。`src`树保持 `a7c3f112ccd8a00012925dc3777145f87a447e66`。

集成后实际运行已有纯静态检查：

```powershell
python -X utf8 -B examples/i01/check_freeze.py --candidate be68b8d7c645de556d601458d1d493258f063721 --output docs/evidence/coordinator/heartbeat-20261018-0854/i01-integrated-static-check.json
```

exit=0、mismatches=0；[结果](../evidence/coordinator/heartbeat-20261018-0854/i01-integrated-static-check.json)和原始流保留。未导入产品、打开SQL、运行N/E/U或新增target/dispatch；此前独立完整三路径证据按确切范围继承。运行驱动的固定HEAD守卫不变，主线集成HEAD不能冒充be68b8d7运行候选。

A01公共离线消费者和A内部synthetic三路径已完成本阶段；内容仍PENDING、NOT_SUBMITTED。真实A01→native、B→A可执行映射/执行准入、共同合同及合格真实单题样例、平台/OCR/联合业务仍未由本次证明。A06首候选因结果层版本/kind缺口REWORK，按其独立有界任务推进，不阻止本阶段离线集成收口。
