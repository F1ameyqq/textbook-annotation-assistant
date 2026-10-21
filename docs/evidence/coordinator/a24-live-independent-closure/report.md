# A24 固定实际只读结果：正式独立静态验收

结论：**ACCEPTED_FIXED_PARTIAL_VIEWER_BOOK_EMPTY_FAILURE_AND_OWN_RELEASE_ONLY**。仅接受本轮有限 viewer 准入、固定书籍查询的空列表失败归档，以及已证自有资源释放。当前书籍身份、书源、首题、保存和读回仍未证明；不赋予新轮或写入权限。

actual final `a1250758d0fc14e8c7d5c827ece2c207a4d99aac`；原产品 `eb75fad5ca56daa117929dd1377d2157f2340388`、候选 `d10e30b4567ba5c4a81b8aa53396e35619e05f191e457a40c371866499161753` 保持。正式独立 `01a15cf8-68e0-7b63-91a3-657a567b344c`；本次复核 workflow `1cbc90e6d002f8cd353fda41a5bf56091292aa73`。

## 原件与独立核证

仅使用新隔离 `D:/1800-worktrees/a24-live-review`。根输入清单 SHA256 `5d4058dca8106214a14f1bfacf908133e69eaadb8fe6ee5e052f389041762bb5`、任务 SHA256 `d6e9fcc0d901a02daa3c49dcdcfdb8086092b6134fa76a10dab7d8da8b5443eb` 均匹配派发。

独立静态核完70份输入、37份候选依赖、31份交付成员及12份有限 raw 副本的大小/摘要/Git blob与清单约束；作者交付清单 SHA256 `1ceb1550050ccde34277e6bdb9c11ca7b809bf0a0de3441001526de455722e3d`匹配。没有打开副本清单里的私有source路径，没有读取活动作者目录、full Script、sidecar或完整业务响应。根机械核证的32,271旧成员保全、32新增/0修改/0删除作为固定输入边界引用，本次没有重复全库扫描。

`inspect_fixed.py`只用标准库读封存字节、解析JSON/AST并作交叉核对，无产品导入、suite、launcher、capture/archive执行或真实资源。原始控制记录为 `static-checks.json`，进程退出0；后续复核原输入不变并封存输出。

## 本轮已证事实

- 唯一窗口：2026-10-21北京时间14:19:45.162040—14:34:45.162040（UTC06:19:45.162040—06:34:45.162040），900秒不延长。记录launch1/retry0，argv/cwd、activation/decision/原独立报告摘要和immutable markers一致；各保留UTC及进程FILETIME落在窗口内。
- launcher记录14:22:44.996396启动、14:22:55.993707结束；capture记录14:22:56.491223结束。outer launcher退出2，持有product退出2、worker退出2、occupancy退出0。作者记录capture envelope退出0，仅是采集完成，不是产品成功。
- 原主导航关联 `ORIGINAL_MAIN_DOCUMENT_NETWORK_ID`，HTTP200、domcontentloaded及可见容器等待完成。原VIEWER permissions响应关联 `ORIGINAL_FRAME_RESERVED_NETWORK_ID`、HTTP200及有限业务码投影接受，viewer组合准入；主动profile意图0，账号字段NOT_OBSERVED，凭据配置读取/登录提交0。这不证明账号字段或书籍身份。
- 绑定的page=1/pageSize=10/id=46007447最小书籍GET留有HTTP200/code0事实。data为object，records/books/list均为长度0数组；canonical选records，item_count0、target_match_count0、target_fields空，分支 `BOOK_TARGET_ABSENT`。book步FAILED，首次失败在cleanup前后保持，book_identity_confirmed=false。
- directory/frames/source/page14/page173/两原图/两mapping/样题及正文均NOT_RUN，sources为空；body/schema UNKNOWN、sample0、automatic_schema_confirmation=false、production_ready/write_eligible=false。没有获得首题写入事实或方案。

空列表只证明这次绑定的精确查询没有目标匹配。total仅留integer类型，值未投影，保持UNKNOWN；不能称全库空、书籍不存在、错书、角色/权限/筛选原因，也不能反推旧A23缺失响应的结构或原因。没有替代查询、账号参数添加、角色猜测、分页、重发或重试的证据。

## 发送账与释放

16项network audit是双层观察事件，不是16个HTTP请求。book native发送预留1且有实际HTTP200；原permissions实际HTTP200关联已留。version native/context各预留1，HTTP成功UNKNOWN；预期CDN拒绝完成1、共享排除事件1/限16。其他辅助HTTP发送总量、DNS/TCP/TLS活动、被拒脚本必要性UNKNOWN。实际审计没有方法扩为写入；不根据预留推定HTTP成功。

| 持有资源 | PID | 创建FILETIME | 实际退出 | 关闭证据 |
| --- | --- | --- | --- | --- |
| product | 55316 | 134370373650052349 | 2 | 前后PID/创建身份一致、exit_observed、product handle关闭 |
| worker | 19348 | 134370373659278351 | 2 | 前后PID/创建身份一致、exit_observed、worker handle关闭 |
| occupancy | 25836 | 134370373669362123 | 0 | 前后PID/创建身份一致、exit_observed、handle关闭 |

两项自有Job均已分配、final active0且closed；context close/runtime stop为true，释放errors空，callback pending0，guard首错保持，没有记录超期。只接受以上有持有身份的有限自有释放，不扩为全机进程/profile清理。outer launcher PID54248/returncode2有采集观察，自身OS创建身份UNKNOWN。

## 保留限制与更正

outer stdout135原始字节已按摘要复核；product stdout只有90字节计数及摘要，原字节不可用。stderr为0的记录/摘要不冒充公开保留原件。保留各自单调钟、UTC及FILETIME记录；launcher duration11093ms与UTC间隔10997.311ms相差95.689ms，worker9625ms与UTC间隔9617.650ms相差7.350ms，原因及精确分解UNKNOWN，不据此补造统一时钟保证。

前次离线报告曾把新错误码可能显示UNKNOWN列为限制：当时静态检查只处理初始Assign，遗漏后续 `SAFE_STOP_CODES |= ...` 的AugAssign。固定源码实际已追加这些失败码，本次静态纳入追加词表，确认 `BOOK_TARGET_ABSENT`与raw顶层/guard记录一致。此处明确更正前次检查遗漏；旧报告与产品字节均不重写，不重跑产品。其他缺失、旧失败和消耗预算继续保留。

## 收口

本轮live used1/remaining0/retry0，原activation/output/claims保持关闭。此验收不派修正查询、不激活新轮或写入；根可在同A24工程中另固定明确修正候选与新scope/budget。当前书籍、目录、框、原图、正文、未录入首题、保存wire/receipt、裁片计数及完整旧正文保全仍需真实证据，不能借此失败归档准写。

本次suite/产品导入/launcher/browser/network/profile/credentials/native/occupancy均0；只写指定独立报告目录，没有产品改动、原输入改动、外部消息、推送或保留等待进程。其他三例HOLD，Q22不导航/样题/重放。静态独立验收已固定并释放。
