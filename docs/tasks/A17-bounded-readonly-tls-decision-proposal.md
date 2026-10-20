# A17 本轮真实只读观测：临时 context 证书例外决定提案

2026-10-20。状态 **READY_FOR_USER_DECISION / NOT_AUTHORIZED**。正式独立及调度已接受精确候选的有限只读预检，下一步直接取得真实当前书籍、来源和题框库存。无需补做旧21组测试，不因非阻断报告残留另开修订；本提案不申请业务写入或额外诊断轮。

## 已固定版本与验收

| 项目 | 固定值 |
| --- | --- |
| 产品 / final | `1168a75eb35f319c3ced270b6c515adbdb38603f` / `8bffd88dacc146fc3f061ed0863b299fa5dabd30` |
| 候选 SHA256 | `4ed38cb1f703c3d0b5e94d601f2f267c05ead871b9a26004e2e44e5d6eeb31dd` |
| 产品 workflow / run_id | `d137a1bba49550f661b110ee14c9541a1dc4fb19` / `A17-excluded-static-01a158fd-281c-7282-a3b4-db876697686c` |
| scope | `CURRENT_BOOK_SOURCE_INVENTORY_EXCLUDED_STATIC_OBSERVATION_ONLY` |
| 正式机器报告 SHA256 | `8973892de754b4a28f506ab76b53a0eb3df1494e9b95f42f9e4bd8347f474b51` |
| 正式报告 / 清单 SHA256 | `9ca171b6e205993c1d411bcb5ad70f5398c77662ce8e2464b18c8b4df5c67a5e` / `77c9b557a0151624c05971264903bb4657aee1ac9c86579d2cbbd74c056f8743` |

[正式独立报告](../evidence/coordinator/a17-independent-closure/REPORT.md)结论为 `ACCEPTED_OFFLINE_ONLY`，依据 `BOUNDED_READONLY_PREFLIGHT`；新11项差量、两个独立小控制均无阻断失败，19报告成员+清单、56输入已核原bytes。R01残留仅影响顶层错误显示：嵌套具体首因、拒绝与停止原件完整；不声称R01全关闭。旧21组NOT_RUN保持，未证明真实认证或平台取数。

## 这次实际做什么

只复用原专用无头 profile，保留日常 Edge 登录态；最多 **1个 context、1次主导航、900秒含释放**。目标 `https://www.usense.com/qieti/annotateUnified`，书 `46007447`。

- 六个固定业务GET各最多一次：书查询、目录、全量题框、来源元数据、viewer14和173页响应。UI已发则复用捕获，不再次发送。
- viewer14、173两张原图各最多一次，地址必须来自本轮页响应；仅主站或 `https://oss-ef-bd-2026-gz.oss-cn-guangzhou.aliyuncs.com` 的 `/upload_images/46007447/`。同源session/static原白名单保持，不能把这些辅助请求混称总HTTP只有8次。具体固定规则见[本候选policy](D:/1800-worktrees/a17-first-cause-r1-review/src/annotation/source/usense/current_readonly/policy.py)。
- 已观察的 `https cdn.bootcdn.net:443 GET Script` 仍发送前拒绝，符合原主框身份、非重定向等条件时允许继续观测；两层合计最多16个排除事件。不会下载、替换或另取该脚本，也不假称它非必要。
- 样题、登录提交、业务写入、上传、OCR、书级送交均0。原始同源脚本仅捕获既有获准响应，保留在受控 `.local`，不增加请求。

首次非预期失败、身份/数据不足、期限或标记冲突就停止；不重试、刷新、延期、清标记或换目录。正确拒绝和停止的报告名称差异保留原件即可。成功也只记录有限只读事实，正文/schema UNKNOWN、样题NOT_RUN、写入资格false。其他三例HOLD、Q22不重放，0B或外部联系人消息。

## 本次需要的决定

仅为上述 **这一个专用 context** 临时启用 `ignore_https_errors=true`（`tls_mode=CONTEXT_EXCEPTION`），同时影响主站及获准OSS请求；CDN仍被拒绝。既有登录态可能随主站请求发送，忽略证书校验时不能依靠证书可靠确认服务端身份。不开全局设置，默认行为保持严格校验。

本轮不另测证书；不把A14历史观察说成当前证书状态，也未证明OSS证书有问题。此前A16的“仅此轮”批准已用完，不能转移。本决定只覆盖以上固定A17轮次，不授权下一轮或后续写入。

明确批准后，由调度绑定答复原文、本提案SHA、候选、机器报告、原专用profile非敏感指纹以及新的15分钟UTC窗口；再派同一正式执行对话运行唯一一次，固定结果后由同一独立核验。当前尚未创建决定或激活对象：

- 决定：`D:/1800/docs/approvals/A17-excluded-static-user-decision.json`
- 报告：`D:/1800/docs/evidence/coordinator/a17-independent-closure/independent-result.json`
- activation：`D:/1800/.local/stages/a17-excluded-static-activation.json`
- 唯一输出：`D:/1800/.local/stages/a17-excluded-static-live`

执行 `01a158fd-281c-7282-a3b4-db876697686c`、独立 `01a158fd-cbeb-7a31-a3e6-661c7d4c95d4`，host local。未收到本轮明确决定前不创建activation或启动live；平台连接和测试书许可无需重新确认。
