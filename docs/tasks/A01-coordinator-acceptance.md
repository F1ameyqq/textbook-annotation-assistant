# A01 主调度验收与本地集成

日期：2026-10-17。**ACCEPTED**：`180bb1e86fb2a7eb1546be85af70f466f069daf5`，实现 `31d715a5f2e6435af3a7e98a6c19b41b72d883bd`。范围为两本已指定样书的离线来源接入和 `a01-geometry-1` 公共几何，来源版本 `a01-static-1-r3`、合同 `1.0.0-a-proposal`。本次接受不代表 B 确认、完整性自动放行或平台能力通过。

[R3 独立报告](A01-review-R3-report.md) SHA256 `5fa9bb4d4cd4743fd1dfe632f73423e9d9734e5931c2b8f9fcd0f95ed2f362b1`；[统一清单](../evidence/A01/review-R3/sha256-manifest.json) SHA256 `13f10d73e80086c612ffaaded21bb11ff29c826070d483f9202d7f87216581d8`。原 R1/R2 失败及 R3 中断记录均保留。

## 决定依据

- 独立验收已完成：两种文件形态完整入口均退出 0，各自 A01 48 通过、1 权限跳过及 C01 70 通过；61 个独立 URL 正反例、8 个保全门禁对照符合预期。几何 630 项矩阵引用未改实现的 R1 结果，本轮未重跑。
- [归档前检](../evidence/A01/coordinator/acceptance-R3-preflight/result.json)核对 536 项正式记录、含清单共 537 个文件；16 个 Git 忽略日志仍纳入。1,144 个冻结源文件与 Git blob 一致，527 个中断前文件、1,402 个旧验收材料、31 个原输入及 6 个主目录材料保全；19 个报告链接有效。
- [主调度复现](../evidence/A01/coordinator/acceptance-R3/coordinator-check.json)先核对实际使用的 11 个源文件和 60 个反例输入，再重放 Q01/Q02/U23/U24/U25 的完整包。五例公共资源校验均通过，来源层均返回 `SOURCE_URL_COMPONENT`；两书正常包通过，另有 8 个组件字符串层负例符合预期。输入前后摘要未变。
- [复现命令回执](../evidence/A01/coordinator/acceptance-R3/command-result.json)退出 0。初次主调度脚本误用清单键 `files`，退出 1；脚本与回执另存 attempt-01，再修为实际 `records`，未改被验实现或输入，不把工具错误当实现失败。

复现入口为 `python -B docs/evidence/A01/coordinator/acceptance-R3/reproduce.py`，依赖报告中绑定确切提交的只读副本；脚本拒绝覆盖原输出，复验须使用新的证据目录。此次没有网络、平台、模型调用；无自有浏览器会话。

## 限制和集成安排

S01 公共来源完整性资格、D01 根 Pillow 依赖/清洁安装、N15 非认证 precision 标签和 Windows symlink 权限跳过保持明示。直接 HTTP(S) JPEG URL 的 query/fragment 严格拒绝；没有主机真实性或签名 URL 承诺。历史题内容不是金标准，全书独立分母、OCR/配答、CSS/DPR、真实保存恢复及成本仍未通过本任务验收。

下一步正常合并此确切提交，保留他人文件并运行 A01/C01/A02/登录受影响检查；通过后才记 INTEGRATED。D01 由调度在合并后补最小依赖并验证独立非 editable 安装。A04 待正式发布可用基线后继续，不能仅凭本文 ACCEPTED 开启会话。实际合并、命令及结果将在下方追加；本地归档不表示推送或共享给 B。

## 集成尝试：未通过，已撤回

从 `4946b8ab307f88bdc25c14ace5ead774e3119fc5` 正常合并上述目标到未提交状态，414 个暂存路径与目标 Git blob 一致。[实际回归](../evidence/A01/coordinator/integration/checks.json)：A01 47 通过、1 跳过、1 失败；C01 70、A02 52、登录 8 通过。唯一失败是测试把当前整个工作目录当作历史 971 项不可变快照，受到两份已更新调度文档及 18 个 checkout 换行表示影响；没有改写历史参照来放行。

[失败分类](../evidence/A01/coordinator/integration/mismatch-classification.json)与[撤回回执](../evidence/A01/coordinator/integration/merge-abort.json)保留。原 R3 有界离线 ACCEPTED 不等于集成通过；A01 未记 INTEGRATED，A04 未释放。已准备[集成修订 R1](A01-integration-rework-R1.md)，在原执行/验收对话按限定范围修复测试适用边界后重新集成。D01 尚未开始。
