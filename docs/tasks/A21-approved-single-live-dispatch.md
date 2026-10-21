# A21 已批准的一次登录及同会话书源读取

用户对固定提案直接回答“批准本轮一次登录及读取”。提案 SHA d2539d443c95ddc1ac39e43ff5f1a7a42824e2e1d0be2dfd3fc15d34fc0deffc，问题及原答复保存在同目录 answer-record.json；授权只覆盖本轮，不恢复旧额度。正式独立与调度已 ACCEPTED_OFFLINE_ONLY，完整47项绑定一致。

原执行 01a15c27-595a-70e0-88b4-fe064550c884，产品 b65d85156b56840d6ae055880d4d707b998e2ff3，final cf03910d9554d6e3198c59494de2d4ce7bf7ad80，候选 SHA f0710e872776c452728e68710052c8580ae45fc4ea55cbff7fddb11a11d18657，产品 workflow 82c2b7ee62a126bb74bc08c2d2dedbe5c556d1ca。从固定 raw 目录 `D:/1800-worktrees/a21-static-image/docs/evidence/A21/static-image/raw-checkout` 按 docs/evidence/coordinator/a21-live-dispatch/dispatch-intent.json 的完整 argv 启动外层 launcher 恰好一次；27依赖、候选及三个模板已逐bytes核对。环境 PYTHONIOENCODING=utf-8，DEBUG/PWDEBUG不设置。不先跑静态launcher、suite、旧驱动或额外探测，不直接调用内部probe。

唯一窗口 UTC 2026-10-21T04:00:33.566376+00:00 至 2026-10-21T04:15:33.566376+00:00，900秒含释放。activation SHA 1a158399b9350c605a036cb255dcf82c35364ae8198917926d1504ce215beb95，decision SHA 53254d74c20fda06724bfbfa94718cc49fc8192a5b3feb543108b0a3a9f7e9b0，独立机器报告 SHA 2fa24bc6c8cb1cd7a898a502bed0ba678b331ab6c04cd0732eff452ea3d9523a。原profile指纹 b4620cd9fe064121a916062126321b7bba3862185d8919bf228f1399097a0d00。本轮原context临时TLS例外仅固定来源，保留Edge及原profile。

最多1外层启动、1原context、按序登录页/qieti/login和viewer/qieti/annotateUnified各1固定Document主导航、最多1次官方UI登录提交。真实配置仅固定产品在本轮受控步骤读取 D:/1800/.local/usense-login.json；禁止人工读取/输出值。登录POST仅原站/qieti/api/user_login/login，username/password两键，点击前意图标记，双层一次预留约束同一请求。验证码/MFA、未知、拒绝或异常立即停止；不refresh POST、不重发、不第二次点击。

认证后必须在同一context继续全部六个固定业务GET、viewer14/173两原图各最多一次；session三路径在LOGIN/VIEWER各最多一次，version至多1、共享拒绝排除16。所有精确URL/参数/表单和响应判断以已冻结候选及提案为准，不临时放宽。0业务写入/上传/OCR/样题/书级提交，正文/schema未知、写入资格false保持。URL或HTTP200不能单独证明认证，审计事件不冒充发送次数。

首次异常或未知、过期、占用/标记冲突即停，保留首错与后继NOT_RUN。禁止重试、延期、清标记、换目录、换profile、token注入、复制其他会话或批量kill。只等待本次自有执行session，固定产品负责自有资源释放；身份/根因未知如实记UNKNOWN，不额外探测补证明。

完成后只在作者工作区新增 docs/evidence/A21/static-image/live-delivery/，固定脱敏报告、原始结果/审计/登录安全元数据/释放、raw清单及final commit并释放。不得提交凭据、完整URL query值、headers、cookies、profile、原Script或sidecar；Script仅.local。不得改冻结产品、旧原件或根协调文件。明确实际登录次数、认证/书籍/目录/框/源图/映射、首错和释放依据。由同正式独立静态核实际结果。其他三例HOLD、Q22不导航/样题/重放、0B消息。作者不自行开启任何后继。
