# A25 固定实际有限验收

结论：接受首两题真实保存及不同进程/新context完整回读；接受第三题成功回执、已捕获新鲜回读的固定事实及原严格失败；接受六context/runtime及最终整批OS释放。整批保持STOPPED_NO_RETRY，第4、5题NOT_RUN，authority已消耗1/剩余0。

核202份根冻结原件，并复用已接受的8990产品/五计划120份隔离原件。未运行产品、访问平台、读取活动修正或触碰真实ledger。三次POST分别有200/code0完整成功原回执，三个reader均在各自writer退出后启动，PID/run_id不同，全部12响应的观察时间晚于writer结束、原始bytes/hash闭合。共72业务GET是writer36+reader36；双审计层不相加。

首两题完整目录、全部76框、题框、全部info/五区、source/两页均按原规则通过，只有目标info.updated_at允许推进。第三题除该既有更新时间规则外，递归遍历完整原生快照，遇键序差异仍继续核每一个字段；字段集、精确类型、每值、全部文字、数组长度/顺序/元素类型以及未知字段均一致。仅两处对象键序不同：zones.question.data和zones.answer.data，预期rect_ids,ocr_result,success，返回success,ocr_result,rect_ids。两区此前确实缺失；现success为bool true，题干文字逐字相同，答案字符串4，rect_ids数组和顺序逐项相同，无额外未知字段。详见third-deep-facts.json及result.json的遍历计数和逐区摘要。

这项原值事实不改写旧strict FAIL，不生成新规则或第三题accepted标记。冻结ledger是3个intent/2个accepted；后两题只有准备文件，没有writer/reader/intent。原批错误READBACK_ACCEPTANCE_FAILED、outer exit2和未执行后继全部保留。第三题不得重发，本报告不授权补改ledger或恢复额度。

最终整批Job active0，99个唯一PID+creation_filetime身份均退出并关闭持有handle，launcher/process/thread/Job handle关闭；六writer/reader PID均在持有身份集中，六context/runtime释放。只证明最终整批OS释放，不能提升为逐writer在下一reader之前所有子进程的OS释放。

实际发生于2026-10-23 19:17–19:18（Asia/Shanghai）；机器报告保留原UTC时间。独立验收完成并释放，sole1800-a保持PAUSED，未改产品、ledger、根JSON或Git。
