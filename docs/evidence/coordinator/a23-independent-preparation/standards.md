# A23 独立准备标准

状态：WAITING_EXECUTION。仅准备，无产品结论；本轮结束即释放，不保留等待进程。
绑定：CURRENT_SESSION_COMPLETION_AND_SOURCE_READONLY；workflow d86dbcb82ebd7b61d5e87f02402bfe8a6bcd1b15；base 3517982bd416ff77fdf596e80c502a75d780f2b9。

根提供作者固定产品/final、明确释放和隔离 Git raw 后，再进行必要的新差量预检。先核原 bytes、依赖闭包、允许差量及旧证据保全。只读固定 raw，不读活动作者目录；不刷旧 suite 或历史 NOT_RUN。未改部分仅在 raw 同一性成立后引用原有限证据。

| 重点 | 必须成立的边界和最小观察 |
|---|---|
| 原请求结清 | 先核原 page/main_frame、精确 TARGET、可见受保护 viewer、无登录/密码表单、guard 无失败。已有本轮成功有限投影则复用；已预留/在途 session 关联原 request、frame 和两层预留，在同一 <=20 秒期限内等原响应及 body 投影，不能只等回调队列为空；不得重置期限或补发。 |
| 唯一主动 GET | 仅没有本轮成功投影且没有任何已预留、在途或 UNKNOWN session 时，允许原页面内精确 /qieti/api/user_login/profile GET <=1，计入原 session 三路径各1/总3。调用前同步预留意图，await 前记账；原权限/teams 只被动观察。已有失败或 UNKNOWN 不可补救。 |
| 双层并发 | 核主动意图、前端请求、两层预留、真实发送之间关联。覆盖前端先预留、主动先预留和 await 边界交错，任何同路径第二发送须被阻止；不能用最后计数覆盖已发生双发。 |
| 有界停止 | 延迟原响应可成功；超时、401/403、网络失败、错 request/frame、晚到 guard 失败均停止并保留首错/UNKNOWN；原 pending 结清、900秒含释放和一次性捕获复用保持。 |
| 有限投影 | Python/日志只收固定 HTTP、有限业务结果和身份字段是否存在，无完整 body/profile、用户名、token 或原身份值。HTTP200、token 或 A21 历史响应不独立证明当前身份。主动 profile 语义不足则 UNKNOWN 停止；permissions/teams 有限准入可保持账户身份 NOT_OBSERVED，不能为补身份额外 GET。 |
| 零新增登录/写入 | 用户名密码配置读取/解析、填写、点击、login POST、refresh、自动重发、业务写入、上传、OCR、样题、书级提交均0；原 auth 禁登录入口仍在 I/O/预留前拒绝，无开启开关。认证材料留在原页面既定 GET 中。 |
| 同轮书源 | 当前组合证据成立后，同 context 按原序读取 book46007447、目录、全量框、来源、page14/page173 六GET及两注册原图/映射，各1。成功不在认证处提前结束；原图只用本轮源响应登记 URL，不猜 URL。book200/ID 不独立证明账户身份。 |
| 范围和未改边界 | 完整绑定 task/run/executor/workflow/candidate/模板/报告/decision/activation/output、20秒、精确主动路径和1次、session总3、credential/login/write=0、原profile指纹、单context/单viewer导航/900秒、六GET/两图各1、version<=1及共享排除16。仅五获准产品文件的必要差量；decode/js_wire/native/reference/OS释放/总期限原bytes保持。原静态窄Image、来源逐跳、方法、WS/API身份、登录跳转/表单和未知API停止边界保持。 |

未来必要 fake 控制集中覆盖上述新语义；作者测试只是输入。微小报告差异若正确停止且原件完整，列限制，不为格式重跑产品。语义反例/越界/依赖缺失保留原件并明确 REWORK 或未完成范围，后继 NOT_RUN。

未来最高结论为 ACCEPTED_OFFLINE_ONLY / BOUNDED_READONLY_PREFLIGHT，不能宣称实际平台认证、书源、首题保存或独立读回已通过。A22 当前只据协调记录为作者固定释放、实际失败静态独立仍活动，本轮不代审。A23 live 还需 A22 释放核证、固定交付、正式独立与根预检，由根绑定 A17 持续同类只读 TLS 许可和 A23 自己唯一轮；不重复询问同类 TLS，不自激活，不借 A21 登录批准或旧耗尽额度。其他三例 HOLD，Q22 不重放，0B/外部消息。
