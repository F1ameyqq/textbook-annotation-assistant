# A19 已释放实际证据：登录目标路径匹配

辅助静态比对，非正式实际验收。旧 notes 保持。来源为实际 final `38e86a1c153eb0ad68ebd22d4403602ffaa6852b` 的 Git raw；未读取 .local live、活动作者目录或 source sidecar。0 产品执行/import/测试/网络/browser/profile。

**结果：目标 path hash 精确匹配 `/qieti/login`，该路径是已捕获 Script 明确出现的登录导航目标。** 原 TARGET 路径 `/qieti/annotateUnified` 的 hash 不同；本事件不能解释为原 TARGET 路径本身的原样重载。是否由某个具体响应、认证状态或其他流程触发，仍 UNKNOWN。

## 固定实际与算法

- `docs/evidence/A19/navigation-evidence/live-delivery/network-audit.json` SHA `d66f01560587428a54327e945ec89b992ad1ee0fa2c87841dcb43d87861ab397`，14 个事件与 `raw/current-state.json` 内嵌 network_audit 完全相同。
- `raw/current-state.json` SHA `7fdc9ce0f422937cceeb29698df6ff6ca473fc4e76d145c92f186645b31fbc8a`：原导航 DONE，返回 HTTP 200，DOMContentLoaded 已观察；goto 15391 ms。readiness 在 30172 ms 后为 TimeoutError/UNKNOWN；book 及所有后继 NOT_RUN。两个 guard snapshot 首错均为 Stop/NAVIGATION_BLOCKED。
- 被拒绝事件时间 `2026-10-20T13:50:39.712394+00:00`，`source=FETCH_REQUEST_STAGE`、`GET`、`Document`、`decision=BLOCK`、`category=NAVIGATION_BLOCKED`、`redirect_hop=false`，`https / www.usense.com / 443`；query 名列表为空且 redacted 名数 0。这里只识别 pathname，不补造完整 URL/query。
- actual final 的 policy SHA 仍为 `6665327d71e35e895b67bc578eec5f58165cd8e3a1713fb447112bc9abd7aea2`。`policy.py:101–102` 算法为 `urlsplit(url).path` 的 UTF-8 bytes 做 SHA-256；不包含 origin/query。
- 原生分支 `probe.py:472–476` 以已绑定 main_frame_id 判断 ownership，`classify:346–365` 先覆盖非自有、已停止和 redirect。结合本固定最终 category，可从固定分支推得该拒绝事件属于原主框、无已观察 redirect 标记；不是仅凭 `main_navigation=true` 字段下结论。

## 仅对明确源码路径的哈希匹配

| 明确来源 | pathname | SHA-256 | 比对 |
| --- | --- | --- | --- |
| gate 固定 TARGET | `/qieti/annotateUnified` | `87ec8139f55b0c2b54ad542b07fea420ccd00dd1020e2c758dfb82005d0a63c3` | 不匹配被拒绝事件；匹配原导航 ALLOW |
| Script 两处 window.location.href 导航赋值 | `/qieti/login` | `55d900e6fc7524cac0de130ea2e6c249426846e56af5165e9b0ddbcaed4d746d` | **精确匹配被拒绝事件** |

Script 原件为此前获准的 A17 static asset，本次重核 3,065,996 bytes 与 SHA `d0a5ebce18bc92d7643662ecec2d078bb295214111e7cb32688f0b88e05bed41` 一致。A19 固定 current-state 的唯一 static_assets 成员也记录相同 SHA/size；没有读取其 A19 .local 副本。

所有 Script offset 为 **0-based UTF-8 bytes**：

- `/qieti/login` 字面量位于 **1068568、1069044**；相应 `window.location.href` 赋值起点 **1068547、1069023**。
- 两处静态赋值均位于 `response.status === 401 && !_retry` 条件所在分支（条件起点 **1068180**）。这只能说明源码具备相应跳转路径，**不能证明本轮确实收到哪一条 HTTP 401、触发了哪个分支，或为何认证未成立**。
- router 路由对象起点 **3062006**，`path: "/login"` 的字面量 **3062012**、`name: "login"` 字段 **3062021**，补充确认其登录路由语义。实际匹配直接采用源码已明确的 `/qieti/login`，没有靠拼接、字典候选或网络试探。

