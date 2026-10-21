# A21 静态图片分类纠正与同会话认证书源读取准备

本阶段正式执行任务，仅离线开发，尚无新live或凭据提交许可。已完成A20实际失败与释放核证；A20唯一轮已耗尽，原决定/activation/output/标记不动。原真实路径用途和是否静态误拒仍UNKNOWN，不能把已证分类冲突写成平台实际根因。



- 只修一个明确的分类交集：原站 HTTPS、原页面主框关联已成立、无 redirect、无 query 的 GET Image，路径严格为 `/qieti/assets/<单一 basename>` 或 `/assets/<单一 basename>`，扩展名仅沿用原 STATIC 图片集合 `png|jpg|jpeg|gif|svg|ico|webp`。basename 必须符合明确的规范字面形态；不接受编码/反斜杠、点段、空段、重复分隔符或其他歧义路径。此窄图片类可先于 basename 关键词保护判定；不要把整条旧 STATIC 无条件前移。
- 原站、原主框及逐跳守卫仍须在两层实际执行路径成立；仅 policy 返回静态类不能代替框身份核验。API 路径、嵌套目录或受保护路由段、Document、XHR/Fetch、登录 POST、其他方法或来源均不得借此获得许可；既有登录提交意图/双层预算、session/version、CDN/排除上限、截止与自有释放规则保持。不得扩大到 `/static/`、任意带图片扩展名的 URL 或全部 Image。
- 仅做 policy 的纯静态分类窄修及必要的 A21 身份绑定。原认证、业务、两层守卫和释放流程保持；不另造通用诊断系统、浏览器驱动、图片探针或额外观测。
- 允许正常必要的新离线修正和少量相关 fake transport 测试：合法静态 basename 前缀、原先正常图片、API/嵌套路径、错误类型/方法/origin/frame、query/redirect/编码歧义的负例，以及双层拒绝和既有登录预算边界。保留新失败，不跑旧 suite、不刷历史 NOT_RUN；不读取真实配置/profile，不运行产品或原生占用探测。
- 交付固定产品/final、完整候选依赖 raw、变更清单、新差量结果与精确释放。A20 旧候选、失败、决定、activation、标记与 live 输出原件不动。不新增诊断字段，不记录 URL query 值、凭据或任意错误文本。

## 后续独立要求

- 等作者冻结释放和调度核 raw 后，使用独立隔离输入核窄图片类仅解决 basename 关键词冲突；重点检查其无法绕过真实 API、导航/登录、身份、方法、逐跳和既有预算限制。必要的新小量相关控制即可，不重跑历史 suite，也不为完整原件下无实质影响的报告细节反复返工。
- 核候选/范围/门禁模板绑定本阶段，旧 A20 决定或 activation 不能激活 A21；实际阻断路径和认证/书源仍 UNKNOWN，不以离线控制证明真实根因或平台成功。输出固定有限结论、报告清单及释放，交根调度核证。

## 未来唯一真实轮的边界

本草稿没有新 live 或凭据发送许可。完整可运行候选、正式独立及调度预检通过后，根调度固定准确本轮方案和直接决定：原专用 context 最多一次、900 秒含释放、登录页与原 viewer 两个固定主导航、官方 UI 登录最多一次；认证后同一 context 继续书 `46007447` 的六个固定 GET 与 viewer 14/173 两图各一次，不把书源再拆成诊断轮。version/session/共享排除仍按新候选明确列出原有有界预算；0 业务写入、上传、OCR、样题或书级提交。

用户 A17 持续只读 TLS 许可与 A20「仅本轮一次登录及读取」的已消费许可分别保留，不能拿 A20 决定激活新一轮。未来凭据发送仍须本阶段具体直接决定，使用原配置和原 profile，不索取新密码、不复制会话或替换 profile；异常停止固定、不重试。正式 ID 和上述绑定由根创建与派发，辅助不代建、不执行。

辅助准备记录：首次读取固定 Git policy 时遗漏路径中的 `source/usense`，Git 返回路径不存在；随后通过该固定树的路径清单定位后只读成功。这是辅助读取失败，未运行或重跑产品。`notes.md/json` 与 `notes-r1.md/json` 保留，本次仅新增此草稿。

## 执行绑定与交付

工作区 D:/1800-worktrees/a21-static-image，branch codex/a21-static-image，基线 f45fa86789b8f154d03e8c4807412a2161d678f6；根调度已创建干净短路径worktree，不重建。正式threadId及workflow见根docs/coordination-state.json和本阶段creation-intent。新scope固定 AUTHENTICATION_RECOVERY_STATIC_IMAGE_CLASSIFICATION；task/run_id/executor/workflow/candidate/report/decision/activation均绑定A21自身。门禁拒绝A20旧决定和activation。候选、scope与模板明确固定本次窄静态图片规则，不能只改身份字符串而遗漏政策绑定。

预留 D:/1800/.local/stages/a21-static-image-live 与 a21-static-image-activation.json，决定 D:/1800/docs/approvals/A21-static-image-user-decision.json，报告 D:/1800/docs/evidence/coordinator/a21-independent-closure/independent-result.json；当前不得创建。原专用profile指纹 b4620cd9fe064121a916062126321b7bba3862185d8919bf228f1399097a0d00、配置路径和原站/OSS不变。未来预算和精确会话/业务URL沿用已冻结A20具体界限，但必须以A21新候选和用户具体直接决定绑定，不能借用旧单轮批准。

产品修改白名单为 src/annotation/source/usense/current_readonly/policy.py、gate.py、tools/a16_current_state_probe.py、tools/a16_current_state_launcher.py；policy窄分类及必要原框检查，其余仅本阶段身份/范围绑定，不改原认证流程、业务解码、js_wire/native、截止或释放实现。如最小实现确需其他产品路径，先给具体差量理由让调度明确处置，不自行扩展。新增 tests/a21_static_image/ 与 docs/evidence/A21/static-image/。原auth.py和decode/js_wire/native保持raw。

允许正常必要新纯内存fake transport测试迭代，失败保留；可导入固定Python模块作纯离线fake测试，0产品/launcher/native实际子进程、browser/network/profile/真实配置或占用检查。旧A20 35项/5控制及所有旧suite不运行。复用原内核，不额外造诊断或恢复系统；有限差量集中核新分类/框身份/方法来源以及新scope门禁。不要为了报告细节重复已通过测试。

交付产品commit、final、候选所有依赖原Git bytes、作者有限测试结果、原错误、精确释放。raw-checkout测试只核该新候选相关差量；打包必须从固定Git raw导出，不把Windows普通checkout与raw作相等比较。完整清单固定所有依赖/原件，禁止缺父包。只提交白名单，不reset/clean/stash/全量add。根AGENTS及协调文件不改；Git先GIT_NO_LAZY_FETCH=1，每条-c core.longpaths=true。

根已核辅助原件 docs/evidence/coordinator/a20-static-image-analysis/，仅读取而不执行辅助脚本。独立等待固定交付由根隔离，不读活动作者目录。其他三例HOLD、Q22不导航/样题/重放、0B或外部联系人消息、无书级送审送交。目标仍2026-10-22日晚普通单选首题真实保存读回后最多5题，先完成必要适配，不拆无关诊断轮。
