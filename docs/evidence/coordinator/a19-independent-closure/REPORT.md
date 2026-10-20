# A19 导航证据适配：有限独立预检

结论：`ACCEPTED_OFFLINE_ONLY / BOUNDED_READONLY_PREFLIGHT`。仅接受固定 A19 产品的离线预检，不证明认证、当前书源库存、真实平台成功或写入资格。

- 基线：`35ad2ef50088373435f48f530efe32b59824da8e`。
- 产品：`13067ff38ea8c0fbeae1c896d415c79238443b0e`；final：`e999f4e753cd5f1e44a19ab55dd776d2fa589389`。
- 产品 workflow：`c4cfdb2012b36f47f13e633a24dafad6c3daa8ab`；本次独立派发 workflow：`dbe356d7742228af4f7690a1534bbe065e2aebaf`。
- 正式独立：`01a1597d-225a-7902-837a-5d5a2dadffe2`；原执行：`01a1597c-8eb9-7692-8279-685c4d9d105d`。
- 候选 SHA256：`2e94be09ff3d733bcf65b7fa556187280deb09574134866b110e3575dd233f7f`。
- 固定输入清单 SHA256：`71e0d0b8d8f5c3d504126a4f55d695c220873df4623d1d40a44dbf3be23cc1bc`。
- 仅消费 `D:/1800-worktrees/a19-independent-fixed`，未读活动作者目录。输出全部新增于本独立目录，未覆盖作者 runs/raw-checkout 或候选。

64 个输入 raw 逐项核大小、SHA256、Git blob SHA1；20 个候选依赖及其 raw-checkout 副本相同；55 个交付清单成员全部核证。运行后再次核实 64 个输入未变，新增文件全部在独立输出目录。基线 31677 成员、30448 旧 evidence 的全面 mode/type/blob 保全引用正式派发中的调度核证与固定 preservation 记录，本独立未重做完整基线 Git 树比较。policy/decode/js_wire/native 六份固定原 bytes 与候选、raw 副本一致；未改请求规则和释放实现只在该同一性边界内引用原有限证据。

| 实际验证 | 结果 | 本进程耗时 |
|---|---|---|
| 固定 A19 新差量 | 18/18，0失败/错误 | 438ms |
| 独立少量控制 | 3/3，0失败/错误 | 141ms |

新辅助 runner 仅调整输入 ROOT、输出目录、测试模块位置及 failfast；固定测试源码未改。使用纯内存 selector、伪 page/session，以及网络、Popen、native、profile 和占用禁用补丁。实际命令与结果见 `execution.json`；逐项输出及原始快照见 `delta/run01/`、`controls/run01/`。没有运行旧 A18 20/4、A17/A16 或其他 suite，历史 NOT_RUN 不重标。

有限证据支持以下判断：首次获准原主框 Document 的 networkId 仅驻内存，无关请求/iframe/未知身份不归入其响应；HTTP 数值、loadingFailed 的取消/安全码与异常来源分开，缺失关联保留 UNKNOWN。独立混合来源控制同时保存 HTTP503、事件 ERR_ABORTED 和 TimeoutError/ERR_TUNNEL_CONNECTION_FAILED，根因仍 UNKNOWN，未回显敏感哨兵。goto/readiness 的阶段、本进程 monotonic 耗时和原 45000/30000ms 保持。新增监听同步且被动，无新 CDP 命令、请求、body 读取或异步任务。

首错及最终结清控制通过；晚到/SEALED 事件保全，首错不被清理错误覆盖，既无新发送也不复活轮次。导航成功路径在同一 collect 中进入原书源读取；导航失败后继保持 NOT_RUN。仅修改获准 probe/gate/launcher，未接受任何网络策略、超时或预算扩大。

机器结果从冻结模板生成，逐项核完整 29 项 scope_binding，包含全部预算及零登录/写入/上传/OCR；独立控制拒绝窄18项报告、布尔替代整数预算、非零上传/OCR和旧 A18 报告路径；原新18项同时核旧 A18 activation/身份拒绝。scope/run_id/workflow/executor/candidate/决定/报告/activation/output 均绑定 A19。

作者首次 PowerShell stdin SyntaxError、复合命令 exit0 与写入器单独退出码 UNKNOWN 原件保持，不归为产品失败。没有发现本次有限范围内的阻断项；离线伪事件不能证明真实 CDP 事件一定到达，缺失 networkId/事件时仍须 UNKNOWN。旧 A18 失败、根因/HTTP/认证及 launcher 自身 OS 身份 UNKNOWN、已耗额度均保持。

本独立不创建 decision/activation/live。调度可依据本有限接受及用户已有同类 TLS 持续许可，绑定 A19 自己唯一具体窗口：1 launcher/1 原专用 context/1 主导航/900秒含释放，六固定 GET、两原图各最多一次，version1、共享排除16；成功直接同轮集中书源读取，失败固定新诊断后停止。session/static 仍按原白名单，不将总 HTTP 冒称8或9。

sample0、自动schema停用、正文/schema UNKNOWN、write_eligible/production_ready=false、旧 R02 未修；其他三例 HOLD、Q22不导航/样题/重放、0B消息、无书级提交。真实运行和首题保存/刷新重开独立读回尚未证明。

已释放本次独立执行资源：两个纯离线 Python runner 均 exit0，无产品/launcher 子进程、browser/context、network、profile、native、占用、login/write 或持续等待进程；未查询/终止无关进程，未改根协调文件。释放仅适用于本次独立，没有提升历史 launcher 自身 OS 身份结论。
