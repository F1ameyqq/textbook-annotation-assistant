# A20 登录页 Image 阻断：静态来源准备

状态：STATIC_PREPARATION_ONLY，不是正式验收或实际阻断路径定论。调度转述本轮首个失败为同源 Image GET / API_BLOCKED，作者正在封存；本辅助没有读取活动作者目录或 live 输出，因此实际 path/hash、请求发起者和用途仍为 UNKNOWN。

已先核原获准 Script：3,065,996 bytes，SHA256 `d0a5ebce18bc92d7643662ecec2d078bb295214111e7cb32688f0b88e05bed41`。以下 offset 均为原 UTF-8 bytes 的零基偏移；区间为左闭右开。

1. `LoginView` 的 `IFe=Object.assign(TFe,...)` 至 `EFe=Ur(IFe,...)` 位于 `[1095192,1097198)`。此组件含 `login-background` 空 div，完整节点起于 **1095872**、class 值起于 **1095888**；scoped id `data-v-3765519e` 的字符串起于 **1097177**。该区间未见直接 img 创建、`src:`、CSS `url(` 或 captcha 标记。组件本身没有给出背景图的 URL；class 名不足以证明图片存在或路径。不能由此排除外部 CSS、页面 HTML、其他组件或服务器当时行为，且本辅助没有读取这些来源。
2. 同脚本确有公开静态 logo：**`/qieti/assets/logo-Dj3LIo9h.png`**。变量 `Dut` 定义起于 **2230354**、路径字面量起于 **2230359**；所属组件名 `AppHeader` 在 **2230691**，`img` 使用 `src:Dut` 的节点起于 **2231537**。这是共享页头静态资源的明确引用；它不在上面的 LoginView 区间，不能据此认定登录页本轮加载或被拦截了它。该路径字面量不含 query。
3. 没有从所核 LoginView 源码取得明确的验证码请求路径，也没有取得登录背景图 API 路径。`captcha` 标记缺失不能证明实际页面不需要验证码；当前不得猜一个 endpoint、把图片归为非必要资源或据此扩展网络许可。

固定 A20 源码来自 Git final `b41e88d7756fde9d7f1b348ce5a300d1104e765b`，未读取活动 checkout：

- `src/annotation/source/usense/current_readonly/auth.py`，SHA256 `90b8a25d2f6ee3966e469207c28635658b5077dfc9345e53010d6c1fb3855be9`。`known_form` 在 189–198 行检查当前登录 URL、单一可见用户名/密码/按钮，并拒绝 iframe、注册额外字段、one-time-code、captcha class/id。它不是图片路径识别器，也不证明本轮表单检查已经执行。
- `src/annotation/source/usense/current_readonly/policy.py`，SHA256 `e12e50c32e6c1dd7c427d6e6b07492fe0ffffbd8edbf509ea1d93b3416231b94`。`decide` 在先处理已登记原图、精确业务和 session 后，182–183 行对 `PROTECTED` 匹配返回 `API_BLOCKED`，早于 184–185 行普通静态路径准入。该保护匹配包括 api/login/auth 等路径片段，不能单凭错误名判定某个 API endpoint 或用途。对本次转述的同源 Image GET，资源类型本身不会使该受保护路径变成预期排除。

下一步只在作者固定交付、调度 raw 核证后，用实际被拒路径的安全模板/hash 与已有明确字面路径核对。若只有 hash，则只能比较已有明文来源，不猜测枚举未知路径；若现有 JS 不含实际路径，继续明确来源缺口，不把 AppHeader logo 或 captcha 当成已证答案。本辅助不提出新许可、探针或重试。

辅助释放：只写本目录 notes.md / notes.json；原 Script 仅在内存中离线搜索，没有执行、重新请求、复制原件或 sidecar 到 Git。未读取 live 输出、真实配置、profile 或凭据；未运行产品/测试/native/占用，未联网或提交，无等待进程。
