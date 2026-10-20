# A17 固定候选的正式独立离线复核

2026-10-20。续派同一正式独立 `01a158fd-cbeb-7a31-a3e6-661c7d4c95d4`，host local，xhigh/model沿用，不重复创建聊天。原准备4成员+清单已核原bytes，所有24组只是待验标准，不是产品通过。作者 `01a158fd-281c-7282-a3b4-db876697686c` 已完成固定交付并释放。

## 固定输入与允许输出

- base `003f862065a2d630e666323c0d158e33bcee91e9` → 产品 `e7ee24245ffaf4d4b81cbddae8b3720aac214c1b` → final `1d2ba3766558fe9cc911756666d962184cc1de57`，均为唯一直接父链。
- 产品任务 workflow `811c3ac9e5913812bc71d74bc665eded96e23aa3`；候选 `docs/evidence/A17/excluded-static/candidate-manifest.json`，SHA `43870eac7194cb10d8542826a9a81e2a3c98dde1f191241bd4c1c43f007a787b`。
- 新隔离 `D:/1800-worktrees/a17-independent-fixed`：46交付成员+清单自身、18候选依赖去重共61 raw，包含包初始化。冻结输入清单 `D:/1800/docs/evidence/coordinator/a17-fixed-delivery/input-raw-manifest.json`，SHA `9e6704424c67e5c38802606832c4c1bab16f525504916b300a32573384210bc3`。
- 交付清单 SHA `dbc07911f7a753e78fd7768ecc53db413ddf0bcf63ad4605a01bec8ac39c6d26`；REPORT SHA `e33cc03fab7d3ac51d983d6708184ab152a34401e194c9ce51eb1c4672ce68dc`；release SHA `cd2691a45112807066adddf85601a35d6ef581730fae3932ab9ac4c47a866a32`。
- 调度核31,479旧成员中仅4个获准产品文件变化，新增50、删除0；30,259旧evidence成员mode/type/blob全保全。此为机械预检，不替代本次语义验收。
- 只新增隔离内 `docs/evidence/A17/independent-review/` 的报告、必要控制和运行记录，以及现有新A17 runner首次输出的 `docs/evidence/A17/excluded-static/runs/run03/`。旧run01/run02、raw-checkout内run01及所有61输入不可改写。不要在内嵌raw-checkout运行以免混用运行根。

当前只允许本阶段新34项离线suite及必要独立控制，复用你已固定的24组标准并按实际证据给结果。命令工作目录为新隔离根，`python -B tests/a17_excluded_static/run.py`；先静态核实无真实资源调用和路径边界，再运行。独立控制只用内存fake transport，不访问native、browser、network、profile、凭据、占用或真实平台；0产品子进程。默认launcher仅静态审查即可，不启动带live入口。旧A16 18/33/75、A12/A15等旧suite全部不运行。

## 集中验收

完整执行原 `A17-independent-excluded-static-review.md` 的七项边界，特别核以下实际行为，而非仅核分类字符串或作者自报：

1. 被排除的 `https cdn.bootcdn.net:443 GET Script` 仍真正abort/fail；精确匹配、主页面/主框身份、非redirect成立才可继续。未知/缺失框身份不能依赖另一层补判；Document/API/login/WS/其他来源方法资源等硬停止优先。
2. 两层全轮共享16事件，await前扣额；同请求双层按两次计，第17仍拒绝且fatal，纯policy/capture/get_once查询不扣额。结果不能把事件数当HTTP发送数，更不能扩大到DNS/TCP/TLS零活动。
3. native/context均真正发送前拒绝，不continue/fulfill/替换脚本/下载body；观察到排除脚本response必须停止且不读取body。拒绝错误、取消、不响应取消、关闭与结清时新回调和late fatal进入最终ERROR/UNKNOWN；首错保持，无重新abort同一请求造成无限等待，无越过原截止。
4. 原六业务GET、两原图、同源session/static范围与必要认证/身份/导航/数据条件保持。排除本身可继续不等于数据可用；每个必需条件失败都停止相关后继。sample0、自动schema能力停用，body/schema UNKNOWN、production_ready/write_eligible=false，原R02仍REWORK。
5. 新 task/run_id/workflow/scope、候选依赖、新决定/报告/activation/输出路径及一次性标记真实绑定；旧A16/A15决定、报告、activation不可借用。模板为不可执行，缺批准或期限仍拒绝。未创建新live目录/activation，不以准备模板充当批准。
6. 四获准产品文件及新增A17路径之外无改动；固定native参考、旧失败、旧suite、旧live标记和全部evidence原件保全。作者30项工作树通过与34项固定raw通过分别引用，不冒称本轮全面回归。

作者首次工作树run01因取消后的重复await而被其所属exec会话Ctrl-C中断，exit1；原runner内存日志与完整traceback未取得，只有固定interruption记录，必须保留这一证据限制，不重演或重建。之后同阶段允许的修正、30项工作树run02和34项固定raw run01保持各自根目录。作者test进程只有工具wait/exit记录，没有OS创建身份；不得扩展为原生身份退出证明。以上不因归档完整就抹去。

发现实质新缺口即固定REWORK和原始反例，不自行修产品或改后重跑；依赖该缺口正确性的后继NOT_RUN。无缺口时完成相关有限核证并释放，不为了增加数量补跑无关测试。

## 结论与交付

机器报告复用候选非执行独立模板所列绑定字段。若确实通过，`result=ACCEPTED_OFFLINE_ONLY`，`scope=CURRENT_BOOK_SOURCE_INVENTORY_EXCLUDED_STATIC_OBSERVATION_ONLY`，sample0、六GET、两图、排除事件上限16；同时注明这只是离线预检，没有实际认证/源目标/首题内容或框读回通过。输出名 `independent-result.json`，正式调度接收后才会按原bytes归档到候选绑定的根报告路径。若不通过使用实际REWORK/BLOCKED，不为门禁伪造接受。

给出 REPORT、机器结果、逐项实际控制/运行原件、全部成员size/SHA清单、61输入原bytes保全及精确释放。报告不要把“当前CDN被拒绝”宣称其非必要，也不假设这项修改足以打开平台。

当前0新TLS决定/activation/live；A16仅本轮的批准已经用完。后续由调度在完整具体方案就绪后落实本阶段必要决定，不能自行启动。0B/外部联系人消息、不推送、不写根JSON/任务、不读活动作者目录。所有Git先`GIT_NO_LAZY_FETCH=1`且每条`-c core.longpaths=true`，不reset/clean/stash/全量add。
