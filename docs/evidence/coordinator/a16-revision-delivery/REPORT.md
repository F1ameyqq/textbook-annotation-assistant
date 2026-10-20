# A16 同阶段 R01–R04 修订交付

状态 **REVIEW_CORRECTED_OFFLINE_RELEASED**，等待原正式独立对话复核；不是独立接受或 live 激活。产品提交 `cb26282a2340d2136c4db103a07391e593730cf9`，原 final `4fe417d5246f20fbbbedc577495c7ca400d4ded8`，当前 workflow `f04c1579353de3fd2006b533d5c792c80190f5b8`。最终 final 由本报告所在交付清单及最终回复给出。

- R01：在正文前比较当前单题框与全量库存的数量、唯一 ID 和完整语义投影；同 ID 改角色/顺序等冲突停止后继，列表换序可通过。正文绑定本次验证框；最终守卫失败只发布拒绝结果并清除已读正文的可接受状态。
- R02：以具体 native fetch GET/JSON getter、实参/zone 调用及响应字段来源链证明 schema，记录资产摘要、代码范围和字段引用。词汇、注释、无关函数和 bool 不能登记 API；13 个未知 schema 的 collect 新反例均无样题请求或 AVAILABLE/KNOWN_EMPTY。
- R03：对同一 immutable bytes 执行完整像素 load，再取尺寸/格式及保存。合法 JPEG/PNG、新残缺 JPEG 反例及确切保存字节通过；残缺图在保存前拒绝，不启用全局容忍或下载重试。
- R04：worker RELEASED 要求前后 pid/创建时间有效且相同；失配、缺失或检查异常为 UNKNOWN，错误和父层失败保留。七个内存 held-handle/Job/clock/Popen 控制包含一致成功和独立的 worker 错误。

新修订工作树 suite 为 **75/75 PASS，3359ms**；固定 Git raw 隔离复现为 **75/75 PASS，2906ms**，含62个 collect 场景、23份正式补充控制记录，shell exit0。原 test_offline.py 的33项、A15及更早 suite没有重跑。run01–run05 新输出全部保留；打包命令的一次 stdin 编码 SyntaxError 独立留档。原正式 R01 反例只读固定包，不重新执行旧产品；原 C14–C16 的 NOT_RUN 不变。

新候选19成员明确包含既有 `src/annotation/__init__.py` 的73字节 Git raw blob；缺项门禁拒绝。工作树旧文件74字节 CRLF保持，不修改、不静默归一化。20成员 raw 导出（含候选清单）完成默认静态验证及上述新 suite；可在 [raw-checkout](raw-checkout) 直接按固定字节复核。原隔离包漏项与产品缺口分别记录。

31,259个基线成员 mode/blob 全保全，原39份 A16 证据及旧报告、清单、run01–run09、失败、native 引用全不变。只修改原 A16 五个源码/测试路径并新增修订源码/测试和证据，根任务/调度/依赖未改。精确增改成员及 size/SHA256/Git blob 见 [delivery-manifest.json](delivery-manifest.json)，候选依赖见 [candidate-manifest.json](candidate-manifest.json)，机械保全见 [preservation.json](preservation.json)。

R02 只支持已说明的窄形态，不是通用 JS 解释器。axios/interceptor、箭头函数、别名、跨资产关系和复杂 bundle 未识别时保持 UNKNOWN、不试探；当前平台前端适用性尚未证明。R03只支持单帧。R04均为纯桩，不证明真实 OS Job/浏览器释放。正文覆盖与完整库存仍分开，首题草稿/HOLD及真实保存、内容/题框刷新重开读回 NOT_RUN保持。

本次0真实浏览器/网络/profile/凭据/nativeAPI/占用扫描/登录/业务/B消息。A16无 TLS 决定、activation或live，默认严格 TLS。静态子进程PID76744及新隔离 suite PID68148均 wait完成、exit0、stderr为空；所有测试/native资源为内存桩，无真实会话/Job/原生句柄待释放。不声称观测作者自身 OS 退出身份。

完整逐项响应、原始结果路径、限制和释放见 [author-report.json](author-report.json)。本报告仅作者交付；下一依赖为调度将新固定 raw 交原正式独立复核。
