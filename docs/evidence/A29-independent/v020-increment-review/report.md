# A29 v0.2.0 候选增量独立验收

结论：`REWORK`。6 项增量命令达到预期，1 个独立输出边界反例失败；发现后停止产品执行。包身份、含空格路径下的正常调用、非零退出传播和本轮自有 Job 释放获得有限离线验证，薄持有入口的“包外输出”边界需修正。

固定代码 `389f7defa9db901b101889f15c083c1eefc34d2a`，最终文档 `9123285db87d7ca05f0d3571de1b171fe550ce87`。候选 ZIP SHA256 `dbcd0ac4317299d99debfce43559ff396765e32fd3855d8e54fad12b38f59052`，manifest SHA256 `fb1fdf63a40b193c86aebe6dce2bfd09fb9ad36bfc82c6352b858ddf899808ad`。根冻结索引实测摘要 `815a389190909fcedee843781f4cdba82b2a552cc3a0755087e4f2265dd79134`，49 个 frozen 输入及独立副本逐项核验；未读取索引的活动 source 路径。

相对已接受 v0.1.3，包新增 8 项、变化 4 项、移除 0 项，96 项逐字节相同并复用原结论。新 ZIP 有 108 个清单成员加 manifest，共 109 个文件。10 个新增/变化的 Git 来源文件与固定 raw blob 相同，最终报告与 final commit 相同。原 owned_process.py 的 8826 字节及摘要 `a1582782024994d841ddeadc0e2df6c8ef29a35bc8e428dcb4dd8b8cdc589ee8` 相符；运行时锁、launcher、合成输入生成器及 A26 ZIP 均未变。不重跑已接受 v0.1.3 基础套件。

独立解包目录和产物路径均含空格。实际执行：新包 check、holder help、START_HERE sample-preflight、holder 包外合成预检、重复 record-prefix 拒绝、非零子进程传播，六项均通过。正常预检与 sample 结果深度相等，合成 profile 与 ledger 为空。正常及非零子进程分别原样得到退出码 0 和 2；非零结果为 STOPPED_NO_RETRY，没有被包装为业务成功。

阻断发现 A29-I01（P2）：`app/tools/run_usense_owned.py:13,22` 把 ROOT 定为发布包内 `app`，仅拒绝 ROOT 及其子目录。README 要求包内容保持只读、输出在包外，但 `--record-prefix <解包根>/top-level-output-01` 仍被允许。独立字节相同控制副本中，使用 `batch -- --help` 作为无业务子进程，薄入口实际退出 0 并报告 CHILD_EXIT_ZERO_AND_OWNED_OS_RELEASED，在发布根写入 `.stdout`、`.stderr` 和 `.process.json` 三个清单外文件。此时实际文件集合已不等于固定 manifest。没有在失败后再运行 check；文件集合不等通过静态清点记录。

最小修正：保留 app 作为原工具 cwd，但输出路径验证覆盖包含 manifest.json、launch.ps1 的完整发布根；在 mkdir、Job 或子进程创建前拒绝包顶层及其所有后代输出。保留原 holder 字节和包外正常调用行为。本次不修改作者产品。后续只需复验该原反例及受影响的目录边界/正常包外控制，无需重做 v0.1.3 或 A28 业务套件。

正常预检、非零子进程和反例三个 Job 均在 resume 前绑定，最终 active=0；本轮共持有 9 个进程身份，其退出及句柄关闭均有原始记录；Job、进程、线程句柄均关闭，owned_os_release_confirmed=true，无 timeout/errors。输出边界失败没有伴随释放失败。7 个审查命令均结束，无待释放自有会话。原验收包、旧 v0.1.3 与 root 冻结输入保持不变，仅控制副本被反例添加三份记录。反例后产品执行均 NOT_RUN。

START_HERE 已清楚标示离线候选、现仅五题成果、本机 Python/Edge 依赖以及九题成果未纳入。最终九题出口、具体核对命令和未来新输入的完整持有器入口仍待根提供。A28 48cbd 的业务正确性、正式接受、实际四题操作及最终九题成果属于另一正式验收；本轮仅核固定字节和包的接手路径，不运行 A28 套件、不代其接受。候选不得作为最终业务版接受。

本轮平台/网络业务、浏览器、真实 profile/credential 读取、OCR、成功保存重放为 0。只读独立合成 profile。未改产品、根 JSON、AGENTS、自动化；未推送或发送 B/外部消息。1800-a 未被本审查操作。旧 v0.1.3 接受结果不受此新包装反例影响。
