# A24 current-context-r1 正式独立预检

结论：**ACCEPTED_OFFLINE_ONLY / BOUNDED_READONLY_PREFLIGHT**。仅接受此冻结只读修订的有限预检；实际平台认证、账号上下文/权限、当前书籍/来源、首题保存及读回均未在本次证明。无实质阻断项。

产品 `dde5746600df9854c33c5814a8f41ad85b7b4e16`；final `6740d7533ea7b5bf5f322d768e8688826afe5d43`；基线 `a1250758d0fc14e8c7d5c827ece2c207a4d99aac`；候选 SHA256 `c68ce354be516552e1aadafe253cd3f9c12785b3107d2454e59f10446ef31b77`。

产品 workflow `2574b9be93886494ce0b7b91798e65f83ce00341`；source supplement workflow `cd591394db393b8f27d9f45d1e1890725d95d800`、SHA256 `34a2f98a22d8e62e192ef0dfdb58601a3b76edfea7f213256bf62eb10f00c4b1`；本次复核派发 workflow `b93bdf8abc478567694bc17a6e8d37399a19b2bd`。同一正式执行 `01a15cf8-0c63-70d3-b374-ce85e6f29fd7` / 独立 `01a15cf8-68e0-7b63-91a3-657a567b344c`。

## 原件与运行

唯一产品输入为 `D:/1800-worktrees/a24-current-context-r1-review`，未读作者活动目录或并行首题代码。根 input manifest SHA256 `4ad6a9003ed23442b3f449b8d5216d6011a3df94fefcb5ce980d63e1e20675a1`及复核任务 SHA256 `08587130a3cb0aac84c62269cf963bf39e52d3f235fd890c45a16c4fe70e2a0e`均匹配。独立逐项核120 raw、42候选依赖、108交付成员的大小/SHA256/Git blob/mode/type；交付清单 SHA256 `fa17d70cf3d56e3232b548a57d806d6bdecdf1b1af46abbcfe76fc7f1f998610`匹配。测试后再次核全部120输入与唯一输出边界。

| 本次独立运行 | 结果 | 外层计时 | 原输出 |
| --- | --- | --- | --- |
| 新 Python fake suite | 28/28，0FAIL/ERROR | 781ms | `python-runs/run01/` |
| 新 Node VM fake storage/fetch | 15/15，Node exit0 | 141ms | `js-runs/run01.json`及原始Node stdout/stderr |
| 独立完整绑定控制 | 1组PASS，618次拒绝 | 313ms | `binding-runs/run01/` |
| 独立 PUBLIC_JSON VM | 3/3，Node exit0 | 171ms | `public-vm-result.json`及原stdout/stderr |

在隔离cwd执行：

```text
python -B docs/evidence/A24/independent-current-context-r1-review/new-python-runner.py
python -B docs/evidence/A24/independent-current-context-r1-review/new-js-runner.py
python -B docs/evidence/A24/independent-current-context-r1-review/binding-runner.py
python -B docs/evidence/A24/independent-current-context-r1-review/run_public_vm.py
```

全部调用带GIT_NO_LAZY_FETCH=1。新runner只重定向ROOT/输出/冻结模块路径，Python增加failfast，Node附加保存原stdout/stderr；测试逻辑、VM及全部原offline guards保持。未运行旧21项/更早suite、作者package/seal/raw verifier或产品launcher。两个Node子进程只是局部fake VM，无浏览器、真实storage/fetch、profile或runtime账号。运行均已退出0；无测试失败需要重跑或隐藏。

## 已核关键行为

**当前官方上下文查询。** 固定9键及顺序为page/pageSize/status_list/id/title/team_name/username/role/is_admin。状态列表按role.trim派生，is_admin仍只按原始role==='admin'；空title/team_name及Axios标量编码保持。仅在原已准viewer/frame内从页面既有storage作瞬时派生，发送前同一parsed user重读并核精确URL。缺失/畸形/变化/不支持上下文发送0；没有用户名/角色猜测、额外发现GET、旧最小查询、bookId路由或fallback。账户URL仅瞬时内存；token留页内，安全诊断仅有限状态/键名，不落盘值或账户指纹。

