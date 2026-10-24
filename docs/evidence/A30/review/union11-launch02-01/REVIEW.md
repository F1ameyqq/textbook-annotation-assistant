# A30 合成11与首次17区域启动02有限独立验收

结论：**ACCEPTED_OFFLINE_UNION11_17_CLEAR_ROI_AND_LAUNCH02_ONLY**。

接受冻结11的修正与必要缓存/worker/停止边界，以及启动02的静态绑定，范围只限**17个明确数学区域、每ROI最多一次首次本地调用、首错停止、结果全部待审、平台0/付费0**。根协调可据此绑定首次有限实际执行；审查没有自行激活authority、修改实际settings或运行启动入口。20个人工区域、全课内容就绪和最终包不作为这17项局部实测的前置门槛。

## 精确输入

| 对象 | SHA-256 |
| --- | --- |
| union11 manifest | `75c42aad2bcf40f8b789fc851ab35d85d90d97f239970ba464f1f056265dcf91` |
| union11 report | `47c8481dfee60f9bbeac349a7a45b3a28a2e1f233c5eff6818d18dfd8af47acc` |
| 当前17＋20计划 | `259c938c5aa644d0daf17bb311b1016fe305d6ecf7f21fd12ca61e6c6a029c91` |
| launch02 manifest | `a914e5e8cfac702a05a1e42c0cf24c1b7f7a44a5b88b250b3265dc60992ae387` |
| launch02 binding | `a4fab356cdd023362c42a33fa7d371d8b2a339df8603494ced7dcc5d13146f2d` |
| launch02 entry | `f0c73ee2091af20308b9443e7d8beb5e55aea82f312fd3e8634989ac949c5574` |

11的236程序＋27证据＋3metadata共266件、启动02的4成员＋2metadata共6件均已独立复制、原字节核验。协调端对应266＋6件冻结副本核验一致。独立目录为`D:/1800-private/a30-union11-independent-20261024-01`。

11相对10仅5件修改、2件新增，229件原字节相同，无删除。公式runtime/cache/history/worker、Windows holder、客户入口、09恢复/生产/读回及既有图框保护分支均沿用原字节。10的原REWORK、23件主清单及8件静态补充均复核保持；旧作者检查与旧实际/OCR/模型记录没有重跑。

## 原反例与当前范围

10中Q8三行的5/6像素相交已由程序合并为同源、同题、同分区的一个连接组件，保留原proposal、bbox、evidence refs及覆盖行/哈希；组件所覆盖的中文参与分类，不能仍伪称明确纯数学行。与Q7答案的跨题边界冲突双方进入人工审校，未调整或仍与任一相邻范围相交时，普通调用路径在worker前拒绝。既有已消耗ROI防重跑保护未放宽。

对固定计划独立几何核对：17明确区域与其余候选的相交0；20个人工区域中仅保留1对已标记的跨题边界冲突；37个区域与7个已知旧消耗区域相交0。1/5/10/11四项既有成功不在范围内。有限历史只证明明确保留的7个区域，不作全历史不存在未知尝试的声明，普通OCR索引仍`tex_cache=false`。

11声明计划head为`24f94121bd513e31db6cd1d8d62724e28a6081a6a4204f13b7bbac7446e11baf`。旧冻结head可重建其中15个明确区域，内容逐项相同；Q16普通配答后新增2个答案ROI，其原图哈希、尺寸、原始行及bbox均与独立保留的原始evidence相符。当前37项组件所声明覆盖行也逐项核验原文和行哈希。没有把旧head下缺少Q16配答解释为代码回退，也没有重建真实workspace。

本代码交付不包含新head的完整job blob，因此本独立没有宣称重建完整当前job或接受Q16配答内容；首次执行由冻结入口读取真实当前head，要求两组区域摘要、source refs、source pages、35条原操作和四成功项均仍与绑定相同。若普通UI改变区域列表，则入口HOLD，需由程序更新实际绑定，不能另建任务绕过。

## 必要新检查

5组独立Python控制＋2组受控JS检查通过，使用新的合成图像/状态，未执行作者已有测试：

1. 原图尺寸变化在读取模型身份前阻断；新ROI字节解码后等于原RGB裁剪，请求绑定原source哈希。
2. 精确COMPLETE缓存可零调用复用；同ROI换模型配置、改裁剪造成同源相交均拒绝，不重发。
3. worker释放未证写`FAILED_NO_RETRY`，重入不再调用；无输出INTENT保留并阻断换区域绕过。
4. 批次先复用一项缓存后到达900秒启动预算，后继停止，失败批次重入被拒绝，未产生新模型调用。
5. 执行冻结worker的两个负向路径：运行时身份变化在模型初始化前拒绝；显式合成backend仅一次引擎替身调用即被Python网络审计事件阻断。没有真实socket、真实模型、onnxruntime或rapid_latex_ocr初始化，未生成任何实际推理成功声明。
6. 批次按钮保留未保存草稿；请求在途时再次点击不发第二请求；返回仅为候选待审，未自动保存或确认内容。
7. 过期原图加载回调不能触发旧题请求；新的双相邻区域案例中，只消除一个冲突仍拒绝，明确调整并重新核对后才发送正常API请求，草稿未自动改写。

真实Edge/UI视觉验收及真实模型质量不由这些控制证明；所有新检查的platform/model/OCR calls均0。

## 启动02静态边界

启动包经普通`CustomerReviewWorkspace.formula_batch`进入上述代码，没有替换发送或识别实现。静态核验绑定的5个原图字节/尺寸、source refs、35条既有操作、四成功候选摘要和未激活settings均与此前已接受的冻结实际副本一致；没有读取或改变活动workspace。

入口在任何模型资源前核验代码清单、Python/holder、当前区域列表、来源原件、既有操作、允许的普通UI事件、模型身份和7旧区域保护。实际UI服务须有closed/outer-release证据。新激活authority、精确入口/启动manifest、root接受收据及有效窗口缺一即拒绝；原模板为activated=false。先以排他新文件写outer intent、child marker、实际计划及原job记录，再执行普通批次。只在内存启用当前公式设置，原settings不写。

固定上限17新ROI、每ROI1次、worker180秒、批次启动预算900秒、外层1140秒，首错后继停止。外层与worker复用相同Windows Job holder。失败时summary明确写`UNKNOWN_UNTIL_RAW_RECONCILIATION`，不把部分计数推断为全部调用数。实际原生进程释放需由后续实际原件证明。本次没有运行launch preflight、main或真实worker。

开发启动包是本轮测试绑定，不是客户每课时的authority/JSON/agent依赖；客户main/wizard等入口沿用已接受版本，常规动作通过普通界面触发。

## 保留事项

本轮辅助检查最初错误要求新旧head的全部明确区域相同而退出1；原脚本/输出/退出码保留。查明为Q16配答新增2区域后，只修审查辅助比较：15个共同区域逐项相同，新增2个逐项验证原source/行/bbox；02辅助检查通过，产品原件未改。另一次只读查询误用`manifest.json`而实际文件为`launch-manifest.json`，原缺路径错误保留；未因此启动任何入口。

10原批内重叠FAIL、作者11冻结前的边界策略失败及既有UNKNOWN/spent记录永久保留。本结论不接受模型转写内容、不接受其余12题生产或最终客户包；`CUSTOMER_READY=false`，`1800-a PAUSED`。本轮真实workspace/profile/ledger修改0，新平台/付费模型/OCR/真实模型推理0。
