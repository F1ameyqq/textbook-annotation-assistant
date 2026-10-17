# A02 portability-R2 主调度收口

2026-10-17。**ACCEPTED**：冻结交付 `a1e5be00909172429d792b6c41bdaf384258694e`，补丁 `ad71284f3b6ffc8454ee1d1e30933c8e39d7c1d8`，基线 `38aca9dcc8d027409b95193e9cc142c2336b76d3`。接受范围仅为身份示例工具在 Git 缺失或查询失败时返回明确 unknown/null，仍保留依赖 Git 的绑定拒绝条件。

[独立复验报告](A02-portability-R2-review-report.md)已完成，SHA256 `92217848c055e133e2b79b4318027e1185105e8a75e5fc14531a7f1fda937d77`；[清单](../evidence/A02/review-portability-R2/sha256-manifest.json) SHA256 `0deab33db966b2b9f13c0fc90c7de0e8aa16c7d634ec2992a75fb8e439188555`。14项专项检查通过；同一套62项A02测试在真实有/无Git两环境各通过，不相加为124项独立成绩。原单例实际运行无skip，7条预期非零收据（旧版两条失败对照、五个绑定拒绝场景）保留。两次独立采集器错误和作者原失败均保留。

[主调度复现](../evidence/A02/coordinator/portability-R2-acceptance/coordinator-check.json)从确切Git blob另导出92个文件，完成三条命令：原单例在无Git环境退出0且无skip；无Git绑定实际退出1；真实正常仓库身份成功后，仅改变子进程PATH使第二次实际OS启动失败，helper返回unknown/null。退出码依次为0、1、0，导出文件前后摘要不变。未重跑完整套件。复现脚本为 `docs/evidence/A02/coordinator/portability-R2-acceptance/reproduce.py`，一次性新目录生成，所有同步子进程已返回。

[归档审计](../evidence/A02/coordinator/portability-R2-review-archive-audit.json)核对独立报告、清单与证据闭包；归档暂存区/Git原字节检查另记在本次调度归档记录中。[交付前检](../evidence/A02/coordinator/portability-R2-delivery-preflight/audit.json)确认唯一既有修改是 `examples/a02/R1/identity.py`，`source_binding` 函数字节不变；188项净改动、187项清单与2,084个既有文件保全事实保持。

这是局部补丁接受。原A02 R1业务范围、N1/N2、A01原REWORK与I04非阻断标签限制不改写。A01完整集成入口尚须以新固定集成父版本复验；A04/D01尚不释放。A03、I01、S01、B共同确认、真实平台和质量/成本仍按各自门槛推进。零平台、浏览器、凭据、OCR、付费模型；自有进程释放是同步命令回执/声明，无系统全进程普查。当前仅本地，不等于已推送或共享B。

## 集成安排

本文件首次归档时仅记录ACCEPTED。主调度将明确合并上述最终提交，核对范围与原字节，并在实际集成版本运行受影响A02回归；成功后再追加INTEGRATED及确切合并提交，继而续派原A01独立验收对话。不得用本段计划提前释放依赖。
