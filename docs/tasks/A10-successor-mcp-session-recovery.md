# 接任调度与现有 MCP 会话恢复（2026-10-20）

接任对话 `01a15768-1e2d-7781-b29f-1f7376270216` 已用环境身份及应用 `list_threads` 双重核对并登记。实际接任基线 `8f0e3eb7ef9378c9144190192c6aaeb7528b03bd`，分支 `codex/local-login-config`；交接前基线20ed7aa0保持为历史运行依据。既有未提交源码、样例和未跟踪目录未被本任务改写或清理。

## 当前结论

现有 Playwright MCP 服务到 Edge 的扩展会话已恢复。用户在官方连接页选择新建的 Usense 登录标签后，本对话一次 `browser_tabs(list)` **17 ms** 返回当前 `https://www.usense.com/qieti/login`。这只证明协议、扩展握手及标签操作可用；尚未证明认证、书46007447读取、专用无头会话或真实保存。

原 A04/A10 运行设计是账号隔离的专用无头 profile，见[本地登录说明](../local-login.md)。当前既有 MCP 配置显式使用 `--extension --browser msedge --profile-dir-name Default`，连接日常可见 Edge。两条路径及登录态不能混用。后续仍按专用无头设计核实已有登录态和当前源/目标，不能把日常 Default 登录页当旧无头会话已恢复。

## 已执行的有界动作与失败保全

1. 读取交接两文件、AGENTS、调度/开发计划和完整JSON解析，按最新分项状态核对 A10/A11；实际 Git 保留旧改动。未恢复任何旧任务的成功/失败额度。
2. 更新既有 `1800-a`，目标改为本对话；工具回执和 `automation.toml` 独立读回确认为唯一匹配项目的 ACTIVE、30分钟 heartbeat。没有新建重复自动化；无变化时静默。
3. 新绑定一次 `resources/list` 立即返回服务端 -32601。基于新对话绑定及新进程证据，登记后执行一次标签检查：**120020 ms 超时**。这是第三项累计超时记录，前两项原证据保留。未同状态重发。
4. 用户报告官方连接页出现，但没有Usense；一次人工F5仍缺。只读源码确认候选来自 `chrome.tabs.query({})`，排除内部协议和已被其他本扩展连接占用的标签；列表仅初次加载，不订阅新标签事件。不能仅凭缺项断定是哪一种原因。
5. 当前受支持 `cua.getState` 已能提供确切 Edge/标签 URL；它与此前无法识别URL的原生截图通道不同。本次没有使用原生窗口、截图、底层CDP或命令绕过旧限制。原连接页的 relay端口53652与新CLI36660监听对应。浏览器清单确认该配置没有Usense标签。
6. 在已识别的现有Edge配置中新建一个Usense标签，限定一次导航、零登录和零业务写入。导航工具先报10秒超时；随后对同一实际标签的只读核对显示平台登录页及表单。记录为 `TOOL_TIMEOUT_THEN_ACTUAL_LOGIN_PAGE_OBSERVED`，没有重试导航。
7. 绑定原用户连接页时发生两次本地句柄错误，均在刷新/选页前：先把用户标签误用为session标签，随后引用了未成功声明的变量。错误保留，按返回文档改为 `user.openTabs/user.claimTab` 并建立有效句柄，没有重启或新建连接页。
8. 对该原连接页的一次工具reload被浏览器URL策略拒绝：不允许 `chrome-extension://`。立即停止自动操作，没有换表面、CDP或间接执行。用户自行在原官方页刷新并点击Usense的 **Allow & select** 后报告成功；随后一次有新握手证据门控的MCP标签验证立即通过。

没有读取、复制或重新生成扩展token；没有提交登录、改证书策略、结束进程、清profile锁、重跑旧native/代理driver、改原业务源码、推送或向B发消息。原120秒超时不证明后台已取消；当前已知状态以成功后的实际标签清单为准。

## 下一依赖与剩余路线

先静态核对专用无头 profile复用入口和现有工具能力；必须有可说明的实际差量及新有界任务后才能做新的当前只读观测，不循环旧导航或恢复旧额度。当前Default保持未登录；专用profile认证状态尚未重新观测。

取得当前认证书籍事实后，固定具体新普通单选、来源/目标、Q/W/W/W/W/A、内容/坐标、真实执行政策及写入次数，再补A11必要真实适配。首题真实保存及内容和题框刷新/重开独立读回通过后，才扩到总量最多5题并独立验收。暂截止2026-10-22日晚不重新起算；其他三例HOLD，Q22不重放，书级送审/送交仍人工负责。

## 证据入口

- [接任/初次会话意图](../evidence/coordinator/takeover-20261020/intent.json)
- [自动化转移回执](../evidence/coordinator/takeover-20261020/automation-transfer-receipt.json)
- [新超时记录](../evidence/coordinator/takeover-20261020/session-check-result.json)
- [当前浏览器只读意图](../evidence/coordinator/takeover-20261020/current-browser-readonly-intent.json)
- [扩展接入意图](../evidence/coordinator/takeover-20261020/extension-attach-intent.json)
- [本地绑定错误与纠正边界](../evidence/coordinator/takeover-20261020/tab-binding-correction.json)
- [人工握手及URL策略边界](../evidence/coordinator/takeover-20261020/manual-handshake-receipt.json)
- [MCP成功后的实际标签结果](../evidence/coordinator/takeover-20261020/post-handshake-result.json)
- [调用前快照](../evidence/coordinator/takeover-20261020/processes-before.json)、[等待期间快照](../evidence/coordinator/takeover-20261020/processes-during.json)

独立辅助 `/root/mcp_wait_path_audit` 只核查源码、日志格式及进程元数据，没有调用浏览器、启动/重连/结束服务或修改文件。它的源码解释和主调度/用户实际观察分开记录，不构成真实平台验收。
