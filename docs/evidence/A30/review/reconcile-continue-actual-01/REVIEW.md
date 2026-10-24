# A30 续跑实际01独立验收

结论：**ACCEPTED_FIXED_RECONCILED_Q1_THREE_SAVES_NATIVE_DELIVERY_AUTOMATED_DISPLAY_AND_OWN_RELEASE_ONLY**。

指定独立审查`01a16bf6-f61d-7f40-a4cc-2f1201f2ece3`接受固定证据所证明的4项结果：Q1以原fresh读回完成本地对账、零新增GET/重发；5/10/11各一次实际保存及各7个fresh读回上下文；4项完整内容唯一映射至平台原生导出；离线交付文件及原自动显示检查通过；本轮自有资源释放已证。结论只限此批，仍有12个候选未完成，`CUSTOMER_READY=false`。

## 固定输入与执行边界

固定目录：`D:/1800-private/a30-reconcile-continue-actual-fixed-20261024-01`。

独立隔离：`D:/1800-private/a30-reconcile-continue-actual-independent-20261024-01/input`。

| 对象 | SHA-256 |
| --- | --- |
| actual manifest | `fca29262751ee69f085c33374f01f7bc1be9fbb246ad90db85d5d75f68789c16` |
| actual summary | `59dfed00dd35b7c3f5906a2a1b380467bb1ecdbbc63deabdef495d9ad25c223e` |
| 本次authority | `8cc5959645525b894cc352f1e7833f7ff4035fb4a79b5e7aaf1c55feec8d0677` |
| 09 product manifest | `c8c0f087c44c94400656ae243b2a9587098e3ee4f19b759a0091d3c64fa04196` |
| 已接受launch02 entry | `1582a1b10f3991769c987ec225b9aa09b9377c8a0a76bf26fd6b2504b58839a1` |
| 已接受launch02 binding | `3d0dbd4e7f706b32dfb80749902620ce96b60a6010fc144fda83dbd7976353be` |

3645 raw＋2 metadata共3647件独立复制并核验，约25.1 MB。代码/启动既有离线接受未重跑。本次只解析冻结JSON/HTML、校验原字节及使用`mode=ro&immutable=1`读取独立副本SQLite；未导入或执行产品发送、采集、对账、导出或显示入口。无新网络、浏览器、模型、OCR或真实workspace/profile/ledger访问。

新authority `fdb797b5-26fd-430e-b957-8189361042cd`的原intent/outcome均spent1/remaining0，无自动重试；原始活动窗口及启动/完成时点相符。旧authority `9288a8d9-6321-4239-8ae6-4e31bed17f97`不被恢复。三个root前置收据哈希、entry/binding及固定限制相符。

## Q1对账与历史保全

Q1原UNKNOWN对象`ddc6a635da6bbd20405b0faf5a5d1033d97ab2b4c3b0b43219b6ea7c2e8c9380`原字节保留。新acceptance `4165c12edb3d249d86f0b0984c75122f18df4fba548180b9e259bf5fc010ff6e`保留`previous_state=UNKNOWN_NO_RETRY`及`previous_output`；其writer、plan和7个原post-writer进程与原UNKNOWN绑定的对象相同。原读回hash仍为`d4d9c8b7f7aba498799849282608e7d68e5eb0ef4906c2b9d022e9ae9d0e892c`。

本次本地对账先于第一个新采集进程完成，所有被复用的Q1进程均早于本次业务开始。新账本只追加一次reconcile并将原Q1操作转为COMPLETE；生产状态为REUSED_ACCEPTED。本次Q1新增GET0、保存0。原键序失败、原±1秒窗口失败及旧failure事件保持原状；09固定±5秒政策下的接受不改写原失败，时间偏差原因仍UNKNOWN。

相对原实际01的1089个workspace成员，只有`state.sqlite`改变；1088个其他文件原字节相同。29条原operation中除Q1显式对账外的28条原行完全相同；旧20条events为新events的原前缀。新operation仅6条：reconcile1、save3、native-export1、display-check1，均COMPLETE。新events恰为一次对账、三组SAVE_INTENT/READBACK_ACCEPTED、PRODUCTION_COMPLETE、NATIVE_EXPORT_COMPLETE、NATIVE_DISPLAY_RESULT。

另一个旧job未变；16个候选的内容、来源和框未变，未选择的12个候选整个对象未变。原settings、OCR记录及旧成功材料保留，无新OCR行或原图重取操作。未检查真实外部profile/legacy-ledger的全目录字节，因此不作该范围之外的全局保全声明。

## 三次保存及fresh读回

| 印刷题号 | 原生序号 | node_id | info_id | 本轮操作 |
| --- | --- | --- | --- | --- |
| 1 | 28 | `1792827055018` | `2113895998990761986` | 原证据对账并复用，0保存 |
| 5 | 27 | `1792148510557` | `2111049977118109698` | 既有题补question/answer，1保存 |
| 10 | 29 | `1792829827657` | `2113907628113838081` | 插入2框，1保存 |
| 11 | 30 | `1792829910856` | `2113907977151234049` | 插入3框，1保存 |

