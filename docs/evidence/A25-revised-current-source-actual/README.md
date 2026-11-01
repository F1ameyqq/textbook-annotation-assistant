# A25 修订版当前源实际固定交付

固定产品 afc9d761 / launch fef3638d 的唯一新实际轮已停止：CONNECT HTTP200后，native TLS do_handshake抛FileNotFoundError/errno2，缺失文件名未记录，leaf/业务响应0，根因UNKNOWN。两条持有身份、Job及句柄释放已证，当前轮1/0；原轮也保持1/0。五题新身份/来源候选、账本初始化及保存读回导出均NOT_RUN。

[实际报告](../../a25-revised-current-source-actual-20261023.md)、[机器结果](../../../evaluation/a25-revised-current-source-actual-20261023.json)与本目录raw-manifest.json/sha256组成交付。这里只提供原件路径、长度和摘要；凭据、profile内容和业务正文未发布。没有新产品修改、测试、重试或自验收。

已在评论即时交付两个不可变私有入口：checkpoint `1b1a98a1a4ac1fa90e74d9dc79aec521531cda461106affe7424d8340e4ab22b`；实际失败小包manifest `c8d748c684d239104c1ca48d360d7c8962a269774c76fe323cf48937c3abfdcf`（34raw+3直接源码）。小包冻结副本保持，不把后续日志观察写入原件。

完整清单另绑定已固定afc9d761的30源码闭包、原监督器及6项本地静态/日志补充。后续只提取本次时间窗/目标的一行既有代理日志：GeoIP(cn) using DIRECT；没有TLS中断原因或PID绑定证据，不把该观察升为网络根因。现有材料未确证可修复的本地缺失路径，未猜文件补建、改错误名或放宽TLS。

实际结果供同一独立对话作有限静态审查；不得据本包重开新旧authority、config、claim或输出。下一实际动作继续由根具体绑定，sole1800-a保持PAUSED。
