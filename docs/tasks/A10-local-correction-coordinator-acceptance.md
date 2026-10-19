# A10本地检查器与清理差量：调度有限接受

2026-10-19。有效结论 `ACCEPTED_LOCAL_NATIVE_CHECKER_WITH_AUTHORIZED_CLEANUP_DELTA`。这允许准备下一固定只读前检driver，不代表真实Windows调用、profile空闲、浏览器或平台已验收。

- 原纠正候选 `5543aba6fdcc146a5b1439a539ba0046e5f11cda`：14新增，29,952旧路径保全；13成员52,616bytes及自排除raw清单核对。原独立 `1df8d7dbf0e9d01f38277a66932f983e6c24efee` 一次23项通过，但保留 `HOLD_OWNED_HANDLE_CLEANUP`，仅作为历史结论，不抹去R01。
- 用户[追加授权](../approvals/A10-owned-handle-cleanup-delta-approval.json)明确一次清理段差量。产品/驱动 `1341fec30eca224019b432e57e73ad51dfcaabc4`，作者最终 `52f1738c29955661f188f3e585b292fd72cb70a8`；14新增、29,966旧路径及6个产品成员原bytes保持。最终13成员34,436bytes、授权及原依赖摘要全部核对，见[交付预检](../evidence/coordinator/a10-local-correction-20261019/cleanup-delta-preflight.json)。
- 独立 `de5a8e988aceb15406391d62d9c670c8fb9b38c9`：11新增、10成员29,848bytes及自排除清单核对；清单SHA `ab4f55222a2b85b1f26eb8054f9c1d7552290ede13ff5b0f64c02c4b3e383d4b`。独立仅一次五例差量，5/5通过并释放。

调度静态核对逐例真实记录：三个close均各尝试一次；句柄关闭失败准确记录false，任一异常拒绝返回数；两流关闭异常且退出未证时仍尝试句柄，保持 `OWNED_CHILD_EXIT_UNPROVEN` 与exit_observed=false，不因handle_closed=true而升级为已释放。原清理段以外前后bytes和依赖保全。调度0新增测试、0真实进程探针/profile/browser/platform。

R01在这一次固定差量范围关闭。作者和独立新增额度均用完，不追加验证；旧23项结果、原错误源码、旧失败和一次性标记保留。实际profile匹配、真实Popen原句柄行为、登录、网络、原图与坐标仍需原计划中尚未发生的一轮只读观察。原 `04a513c7` 的精确PID证据缺口不以新结果回填。

下一步按[新前检接线任务](A10-native-readonly-preflight.md)先固定新driver及输入，调度登记唯一启动后才访问平台。用户既有连接/测试书许可持续有效；本接受不产生新题写入、OCR、送审、题22重放、推送或B消息权限。
