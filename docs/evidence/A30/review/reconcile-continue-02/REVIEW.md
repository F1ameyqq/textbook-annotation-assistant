# A30 产品09与恢复启动02独立审查

结论：**ACCEPTED_OFFLINE_RETAINED_RECONCILE_AND_CONTINUATION_SCOPE_ONLY**。

指定独立审查：`01a16bf6-f61d-7f40-a4cc-2f1201f2ece3`。本次对冻结09产品及启动02的有限增量予以离线接受，未发现阻断该固定恢复路径的问题。允许协调者据此准备新的、独立的一次性实际授权；本报告本身不激活执行，不改变真实账本。客户UI06/figure融合是另一条修改线，`CUSTOMER_READY=false`。

## 固定对象及原件

| 对象 | SHA-256 |
| --- | --- |
| 产品09 manifest | `c8c0f087c44c94400656ae243b2a9587098e3ee4f19b759a0091d3c64fa04196` |
| 继承08 manifest | `6d7dffc83177af0eb8fd84a5229c1d00efa20bd86ecf93a43b8f4dc2bdc85489` |
| 恢复启动02 manifest | `ec07cf74f5af6abc9d8288db81df8775dde665dafbf57da643562a87a53002dd` |
| 启动02 entry | `1582a1b10f3991769c987ec225b9aa09b9377c8a0a76bf26fd6b2504b58839a1` |
| 启动02 binding | `3d0dbd4e7f706b32dfb80749902620ce96b60a6010fc144fda83dbd7976353be` |
| continuation-plan | `0774a8f283a58d8d5e607968b78126a653d6a5a824e4a467647f6d86b484d614` |
| 原实际01 manifest | `2ac2bba8cc321210d5f98698a1decf4aca5c0d9ed036f49d40e6913d7749ebeb` |
| 原实际01 summary | `f5bf4223badd2373a94ad53560f58b4550c08328648b182331c3cb38ed3aa142` |

冻结产品路径：`D:/1800-private/a30-integrated-flow-r1-fixed-20261024-09`。冻结启动路径：`D:/1800-private/a30-reconcile-continue-launch-fixed-20261024-02`。独立材料：`D:/1800-private/a30-reconcile-continue-independent-20261024-02`。原实际原件使用此前独立隔离的 `D:/1800-private/a30-first-batch-actual-independent-20261024-01/input`。

首次隔离236件，包括产品09的216个源文件、3个证据、manifest/report，启动02的6件及父08的9件。另核验根侧09的222个副本和启动02的6个副本；09根侧多计的一件为manifest摘要旁文件，并不表示产品源码数量不同。原实际1097成员逐个复验。没有读取活动作者树或真实workspace/profile/外部ledger。

09相对已接受07仅改变`native_plan.py`、`existing_fill.py`、`production.py`并新增`retained_readback.py`，212个原源成员相同。相对08仅改变`production.py`并新增`retained_readback.py`，214个原成员相同。08原7项及09作者3项仅作为冻结证据读取，未重跑；原内容审校、07固定范围、旧成功保存、OCR和已耗尽实际均未重放。

## 接受的有限行为

1. 新题回执节点与目录节点允许对象键排列不同，双方键集合、每个值及解析类型必须一致。旧目录、旧题完整正文、旧题框及未知字段仍沿原严格比较路径核对；当前原件的新节点四个字段及类型已由实际01独立确认。
2. 时间政策明确变更为原有有时区、最长120秒发送窗口两端各固定5秒，不按当前观察值动态拟合。插入的新info/frames、因插入顺移而允许的旧记录`updated_at`，以及existing-fill原本允许的`updated_at`变化使用此边界。后两类仍必须单调前进，其余字段仍严格保全。因此本结论不是“旧记录所有时间一律不能变”的额外声明。
3. 原UNKNOWN哈希绑定进程链；进程记录绑定配置和stdout；stdout内摘要绑定响应原字节。恢复器要求7个独立run_id、原writer释放后顺序执行、观测时间落在各进程内、原authority引用及book相同、完整库存/题目/页面端点集合、重复响应一致、source/page身份相同。缺件、变更或时序不合均HOLD，不回退另起GET。完全没有后续采集的通用分支仍保留旧的显式新读取路径，但本次启动02在进入正常对账前强制完整原读回，无法使用该分支。
4. 正常`reconcile`保留原保存UNKNOWN对象和事件，追加对账记录；`Store.resolve`的成功对象保留`previous_state`和`previous_output`，不删除或改写原失败。之后正常`produce`按相同内容来源key复用Q1。真实路径未注入`transport_factory`、新候选或替代业务实现。

原UNKNOWN输出：`ddc6a635da6bbd20405b0faf5a5d1033d97ab2b4c3b0b43219b6ea7c2e8c9380`。原计划引用：`17f68491db1072a7fcf3cf97bfe0519a74abdd3ae9ca1be3c851ca1e8e3eb988`。原当前head：`a750a587e668388546d2f39477d6f6d66cff9722822cda5f80754d592d5eeb0c`。

