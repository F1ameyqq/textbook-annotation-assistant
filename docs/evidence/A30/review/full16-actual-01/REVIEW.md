# A30 full16 actual f450：固定失败、保全与自身释放审查

结论：**ACCEPTED_FIXED_HTTP401_PREWRITE_FAILURE_PRESERVATION_AND_OWN_RELEASE_ONLY**。

接收固定输入 manifest `171c574c65d0f52f049a261fe9313d687cb4ef2d102b88528e51d1b069644584`、summary `2c43df767911cb67bbf80e33a24128912c143e48c119ca147d80a6887b975c05`；3857 raw +3元数据共3860成员，复制到私有审查目录后逐字节核对，并最终重新验证。只有有限原件检查，没有运行实际入口、preflight、产品、浏览器、模型或网络，也没有重跑UI18/v62内容矩阵。

固定授权 `f450d618-0316-472a-ae9e-e7c9eaccd5d3`（raw hash `011d325231c2c93eaf61ff94c96ea2bd9ae7b626f5107f7c86623881f9c54792`）绑定已接受产品18/UI03/launch03，entry、binding和launch七件与独立审查原字节相同；16题选择、12首次/4复用及预算一致。外层intent/child/result/outcome均关联此授权，spent1/remain0、禁止自动重试，顺序与业务时间均在原窗口内。原root回执引用保留；本审查不把其引用数当作新的实质接受，也不重新授予任何权限。

新增五组原件检查 PASS：

1. **确切失败。** 北京时间2026-10-24 19:35:34.264336，首次目录GET得到HTTP401，响应实体0字节，空文件hash匹配。capture-error/traceback关联 `CAPTURE_HTTP_FAILURE` / `GET_directory`。network-events为1条本地惰性文档事件及同一业务URL的native/context两层GET观察；不是两个业务调用。仅1份目录业务响应；后续frames/source/inventory/readback均未执行。TLS原件记录DIRECT、1次probe、原leaf `52d86421…`精确匹配、无fallback。这证明传输已到HTTP401，不证明认证成功，也不能诊断为session expired；具体原因UNKNOWN。
2. **零保存与停止。** capture和release均save_attempts0，无POST观察、无writer新增文件、无save新operation。程序result STOPPED_NO_RETRY，job BLOCKED_BEFORE_SEND。12题无acceptance、无保存intent且内容原样，后继保存/全16导出/显示NOT_RUN。没有同轮重启证据；授权保持1/0。
3. **旧状态保全。** 77条旧operations按完整数据库行精确相同，83条旧events前缀相同，只新增seq84 PRODUCTION_STOPPED。3816旧workspace成员中3815非数据库成员原字节不变；新增15件（停止head及单次capture记录），state.sqlite唯一改变。旧9及四题的既有证据保留、四份acceptance引用不变；Q5/10/11仅本地platform_status改为REUSED_ACCEPTED，Q1及12待写题完整不变。head由 `4169e60b…199325`→`b5382e4e596eeb8e082a54db7fe92a045c2b72f4e0dc4e1367bacbbe6d3551f6`。frames、正文、hash、审校状态、settings均未改；review_actions仍61。job的native_export_status仍是旧四题成功状态，原delivery mapped_count=4、ref/display_checks均未变化，绝不解释为本次16题导出。
4. **自身释放。** 固定release证明context_created/closed、runtime_started/stopped、pending_callbacks0、errors0、login请求空、自动登录false。内层capture holder exit2与外层production holder exit2均为原失败退出；分别13/18个进程观察条目，共31条、18个不同(pid,creation_filetime,image)身份，重合身份退出码一致。所有观察进程exit signaled与句柄关闭，两个Job active_after=0，thread/process/job句柄关闭；对应stdout/stderr原字节与hash全部匹配。未枚举当前机器进程。上层“失败或释放未证”是通用错误文案，不推翻这批原件已证明的自身释放。
5. **封存助手首错保留。** 原freezer在空directory.json做JSON解析抛JSONDecodeError/exit1，原helper hash验证，空HTTP实体不被改写。R1仅使同一原件拷贝/汇总能保留非JSON响应；原错误说明明确是聊天输出转录，不是raw stderr，原工具原始stderr没有在此包单独提供。没有借助手修复重跑业务。

业务wrapper计时5.0714730999970925秒；ISO时间差5.071482秒。job内部production_seconds为5.030138199999783，是本次内部计时并覆盖该字段，旧349.41077000000223仍在保留head，不把它当累计客户耗时。累计客户总耗时/手工操作未测；61为既有代理UI动作。

本结论只接受固定失败事实、旧状态保全和自身释放，不接受新题保存、认证恢复、全16交付或客户就绪。原所有失败、耗尽授权与UNKNOWN继续保留。UI18/v62已接受内容不需重做；任何将来手动登录或登录后的12题续行须由相应执行方另行精确绑定，不能再用f450，不能重存旧9/4或重播OCR。本reviewer没有打开登录窗口、改profile、解锁或启动新业务。CUSTOMER_READY=false；1800-a PAUSED。
