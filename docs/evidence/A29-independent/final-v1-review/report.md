# A29 v1.0.0 最终接手验收

结论：`ACCEPTED_OFFLINE_ONLY`，限定为**第二课时九题成果、本机固定运行时和明确有限契约下的接手包装**。无阻断发现。代码 `08d4a3585e5ab0458dbcf1dab97dc69e012830fd`，最终文档 `32388d553d3dcce9670b4671e492a5ad4014695e`。运行 ZIP SHA256 `ffa8667f25a53d19404a8e5a1111f9b630770ad763f1772e052aca28d65824a3`；manifest SHA256 `3b9089c4d749b3a8ef29c27379a738848b91ea8857f24d28693405ffc70c3967`。

278 份声明原件已核验并复制，后补根索引 `da49d3505575dd5ebdb9a6ac7e968b1738f5da4c45d78f2a2decdadb6587ede9` 的 280 项与原件、声明、清单对应。根索引到达前只读确切固定路径；作者报告从 final commit 原始 Git blob 取得，未读取活动作者工作文件。最终 ZIP CRC 和相对路径检查通过，259 文件/258 清单成员逐字节一致，在含空格的新目录解包。

相对固定 v0.2.1：151 项新增、4 项变化、2 项删除、103 项不变；变动集中于成果、接受凭证、状态和说明。5 个新增/变化的 Git 来源文件与固定 raw blob 相同；全部 app/src、app/tools 和运行时锁与基准相同，R1 wrapper 及原 holder 摘要精确保留。复用 v0.1.3、原增量 6 项和 holder R1 接受，不重跑旧矩阵。

包内 `delivery/lesson-nine-delivery.zip` 精确等于已正式接受的 `9f3ee0898149cac060feb52142f327e83d03deafb906bde203b084f606b3a1ba`；其 140 个展开文件全部与 `delivery/lesson-nine/` 相同。A28 内容、原生映射和 55 张截图直接引用另一独立结果 `e910de177135a4461eb651107b3711a9ceba213cb31fe75a1828d6c1e57d6b15` 及根回执 `40df778223134cb370704bfd345f363b648838c470377d480db344576b5ae70b`，本轮均未重测。

4 项最后检查通过：最终包 check；按说明读取完成状态及冻结 manifest/summary 引用；实际执行 operations/01 的原文预检；解析 operations/02 的生产命令。文档预检仅以审查方原有隔离合成输入替代 9 个 Read-Host 回答，未改变脚本文本，未使用已完成九题或真实 profile。预检生成 `batch/batch-preflight.json` 和 `outer/batch.*`，子进程退出 0，1 个新 Job 的 active-after=0，3 个持有身份退出/句柄关闭及 owned_os_release_confirmed 均成立。生产片段仅解析，未执行；两份 operations 文本与 README 对应代码块相同。全部包文件在运行后不变。

说明明确：9/9 仅本课时；A28 新建题仅书 46007447 第二课时 q6/q7/q8/q8-variant 固定契约，不是更换任意 manifest 即可通用写入；完成输入禁止重放；当前耗尽的专用 authority 不可由通用命令替代。当前机器外部 Python/OpenSSL/依赖及 Edge、既有 profile/ledger、历史 UNKNOWN 和 A25/A27 限制均披露。未新增实现或扩大业务接受。

包内 native/final pending 是不可变的构建时快照。后续 native 正式/root 接受已由固定声明和外置模板绑定；模板同时绑定运行 ZIP 与 manifest，位置在 ZIP 旁、包外。最终 `.acceptance.json` 在本次检查时尚不存在，由根在本正式结果后创建；这是预定收口步骤，不要求修改 ZIP。审查方未创建或授予任何 sidecar authority。正式 sidecar 的读取命令保留为待根创建后执行。

本轮平台、浏览器、真实 profile/credential、OCR、保存重放和业务/视觉重验均为 0。4 个审查命令结束，新 Job/持有身份已释放，无待释放自有会话。未改产品、根 JSON、AGENTS 或自动化，无推送或 B/外部消息。仅新增独立审查证据和隔离合成预检输出。
