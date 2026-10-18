# A03-R1 首包调度收口

2026-10-18。整包 **REWORK**；固定产品 `6097a06de937fee8876feccedf46920510850b83`、最终交付 `54e86adfaf144093a688b62fe0dad5190ceb2fa6` 的 **M 五例、L1 和独立验收列明的依赖拒绝范围 ACCEPTED**。不等于全部 A03 通过，未进行主目录产品集成，I01-A 尚未释放。

## 依据与复现

- [独立验收报告](A03-R1-review-report.md) SHA256 `752dac77082ab1f60a6e69cda1b0c2db70bd6c8f7c2ab0fb222ef79255db10b4`；[验收索引](../evidence/A03/R1/review/manifest.json) SHA256 `8fce2dac7e30db072bb83c5f96fc0d06e54de31a20cbca26024c124ff524381f`。
- 调度核对独立交付 1204 项、36840794 bytes，无长度或摘要差异；作者的 1300 项固定交付核对沿用[上轮预检](../evidence/coordinator/heartbeat-20261018-0629/delivery-preflight.json)，未重复全量作者测试。
- 调度取最终交付 raw Git 中的 `tests/test_a03_t3_closure.py`，仅运行 `MRetainedEvidenceTests` 检查独立验收封存材料，5/5 通过；另核 L1 的 `1→2→3→2`、整书 `BOOK_WRITE_PAUSED`、目标调用记录 `2→2`、两个 legacy 未决、原 intent.receipt 不变及 owner 释放。未导入产品、连接 SQL 或重跑业务。
- 复现结果与确切检查脚本摘要见[调度核对](../evidence/coordinator/heartbeat-20261018-0659/coordinator-checks.json)及[断言输出](../evidence/coordinator/heartbeat-20261018-0659/retained-assertions.txt)。独立验收的真实产品运行为 5 native 起点、10 dispatch、8 次实际目标变更；L1 复用其 M2，零新增 dispatch。keeper、owner 和记录内子进程已释放，pending/hold 按业务结果保留。

## 有限接受与未完成

M1 三动作及重开去重；M2 充分/不足 ABSENT 与未尝试尾段；M3 hold 最终再读、真正新规划及最终漂移保停；L1 当前全书跨 scope/run 未决扫描及 UNKNOWN 历史/正式报告链，按独立报告实际范围接受。资源/pins/root/registry/逐 consumer 声明拒绝按已实测项接受。均限 fresh native synthetic，内容 PENDING、NOT_SUBMITTED，不扩大为平台、OCR、B 侧共同合同或任意性能结论。

独立审查未发现上述实测路径中的产品语义缺陷。L2 的 checkout PGM 被 CRLF 改写而 `RESOURCE_HASH`，是确定的驱动/输入问题；不是另书隔离功能已失败，也不是已通过。L3/L4、G 余量和 F 总体收口仍缺，逐项以独立报告原有限清单为准。不重跑无影响 M/T1/T2/旧切点来凑通过数，不把相同叶文件等同所有新消费者已验证。

本收口保留全部失败、作者/独立运行计数和未运行范围；不得以新名字重置驱动纠正次数。下一次业务派发必须单独写明它在 A03-R1 最多两次冻结候选中的位置和剩余上限。已接受的上述证据先按固定版本保留，不先把不完整产品合入主目录。
