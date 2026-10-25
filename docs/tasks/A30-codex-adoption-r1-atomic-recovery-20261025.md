# A30 02 修订：恢复提交一致性及既有节点精确绑定

由协调 `01a171f5-e73e-7452-982b-1885115e96ff` 派发给现有开发 `01a171f9-3a3f-7832-9a94-70bee44d9510`；修复后由现有独立验收 `01a171f9-b65a-72d2-8d8d-f23107cd00dd` 复核。这是同一有限任务的返工，不激活 actual。

## 固定反例

01 产品 manifest `3ec8c073c8be0c5e132f644afe5b92e45c98ddcc87f63fdbccf1525bca6a4d35`；launcher `a7c33d41cd38720d3f8318c51f2c2d948ed40663e5601161a426f60d52098484`；构建报告 `2d9708841dcf1bafac18655ab1cd40f0279f0817063cc7cccf31b5318a749cc5`，均保留不改。

独立评审目录 `D:/1800-private/a30-adoption-completion-code-review-20261025-01`：manifest `5a6841c1438a806de80b9861fcb99decf7915da39a13273fdbfb3bfec18b053d`；decision `844db4e534c1f16c7507ff934bca16ce212ff99e93efd6f1d922c3104007f270`；`raw/commit-failure-control.json` `d273c37bc3827d47713c9a9c394cd11c1ff7a374ecb3b360f02068dce3f06486`。结论 REWORK。

普通恢复入口在真实工作区隔离副本上，原 save CAS 更新前注入 Hold 后，新 reconcile-retained 已为 COMPLETE，但原 save 仍 UNKNOWN、job 未恢复；再次恢复被原一次性记录禁止。恢复操作提前完成，违反失败状态合同。原真实工作区11176文件前后不变，transport构造/平台调用0。

## 最小修复

1. 允许在 `customer/store.py` 增加专用最小事务辅助，和 retained recovery 的调用点形成一次一致提交：验证原 save state/output、恢复 intent、job expected head；当前 save 的 CAS、新恢复终态、job head及event同时提交。必要接受 blob 仍为不可变内容寻址记录，原 UNKNOWN/发送/失败对账/历史头和事件不得改写。
2. 不得仅交换 finish/resolve 顺序制造另一处半提交。恢复失败必须保留原 save UNKNOWN和原job/head/events，新已开始操作 FAILED_NO_RETRY；前置链失败不建op。一次性和零平台约束继续有效。
3. 在隔离副本验证成功，以及 CAS更新、恢复终态、job/head/event发布等关键提交边界的失败回滚；检查原UNKNOWN/失败链和历史字节、重复拒绝、transport构造0。独立验收应自行构造至少覆盖原反例和较晚job/event提交失败的控制。
4. 补齐既有采纳的精确新读绑定：把原已绑定四个尾节点的 order/created_at 从保留依据生成到 adoption selection，并在普通 `_execution_plan` 的 ADOPT 分支与当前只读记录比较。不得硬编码新事实或放宽校验。正例保持39—42/原created_at；任一值变化应Hold且0保存调用。此项是原绑定要求的最小收紧，不扩大采纳范围。

## 冻结与复核

新产品/launcher/build均用20261025-02后缀。先固定源码/launcher立即回报精确hash，再补构建报告。01报告中的大批工作区副本无需复制或重跑，可精确引用未变原件；02只保存本次差量、失败控制和必要受影响验证。不得删除旧失败输出、减少原断言或声称01未跑项已通过。

原评审因R1停止，剪除反例、ADOPT/顺序控制、普通入口完整拒绝矩阵、preflight及尚未完成项仍需在02完成必要独立检查；字节未变的已核事实可复用。任何新失败记录原件后做最小修复，不改已冻结目录。

除上述源文件/相关测试/说明/冻结计划的最小变更外，旧任务及统一合同继续有效。0POST、真实现场不写、无浏览器/profile/模型、所有旧authority spent、customer_ready=false、1800-a PAUSED；接受后由协调另绑定新唯一实际。
