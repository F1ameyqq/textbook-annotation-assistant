# 第二最终候选的唯一纠正

首候选 `f5e3d63e6e31a87eb2b45789dbebadf89b4ac81e` 唯一实际 suite：前6 case PASS，第7 T4 ERROR，余10 NOT_RUN。错误是公共 C01 `CHECK_SUBJECT`，不是平台、业务或目标状态错误。

精确纠正仅为 `delivery/live_pilot/plan.py` 中新 TARGET CheckReport 的 subject 从 graph ref 改为 snapshot ref；graph 独立字段及 input_refs 保留。公共 C01 合同要求 PRE_APPLY/TARGET/POST_APPLY 的 subject 分别绑定 graph/snapshot/receipt。没有修改旧 C01，没有放宽验证或更改 suite/fixture/预期。

保留首候选及 attempt-1 所有失败证据。第二候选只作语法/差异静态检查，冻结后唯一运行相同17 case suite。累计至多2尝试/1成功；无第三候选，无成功后补跑。
