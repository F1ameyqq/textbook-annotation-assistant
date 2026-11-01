# A24 单标签只读连接恢复记录

日期：2026-10-22（Asia/Shanghai）

## 结果

已在 Edge `3` / “用户配置 1”中仅创建一个新的独立恢复标签：

- 标签 ID：`1199071977`
- 请求地址：`https://www.usense.com/qieti/home`
- 状态清单实际地址：`https://www.usense.com/qieti/home`
- 标题：`数据标注平台`
- 会话名：`📖 A24只读恢复`

创建调用本身在 30 秒后超时并重置运行时，但随后的独立库存读取确认新标签已经存在并直接位于主页，没有重定向到登录页。因此可以确认同一 Profile 的登录状态被复用；不能据此确认页面 DOM、账号、目标书或业务接口已经可读。

随后只进行了一次 `getTab("1199071977", {browser:"3"})` 绑定尝试。该调用同样在 30 秒后超时并重置运行时，未返回页面状态。按本轮有界要求没有重试、没有创建第二个标签、没有回退 Windows 原生窗口。

## 影响与边界

- 旧主页 `1199071786`：未附着、未读取。
- book/directory/fullframes/natural export GET：0。
- DOM/账号/书号验证：未取得。
- 网站标注编辑、保存、提交：0。
- Cookie、token、凭据读取：0。
- Profile、扩展权限、锁或浏览器设置修改：0。

最终状态：`LOGIN_REUSED_BROWSER_BINDING_TIMEOUT`。

下一步不需要再创建新标签或重新登录；需要受支持的浏览器扩展成功返回对现有标签 `1199071977` 的 `getTab` 绑定。机器可读回执见 `outputs/A24-browser-single-tab-recovery-20261022.json`。
