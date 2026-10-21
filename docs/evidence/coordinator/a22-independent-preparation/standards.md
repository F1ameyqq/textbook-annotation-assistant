# A22 独立验收准备标准

状态：PREPARED_WAITING_FIXED_DELIVERY。本文件只固定标准，全部产品验证 NOT_RUN，不构成候选接受或 live 激活。

- 独立对话：01a15cad-c63a-7062-8fe6-2fc4add9e9a5；执行对话：01a15cad-c139-76e2-88f8-705093575a7e。
- 基线：29a243227893cdbd8e7d235a8c787b4d721ed8e2；workflow：68279e400143c5681338530db409060a39760c0a。
- 范围：POST_LOGIN_SESSION_REUSE_CURRENT_SOURCE_READONLY。
- 任务 SHA256：d47f5b4c37b1e97d9ee702dce9b6ab0bb65f670819875830a4af97023969b3fe。
- 独立任务 SHA256：76a3cc01dc5b300ed4ace9e6e8c80d50f076a3f7a49f3b8ae9a5dd7f50a4c1a1。

收到根核证的固定产品/final、完整 Git raw 依赖和交付清单、新相关测试及失败原件、作者释放后，根另给隔离输入，在本对话进行有限纯 fake 预检。当前不读取活动作者目录，不提前查产品/导入/运行。

| 标准 | 固定交付后需核证的事实 | 当前 |
|---|---|---|
| S01 原 bytes 与范围 | 核产品/final/base/workflow、候选依赖及父包完整、清单成员/自身 hash、根保全记录。产品差量仅 auth.py、policy.py、gate.py、a16_current_state_probe.py、a16_current_state_launcher.py 和获准新测试/证据。decode/js_wire/native/reference/OS 释放与时间守卫保持原 bytes；旧失败不覆盖。 | NOT_RUN |
| S02 零凭据动作 | read_credentials/arm_submit/reserve_login/旧登录入口在文件 I/O、表单动作、网络预留前硬拒绝；无运行时开关恢复。fake spy 核本机用户名密码配置读取、fill/click、登录 POST 均为 0；不以跳过 authenticate 代替 auth/policy/gate 一致收窄。 | NOT_RUN |
| S03 单阶段单导航 | auth 从 VIEWER 开始，不预设 reused/authenticated。唯一 TARGET 为 https://www.usense.com/qieti/annotateUnified；两层各 1 预留对应同一次实际导航。拒绝 LOGIN Document、额外主导航/reload/redirect；不修无关 /home 等待。 | NOT_RUN |
| S04 当前组合证据 | 同 context 原主框、精确 TARGET、可见受保护 viewer 容器、无登录/密码表单、本轮获准 session 响应关联与有限业务投影共同准入。单独 URL/HTTP200/本地 token/A21 历史 receipt 不准入；缺证、401/403、登录跳转/表单或 UNKNOWN 首错停止，后继 NOT_RUN，无自动登录/补请求。 | NOT_RUN |
| S05 原 session 预算 | 从冻结 SESSION 核实三条实际字面，本文不按任务缩写猜路径；VIEWER 单阶段每路径至多 1、总至多 3，按前端既有请求观察，不新增 profile 诊断必发门槛或补发。页内既有 GET_JSON 可使用既有 token；token 不导出 Python/日志/文件，不注入或复制到别的会话。 | NOT_RUN |
| S06 同 context 书源 | viewer 准入后首个 book GET 核 46007447，通过才继续目录/框/来源/页映射/两原图；成功 fake 贯穿同 context。viewer 访问、账户身份字段可用性、书籍身份分别报告。六业务 GET 各 1，viewer14/173 两原图各 1，不拆新诊断轮。 | NOT_RUN |
| S07 原双层守卫 | 两层方法/来源/主框/身份/逐跳/WS/未知 API 保持；POST 和其他写方法一律拒绝。沿用原图注册路径、窄静态图片准入、CDN 与未知同源发送前拒绝/有界继续条件；version 至多 1、共享排除事件 16。await 前记账；late fatal/未结清仍进入 ERROR/UNKNOWN。 | NOT_RUN |
| S08 完整新 scope | 新 task/run_id/executor/workflow/candidate/report/decision/activation/output/单次标记完整绑定；候选、完整 scope/template、报告、决定同类型同值逐项核，字段数按实际新范围。local_credential_config_read_limit=0、login_submission_limit=0、navigation_limit=1、navigation_sequence 仅 TARGET、session_phase_limit=1。旧凭据授权 true 和 A21/更早候选/批准/activation 拒绝。 | NOT_RUN |
| S09 期限与释放 | 最多 1 原专用 persistent context、900 秒总期限含释放。原 profile 指纹 b4620cd9fe064121a916062126321b7bba3862185d8919bf228f1399097a0d00 通过固定 profile_binding 静态核；不读真实配置/profile，不新建替换/清锁/批量 kill。固定释放证据区分持有创建身份的对象、context/runtime、launcher 自身 OS 身份未知，不作 OS 全局扫描补证。 | NOT_RUN |
| S10 权限与预算 | A21 已关闭且 live1/余0，不重开。核 A22 自己的唯一额度/版本/窗口及 A17 同类只读 TLS 持续许可绑定；此准备不生成决定/activation，不借 A21 登录许可，不恢复旧额度。登录/写入/上传/OCR/样题/书级提交均 0，其他三例 HOLD、Q22 不重放、0B/外部联系人消息。 | NOT_RUN |

有限控制集中覆盖：成功 fake 同 context 全链；凭据 I/O/表单/提交零 spy；第二导航/第二阶段或同路径第二 session 拒绝；历史 receipt 拒绝；登录/401/403/缺证/UNKNOWN 停止；两层 POST 和旧授权拒绝；await 前预算、late fatal 及完整 scope 的代表性单字段改动。实际控制先按冻结差量精简，不运行真实产品/launcher/native 子进程。此表不是预先批准任意 suite。

旧 A21 16/5 及所有旧 suite 不重跑。未改模块只在核得精确 raw 同一性和原有限证据的适用层后引用，不能升级为新平台证明。实质越界、错误准入或安全失效固定证据后停止并报 REWORK；正确拒绝/停止且原件完整的细微报告差异可列限制，不做无关返工。

预检结论最多为 ACCEPTED_OFFLINE_ONLY / BOUNDED_READONLY_PREFLIGHT，不证明真实认证、profile 持久化、书源或首题保存读回。正式结论须有完成的独立报告；当前等待固定交付，不保留进程等待。
