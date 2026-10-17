# A01 集成 R2 主调度收口

2026-10-17。结论：**ACCEPTED，并已本地 INTEGRATED**。独立复验绑定新主父 `2d1dc8b97713ee06ec5bf35febe0b894ece584b2`、A01冻结交付 `5f872150a237b195f73c78e02e13a91d2f4f46a7`、组合树 `0645ac862f79fb4e232e4cfbd5f6bb5055a68d62`。

[独立复验](A01-integration-R2-review-report.md)报告 SHA256 `aa7ec3b060c30fa8ceefe282a2885669c50ff0138826b7840c8f0f7310c1f645`，统一清单 SHA256 `4a81d1f9ee38793c8ec3502d15650f9bfe382b908966435a73a45556e282f66e`。[归档审计](../evidence/A01/coordinator/integration-R2-review-audit.json)核对127项及清单自身、4个精确忽略日志、25处报告链接、24份固定Git输入和旧226项证据闭包，无交付缺口。双形态各11个完整入口命令实际退出0，A02各62项零跳过；原无Git裸单例1项零跳过。实际导入出处与固定字节索引已核对。

主调度从同一组合树另建原始Git字节副本，[有界复现](../evidence/A01/coordinator/integration-R2-acceptance/checks.json)证明真实无Git环境下原失败单例通过、3项固定输入保护测试通过、5个URL反例符合预期、两书R3包搬运换cwd后完成消费和图像解码。205个固定输入文件运行后保持原字节。未重复整套双形态或630项几何矩阵。

首次主调度导出漏掉R3 URL固定夹具，URL探针因文件不存在退出1。原脚本、日志及[首次记录](../evidence/A01/coordinator/integration-R2-acceptance/first-attempt.json)保留；仅补入确切组合树的缺失夹具，复跑该失败探针及尚未执行的两书消费。没有修改产品代码、断言或冻结样例，也未重跑已成功的单例/保护测试。

本次接受关闭原 I1-GIT-01。旧REWORK、原R3静态接受、I04冗余标签未认证及文件symlink权限跳过均保留。A01夹具Git LF与作者CRLF清单关系、A02五个源码文件默认checkout表示也保留，未扩大旧971/25或62/3固定允许集合。

实际合并提交为 `c6bebdf43eb93f7a6ae21e96ec07ed155686777d`，主父为已归档接受证据的 `50cf3e22b1a70b10ff3345d945bd3f140f3d04bb`，另一父为上述A01交付。464条合入差异逐项等于受验组合的对应Git字节，其他主父文件保留，零冲突；默认checkout另有29个精确LF→CRLF表示。[合并核对](../evidence/A01/coordinator/integration-R2-integration/merge-index-check.json)保留逐文件双摘要。

[真实集成检查](../evidence/A01/coordinator/integration-R2-integration/checks.json)在实际主工作目录完整运行一次常规入口：11个子命令均0，A01运行52项（51通过、1文件symlink权限跳过）、C01 70、A02 62、登录8，另有5个URL反例及6次来源消费。464条差异运行后未变。原结果收集器将C01一个通过测试名称中的 `skipped` 误判为跳过，收集器退出1；产品入口及全部子命令实际为0。保留[校验器纠正记录](../evidence/A01/coordinator/integration-R2-integration/checker-correction.json)，只解析原有unittest终局结果，没有重跑产品入口或修改代码。

独立验收及主调度同步子进程均已结束；保存的任务路径进程检查是其观察时点证据，不冒称当前全机普查。本轮平台、浏览器、OCR、模型调用为0，未推送或共享B。A04的A01依赖已释放，继续原只读坐标联调任务；D01清洁安装另行派发。S01完整性、A03恢复功能、B确认及全书质量/成本仍独立未决。
