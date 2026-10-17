# 有界独立损坏对照

输入固定为最终交付 `5f872150a237b195f73c78e02e13a91d2f4f46a7`、补丁 `f8f2981a815f96147144d3747d26752b564cc9f7` 与主父 `4946b8ab307f88bdc25c14ace5ead774e3119fc5` 的集成树 `2078731114ad3a07368ca46a2f34c3544af64e2b`。只复制完成 Git blob 核对的 root raw 副本中 508 个必要文件；原发行 `180bb1e86fb2a7eb1546be85af70f466f069daf5` 的 1,144 个文件另复制隔离。每次变异后还原，全部运行后逐项摘要确认两份 root 输入 9,937 / 1,144 个文件不变。未写旧证据，未改 root 复验副本。

`run_negative.py` 收集实际命令、独占临时环境、不同 cwd、无 Git PATH、退出码、stdout/stderr、变异前后原字节和摘要。采集器进程退出 0；这只表示采集完成，不能把 I04 的意外接受写成拒绝通过。单个 case 的 `result/results.json` 保留新入口实际子进程回执。

采集器顶层 stdout 已由执行工具回执保留，启动时未另存 raw stdout 流；`collection-stdout-transcript.txt` 是根据该回执的完整 JSON 文本及相同的 summary.json 转录重建，未把它冒充另行捕获的原始字节或主张独立原始流摘要。各实际门禁子进程的 stdout/stderr 均在采集时按原始 bytes 保存。`collection-receipts.json` 记录真实顶层退出 0 及这一限制。

| 探针 | 实际结果 |
| --- | --- |
| I00 新入口 --focused，原样 | 外层 / A01 子进程均 0 |
| I01 生产 importer.url_index 返回值 +1 | 外层 / A01 均 1，真实函数调用 13 返回 14；实际 import 路径和 SHA 在独立实际导入探针，失败栈也指向隔离生产源码 |
| I02 编码原件翻转一字节，保留全部期望 | 均 1，fixed Git original digest mismatch |
| I03 第一条 Git blob OID 单独变异 | 均 1，逐条原参照等值断言失败 |
| I04 顶层 reference_commit 单独改为 40 个 0 | 均 0；该重复元信息未核对，原始意外结果完整保留 |
| I05 顶层 source_manifest_sha256 单独变异 | 均 1，来源清单摘要等值断言失败 |
| F00 / F01 选定原件原字节 / 明确允许的整份 CRLF | 保全 audit 均通过 |
| F02 混合换行 / F03 未允许 build.py CRLF / F04 PGM 中间一字节 | 均由保全 audit 以 CONTENT_MISMATCH 拒绝 |
| R00 原 180bb1e 树中原 R3 verify --preservation-only | 0；971 保全、62 代码参照接受，全部原始 Git 表示 |
| R01 同一原冻结树仅改真实 consistency.py | 1，implementation / CONTENT_MISMATCH |
| R02 同一原冻结树仅改参照 JPEG 一字节 | 1，preservation / CONTENT_MISMATCH |

I04 不能解释为字节或参照绑定可被绕过。补充 `explain_root_reference_probe.py` 实测：变异只有顶层 reference_commit；四条 payload、每条 Git OID/SHA/长度/representation 与 971 原清单条目完全相同，重算四个 Git blob SHA1 仍相同，source_manifest_sha256 仍精确绑定原清单。原常规测试会以原清单检查逐条等值；I03 和 I05 的实际失败提供对应对照。该字段是这一路径中未经断言的重复说明字段，是否记录为范围限制由主复验者判断；此子任务不决定整体结论。

没有把原 R3 verify 放在已改测试的新集成树上运行，没有重跑 630 项几何矩阵。上述均为离线源码、夹具和固定字节对照；不涉及业务来源语义包重封，因此“先经 load_bundle”不适用。未访问网络、浏览器、平台、凭据/profile、OCR 或模型。所有子进程串行等待结束，采集器已退出；`process-check.json` 的任务路径过滤下匹配为零，零待释放自有会话。
