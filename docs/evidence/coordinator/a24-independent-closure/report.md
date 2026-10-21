# A24 固定只读候选正式独立预检

结论：**ACCEPTED_OFFLINE_ONLY / BOUNDED_READONLY_PREFLIGHT**。接受固定 A24 只读候选；本次真实认证、当前书籍/来源、保存、刷新和独立重开均 NOT_RUN。根仍须将自己的具体只读 activation 与候选绑定，方可派发。

- 产品：`eb75fad5ca56daa117929dd1377d2157f2340388`
- final：`3d53a0b670c04cf84387cd77d69b0a9571741328`
- 基线：`454c6ff4a89580e6209b4c45fd6bc74a5e603d83`
- 产品 workflow：`c3026c05d1603038328ceca6918452d3ec4504b7`
- 本次复核派发 workflow：`aafc87ac26a67d01d1cf7d814f1fb7262f74a4dc`
- 候选 SHA256：`d10e30b4567ba5c4a81b8aa53396e35619e05f191e457a40c371866499161753`
- 正式执行：`01a15cf8-0c63-70d3-b374-ce85e6f29fd7`；正式独立：`01a15cf8-68e0-7b63-91a3-657a567b344c`

## 固定输入与范围

唯一产品输入为根提供的 `D:/1800-worktrees/a24-independent-fixed`，未读取作者活动工作区或输出。根 input manifest SHA256 `e13ed9bf40a0fb9a9146ca61eb4657f0d0d501ac728465db99ff6fd4446950cd` 与固定复核任务 SHA256 `94d94407e80796593fdd61107875e1ff3dfefd8486ba4c2fc893dfc7f04bd450` 均核对并在本目录固定。

独立逐项核完111份输入、37份候选依赖、98份交付成员的路径、size、SHA256、Git blob SHA1、mode/type。候选字节与派发摘要一致。测试后再次核111份原输入及输出边界，结果见 `input-preservation.json`。本目录之外没有写入。

根已经机械核证32,176旧成员仅 decode/gate/probe/launcher 四处获准变化，30,920旧 evidence保全。冻结包中 product/final preservation 和 unchanged-regions 记录原件保留。本次不重新枚举全库或运行历史 suite；未改变的 auth/policy/native、session等待、双层守卫及释放/时间框架以固定 raw 依赖和既有机械比较为依据，不据此声称全回归。

## 独立运行结果

| 运行 | 结果 | 外层计时 | 证据 |
| --- | --- | --- | --- |
| 本次新21项 suite | 21 PASS / 0 FAIL / 0 ERROR | 516ms | `suite-runs/run01/` |
| 四组独立相关控制 | 4 PASS / 0 FAIL / 0 ERROR | 344ms | `control-runs/run01/` |

已执行命令（cwd `D:/1800-worktrees/a24-independent-fixed`；均带 `GIT_NO_LAZY_FETCH=1`）：

```text
python -B docs/evidence/A24/independent-current-contract-review/new-suite-runner.py
python -B docs/evidence/A24/independent-current-contract-review/control-runner.py
```

使用新的 `new-suite-runner.py`，只改ROOT、输出位置、冻结测试模块路径及 failfast；原 runner、fixture、源码和原结果未改。socket、subprocess、私有路径、native、profile、occupancy禁用保持。独立 control runner沿用同一保护。两个命令均退出0，无旧 suite、作者 packaging helper、产品 launcher 或真实 transport执行。

四组控制核实：

1. canonical的非首行目标、JS空数组/对象真值和优先序、重复/坏行/别名/缺标题拒绝；六端点投影不含未知键或秘密值，匹配数精确而目标投影最多2条。
2. 六端点HTTP文件在 body读取前保存；事实在adapter异常前已留存，book步 FAILED，后继读取未发生。
3. click/fill/press全部设为失败陷阱仍完成六业务/两原图；自动已捕获book复用，主动book发送0；context/native replay新发送0，在途UNKNOWN新发送0。无被动canvas时 visible/save mapping保持UNKNOWN，write_eligible=false。
4. activation/decision/report全部66项各做删除与错类型/错值，共396次拒绝；三份固定模板的全部66项逐类型对齐。decision未准、activation日期为空、report仍NOT_REVIEWED的原件均未激活。

