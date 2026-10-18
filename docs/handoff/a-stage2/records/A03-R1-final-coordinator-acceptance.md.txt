# A03-R1 最终调度接受

2026-10-18。A03-R1 的原 V01–V10/R01–R18 有限离线范围 **ACCEPTED**。最终交付 `19ab03c849bfab3dcde2dc86be37c59f3add1ebe`，运行冻结 `9992cd8aba10987d25dd0dc0d0874abec02b27ef`，产品 `6097a06de937fee8876feccedf46920510850b83`。本记录接受候选；本地集成结果另记，不能仅凭本记录释放 I01。

## 证据与复现

- [最终独立报告](A03-R1-final-delta-review-report.md)，SHA256 `8e05ba6963c51170cb39158438da76028f9e2622ddfe3eba573549a8c09ba507`；[最终索引](../evidence/A03/R1/final-review/manifest.json)，SHA256 `3263f166f7bd3c014277177e18f254b446aded85ddc27db64353db334e9742c3`。
- 只读复核：独立 437 项／9,775,355 bytes、作者 raw Git 445 项／9,292,341 bytes 全匹配；旧独立 1204 项／36,840,794 bytes 保持原摘要。作者/独立各 32 个业务及读进程有实际完成记录，12 组 capture 均已释放 owner/PID/lease；16:02:38 +08:00 的系统快照中 66 个唯一登记 PID 均不存在。pending/hold 按业务结果保留，未清锁、恢复或迁移旧库。
- 调度执行 `python -X utf8 docs/evidence/coordinator/heartbeat-20261018-0759/retained-checks.py`，[9 项断言全部通过](../evidence/coordinator/heartbeat-20261018-0759/retained-checks.json)：实际十阶段一次、2 新目标/3 dispatch、另书隔离、UNKNOWN→ABSENT→新 UNKNOWN、不同 plan/action/intent、原 receipt 保留、G6 持久预算重开 0 补读、释放记录及 F 只读稳定性。未新增产品业务、SQL 连接或产品导入。
- 调度沿用[首包有限接受](A03-R1-coordinator-acceptance.md)的 M 五例、L1 及依赖拒绝；T1/T2、旧切点/owner 仅继承其确切已接受范围。

## 接受范围与限制

最终独立差量新增 2 个目标、3 dispatch、2 次实际目标变更；十阶段均一次完成，G6 的三次 FAILED_READ 是预期故障，重开没有补读或计数重置。新业务 M/L1/G4/legacy 均为零。最终运行没有业务失败、外层超时、冻结后修复或重跑。

L4 的环/错 receipt 在精确引用层拒绝，G1 部分在结构层拒绝，G5 在值层拒绝。对照原有限 key，这些实测拒绝满足原要求；不冒称未到达的更深层已验证，也不追加更深拒绝标准。G2 仅真实 transaction wrapper 失败回滚及已列文件冲突；G3 仅归档角色与 INCOMPLETE 拒绝；不推广为任意 I/O 原子性、数据库迁移或 mixed-native 多书执行。

全部结论限 fresh synthetic 离线场景、PENDING 内容及 NOT_SUBMITTED；不等于真实平台、OCR、B 算法/共同合同、批量稳定性或任意性能保证。45 秒不作为业务 SLA。全部失败现场、已消耗冻结次数保留，不再向原 A03/T3 或 R1 作者派补丁/新业务。

下一步由调度把已审 A03 产品以明确文件范围集成本地主目录，保留已有 A01/A02/A04/D01 与其他改动，完成相关检查后记录 INTEGRATED，再派 I01-A 的三路径离线最小集成及独立验收。
