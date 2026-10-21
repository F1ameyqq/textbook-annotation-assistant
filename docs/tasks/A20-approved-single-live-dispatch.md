# A20 已批准的一次登录及同会话书源读取

用户对固定提案直接回答“批准本轮一次登录及读取”。提案 SHA 828db3f6f07597673db32649ec193de2d4912548661ce7dd10477bd81f2623f9，问题及原答复保存在同目录 answer-record.json；授权只覆盖本轮，不恢复旧额度。正式独立与调度已 ACCEPTED_OFFLINE_ONLY，完整39项绑定一致。

原执行 01a159aa-42b4-7103-bfaa-9767969d9b8e，产品 28203196b4f2dae27b1de4213b27da9a41ae3139，final b41e88d7756fde9d7f1b348ce5a300d1104e765b，候选 SHA 91db377e44b5b864208cc27a078d25266b3375bba2fdee18b9c648f37b572a7b，产品 workflow 52be34a72c43a7331976aba4b286138b9183856b。从固定 raw 目录 `D:/1800-worktrees/a20-authenticated-source/docs/evidence/A20/authenticated-source/raw-checkout-v2` 按 docs/evidence/coordinator/a20-live-dispatch/dispatch-intent.json 的完整 argv 启动外层 launcher 恰好一次；27依赖、候选及三个模板已逐bytes核对。环境 PYTHONIOENCODING=utf-8，DEBUG/PWDEBUG不设置。不先跑静态launcher、suite、旧驱动或额外探测，不直接调用内部probe。

唯一窗口 UTC 2026-10-21T01:33:24.446405+00:00 至 2026-10-21T01:48:24.446405+00:00，900秒含释放。activation SHA 69d597305e9a90b536380159102286b4b7a81d2505e9ff1b129f6a61bf2f7506，decision SHA ed63b7ceff7ff5d4498af1543efea86a7deba779e42920e69c07bcb6464def2e，独立机器报告 SHA 93da76c7dcd34c55b80ac6d408a328096a714d1a574876986a149d3347fd58fd。原profile指纹 b4620cd9fe064121a916062126321b7bba3862185d8919bf228f1399097a0d00。本轮原context临时TLS例外仅固定来源，保留Edge及原profile。

最多1外层启动、1原context、按序登录页/qieti/login和viewer/qieti/annotateUnified各1固定Document主导航、最多1次官方UI登录提交。真实配置仅固定产品在本轮受控步骤读取 D:/1800/.local/usense-login.json；禁止人工读取/输出值。登录POST仅原站/qieti/api/user_login/login，username/password两键，点击前意图标记，双层一次预留约束同一请求。验证码/MFA、未知、拒绝或异常立即停止；不refresh POST、不重发、不第二次点击。

认证后必须在同一context继续全部六个固定业务GET、viewer14/173两原图各最多一次；session三路径在LOGIN/VIEWER各最多一次，version至多1、共享拒绝排除16。所有精确URL/参数/表单和响应判断以已冻结候选及提案为准，不临时放宽。0业务写入/上传/OCR/样题/书级提交，正文/schema未知、写入资格false保持。URL或HTTP200不能单独证明认证，审计事件不冒充发送次数。

首次异常或未知、过期、占用/标记冲突即停，保留首错与后继NOT_RUN。禁止重试、延期、清标记、换目录、换profile、token注入、复制其他会话或批量kill。只等待本次自有执行session，固定产品负责自有资源释放；身份/根因未知如实记UNKNOWN，不额外探测补证明。

完成后只在作者工作区新增 docs/evidence/A20/authenticated-source/live-delivery/，固定脱敏报告、原始结果/审计/登录安全元数据/释放、raw清单及final commit并释放。不得提交凭据、完整URL query值、headers、cookies、profile、原Script或sidecar；Script仅.local。不得改冻结产品、旧原件或根协调文件。明确实际登录次数、认证/书籍/目录/框/源图/映射、首错和释放依据。由同正式独立静态核实际结果。其他三例HOLD、Q22不导航/样题/重放、0B消息。作者不自行开启任何后继。
