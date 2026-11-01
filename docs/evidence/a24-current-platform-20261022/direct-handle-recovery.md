# A24 直接 Browser 标签句柄恢复

日期：2026-10-22（Asia/Shanghai）

## 结果

浏览器读取连接已恢复。

使用本会话已确认的 Edge browser `3` 后：

1. `browser.tabs.get("1199071977")` 立即返回 agent-owned tabs 为空；
2. `browser.user.openTabs()` 在用户标签集合中精确返回目标标签；
3. 使用该新鲜返回对象执行 `browser.user.claimTab(...)` 成功；
4. 通过所得句柄直接读取 URL 和标题成功；
5. 已对该标签执行 `markHandoff()`，用于下一回合继续只读采集。

可信句柄结果：

- 标签 ID：`1199071977`
- Provider ID：`["88ee73e8-3aca-483a-a9a2-eeb292dae62e","1199071977"]`
- URL：`https://www.usense.com/qieti/home`
- 标题：`数据标注平台`
- 标签组：`📖 A24只读恢复`

这证明浏览器扩展连接和标签句柄正常；此前 `cua.getTab` 的超时集中在自动初始 AX 路径，且该标签原本属于用户标签集合，不属于 `browser.tabs` 的 agent-owned 集合。

## 证据边界

本轮只完成连接诊断，没有读取页面 DOM、账号或 book `46007447`，也没有调用业务接口：

- book/directory/fullframes/natural export GET：0
- 私有响应文件：0
- 网站标注编辑、保存、提交：0
- Cookie、token、凭据读取：0

最终状态：`DIRECT_TAB_HANDLE_RECOVERED`。下一步可复用该直接标签句柄，在禁止写入的边界内验证账号/目标书并执行固定四个有界 GET。
