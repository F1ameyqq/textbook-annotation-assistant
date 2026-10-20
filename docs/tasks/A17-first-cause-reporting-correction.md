# A17 同阶段纠正：最终报告保留具体首错

2026-10-20。原正式独立已固定 REWORK 并释放；调度核19输出成员+清单及61输入原 bytes，见 [固定报告](../evidence/coordinator/a17-independent-rework/review-output/REPORT.md)。这是 A17 内的必要离线修订，依据用户持续推进和本阶段正常迭代授权安排，不新增阶段或聊天、不恢复任何旧测试或平台额度。

## 固定事实

- 作者 `01a158fd-281c-7282-a3b4-db876697686c`、独立 `01a158fd-cbeb-7a31-a3e6-661c7d4c95d4`，host local，xhigh/model 沿用。原作者工作区 `D:/1800-worktrees/a17-static-exclusion`、分支 `codex/a17-static-exclusion`；从已释放 final `1d2ba3766558fe9cc911756666d962184cc1de57` 继续。
- 原产品 `e7ee24245ffaf4d4b81cbddae8b3720aac214c1b`，候选 SHA `43870eac7194cb10d8542826a9a81e2a3c98dde1f191241bd4c1c43f007a787b`。原34项作者及独立 suite 均通过，但独立新增反例1 FAIL/78ms，后续21组 NOT_RUN，原包不接受。
- 正式报告 SHA `356fbc2f2dcf5e80f86c53dbe1080e00d8c50bd57bd10d03f253c0508921347d`，机器结果 SHA `4d8c2ddd115fe1b206451c288a861777e1deb93c96fa6f262d5f25a42599799e`，原清单 SHA `d95b92c92caadd59cc60dc2eb4512e7ac306dffc07be7c18709b27637920973f`，释放 SHA `25a23885807f6046f1de007e975a0e5a7da331f13d8b547335a0d87a8548038e`。
- A17-R01：final drain 阶段首次出现的守卫 `ORIGIN_BLOCKED` 已拒绝请求且最终 ERROR，但顶层 `error` 被包装为 `NETWORK_GUARD_STOPPED`。具体首错在两个嵌套快照仍在。问题限于顶层错误归因，不扩称请求放行或首错全部丢失。

## 最小修正与新差量

仅修 `tools/a16_current_state_probe.py` 中 `observe_live()` 收尾阶段的错误选择。顶层为空或仅为通用 `NETWORK_GUARD_STOPPED` 包装、且已有具体守卫首因时，提升具体首因。更早已记录的具体业务/导航错误保持；不得用后到关闭错误覆盖。主 catch、finally drain catch、关闭后结清和最终序列化规则保持一致即可，不增加通用错误框架。

网络分类、来源方法白名单、16事件预算、原主框身份、等待/释放期限及业务门禁不变。若发现上述窄面无法正确实施，说明具体原因再由调度处置，不扩大范围。允许为新候选的 workflow/清单/默认拒绝模板作必要绑定，沿用原白名单；不改变公共合同、根依赖、冻结 native 参考或旧证据。

新相关测试仅 `tests/a17_excluded_static/first_cause_r1/`，新增证据、失败、候选及原 bytes 包仅 `docs/evidence/A17/revisions/first-cause-r1/`。原测试文件可只读复用 fake helper；新入口不能自动运行旧34/30项。必要覆盖：

1. 以明确队列/事件同步将非法请求回调首次执行点固定在 finally drain；验证顶层、嵌套快照首因一致，最终 ERROR/exit2，fake 实际拒绝且无 continue/fulfill。
2. 更早具体业务失败优先；后到守卫失败保留于嵌套字段，不覆盖顶层业务原因。
3. 主执行及关闭后结清阶段首次守卫错误保持；第二错误不覆盖；没有具体首因时不伪造具体原因。
4. 无错误对照不被修正误标失败，依然 sample0、正文/schema UNKNOWN、write_eligible=false。

只做本次相关内存 fake transport 差量，不靠任意 sleep 制造竞争。正常必要离线迭代允许且保留失败，不人为设置开发候选次数上限；不运行旧 A17/A16/其他 suite，不重演原中断或改写旧报告。原 run01 缺完整 buffered traceback、test 进程无 OS 创建身份等限制保留，不用新结果补造旧证据。

## 固定交付与独立续验

先记录本次修订意图和测试输出位置。新候选必须绑定本任务落盘后的实际 workflow commit；task/scope/run_id、未用的 A17 live 和预留路径保持，旧决定/activation 继续拒绝。所有计划/决定/报告模板保持不可执行、未批准。不能把当前根派发 commit 当产品基线合并进来。

交付产品 commit、final commit、完整依赖清单（含包初始化与实际复用 helper）、新差量命令及原件、候选/报告/清单 SHA、旧成员 mode/type/blob 保全和精确释放。最终 raw 包必须可在新隔离目录运行本次新差量，不依赖作者活动目录。原 final、原候选及独立反例原 bytes 不变；作者不能自行宣布接受。

调度机械核证后给同一正式独立新的 raw 隔离。独立核本次纠正和仍未完成的相关边界，保留原21组 NOT_RUN 的历史事实；这不授权重复运行旧34项 suite 或重跑旧反例原入口。新控制可针对修正后的 finally 场景核验具体首因。独立发现新缺口时保留实际失败，再明确同阶段处置。

当前0 browser/network/profile/凭据/native真实API/占用/登录/业务，0新TLS决定/activation/live。六业务GET和两原图各一次、1context/1导航/900秒、sample0、16事件范围保持；这里只是离线计划。A16一次批准已用，不转移。独立及调度接受后才定稿新的具体只读方案并落实适用决定。其他三例HOLD、Q22不重放、0B或外部联系人消息、不推送或书级送交。

所有 Git 先设 `GIT_NO_LAZY_FETCH=1`，每条 `-c core.longpaths=true`；不 reset/clean/stash/全量 add，不改根调度 JSON、任务及其他人的文件。
