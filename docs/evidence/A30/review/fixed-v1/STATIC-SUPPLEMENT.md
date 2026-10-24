# A30 v1：同时交回的静态接线缺口

基于同一固定提交 `8ac7be97c104c4cc57004de691ba21e5d4b92b33` 与根索引 `ba98f2ecf0f8eb4bcf6f8411304c12eb338404243d8cf2839cca7e4fdbf83d85`。仅消费独立复制的 `root-input/raw-source`。本补充没有运行产品、OCR、模型或平台；不改变已固定的数字答案反例及六项后继 `NOT_RUN`。

| 缺口 | 固定代码证据 | 对完整客户流程的影响及本轮必要修复 |
| --- | --- | --- |
| 选书/范围尚未接到自动取得来源 | `tools/customer.py:78` 要求填写书号、末级名称及来源页码并选本地文件；`:150` 直接调用本地 `prepare`。`customer/transport.py:capture` 仅由准备完成后的生产分支调用。 | 当前可提供本地材料导入，却不能以“选平台书与目录/范围”为起点自动准备。重名目录目前还要求源码 API 完整路径（交付说明已承认）。把已验证当前目录/范围选择与来源取得接到准备之前；日常用户不应查内部 ID 或写 API。 |
| 每个图片候选都要求逐题人工确认 | `customer/prepare.py:99`–103 对任意 image 来源无条件添加 `IMAGE_TRANSCRIPTION_AND_FIGURES_REVIEW`，候选进入 `NEEDS_REVIEW`；`customer/production.py:55`–59 要求全部候选已准备。 | 这与“正常项自动推进、异常项才审校”的终点仍有差距。现有 HOLD 是正确的保守边界，不能直接删掉；需要有依据的正常项判定和真正可处理的异常出口，真实识别质量另行记实。 |
| 旧成功/未知记录没有跨新工作目录接入 | `customer/production.py:60`–78 只查当前 `Store.state.sqlite` 的 `save:<book>` 操作；首次配置仅检查既有 profile 相邻账本目录存在（`tools/customer.py:39`–45）。接线生成 `customer-<source-key>`（`customer/wire.py:54`），原 writer 只检查本次这个 claim 文件（`runtime/usense_live/insertion_writer.py:157`–158）。 | 旧 A25/A28 成功不能仅因保留原账本就变成 `REUSED_ACCEPTED`；旧未知记录的不同 key 也没有接到此处的书级未决检查。需在当前书开始前读取并关联原回执/来源身份及未决状态，成功项复用，未知项对账后再推进。不能清账或给旧成功生成新保存。 |

最后一项是静态连接缺口，**没有实测重复发送或平台损坏**。`customer/native_plan.py` 的既有同区框重叠检查仍会阻止已存在相同几何的插入，这能安全停止，但不等于复用旧成功或全书未知记录已经对账。新 Store 内的去重测试也不能证明旧账本已接入。

图形/公式生产、原生导出和首次部署仍按作者固定声明为未完成/未实测，本补充不增加额外报告门槛。建议同一修订一起解决以上接线及数字答案反例；仅检查实际相关增量。当前结论继续为 `REWORK`、`CUSTOMER_READY=false`。
