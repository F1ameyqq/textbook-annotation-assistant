# A20 Image 阻断补充：匹配边界与固定审计

STATIC_PREPARATION_ONLY。原 notes.md / notes.json 保持不变。本补充只核固定原件与正则机制，不作平台验收、产品修正或新运行授权。

实际作者 final `f45fa86789b8f154d03e8c4807412a2161d678f6` 的 `docs/evidence/A20/authenticated-source/live-delivery/network-audit.json` 已读取 Git raw；8,256 bytes，SHA256 `bbd0cd07e1e4ed0c6abcd661d45e432465e8f03800111ff8b8e632e1db2ae341`。零基事件 8 在 `2026-10-21T01:34:35.501292+00:00` 记录原站 HTTPS 的 GET / Image / FETCH_REQUEST_STAGE / API_BLOCKED；redirect=false、query 名称为空，path_template=null、known_route=UNKNOWN。路径 hash 为 `7f8d9b088e7dea613880ef32040bf2c15bda25cb7a672a7ae05a37137bac2eba`。这是固定审计事实，尚无路径明文及用途证明；11 条审计不等于 11 次 HTTP 请求。

固定 policy.py 的 PROTECTED（29 行）是：

```text
(^|/)(?:api|login|logout|signin|signout|sign[-_]in|sign[-_]out|user[-_]login|auth|oauth)(?:/|[._-]|$)
```

调用为 `PROTECTED.search(p.path)`（182 行），启用大小写不敏感。其含义需要准确区分：

- 它搜索整个 path，但词左侧必须是路径开头或 `/`；因此不是任意位置的子串匹配。
- 词右侧允许 `/`、点、下划线、连字符或路径结束；因此也不是只匹配完整目录段。
- **末尾文件名若在一个路径段开头使用 `login-`、`login_`、`login.` 等受保护词形式，同样会命中。** 其他匹配词依相同边界处理。文件名内部较后位置偶然含有 login，不满足左侧边界则不因此命中。
- 183 行立即返回 API_BLOCKED，位于 184–185 行静态 assets/static 后缀准入之前。因此，即使某个无 query 静态图片路径本来满足 STATIC，仍可能先被该文件名前缀规则拒绝。资源类型 Image 不会在这里覆盖保护分类。

以上是代码可直接确定的分类机制。**不能据此认定本次 actual hash 就属于静态文件名误拒**；真实 API、登录路由相关图片和其他命中来源尚未区分。

已有来源直接比对：原获准 Script 哈希仍为 `d0a5ebce18bc92d7643662ecec2d078bb295214111e7cb32688f0b88e05bed41` / 3,065,996 bytes。明确 AppHeader 图片路径 `/qieti/assets/logo-Dj3LIo9h.png`（路径 offset 2230359）的 UTF-8 路径 SHA256 是 `df4ef8fc1c7c80c5786a44a9b3a8d553bd21caaa31a9d593cd38575d3afbf754`，**与 actual 不匹配**。对该同一脚本已存在的完整根相对路径字符串作直接提取和哈希比较，共 333 处、201 个不同字面字符串，无 actual 命中；没有生成、拼接、字典猜测或枚举未知路径。此范围不包含运行时拼接值、外部 CSS 或 HTML，不能据此声称整个前端没有该路径。

固定 Git 的 src/tools/tests/docs 中按登录/背景/验证码图片名搜索只命中两份 A01 bootstrap 命令记录。核后发现是 NUL 分隔仓库路径清单被宽正则跨项连接，修正为字段内文件名边界后均 0；这些本地路径不作为浏览器 URL 或实际来源。首次宽匹配输出过大并被截断，只是本辅助搜索记录，不是产品/平台重跑。

最小后续方向：将“真实受保护路由”与“已明确属于原获准 assets/static 的图片文件名”分开处理，避免仅凭静态 basename 的 login 等前缀误判；具体窄修须以固定来源和相关离线控制为依据，不能直接允许所有 Image、所有含静态扩展名的 API 路径，或将整条 STATIC 判定无条件提到 API 保护前。对本次未知 path 仍明确 UNKNOWN；优先等待已有固定 HTML/CSS/其他获准原件中的明确引用，不新增请求或猜 hash 原文。若来源不足，安全审计可在未来具体方案中补充静态归属模板/匹配段位置，保持 query 值和凭据不落盘；本补充不激活该方案。

0 产品执行/import/测试、网络、真实 profile/凭据/配置/native/占用，未读 sidecar、未修改或重开 A20 旧轮。只新增本补充两个文件，辅助已释放。
