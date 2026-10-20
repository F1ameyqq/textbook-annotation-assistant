# A17 固定产品独立离线复核：REWORK

本次结论为 **REWORK**，仅发现最终结清阶段的主错误归因不符合“首错保持”。未接受产品、未集成，未批准 TLS、activation 或 live。34项本阶段新 fake suite 通过不覆盖该独立反例。

正式独立：`01a158fd-cbeb-7a31-a3e6-661c7d4c95d4`；作者：`01a158fd-281c-7282-a3b4-db876697686c`。固定基线 `003f862065a2d630e666323c0d158e33bcee91e9` → 产品 `e7ee24245ffaf4d4b81cbddae8b3720aac214c1b` → final `1d2ba3766558fe9cc911756666d962184cc1de57`，直接父链已用只读 Git 元数据核对。

产品绑定 workflow `811c3ac9e5913812bc71d74bc665eded96e23aa3`；本次独立派发 workflow `989600f4f8070bed7ae756bc0ecd3bcc5ba53e75`，两者区分。候选 SHA256 `43870eac7194cb10d8542826a9a81e2a3c98dde1f191241bd4c1c43f007a787b`。正式任务 SHA256 `c08b39ab8e739110432e75ebdf6c12f7183d63334dec21a7bfff994a32ab18e2`，输入清单 SHA256 `9e6704424c67e5c38802606832c4c1bab16f525504916b300a32573384210bc3`。

## R01：final drain 包装异常替换主结果的首个守卫错误

严重度 P2，定位 `tools/a16_current_state_probe.py:698–713`，重点为700–701及713。明确验收依据为固定任务集中验收第3项“关闭与结清时新回调和late fatal进入最终ERROR/UNKNOWN；首错保持”，以及原准备A02。

独立控制 `A17-I-A02-FIRST-FATAL-DURING-FINAL-DRAIN` 只替换 open/collect/close/save 为内存 fake，隔离产品自己的最终结清与序列化代码；不声称通过真实六读取或完整 collect。在合成 collect 返回后，排入一个来自可信原主框、未知 HTTPS 来源的 Script native 请求。该回调在 finalizer 的 `drain` 中首次执行：

1. 原产品 policy 判定 `ORIGIN_BLOCKED`，fake CDP 实际调用一次 `Fetch.failRequest`，没有 continue/fulfill。
2. `guard.failure` 首先固定为 `Stop / ORIGIN_BLOCKED`，守卫停止；这也是 shutdown 前和序列化时快照的首错。
3. `require_running` 向 drain 调用者抛出通用 `NETWORK_GUARD_STOPPED`。finally 的捕获分支在 `result.error` 为空时保存该包装错误，最后的 `result.error or guard.failure` 保留了包装错误。
4. 实际返回码2、outcome=ERROR；但主字段 `current-state.json.error.codes` 是 `NETWORK_GUARD_STOPPED`，不是首个 `ORIGIN_BLOCKED`。独立期望主结果与已固定的首个守卫错误一致，故失败。

边界说明：首个错误仍在嵌套 guard 快照和审计中，未全部丢失；本例正确硬停止且拒绝请求，没有证据显示网络被放行。缺口是主结果错误归因不一致，不能扩大为“首错全丢”“守卫未停止”或真实平台失败结论。更早已存在的业务错误也应继续保留，不应因修此项而被稍后的守卫错误覆盖。

复现命令（原始运行已完成一次；本次不再执行）：

```powershell
cd D:/1800-worktrees/a17-independent-fixed
python -B docs/evidence/A17/independent-review/controls.py
```

原始控制源码 `controls.py`；运行意图 `control-intent.json`；实际命令/exit1 `control-command.json`；原 stdout/stderr 为 `control-stdout.txt` / `control-stderr.txt`；完整反例 `control-result.json`。实际1项、0 PASS、1 FAIL、78ms，剩余合成任务/回调0。未修改产品，未改后重跑。

## 已完成的有限检查

静态先核 import 与调用边界：probe 仅装载冻结 native 定义，真实API构造/Playwright启动/profile与占用均位于显式函数内；新suite 使用内存请求/响应/页面/CDP和补丁，runner拒绝真实 Popen/native/profile/占用/urlopen/create_connection。未执行默认launcher或任何live入口。确认可运行新suite后，仅在隔离根首次新增run03：

```powershell
python -B tests/a17_excluded_static/run.py
```

实际34项，0失败/0错误、3766ms、shell exit0。原件位于 `docs/evidence/A17/excluded-static/runs/run03/{result.json,stdout.txt,stderr.txt}`，意图与命令结果在本目录 `suite-intent.json` / `suite-command.json`。这是原本阶段新suite的复现，不是独立新控制全部通过；旧suite0。

静态及该suite有限支持：精确CDN分类后两层abort/fail、原主框身份、共享16事件await前预留、第17拒绝并停止、排除response不读body、sample0和六GET/两图范围、新旧绑定拒绝、必要后继失败与部分异步控制。未据此宣称覆盖全部异步交错或全部准备标准。独立新语义控制首先复现R01后即停止；24组标准中I01/I02完成机械核证，A02为FAIL，其余21组后续独立控制NOT_RUN，具体状态见 `controls-status.json`。

机械核证 `preservation.json`：61输入初次及末次size/SHA256/Git blob ID通过，最终Git mode/type/blob通过；候选18依赖及包初始化/namespace声明通过。base/product完整树raw与本地不可变Git树逐bytes相等，父链通过；31,479旧成员中31,475原mode/type/blob不变，另4获准产品修改；新增50、删除0；30,259旧evidence全部保全。产品树内容在final中原样。只读Git metadata子进程4，不是产品子进程。此项在发现R01后仅做保全取证，未再运行产品控制。

所有产品读取只来自 `D:/1800-worktrees/a17-independent-fixed`；未进入活动作者目录或内嵌raw-checkout运行。输出仅本独立目录和指定新run03，61冻结输入、旧run01/run02和内嵌raw run01保全。根工作区未写入，根JSON/任务不改，不提交/推送。

## 保留的历史限制及释放

作者工作树首次run01被所属exec会话Ctrl-C中断、exit1；只有固定interruption记录，原内存日志和完整traceback未取得，不重演或重建。工作树run02的30项/3156ms、固定raw run01的34项/2422ms，以及本次隔离run03的34项/3766ms分别引用，不混用运行根。作者和本独立test进程仅有工具wait/exit记录，没有OS创建身份，不冒称原生身份退出证明。

本次真实native/browser/network/profile/凭据/占用扫描/登录/业务均0，产品子进程0，TLS决定/activation/live0；fake任务及回调已结清，无真实产品资源持有，见 `release.json`。根只读Git元数据读取与独立Python验证进程不计为产品子进程；未扫描或终止外部进程。

A16唯一live已耗1/余0，其失败及已证释放有限接受仍保持；旧批准不转移，原launcher OS创建身份UNKNOWN、辅助实际发送总数UNKNOWN。CDN路径/内容/用途/必要性UNKNOWN，事件数不等于HTTP发送数，DNS/TCP/TLS活动未证明。当前认证/书库存/目录/题框/源图实际获取、首题保存及刷新重开读回均未证明；sample0、body/schema UNKNOWN、自动schema能力停用，原R02仍REWORK，production_ready/write_eligible=false。其他三例HOLD、Q22不重放、0B或外部联系人消息，无书级送交。

本固定交付REWORK后释放。后续由调度决定同一A17的明确修订及新冻结；此报告不授权作者修后重跑，不恢复旧额度，也不批准新TLS或live。
