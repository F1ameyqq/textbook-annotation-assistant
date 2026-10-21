# A21 登录后 UI 转换：固定源码静态准备

**STATIC_PREPARATION_ONLY / 非正式验收 / 不创建候选。** 只读离线 final `cf03910d9554d6e3198c59494de2d4ce7bf7ad80` 的 auth.py、probe.py 和已获准 A17 Script 原件。未读 A21 活动作者目录、本轮 live 输出、profile、配置或 sidecar。根转述「POST1/HTTP200、UI未确认、TimeoutError/UNKNOWN」仅为待固定报告核实的上下文，不是本辅助独立观察。

## 固定探针究竟等什么

`tools/a16_current_state_probe.py` 795–856 行的登录流程为：登录页导航与表单确认 → 读取配置并填入 → 不可逆意图 → 一次官方按钮点击 → `confirmed()` → drain 与响应关联复核 → 才标记 `ui_transition=True` 并允许第二个 viewer 导航。

- 827–832 行先等 `flow.login_response` 非空；等待期间检查当前表单 `.error-message` 是否可见，命中则 LOGIN_UI_REJECTED。
- 833–836 行随后调用 `wait_for_function(timeout=10000)`，必须同时满足：origin 恰为 `https://www.usense.com`；pathname **仅为 `/qieti` 或 `/qieti/`**；search 和 hash 均空；DOM 中不存在 `.login-form input[type=password]`。
- 整个 `confirmed()` 外层 837 行由 `guarded_wait(...,25)` 包住，包含响应投影等待与 UI 条件等待。765–786 行按本进程 monotonic 检查截止及已有 guard 首错；10 秒 DOM 等待和 25 秒外层等待不可混为同一时限。
- 838–842 行只有上述条件成功、drain 完成、两层 POST 预留各为1且 native HTTP 为200，才把 UI 转换标为真、login_submit 标 DONE。`auth.py` 111–122 行也要求成功响应投影和 UI 标记，才允许第二次导航；随后 probe 985–1001 行才进入 viewer 导航、可见容器、固定 URL、当前 session 和书籍身份核验。

因此该 UI 条件不是“任意离开登录页”，也不是“等待 `/qieti/home` 或 viewer 可见”。UI 标记为 false 只证明此确认链未完成，不能直接表述为服务端拒绝了用户名/密码。

## 有限响应状态如何进入结果

| 原件位置 | 明确行为与证据限制 |
| --- | --- |
| probe 395–407 | 原主框、XHR/Fetch、已预留 networkId 的 native 响应记录路由/有限 HTTP状态/关联类型；LOGIN_POST 的状态写入 `login_http`，不读取或落盘响应敏感值 |
| probe 599–608 | context 响应须对应同一原 request、两层预留各1且未有投影；HTTP200后读取 body，仅交 `response_projection(login=True)`；成功后清除 flow.secret |
| auth 57–88 | body ≤128KiB、JSON对象；数值 code 仅0/200，解包data；非数值code按原body；登录还要求非空字符串 access_token。只返回 HTTP状态、ACCEPTED_NUMERIC_CODE/ACCEPTED_UNWRAPPED、凭据返回是否存在、有限profile字段存在性，不返回 token、用户名或自由message/detail |
| auth 174–186 | `actual_login_post_requests` 为：已记录 native HTTP且两层各1时记1；仅有预留时UNKNOWN；无预留时0。快照分别保存 `login_http_status`、有限 `login_response`、UI标记、protected_viewer标记、导航与session收据 |
| probe 1107–1127 | 关闭后结清回调，将 authentication快照、native HTTP安全投影、首错/guard状态和release写入固定结果；不保存完整登录响应或凭据 |
| probe 70–80、1077–1093 | 安全错误保留有限类型/枚举，未匹配网络枚举即UNKNOWN，不保存原自由message/stack。普通 `TimeoutError/UNKNOWN` 本身不指出哪个 UI 条件为假 |

`login_http=200` 与 `login_response` 非空是两条不同证据；前者不能替代后者。即使有限响应投影通过，也还没有完成 UI、受保护 viewer、当前 session 和书籍身份核验。`login_result_unknown_no_retry` 只按“已记意图且响应投影为空”计算，不覆盖所有 UI 未确认情况；不能只凭它为false就声称登录流程完成。

## 已捕获脚本的明确文本关系

Script SHA256 `d0a5ebce18bc92d7643662ecec2d078bb295214111e7cb32688f0b88e05bed41`，3,065,996 bytes，先核 hash 后只作文本读取。下列 offset 均为**原 bytes 的0基偏移**，不是字符位置。

| offset | 已有明确文本与关系 |
| ---: | --- |
| 1067312、1069878 | `Ui="/qieti/api/user_login"`；Pze 使用 `gn.post` 提交 `${Ui}/login`，键为 username/password |
| 1069105 | `Hn`：数值code仅0/200，否则抛错；成功返回data，非数值code返回原body。这是前端解包规则，不是本轮服务端结果 |
| 1095395、1095416、1095613 | LoginView 的成功分支依次 await Pze、将返回的会话对象写入localStorage `user`、调用 `l.push("/")`；这里只记录键名和控制关系，不读取真实存储值 |
| 3061973、3062050 | 路由表明确 `{path:"/",redirect:"/home"}`，`/home` 标记 requiresAuth |
| 3063770、1013247、1007193 | router 以 `AVe("/qieti")` 为history；AVe保存base并绑定createHref，vVe按base与route拼接href |
| 3063813 | beforeEach对 requiresAuth 的路由检查本地user对象存在及可解析，缺失/解析失败转login；这不是一次服务端认证请求，也不能证明受保护API成功 |
| 3062598 | 明确 `/annotateUnified` 路由，requiresAuth且blockAutoReload；这是后续目标的源码引用，不证明本轮曾进入 |

**可确认的静态差异：** 按该同一bundle的登录成功分支、根路由redirect和history base关系，预期客户端路由落点为 `/qieti/home`；这不在固定探针只允许 `/qieti`、`/qieti/` 的集合中。该推导不执行脚本。这里的redirect是客户端路由配置，不能当成实际HTTP 30x或新增Document请求。

**仍待实际固定原件：** 本轮加载的Script是否与该A17原件同hash；POST两层关联、native状态与有限响应投影是否均成立；登录后实际origin/path/query/hash及登录表单状态是否曾留证；TimeoutError来自哪个等待阶段、较早guard错误及后继状态；viewer与session/书源有无实际证据。本辅助未读取这些本轮输出，不能宣称本轮已经到达 `/qieti/home`、真实超时由此造成、或服务端登录成功/失败。若原件没有这些字段，就明确UNKNOWN，不补发请求、重登或重跑来补证。

## 原件身份与释放

- auth：`src/annotation/source/usense/current_readonly/auth.py`，10,006 bytes / 202行，SHA256 `90b8a25d2f6ee3966e469207c28635658b5077dfc9345e53010d6c1fb3855be9`。
- probe：`tools/a16_current_state_probe.py`，74,576 bytes / 1,317行，SHA256 `0973d5b7af7a939091a633903da3cb0380aa9657d18d9cbbc2181e14f1d0182e`。
- 仅新增本目录 notes.md/json；0产品import/run/test、网络/browser、profile/真实配置/凭据、native/占用操作。Script未执行、重取、复制入Git或读取sidecar。未新造候选、未改根协调文件，辅助已释放。下一正式范围须待根对实际固定证据核证后决定。
