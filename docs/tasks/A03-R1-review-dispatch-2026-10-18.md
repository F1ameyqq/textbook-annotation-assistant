# A03-R1 首个固定交付：独立验收续派

2026-10-18。沿用 A03-R1 原执行/独立验收任务及用户等价替代授权。此单不扩大业务标准，不启动第三轮驱动修复，也不要求作者重跑已成功 M。

## 固定对象与释放

- 执行对话 `01a14da3-8798-75c0-af50-ca8fec19b48c` 已 completed，最终交付 `54e86adfaf144093a688b62fe0dad5190ceb2fa6`，工作树干净。
- 产品候选 `6097a06de937fee8876feccedf46920510850b83`；起点 `d5f777590e72eb070af0497afdb144d60c61b95d`。候选至最终 `src/` 无变化。L 驱动 `d0438c998c9e161ae7d919e2ac83ce9075a56751`，一次纠正 `456740b4360c408efdc3165e6e98b136770613ab`。
- 报告 `docs/tasks/A03-R1-execution-report.md`，raw Git SHA256 `f0a8f282194b9a3b8ea84ce2eeaa3472be99c1c1119e0579b24574f2a3d76f6c`。
- 索引 `docs/evidence/A03/R1/execution/manifest.json`，raw Git SHA256 `be1e8da1c7a7da02b82ddd3e2803bb8fa44e3b1048ccdf8c114a459f5d768f16`。调度已核对 1300 个成员，共 35118730 bytes，无摘要差异。
- 调度预检 [delivery-preflight.json](../evidence/coordinator/heartbeat-20261018-0629/delivery-preflight.json) 记录 M/L1 owner=NULL、lease=0、RELEASED，keeper 停止，51 个子进程完成记录及最终 PID 核对；旧 pending/hold 保留。只读核对 Git JSON，未打开业务库或运行产品。

## 本次要作出的判断

作者交 REWORK，不能直接关闭 A03。M 五例作者材料为 5 fresh 起点/10 dispatch，L1 为 pending 1→2→3→2，正式报告和整书暂停材料存在。后继 L2 在登记前因 checkout CRLF 改变 PGM bytes 而 RESOURCE_HASH；首次 legacy 驱动选择错误及一次纠正现场均保留。L2/L3/L4、G 剩余项与 F 整体结论未闭合。输入失败不能当作另书隔离通过，也不能直接认定产品语义缺陷。

请按原独立验收任务审查这个固定交付，输出一次合并结论：

1. 核对允许路径、实际采用、真实 pins、公共行为和依赖复用拒绝边界；特别检查资源 bytes、root、registry、逐 consumer 声明改变，以及实时 owner/fence/currentness/pending/hold/permit 检查不会被复用绕过。
2. 独立核对作者 M/L1 的真实边界、效果/回执区别和释放。选择与新路径有关的有界独立复现；允许原 M 五例最多 5 起点/11 dispatch 的上界，但不要为重现已知 L2 输入错误再启动业务，也不要重复全部未受影响历史场景。保留作者采用的 180/240 秒外层预算和原内层期限。测试输出必须新目录，只用 fresh synthetic 现场。
3. 原 V01–V10/R01–R18 和已接受 M/L/G/F 映射逐行说明：当前固定交付可独立支持的有限范围、沿用的旧有限证据、确切失败、未运行。不能因共享校验改变把所有旧证据直接重标通过；也不另造无限新矩阵。
4. 对尚未完成部分给一份具体有界清单，区分已确认产品缺陷、驱动/输入问题、缺少验证。评估作者所称“纠正额度已用”对应的是 L 驱动还是两个冻结业务候选，明确事实与规则依据。不要自行给作者续派、修复或追加业务次数；调度根据本次结论决定一次合并后续。

已知未完成项仍保持 REWORK，不要求审查者补写产品/驱动来获得通过。允许对已证明范围单列有限结论；整体 A03、I01 释放和集成由调度决定。未确认问题不要顺便扩为新标准。

## 工作方式与输出

使用隔离审查副本及 raw Git bytes；`git -c core.longpaths=true`。不要在作者目录、主目录产品或旧失败库上运行。只在主目录交付 `docs/tasks/A03-R1-review-report.md` 与 `docs/evidence/A03/R1/review/`，报告注明确切版本、命令、限制及自有会话释放。原始证据不改写。不得启动平台、OCR、付费模型或 B 侧操作；原 A03/T3 对话不续派。
