# A16 只读观测版：本次 context 证书例外决定提案

2026-10-20。状态：**具体方案已固定，有限离线独立验收及调度核证通过；本轮用户决定待答，尚未批准 TLS、尚未激活或访问平台。**

本提案仅请求允许以下固定候选在一次专用无头 context 内临时忽略 HTTPS 证书校验，完成当前书籍、来源、库存与静态脚本的受限只读观测。不是全局设置，不适用于下一轮、其他书、登录提交或业务写入，不转移 A15 批准，不恢复旧额度。

## 固定版本及已完成的前置核证

- 执行对话 `01a15840-7766-7533-818d-cc016aa0a60b`，正式独立对话 `01a15841-0d44-7272-9740-40d013839869`，调度 `01a15768-1e2d-7781-b29f-1f7376270216`，host local。沿用 A16，不创建重复阶段或聊天。
- 产品 `dd22193a30e969aaf90043365f31f84a5a50df59`；final `2453c71c070c153a22a49b772bb2696b3858f5d4`。
- 候选 SHA256 `e66e9f96197871f7123ebe2ed981a587262c50fb3f6e62cdc300f8e96be5a63f`，产品范围 workflow `afed9807c77f33d5363d706d5341acb1fd172baf`。
- scope `CURRENT_BOOK_SOURCE_INVENTORY_STATIC_OBSERVATION_ONLY`；run_id `A16-current-readonly-01a15840-7766-7533-818d-cc016aa0a60b`。
- 正式独立 result `ACCEPTED_OFFLINE_ONLY`，仅上述 scope、sample_limit=0。新 suite 18/18、500ms；独立控制9组全通过、250ms；默认 launcher 仅静态通过，三项自有子进程 wait/exit0。没有真实资源待释放，不扩展为实际 OS 创建身份退出证明。
- 正式机器报告 SHA256 `d536d9b2552586a0e1838384a1b2775df1b14023d3e7ad901ac1a2b991e06a0c`；清单 SHA256 `19c2be4f37d97b5ebd77ca0264a723cfa440a86cfd52ac7cac8bb56926a236ba`。调度核38报告成员及清单自身、59冻结输入均原bytes一致；31259基线和136旧A16证据保全证据有效。
- 固定报告和核证入口：[REPORT.md](../evidence/coordinator/a16-observation-independent-closure/review-output/REPORT.md)、[review-result.json](../evidence/coordinator/a16-observation-independent-closure/review-output/review-result.json)、[intake.json](../evidence/coordinator/a16-observation-independent-closure/intake.json)。

## 请求批准的实际行为

| 项目 | 本轮上限和边界 |
|---|---|
| 会话 | 只复用原专用登录态，最多一个新无头 context，一次主导航，无刷新、重开、重新登录或凭据导出。保留日常 Edge。 |
| 目标 | 书 `46007447`，`https://www.usense.com/qieti/annotateUnified`，viewer仅14、173。 |
| 时间 | 激活时写明 UTC 起止，窗口最多900秒，含释放。worker870秒、product890秒、外层900秒。过期、首个意外异常或身份不符停止，不延长窗口或自动重试。 |
| 业务GET | 以下六个规范化URL各至多一次实际发送。若UI已发送则复用已捕获响应，不能补发：同源 `/qieti/api/claim_book/books?page=1&pageSize=10&id=46007447`；`/qieti/api/annotate_ocr/directory/get?file_id=46007447`；`/qieti/api/annotate_pic/get_manual_annotations_unified/46007447`；`/qieti/api/annotate_pic/pre_annotation_source/46007447?annotationType=mr_pre`；`/qieti/api/annotate_pic/pre_annotation/46007447?pageNum=14&annotationType=mr_pre` 与 pageNum=173。 |
| 原图 | viewer14/173各一次，仅从本轮当前单页响应绑定后读取；允许 `https://www.usense.com` 或 `https://oss-ef-bd-2026-gz.oss-cn-guangzhou.aliyuncs.com` 下 `/upload_images/46007447/`。无query、凭据、fragment或重定向，不猜地址、不扩展域名。 |
| 辅助资源 | 保持已审查的同源session/static GET/HEAD白名单：`/qieti/api/user_login/profile`、`/qieti/api/user_login/config/permissions`、`/qieti/api/user_login/config/teams`；`/(qieti/)?(assets|static)/`静态扩展名及两个favicon。确切集合以固定 policy.py 为准，不扩范围。“六业务GET＋两原图”不等于总HTTP请求只有8次。 |
| 静态素材 | 仅留存正常页面加载、本轮已获准同源Script成功响应的原bytes/hash/source，不增加取脚本请求。原件和完整来源sidecar只存受控 `.local`；公共结果只有引用/摘要/长度/脱敏来源，采集器不解析或执行保存素材。 |
| 禁止副作用 | sample_limit=0，自动schema确认关闭；五样题GET及register_sample硬拒绝。登录提交、业务写入、上传、OCR、书级送交均0。Q22只随全量库存自然保留，不选择、导航或重放。其他三例HOLD，0 B或外部联系人消息。 |