## 对下一步的有限作用

现在可以把后续适配焦点收敛到“原导航成功后，原主框尝试进入已知登录目标而被拒绝”。原页面 HTTP200/DCL 不证明认证书籍页面就绪；版本 GET 的 1 次预留也不证明版本变化或 reload 因果。本次未保存 initiator/call stack，不能判定具体跳转函数，不能据 hash 匹配自动放行登录、第二导航或恢复额度。

此前建议的 version→reload 仍只是静态可能路径；当前精确 pathname 证据已经识别登录目标，但不替代正式实际验收或用户/调度对下一阶段范围的决定。准备完成、释放。

## 追加：两处跳转条件与本轮响应缺口

同一素材 SHA 不变；以下均为源码条件，未读取任何存储或凭据值。

- 共同入口：响应拦截器的错误分支，存在 `response`、HTTP 状态为 401、原配置 `_retry` 尚未置位（1068180），随后设置该标记（1068231）。
- 第一处赋值 **1068547**：将响应 `data.detail` 与 `data.message` 的缺省空串拼接（1068249、1068318、1068388），检查是否包含“过期”、`expired` 或 `exp`（1068394）。**均不包含**时清除本地会话记录、跳到 `/qieti/login` 并拒绝原错误。它不是“本地缺少凭据”这一单独条件。
- 第二处赋值 **1069023**：在上述字符串被判为过期后进入刷新 `try`（1068601），其 `catch`（1068975）清除会话记录、跳到同一路径并拒绝捕获错误。可见异常来源包括本地记录缺失、JSON 解析失败、等待刷新 POST 失败及后续同步处理错误；不能仅凭该跳转断定刷新请求已经发送。返回原请求调用不带 `await`，其后异步拒绝也不能一概归为此 `catch`。
- 本轮固定审计仅保留 `/qieti/api/user_login/config/permissions` 的 native/context 两个 `SESSION_GET/ALLOW` 事件（13:50:39.574044 / 13:50:39.589555 UTC）；**没有该请求的响应码、响应分支或刷新异常分类**。`current-state` 的响应遥测只绑定原主 Document，另有静态素材状态；权限 GET 的两个事件不能当两次请求，也不能当 HTTP401 或成功回执。

因此仍不能从本轮原件区分两处分支。最小缺失事实是：该已知权限请求的实际响应状态，以及触发跳转的有限分支类别；如为刷新异常，尚缺“本地前置异常／刷新响应失败／后续同步异常”的类别。无需原响应正文、错误文案值、存储值或凭据。这里仅标记缺口，不新增观测、重跑或授权。

## 追加：登录恢复的最小静态线索

当前 bundle **包含登录组件及提交代码**，不是仅有登录路由：

- `Ui` 在 **1067312** 定义路径 `/qieti/api/user_login`。`Pze`（**1069840**）于 **1069878** 调用 `gn.post`，精确相对路径为 **`/qieti/api/user_login/login`**，JSON 键仅 **`username`、`password`**。`gn.create`（1067577）没有 `baseURL` 设置，故此调用使用当前页面同源路径。
- 登录组件 `IFe` 的提交处理先检查两个输入非空（1095309），在 **1095395** 调用 `Pze`。包装器将响应交给 `Hn`（1069932）：若响应体具有数值 `code`，仅 0 或 200 被接受并返回 `data`；其他数值抛错；没有数值 `code` 时直接返回响应体（1069105–1069288）。这不是服务端认证保证，也没有显式验证返回凭据非空。
- 此调用正常返回后，组件写入本地会话对象（1095416），再 **`router.push('/')`**（**1095613**）；异常分支在1095625显示错误。没有自动回到原 TARGET 或认证书籍就绪的证明。组件经 `EFe`（1097152）绑定至 `/login` 路由（3062006）。
- 该调用使用同一 `gn` 响应拦截器，静态代码还存在刷新 POST 和原请求重发路径；不能把直接调用旧 UI／工具自行等同为“恰好一次凭据提交、零附带请求”。具体登录次数、凭据提交时 TLS 范围和成功后读取边界须由下一明确任务绑定；本附录不授权任何提交或调用。

本次仅固定源码与释放 raw 的静态追加，原 notes 保留，0 产品运行／测试／网络／浏览器／profile／凭据读取，辅助完成、释放。
