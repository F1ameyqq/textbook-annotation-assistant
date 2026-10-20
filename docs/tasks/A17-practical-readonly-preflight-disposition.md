# A17 修订版有限预检：以真实只读验证为下一步

2026-10-20。用户最新明确要求“不要太保守”。调度据此调整自己的工程验收顺序：本次只读观测的准入重点是不会误写、越界、失控或伪造成功。只影响顶层错误名称、而具体原因和拒绝/停止原始证据仍完整的报告问题，列为已知限制，不再单独阻断真实只读路线。此处不是 TLS 决定，也不恢复任何旧平台轮次。

原正式执行 `01a158fd-281c-7282-a3b4-db876697686c` 已冻结释放；续派同一正式独立 `01a158fd-cbeb-7a31-a3e6-661c7d4c95d4`，host local，xhigh/model 沿用。不再新建聊天或重复检查原34/30项 suite。

## 固定交付

- base `1d2ba3766558fe9cc911756666d962184cc1de57` → 产品 `1168a75eb35f319c3ced270b6c515adbdb38603f` → final `8bffd88dacc146fc3f061ed0863b299fa5dabd30`，直接父链已核。
- 产品绑定 workflow `d137a1bba49550f661b110ee14c9541a1dc4fb19`，本派发 workflow 另见调度消息，不能混用。
- 候选 `docs/evidence/A17/revisions/first-cause-r1/candidate-manifest.json`，SHA `4ed38cb1f703c3d0b5e94d601f2f267c05ead871b9a26004e2e44e5d6eeb31dd`。
- 交付清单 SHA `27adc7048d817c2fee523636bd89cc2b45705cb5e77399733a03656b5f962e98`；作者报告 SHA `aeeb2eaf0d6aece01c18482e30dd78537dfc267cb16b0920f897bb03bd10622d`；release SHA `d7ee5aa6ec884ef780788b53e6e58bb7b090cb0539d439ba2ddd85c49e1b0443`。
- 新隔离 `D:/1800-worktrees/a17-first-cause-r1-review`，18依赖与42交付成员+清单去重56 raw。根输入清单 `D:/1800/docs/evidence/coordinator/a17-r1-fixed-delivery/input-raw-manifest.json`，SHA `2b503c83d7c5f050ac52e2b85a5f77719f3f5e5e5280c225a6435347d01ecd53`。
- 实际45新增、2修改、0删除；31,529旧成员中31,527原mode/type/blob保持，两个变化文件仅 probe 和 gate；30,306旧evidence全部保全。作者新差量11/11、1328ms，待独立核，不当作独立通过。
- 原独立REWORK、34/34和1FAIL/78ms、21组NOT_RUN均保持原状态，见 `D:/1800/docs/evidence/coordinator/a17-independent-rework/`。本任务不追认旧包通过、不关闭历史缺口。

## 有限独立预检

先核56输入原bytes与依赖闭包，再检查与原独立已运行34项的固定产品之间的实际差异。policy、守卫拒绝/身份/16事件预算、回调结清期限、collect读取边界和释放机制若原bytes或相应源码节点不变，可以明确引用原有限证据并结合静态检查；不要求为了把旧21组NOT_RUN逐项刷成动态PASS而再构造整套测试。旧未运行状态保留，新报告逐项区分本次动态、静态、历史引用和未覆盖。

实际新差量可在新隔离根运行一次：

```powershell
python -B tests/a17_excluded_static/first_cause_r1/run.py
```

仅允许新增 `docs/evidence/A17/revisions/first-cause-r1/runs/run01/`（新隔离根当前无此目录，作者的run01在内嵌raw-checkout中，两者必须区分）。不得在内嵌raw-checkout中运行，不修改56输入或作者输出。独立报告及必要小型控制只新增 `docs/evidence/A17/independent-r1-review/`。

集中确认以下准入事实：

1. 排除CDN Script仍在HTTP发送前拒绝；精确方法/类型/原主框/非重定向、双层16事件预算、未知API/方法/来源/登录/WS硬停止未被本次修订放宽。样题、登录提交、业务写入仍0；六GET/两图、单context/单导航/900秒范围不变。
2. 拒绝异常、晚到fatal、未结清回调仍使最终ERROR/UNKNOWN，不能误报真实事实成功；关闭和截止有界。新首因选择不能改变这些执行结果。
3. 新候选、workflow、run_id、scope和报告/决定/activation/输出绑定正确；旧决定和activation拒绝，模板默认关闭。没有批准时不能运行。
4. 作者新11项有可复现原件；根据实际差异仅补充必要独立小控制。具体关注已存在的顶层业务错误与当前except新产生的fallback区别，但只影响错误名称、而嵌套具体首因完整且最终正确拒绝/停止时，明确登记残留报告缺口即可，不能将其冒称完全修复，也不再因此重开一轮产品修订。

真正改变拒绝/写入/身份/停止/期限行为、丢失关键原始事实或误报成功的缺口仍需REWORK；报告美化、非必要字段排序或更精细首因显示不构成本次只读准入阻断。若11项中出现报告层差异，先按上述边界分类并保留原件，不机械把所有后继停止；不要为了满足原控制数量进行无关回归。旧34/30项、旧反例入口、旧A16及其他suite均不运行。

## 报告与后续

若上述有限范围可接受，使用候选模板的真实绑定，`result=ACCEPTED_OFFLINE_ONLY`、`scope=CURRENT_BOOK_SOURCE_INVENTORY_EXCLUDED_STATIC_OBSERVATION_ONLY`、sample0、六GET、两图、16事件，并明确 `acceptance_basis=BOUNDED_READONLY_PREFLIGHT`、历史21组未执行与本次证据来源、残留finding状态和限制。机器输出 `independent-result.json`，调度接收后才按原bytes放到候选指定根报告路径。

交付报告、机器结果、实际运行/小控制原件、成员size/SHA清单、56输入保全和释放。不需要扩大归档形式或补采无法证明的OS身份。作者旧中断缺完整buffered traceback及所有测试进程无OS创建身份限制继续保留。

本次0真实资源、profile、凭据、native、占用、浏览器、网络、登录或业务；不运行默认launcher，不创建TLS决定/activation/live目录。正式预检与调度核证后，立即把这一次具体只读方案交用户决定所需的context TLS例外，再开展真实当前书源库存验证。A16仅本轮的批准已用，不能借用。

其他三例HOLD、Q22不重放、0B/外部联系人消息、不推送、无书级送交。所有Git先 `GIT_NO_LAZY_FETCH=1`，每条 `-c core.longpaths=true`。不读作者活动目录、不改产品或根调度文件，不reset/clean/stash/全量add。
