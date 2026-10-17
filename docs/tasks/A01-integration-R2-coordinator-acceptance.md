# A01 集成 R2 主调度收口

2026-10-17。结论：**ACCEPTED，待实际本地集成检查**。绑定新主父 `2d1dc8b97713ee06ec5bf35febe0b894ece584b2`、A01冻结交付 `5f872150a237b195f73c78e02e13a91d2f4f46a7`、组合树 `0645ac862f79fb4e232e4cfbd5f6bb5055a68d62`。

[独立复验](A01-integration-R2-review-report.md)报告 SHA256 `aa7ec3b060c30fa8ceefe282a2885669c50ff0138826b7840c8f0f7310c1f645`，统一清单 SHA256 `4a81d1f9ee38793c8ec3502d15650f9bfe382b908966435a73a45556e282f66e`。[归档审计](../evidence/A01/coordinator/integration-R2-review-audit.json)核对127项及清单自身、4个精确忽略日志、25处报告链接、24份固定Git输入和旧226项证据闭包，无交付缺口。双形态各11个完整入口命令实际退出0，A02各62项零跳过；原无Git裸单例1项零跳过。实际导入出处与固定字节索引已核对。

主调度从同一组合树另建原始Git字节副本，[有界复现](../evidence/A01/coordinator/integration-R2-acceptance/checks.json)证明真实无Git环境下原失败单例通过、3项固定输入保护测试通过、5个URL反例符合预期、两书R3包搬运换cwd后完成消费和图像解码。205个固定输入文件运行后保持原字节。未重复整套双形态或630项几何矩阵。

首次主调度导出漏掉R3 URL固定夹具，URL探针因文件不存在退出1。原脚本、日志及[首次记录](../evidence/A01/coordinator/integration-R2-acceptance/first-attempt.json)保留；仅补入确切组合树的缺失夹具，复跑该失败探针及尚未执行的两书消费。没有修改产品代码、断言或冻结样例，也未重跑已成功的单例/保护测试。

本次接受关闭原 I1-GIT-01。旧REWORK、原R3静态接受、I04冗余标签未认证及文件symlink权限跳过均保留。A01夹具Git LF与作者CRLF清单关系、A02五个源码文件默认checkout表示也保留，未扩大旧971/25或62/3固定允许集合。

独立验收及主调度同步子进程均已结束；保存的任务路径进程检查是其观察时点证据，不冒称当前全机普查。本轮平台、浏览器、OCR、模型调用为0，未推送或共享B。下一步实际合入A01并跑受影响常规入口，通过后才记INTEGRATED和释放A04。D01清洁安装、S01完整性、A03恢复功能、B确认及全书质量/成本仍独立未决。
