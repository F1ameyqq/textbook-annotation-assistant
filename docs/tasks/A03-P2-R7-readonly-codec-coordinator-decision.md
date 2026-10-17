# A03 P2-R7 主调度决定

2026-10-17。执行 target `8ad45dd07214ae406a3fab28d76a4b5abd6eef03`，base `81d3ec7e42e0a1a76ad744bf59536fc5f68adee4`。

**ACCEPTED：仅接受 R7 的产品只读 codec，角色为 STATIC_INSPECTION，采用范围 A_INTERNAL_READONLY。** A03 P2 的持久化、原生 PRE/CURRENT、UNKNOWN 恢复尚未接受，I01 尚不释放。

依据为[独立验收报告](A03-P2-R7-readonly-codec-review-report.md)、[调度归档核验](../evidence/coordinator/heartbeat-20261017-1329/review-archive-audit.json)及[调度实际入口复现](../evidence/coordinator/heartbeat-20261017-1329/reproduction-result.json)。清单 608 条加自身共 609 文件；443 个隔离输入副本、171 项原 raw Git pins、3,267 个旧证据文件逐字节核对；10 个审阅父进程、14 个嵌套进程的登记、PID、wait 后退出和原始日志摘要一致。此释放判断只针对有记录的自有进程。

独立验收七个固定包、API/快照/路径和仓库外冻结 wheel 检查均通过。主调度另经冻结产品公开 API 复现正包、target 元组负控、未声明 EvidenceRecord 负控，三例结果及错误路径准确；完整快照和 canonical 摘要核对通过。未运行旧矩阵、native DB、planner、模型或平台。

C01 审阅首轮 70 项有环境隔离/日志编码失败；补齐未改动兄弟依赖并修正审阅日志解码后，仅两个受影响原方法通过定点补测。原失败和补测均保存，不能记为首轮 70 项全绿。该偏差不属于 codec 产品缺陷；本决定不要求重跑审阅旧轮次。

**INTEGRATED（本地、仅 R7 只读范围）**：在主目录原 HEAD `0158a8f42f0d5d5839f41ce898ad90725936d2c5` 上复制 target 相对 base 的 339 个新增路径（产品、测试/固定样例、R7 文档及执行证据），并在当前 pyproject 附加已审 package-data 声明；保留已有 Pillow 依赖和其他改动。未合并 A03 祖先链内未经接受的 runtime 或旧恢复入口。

新组合上的 [R7 13 项](../evidence/coordinator/heartbeat-20261017-1329/integration-r7-results.json)与 [C01 70 项](../evidence/coordinator/heartbeat-20261017-1329/integration-c01-results.json)各运行一次，全部通过，无失败、错误或跳过；导入路径指向主目录实际产品。它们是集成后的新检查，不覆盖或改写审阅首轮失败。[集成文件清单](../evidence/coordinator/heartbeat-20261017-1329/integration-files.json)绑定全部复制文件及 pyproject 差异，原 R7 执行和验收证据保持原字节。实际本地提交写入 coordination-state，不把整个 A03 标成 INTEGRATED。

后续继续原 A03 执行/验收对话，保留用户手动思考强度设置。旧 profile/API/schema 及原始失败证据不回写；原生采用必须另有明确实现/验收边界。字段重置专项保持 `NOT_EXECUTED_NO_RERUN_VARIANT_OR_DELEGATION`。本地接受不代表远端已推送或 B 已确认。