Q1仍绑定book `46007447`、node `1792827055018`、info `2113895998990761986`。原完整读回摘要为`d4d9c8b7f7aba498799849282608e7d68e5eb0ef4906c2b9d022e9ae9d0e892c`；09正常对账比较通过27旧题、90旧框保全。原实际01有限事实接受和189对旧响应原字节相同的结论继续有效。

原±1秒失败、随后仅修键序仍失败的历史保持原状。新记录时间晚于原writer结束2.917605秒这一观察不变；**偏差原因UNKNOWN**。本次接受固定±5秒政策下的09比较，不把原07失败改写为成功，也不证明时钟故障原因。

## 新独立检查及边界

新7项全部PASS，命令真实退出码0，见`independent-checks.json`与`checks-command.json`。

- 正常`reconcile`使用冻结原字节的精确虚拟路径映射，以及内存SQLite中的真实`Store.begin/finish/resolve/save_job`方法：7个原fresh上下文通过，真实transport构造0，新GET0，原UNKNOWN可追溯，28个其他操作和20条既有事件保留。
- 随后正常`produce`在首次capture返回前的刻意内存检查点，选中仍为1/5/10/11，Q1为`REUSED_ACCEPTED`，pending恰为5/10/11。此检查使用观察用transport_factory，因此不证明真实legacy guard、后续capture/write/export/display；这些后继标为`NOT_RUN_INTENTIONAL_SYNTHETIC_CHECKPOINT`。
- 将后续读回的开始时间移到writer释放前：HOLD。
- 保持原摘要不变而改变响应原字节：HOLD。
- 新合成时间验证窗口两端精确±5秒，包括微秒精度。
- 发送区间120秒加1微秒：拒绝。
- 无时区发送窗口：拒绝。

未运行完整启动入口或`--preflight`。未创建真实Store、浏览器、子业务进程或网络传输；测试的SQLite仅为内存，来源是独立冻结副本以`mode=ro&immutable=1`打开。真实workspace、profile、ledger、authority均未修改。全部实际保存、导出和显示检查仍NOT_RUN。

辅助统计脚本首轮错误地把整组旧题传给限6题的端点枚举器，得到`ORDERS_ONE_BATCH_MAX_SIX`，退出1；原脚本、stdout、stderr、命令记录均保留。仅修正审查辅助脚本，按writer实际分批端点并集计算，`static_closure02.py`退出0。该修复没有改产品、冻结输入或原失败记录。

## 启动02静态边界

已核对：启动前同时绑定09源码/manifest、原UI清单、原实际manifest/summary、1089个原workspace成员、原head与UNKNOWN操作、四项候选内容/来源/框、既有Q5原body、Python身份和原profile身份。完整原读回hash及库存28在本地核验；完整性失败在进入对账前停止。

启动后先且仅调用一次正常`reconcile`；验证原UNKNOWN引用、新node/info及零新增GET证明后，调用一次正常`produce`。Q1只复用，后继最多3个保存POST：Q5填既有node/info及原question/answer rect_id，不增删题框；Q10和Q11动态插入，最多新增5个题框。相同四项选择和Q5原body引用与已接受原批次逐字段相同，旧9题不进入本轮保存范围。已有07的选择、操作类型、node/info/rect、完整预检及逐题发送前范围保护继续保留。

后续生产库存序列28/28/29/30，writer预写库存28/28/29；按冻结端点实现推算1529个业务GET响应、32个平台上下文、1个本地显示上下文。此数字是固定正常路径的估算及绑定值，不是另一个运行时总量计数器。Q1对账新增GET0；后续3题的当前库存读取属于新的生产范围。

外层launch-intent和child-entered均独占创建；异常保留结果并停止后继。原单次holder、退出/Job/handle释放、正常原生export及本地display的一次性记录机制沿用未变实现。真实release仍须实际结果独立复验。新授权仅在内存替换引用和到期时间，原settings及已耗尽授权文件不被改写。

非阻断的历史描述字段已识别：continuation-plan里的`product_manifest`路径仍标04，但执行消费的是binding内09路径及双方相同09哈希；原`expected_capture_question_counts`、`expected_writer_prewrite_counts`、`if_four_writes`、`new_native_frame_count`仍是首批历史总量。实际入口消费的当前head、`expected_initial_native_count=28`、选择范围和`expected_api_budget`已更新并被绑定。不得把这些未消费的历史描述字段当作本次新增发送许可。

## 交付限制

本次只接受冻结产品09及启动02的离线路径和固定范围。真实Q1本地状态依然UNKNOWN，未执行解除；Q5/10/11新保存、独立新读回、export/display仍NOT_RUN。原authority `9288a8d9-6321-4239-8ae6-4e31bed17f97` spent1/remaining0，不得复用。启动模板activated=false，必须由协调者绑定新独立授权、窗口及root收据；本审查未执行任何授权动作。

客户UI/figure新修改、最终客户包、全课/全章/全书完成均不在此结论内。`CUSTOMER_READY=false`，`1800-a`保持PAUSED。
