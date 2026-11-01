# A25 作者冻结交付

产品提交 `b551dceadb052efad2e7e47216ec62896213ee40`，B 基线 `ee463c800bef1ec5010ee5950662b9726d474e42`。正式独立验收未执行/未代填。作者已停止本轮平台链，唯一只读额度 1/1，余 0；不得据本目录重新启动 claim/config/output。

阅读[作者报告](../../a25-lesson2-expansion-20261023.md)、[机器结果](../../../evaluation/a25-lesson2-execution-20261023.json)和[清单协议](../../usense-reviewed-batch-manifest.md)。`raw-manifest.json` 的原 bytes SHA256 位于 `raw-manifest.sha256`。

清单绑定 27 个源码/测试/文档文件、3 个外部任务/TLS批准文件、47 个私有证据文件。源码来自确切产品 Git blob，并已逐字节核对 checkout；`raw_path` 是私有冻结副本。私有证据同时保留 original path、SHA256、bytes 和独占创建的 `frozen_path`；原失败文件、spent authority 和单次 launch 记录均保持。浏览器 profile 未复制，配置和业务私有内容未入库。

独立方应先校验此 manifest 及每个成员，再从 frozen/source 原 bytes 建立自己的隔离目录。仅在该隔离目录做本轮必要离线检查，例如 `python -B -m unittest discover -s tests -p test_a25_batch.py -v`（最终 16 个不同新增检查）。不要读作者活动树、重跑旧194、访问平台或代为补采来源。

`checks/` 是作者各版本合成检查的真实 stdout/stderr 副本；局部 `.gitattributes` 禁止 Git 改写这些日志字节。15/15 与最终3/3有重叠；原14/14也保持，不累加成独立覆盖量。具体 argv、cwd、PID、exit、时间和输出摘要位于对应私有 process 原件。

发布预检首个 `git diff --cached --check` exit 2：保留的 CRLF 日志被当作文本，触发 trailing-whitespace 报告。已限定日志为 `-text -diff`，日志 bytes 保持；派生 JSON 清单在计算自身摘要前显式以 LF 写入。该首错登记于 `publication-check-initial-observation.json`，原 Git 输出未另行捕获为进程 bytes，不把观察记录冒充原 stderr。

实际唯一只读轮固定 `CAPTURE_FAILED_NO_RETRY` / `SSLEOFError` / business captures 0。摘要原 `release:null`、单独 release true、外层 Job/进程释放 true 均保留。另有一次外层哈希 helper AssertionError，原因和原 traceback 未落盘的限制如实记录；没有据新PASS抹去它。当前缺口是五题新稳定身份与来源/审校候选，不是可重发的保存请求。五题保存、读回、导出均 `NOT_RUN`。
