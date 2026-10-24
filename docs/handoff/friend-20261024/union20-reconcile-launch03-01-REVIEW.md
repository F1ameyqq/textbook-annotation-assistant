# A30 Union20 与 full16 reconcile-continue launch03 有限独立验收

结论：**ACCEPTED_OFFLINE_UNION20_ORDINARY_INTERRUPTED_RECONCILE_AND_LAUNCH03_CONTINUATION_SCOPE_ONLY**。Union19 已接受部分按原字节继承；本次接受普通对账恢复与固定续行范围，不代表Q12实际对账成功或新的平台执行已获激活。

已私有复制核对401个产品输入及10个launch输入。Union20 manifest `19a3497ef23fa8e128d88b286f65267c5291a674ffe6fa0c68b07e34c6ad817a`，report `dc29b73e3eb3f2aa3e4d3b6a41a60a605c34cb42aeea8d441105eced3d80adf5`。相对19，只改production.py/retained_readback.py，新增interrupted_save.py及其测试；其余245个既有源文件一致。普通GUI“未知保存只读对账”与CLI reconcile直接调用production.reconcile，客户无需工程JSON、审查聊天或developer manifest。作者固定12项新检查通过，首fixture路径错误和原stdout/执行结果对象键序解析失败原件均保留；未重跑这些检查或已接受的旧矩阵。

审查确认：仅一个匹配pending plan的完整原writer可恢复；原来源、计划、书籍、profile、原ledger路径、配置、发送意图、stdout、原receipt和释放记录须一致。INTENT先转为保留原INTENT前身的UNKNOWN记录，恢复receipt不等于接受保存。完整原读回可复用；已验证但不足的原读回前缀只能进入一次完整新只读核对。正文/库存/时间窗口/操作者仍由原严格比较器决定；失败后reconcile记录阻止再次读取，produce拒绝未决save，恢复路径没有writer调用。

独立新增3组正常默认分支合成检查通过（没有传transport_factory跳过原guard）：有效部分读回后只创建/读取1次、writer0，成功后再点击不重读，原INTENT链、旧接受operation及其他候选保全；已持久UNKNOWN的部分原响应损坏时，创建新transport前即HOLD、operation不变；新只读超时后为FAILED_NO_RETRY，第二次对账及produce均在取得资源前停止，原save保持UNKNOWN。只使用新合成材料和内存transport替身，网络/进程审计闸阻止真实调用。没有重放实际Q12、成功11题、old9、OCR或模型。

launch03 manifest `3bc46a59a3fcc23b2ff7d9041f41feee076afcd8560c58c0586dea3639514faf`，binding `35f87bd50b1e08f0241557ac8a65517697995b56c1e605955ea41152e2905688`，entry `17897293f299aa39eb8321e68c59feabbd92acbb02302f9ad4c7bfb13d4262a7`。以已接受actual02私有冻结副本核对10,748成员身份、85 operations、当前head、16候选内容及source key；11个接受引用一致，Q12绑定原一次receipt/node `1792848391723`，native info保持UNKNOWN待实际读回。没有扫描当前作者workspace/profile或执行launch preflight/main。

固定顺序：Q12一次完整只读对账 → 核对原node/receipt和UNKNOWN前身 → 普通produce复用11题及刚对账的Q12 → 仅Q13–16首次保存/新鲜独立读回 → 全16原生export1/display1。4题新增15框。独立预算推导与plan/template/binding一致：capture38一次对账，加production capture38/39/40/41/42，共1,858 GET；writer prewrite38/39/40/41共1,138 GET；export1，合计**2,997业务GET、最多4 POST、59平台上下文、1本地展示上下文、最多11个绑定题图裁剪下载**。原图重取/OCR/模型/登录/旧11与Q12重发/自动retry均0。窗口**1,800秒+60秒释放余量**。

authority模板inactive、ID/时间/输出目录null、root_receipts空，sole executor固定。独立隔离执行activated的前置guard，inactive模板与旧20b authority均在binding/资源前拒绝；没有运行完整激活或preflight，不声称存在通用spent registry。root仍须另绑定新的唯一authority及所需root receipts，20b spent1/remaining0保持不变。

非阻断说明残留：continuation-plan的window_rationale仍提12 inserts/3600s，runtime_before_save仍提12 plans/four reused。静态查核运行只按当前结构化selection/limits/expected_cost执行，上述文字不参与分支；原文字保持不改，本结论明确采用4首次保存/11原接受+Q12对账/1,800秒范围。报告中的原作者live预检仅作为固定记录接收，本审查结论来自冻结身份与静态/合成核验。

原actual02 exit126、outer release=false、PermissionError5 stage/cause UNKNOWN全部保留；较晚3个PID不存在的有限结果不回填原运行。本节实际状态仍11/16，Q12 UNKNOWN_NO_RETRY、Q13–16 NOT_RUN；全16导出展示及最终包未完成，CUSTOMER_READY=false，1800-a PAUSED。无新增实际平台/模型调用，无profile/settings/真实ledger改写，无旧测试重跑。一次只读rg查错文件路径的错误已保留，不影响产品判断。