完整scope取自独立控制记录的实际 `gate.scope_binding(candidate)`，由最终机器结果平铺携带，未为生成报告再运行产品。

## 具体候选判断

canonical仅选 `data.records || data.books || data.list || []`，身份仅row.id精确目标46007447；不递归拼别名或选第一本。具体请求固定原page1/pageSize10/id，无username/role/team/status添加、替代路由或自动分页。源码不能证明当前账号权限；若最小请求无目标，正确停止并保留事实。

capture在body之前留有限HTTP，JSON之后、业务/字段适配之前留白名单code/shape/目标匹配与分支；不导出响应全文、账号上下文或任意键。主动GET先结清已有capture；自动/主动共用发送账。书身份通过即继续全部获准书源。主动picker及跳页均删除，响应资源映射与被动canvas分开；无canvas不伪称save-page转换已证。

66项绑定涵盖当前任务/run/executor/workflow/candidate/paths、1context/1navigation/900秒、六GET各1/两图各1/session总3/version≤1/共享排除16、sample0及所有写入/凭据/登录/上传/OCR为0；A23等旧材料不能替代。三模板一致，持续A17同类只读TLS许可只由根绑定具体新轮，不重复泛问，不恢复旧预算。

## 保留限制与原失败

- 新canonical/JSON失败码部分未加入顶层 `safe_error` 有限词表，顶层可能显示UNKNOWN；原HTTP/finite facts内canonical branch或INVALID_JSON以及正确停止/步状态保留。按本任务口径列非阻断报告限制，不改产品、不为报告再跑。
- 实际书籍响应、当前书名/权限/源目标、被动可见映射及save-page转换未在本次证明。库存仍PARTIAL，正文与完整旧正文保全UNKNOWN；离线fake不得升格为当前平台合同。
- first-save-readiness五个摘要是未改写入模块的checkout摘要；根另说明与raw LF→CRLF对应，不属于37候选依赖摘要不符。本次未运行或核准真实写入模块；后续接线使用固定raw SHA。
- 作者初始19项1FAIL、后续19/19及21/21、raw21/21分别保留。同名run01不代表同一结果。首次cached replay断言失败及全部helper/封存次序失败不抹除；中间736547f9不是final，git-add单独退出码UNKNOWN保持。
- 本次初始manifest定位在隔离路径不存在，随后按派发所指根manifest正确路径及摘要核证。属于输入定位错误，无产品动作；见intake-result。准备阶段旧PowerShell封存失败原件仍留原准备目录，未重写。

## 后续与释放

本次机器结果为 `ACCEPTED_OFFLINE_ONLY`，accepted_scope为 `BOUNDED_READONLY_PREFLIGHT`，无实际decision/activation/live输出/claim。根可据已获持续只读许可完成具体本候选绑定并派唯一有界真实读取；独立不自行激活。

同一A24对话后续接首题：当前未录入/目录/全局序号、文字与六框bbox、原图SHA/尺寸/页映射、当前wire/完整写集/receipt、裁片上传具体整数、完整旧正文保全机制及各phase整数请求账仍需固定。新题/policy/版本/许可与activation核证后才准写；作者save/get/refresh与正式独立不同session reopen分别实证。只读接受不提前准写，首题代码缺口不阻断本次安全只读候选。

本次两次离线测试及全部元数据命令已结束，未创建浏览器/context/runtime、真实profile/native/occupancy、书锁/journal、产品子进程或等待helper。产品launcher/真实网络/凭据/登录/业务写入/上传/OCR/推送/外部联系人消息均0。无自有遗留资源。其他三例HOLD，Q22不重放，旧失败与耗尽预算保持。正式独立已固定报告并释放。
