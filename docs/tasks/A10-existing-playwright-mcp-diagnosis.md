# 现有 Playwright MCP 服务与会话排查（2026-10-20）

## 结论

现有 MCP 能立即返回 JSON-RPC 协议错误响应，但浏览器会话尚未成功建立；本轮唯一标签列表检查再次在 120 秒超时。未定位到具体卡住的内部步骤，不能断言只是用户未点击扩展确认，也不能据此说 Usense 不可达。

## 已核实事实

- 配置为 Node/npx 启动 `@playwright/mcp@0.0.83 --extension --browser msedge --profile-dir-name Default`，启动期限 30 秒、工具期限 120 秒。
- Edge Default 已安装 Playwright Extension 0.4.0（ID `mmlmfjhmonkocbjadbfplnigmagldckm`）；本地禁用原因列表为空。磁盘记录不等于当前会话已连接。
- 已安装 MCP 和扩展源码均使用协议 2，未发现静态协议版本不匹配。
- 对现有 server 的一次 `resources/list` 立即返回 `-32601 Method not found`。该服务器源码未注册此方法，此结果用于证明协议能返回响应，不是浏览器成功证明。
- 当前用户排查请求下登记的一次 `browser_tabs(action=list)` 返回 120009 ms 超时，未得到标签清单。没有连续重试。
- 初次调用、等待期间及后续完整进程快照均未观察到匹配 MCP 的本地监听/连接。中间两次仅覆盖初次 PID 集合；最后一次重新枚举当前进程。瞬时快照不能证明整个时间段的资源历史或精确释放。
- 已存在多个 MCP 实例，其中可能属于其他任务；没有把“多个实例”认定为故障，也没有终止任何实例或用户浏览器。

## 源码解释与未决点

首次工具调用会延迟创建浏览器后端，经过客户端 roots 获取、扩展检查、relay 创建和扩展连接，然后才分发标签工具。无自动连接 token 时，扩展允许等待用户 `Allow & select`；但这只是可能路径。本次未观察到 relay，无法把阻断准确归到该按钮。原 120 秒超时也不证明内部等待已被取消。

当前配置没有 Playwright token 环境键；未读取或输出 token 值，其他继承环境中的实际 token 状态未核实。不建议为绕过确认而读取或复制 token。

此前电脑操控工具的“无法识别浏览器 URL”停止属于另一套工具策略；本次没有绕过它。Work 本地浏览器开关已开启，不再要求用户重复开启。

## 下一步

优先针对本对话的 Playwright MCP 连接做一次单独重连，保留 Edge、Default 配置和登录态；之后在 Playwright 官方连接界面选择允许的 Usense 标签，再核验会话。重连尚未执行，须能准确识别本对话实例；不批量结束 Node/Edge、不清除 profile 锁或用户数据。仍不进入平台写入、送审或 Q22 重放。

## 证据与范围

- [本轮协议/标签检查结果](../evidence/coordinator/playwright-mcp-diagnosis-20261020/session-check-result.json)
- [独立静态源码核查](../evidence/coordinator/playwright-mcp-diagnosis-20261020/independent-static-source-report.json)
- [本地扩展记录](../evidence/coordinator/playwright-mcp-diagnosis-20261020/extension-config-state.json)
- [最新进程与连接快照](../evidence/coordinator/playwright-mcp-diagnosis-20261020/processes-late.json)
- [任务意图](../evidence/coordinator/playwright-mcp-diagnosis-20261020/intent.json)

独立子任务 `/root/playwright_mcp_static_path` 已完成释放，报告 raw SHA256 `fc21ec57d79108664d4922a7b41eb918b70074f908994e936f513aa7ab051f82`。主调度执行协议检查和单次会话检查，独立只做静态核查。0 显式平台导航/登录/业务写入/设置修改/进程终止/推送/B 消息；工具内部网络与资源释放仍 UNKNOWN，不能报告为零。旧 A10 诊断和旧业务额度均未恢复，其他三例保持 HOLD。