三个writer的原plan、嵌入product计划、预写完整响应、send-intent、HTTP业务回执、actor哈希、post_layers及进程/配置/输出绑定相符。每次post_attempts=1，审计中同一POST分别在context/native各记录一次；无额外POST。writer中的`save_success=false`和`independent_readback=PENDING_FULL_CURRENT_BOOK`是该发送阶段的原记录，保持不动；后续独立新进程读回及CustomerSaveReadback给出完成证据，不能把writer阶段原字段改成成功。

每个writer的外层进程释放后才开始7个新采集上下文；run_id独立、时间顺序有效、配置及stdout/响应哈希完整。当前库存采集7个＋三次保存后各7个＝28个读取上下文。逐个响应核验范围、HTTP状态、请求层计数、观测时点、重复响应稳定、book/source/page身份及完整快照。

Q5保持既有node/info、93旧框和全部目录；只填绑定的question/answer分区，原question rect `3c8ce7f1-13ea-4969-a1ce-45fb72473a1d`、answer rect `56100140-765c-43c9-9d89-3f0a58beb05b`不变。分区新增字段采用既有有限键序，原info.updated_at若改变则单调且在固定±5秒边界。其余27旧题保持。

Q10/Q11分别在全局末尾插入，新增info/rect身份唯一、字段集合及来源payload相符，actor哈希与时间边界相符，未计划分区为空。原28/29题与93/95框完整保全。三次操作合计588对未改旧题响应原字节完全相同；新框总数5，零删除。内容hash及原source_frames均与此前已接受的四项范围相符。

观察到并保留的业务GET响应为capture909＋writer预写619＋export1＝1529。该数字是已留存响应记录，不推断未留存尝试，也不包含导航或静态请求。本次3save、1export、1display符合固定范围；无重放旧9题成功。

## 原生交付及显示

平台原生export为一次HTTP200，context/native各1，原字节19232字节、30条记录，SHA-256 `ad51794260a2bb076fbdb39552d51abd54933224a4fa1c7f918ad0f4cc0fec59`。四项按question/choice/answer/analysis完整内容及题型字段唯一匹配，映射原生行28/27/29/30；不靠序号单独推断，未复用同一导出行。

交付目录：`D:/1800-private/a30-continuation-live-20261024-01/workspace/native-deliveries/55f20a7e27147150bc608f72d8dd9cc63f39d635bf437d28e623c22b9be3d07d/a77e547df13a1ec956c99cd03e0b7e71cead920dd010ba2d561b3bc017a32045`。

已核验该目录7文件（index、原生jsonl、mapping、formulas、receipt、固定MathJax及license）；这里接受离线目录交付，不声称本轮生成了ZIP。HTML四题完整正文/选项/答案与读回相同，固定本地MathJax哈希相符，无远程脚本或内容图片。2个公式均属于印刷Q10；formulas中的`printed_question=3`是交付中的第3项，具体TeX为`15,20,a`与`a=`，不会解释成印刷第3题。

自动显示原证据由worker-result、browser stdout/stderr、browser.process、display-check及账本结果共同绑定：4个article无横向溢出；2个公式各1个可见SVG，merror0，尺寸正且位于对应article；images0；控制台、页面、请求阻断及释放错误均空。显示使用本地文件，profile_used=false，save_calls/export_calls均0；context/browser/runtime及外层进程释放均确认。

**本轮没有显示截图，独立浏览器重开NOT_RUN，人工视觉验收NOT_RUN。** 此结论接受的是固定HTML内容与原自动DOM显示证据，不冒充人工看图结论。交付receipt内较早的`visual_acceptance=NOT_RUN`原字段保持；后来的独立display记录和job的`MAPPED_PACKAGED_AND_AUTOMATED_DISPLAY_PASSED`分别记录自动检查结果。

## 释放、指标及审查错误保留

本轮共33个嵌套进程记录（32个平台上下文＋1个显示worker）和1个外层holder。所有34个launcher exit_code=0，owned_os_release_confirmed=true、Job active=0、持有的process/thread/job handles关闭，无release errors。联合去重546个观察到的持有进程身份均已退出并关闭handle：522个exit0，24个exit3221226029。**不能声称所有子进程退出码都为0，也不推断这些退出码的原因。** 接受范围限已观察持有身份和当前自有资源。

本次业务段记录耗时**358.6086705秒**，北京时间约2026-10-24 16:13:46至16:19:45。此前4次文本保存＋4次确认是agent UI审校，job review_actions=8保持不变；客户全程人工介入次数NOT_RECORDED，全程客户耗时NOT_MEASURED，不写0。

独立辅助脚本两次初始断言失败均保留原脚本、stdout/stderr和退出码1：第一处把同名capture-summary中的1份export误算为普通capture，改为按状态区分28＋1；第二处要求worker.finished_at与外层finished_at相等，改为核验其他字段一致及worker→holder→外层→业务结束时间单调。仅修审查辅助脚本，未改任何业务原件或产品；对应02脚本和业务raw比较最终均退出0。无额外产品测试或实际重试。

本批4/4已接受；任务观察候选16项，剩余12项未接受。该结果不代表完整课时、章节、整书或最终客户独立产品完成。UI支持候选、公式worker和最终客户包的集成仍属于另行冻结核验范围。`CUSTOMER_READY=false`，唯一`1800-a`保持PAUSED。