仅本次 context 的 `ignore_https_errors=true`。该选项也覆盖上述获准 OSS 原图请求，不只覆盖主站。既有登录态可能随请求发送到主站；忽略校验时证书不能可靠确认服务端身份。这是本次例外需要用户直接决定的实质变化。

A14固定历史证书观测曾发现 `www.usense.com` 所得叶证书 SAN 仅含 `qt.lingshubao.cn` 且已过期；根因UNKNOWN。本提案没有新测证书，不能声称当前仍完全相同，也未证明OSS证书有问题。不改访SAN域名，不改系统信任库、代理、日常浏览器或全局默认证书策略。默认仍严格TLS；用户未批准时不自动发起一轮严格尝试。

## 批准后的机械绑定与停止条件

原专用 profile 的非敏感绑定沿用固定参考 `docs/evidence/coordinator/a13-observation-closure/execution-output/live-records/profile-binding.json`，参考 SHA256 `7f67decdf6bdc88d79249a71d64d05d3dc134fadee86dcbafe6badb8df82765c`，profile_fingerprint `b4620cd9fe064121a916062126321b7bba3862185d8919bf228f1399097a0d00`。这只是既有绑定，当前未扫描占用、读取profile或认定认证有效。实际启动须由已验收固定链核同一指纹、锁/占用；不符就停，不换profile或清锁。

用户直接答复后，调度将决定原文及本提案SHA绑定到该候选，使用 `A16-current-readonly-activation/v2`，连同固定独立报告SHA、scope/sample0/count6+2、profile指纹、明确900秒内UTC期限一并封存。固定 activation 为 `D:/1800/.local/stages/a16-current-readonly-activation.json`，唯一输出为 `D:/1800/.local/stages/a16-current-readonly-live`。本提案未创建、清理或访问这些实际运行路径；如果既有标记/输出冲突则停止，不换目录绕过。

网络来源、方法、逐跳重定向、WS/子target、未知API、登录和身份守卫不放宽。仅已证明的非必要外部Image/Font/Media首请求可预期拒绝并继续；主导航、脚本、XHR/Fetch等异常仍停止。样题接口意外触发也拒绝并停止。只释放由固定链持有身份的自有资源，保留Edge及原专用登录态，不批量kill。

本次成功也只表示取得真实只读事实：正文/schema仍UNKNOWN，样题NOT_RUN，production_ready/write_eligible=false；R02仍REWORK且对应能力停用。拿到事实后再固定具体新题内容/目录/框、业务保存payload和次数，以及回执和刷新重开独立读回。首题通过后才推进总量最多5题；UNKNOWN保存仍停书只读对账，不重发。

**拟议决定：批准上述固定A16候选仅这一次专用context临时证书例外及一轮受限只读观测。** 批准不含后续业务写入，也不含新一轮重试。未收到本轮明确答复前保持0 live。