**单一请求账。** 一次bind、一项read intent及两层guard/get_once/cache共同使用BOOK逻辑槽；失败bind也占用，不能rebind/更换角色或查询领取新额度。正确已有响应只本地复用，无缓存重复停止。source只绑定一次互斥LEGACY_DB或OSS计划，每viewer恰一页槽；OSS替换legacy页请求，不追加额度、不回退或重绑。总量是四固定API加两选择页的六逻辑JSON槽，另加两原图，不能把OSS页算成额外六同源API。

**身份、schema与派生。** frames只在本端点接纳数值0/200的data数组或data.annotations、或无code但明确top annotations；布尔/字符串码及畸形容器拒绝，通用book/directory code0未放宽。source缺file_id标NOT_RETURNED并独立记录请求绑定，显式错ID停止。有效缺省source才标FRONTEND_DEFAULT_DERIVED legacy，未知/错误不伪造默认。OSS模板只按first %d→first {pageIndex}替换，viewer14/173资源13/172明确FRONTEND_DERIVED；actual HTTP/响应hash/有限结构独立留存，不冒充server返回身份或save-page。

**来源与凭据。** 页/图限定既有main/OSS HTTPS origin及/upload_images/46007447/，拒绝query/token/userinfo/fragment/traversal/歧义模板。独立执行确切PUBLIC_JSON于Node VM：200/403/fetch异常三分支均一次fake GET、storage读取0、credentials omit、redirect error、无Authorization，异常私值不回显。main-origin页保留既有main auth策略。显式空blocks与缺失/畸形/403/404分开；404停止，无legacy fallback/第二页发送。原图仍要求完整像素解码，不能以元数据代替。

**目录及资格。** raw节点id/type/label/order/flag/tree次序与frontend DFS派生顺序分开；question子孙仅在raw tree保留，派生DFS跳过。无效/重复raw order与不一致保持unknown/disagreement，raw关联及派生候选分开，不成为合法save order。库存PARTIAL、content UNKNOWN、append target null、write_preservation=false，visible/save-page仍需另证。缺完整旧正文与新题事实时write_eligible=false。

**完整权限绑定。** 独立控制从实际gate取得103项scope，activation/decision/report各项分别删除和错类型/错值共618次均拒绝；三份固定模板全部103项逐类型一致。当前task/run/executor/workflow/supplement/candidate/paths、9键隐私、单BOOK及互斥页槽均绑定，旧activation/已耗额度不能替代。原1context/1navigation/900秒、session3/每路径1/统一20秒、version1/排除16、sample/凭据/登录/refresh/写/上传/OCR均0保持。机器结果平铺同一103项，不为报告字段另运行产品。

## 限制、保全与释放

来源链与有限fake只证明声明层；不证明当前服务端schema、角色/权限、书籍内容或旧空查询原因。控制字符/孤代理/超长/URL标准化变化等明确停止的支持范围保留，不自动近似或猜替代查询。OSS frontend-derived资源页不是save-page；frames/全框/计数不是完整旧正文保全。真实未知与正确停止不补成PASS。

根机械核证32,303旧成员仅五处获准变化、其余32,298及31,042旧evidence保全。冻结unchanged-regions保留15段关键probe、auth/js_wire/native/OS/时间及一般decoder比较依据；本次引用其固定字节与根机械核证，不声称全历史回归，也不重跑旧反例。原BOOK_TARGET_ABSENT实际轮used1/remaining0、旧失败及原件保持；本次修订原有开发15/25/27/28及raw结果分别保留，未覆盖。

只接受此冻结只读修订，不覆盖作者并行未来首题wire。当前新题文字/bbox/目录/未录入、当前wire/receipt/crop整数和完整旧正文机制仍未证；同A24后续须固定完整policy/payload/写集/各phase整数预算、独立及根核证并单独准写。UNKNOWN不重发。

本次真实browser/network/profile/config/runtime账号/native/occupancy/产品launcher/登录/写/上传/OCR/activation/live均0；只在指定输出目录增加材料。离线测试及两个local fake Node进程均结束，无保留进程/会话/句柄/等待helper。根可在核证后沿A17持续同类只读TLS许可绑定本修订独立checkpoint，不重复TLS问题，不恢复旧轮或由独立自激活。其他三例HOLD，Q22不导航/样题/重放，0B/外部联系人消息及推送。正式独立已固定并释放。
