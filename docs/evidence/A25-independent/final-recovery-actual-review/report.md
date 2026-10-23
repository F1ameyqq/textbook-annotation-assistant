# A25 五题实际保存、独立读回及数据包最终有限验收

结论：五个既有题目各一次真实成功回执及各一次新鲜独立读回，累计正式接受；五题原始读回数据包完整性接受。范围为书46007447印刷1–5、native18–22，非全书完成、paper原生导出或实际图公式渲染验收。

|印刷题|native|node / info|实际结果|
|---|---|---|---|
|1|18|1792066823781 / 2110707359007944706|原一次成功回执、原独立strict完整匹配保持|
|2|19|1792066869052 / 2110707547843899394|原一次成功回执、原独立strict完整匹配保持|
|3|20|1792067036007 / 2110708248120700929|一次成功回执、原独立读回按已正式接受的有限新增区键序规则匹配；原strict FAIL保留|
|4|21|1792067074506 / 2110708409593016321|原一次成功回执、新首次独立reader40364完整strict匹配；旧writer framework false保留|
|5|22|1792067091596 / 2110708481181396993|writer25400一次成功回执、独立reader55868完整strict匹配|

最终actual110原件及数据包76原件均核源清单/根副本摘要并独立隔离。复用此前固定独立结论d4e226f8、8a5af6d2、d74a0705、389900bb；不重跑旧实际、产品、测试、OCR或平台。产品绑定389d及包摘要1c222acd，runner/outer/恢复plan均等于已接受版本。

本轮按核定顺序先第4reader12GET：新进程/context、每份响应200、原bytes/size/hash及双层计数吻合，观察时间均在旧writer及旧Job结束之后，完整目录/全部76框/目标annotations/全部info/五区按原严格类型、对象键顺序及数组顺序比较，只容许既定info.updated_at推进；source/两页保持。该reader退出且context/runtime释放后才开始第5writer。第5先新鲜12GET核before，再唯一POST取得HTTP200/code0精确成功原回执，writer退出后不同PID/run_id reader12GET完整strict匹配。所有原stdout/stderr、capture-summary、config、TLS、plan、send/ledger/receipt及native原件链已核；没有用纯比较对象中的false provenance标记代替实际独立性证据。

本轮仅1POST、2reader、3context/惰性导航/TLS、36业务GET。三个context/runtime释放；整批exit0、Job active0、47个唯一PID+creation_filetime持有身份全部exit_signaled/handle关闭，launcher/process/thread/Job handle关闭。唯一新authority05b17ac0先intent及原子消费后启动，一轮1/0。累计三次保存/回读批为5POST、5精确成功回执、5个fresh reader、4 strict匹配+1有限键序匹配、10context/120GET；此前取源GET不计入此三批累计。原三批额度均耗尽，无重发第三或第四题。

原六ledger文件逐hash未变，仅新增第5正常intent与accepted，最终8文件=5intent+3accepted。第三原strict FAIL、第四原context_closed=false/runtime_stopped=false及两个TimeoutError不改写；旧context/runtime失败不被最终OS释放覆盖。累计9个framework释放true、原第四writer1个false。第3/4没有accepted marker，此结果不构成它们的未来revision前驱，不授权其他写入。

数据包manifest2b44c551包含76份，其中60份是五个实际fresh reader各12份原生响应；73个已知原件副本与先前接受字节相同。五个stable ID和reader_run对应实际累计表，五区PRESENT/ABSENT、所有原文字及UTF-8摘要逐项等于原响应和已接受plan expected。五个question中的图片URL各与该题当前annotation image_path相符；所有内联TeX/单位字符串原样保留。未下载图片或运行公式renderer；paper原生导出NOT_RUN，实际图片/公式可视渲染NOT_RUN/NOT_OBSERVED。作者导出中的pending/历史状态作为原始元数据保留，由本有限报告给出正式数据范围结论。

保留作者首次封存helper的str/Path AttributeError及初始脚本/原stderr；仅helper修正后110个v2原件逐hash接受。根完成核证和状态写入后打印checkpoint时的GBK解码辅助错误sidecar一并保存；显式UTF-8检查同副本，无产品/平台重跑。本独立helper无新失败。独立完成并释放，sole1800-a保持PAUSED；无Git提交、ledger修补、根状态或自动化变更。
