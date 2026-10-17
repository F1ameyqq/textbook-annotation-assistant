# A03 P2-R3：EvidenceRecord 消费者闭包独立复验

2026-10-17。继续原验收对话 `01a145aa-8d59-7c70-8d81-731712103a9a`。用户手动调整了 A03 思考强度：本次续发省略 `thinking`，保留当前设置，不猜测档位。旧任务及冻结报告中的 `xhigh` 只是历史派发记录，不据此改回设置。

## 冻结输入与状态

- 只读工作树：`C:/Users/ASUS/.codex/worktrees/a03-runtime-recovery/1800`。
- base：`526d264284f36f856c306db88c1d7e71c04152e1`；交付：`87606b73e0754fa670491d9fb958a416c26bfe88`。
- 执行 workflow：`c3b5f38c7e9a3a4a51ae8cbe16a3821ff2f36970`。本次复验 workflow 由派发消息提供确切提交，不能合浮动主树。
- 目标提交的 `docs/tasks/A03-P2-R3-evidence-closure-delivery.md`，SHA256 `c4831f0ceec0036b0bccfcc596a4a704b802f6a0ed31b9a500d341b52a0bc328`。
- 目标提交的 `docs/evidence/A03/execution/P2-R3-evidence-closure/sha256-manifest.json`，SHA256 `16909b0445495e8a1dbbc0af8831947a06907c29714cbe8a8e6d218aeee64d72`。
- [执行任务](A03-P2-R3-evidence-closure-rework.md)、[R2 独立结论](A03-P2-R2-proposal-review-report.md)、[R2 调度收口](A03-P2-R2-proposal-coordinator-decision.md)、[本次前检](../evidence/coordinator/heartbeat-20261017-0834/A03-R3-delivery-preflight.json)。

调度已核对 125 个清单项及清单自身共 126 个新增文件的磁盘/raw Git 字节、27,876 个旧 Git 路径不变、11 个 workflow 输入与 53 个复用 R2 输入、干净工作树及 5 个自有静态运行退出记录。前检只证明可复验的交付边界，没有执行交付代码或给功能通过。静态候选的实际总入口为新增 `examples/a03/P2-R3-evidence-closure/closure.py` 的 `Package.validate`；原 R2 Schema/API/oracle/profile 固定只读。

## 本轮唯一范围

只复验 `R2-SCOPE-EVIDENCE-ID-01` 及受其影响的已有静态行为，不扩大原生实现或边界搜索。SESSION-02、CONVERSION-07 原有有限静态接受保留；R17 版本桥接和登记推导 scope 正包仍分别 BLOCKED，不为得到整项 ACCEPTED 降低标准。

1. 通过 `git cat-file --batch` 隔离导出必要的冻结输入并逐 blob 核对，保留真实执行文件的摘要。先读覆盖层及运行入口，确认只做静态检查且全包检查经过修正后的唯一 `Package.validate`，不能以旁路辅助函数的拒绝充当总入口拒绝。只复用必要输入，不复制全部历史证据。
2. 原反例 bundle SHA256 `b816535f29e8da7e5c85739c6e1b3e6937190c039b7228b518617025125ac653`、inner Resource `ebd3f42cc53726b05919f27e6ee7b3866cbff7c36454473fe8dfda85e10b33af`、outer Resource `e14cf14a7a585ad528f7f01807d26a205cfa227c94a23dd51ff537f079dc32f6` 必须保持。原件从 R2 审阅归档或交付索引定位。拒绝必须来自自身声明/scope 检查，不能靠损坏摘要或改版本。作者报告首个拒绝是较早的 SourceBundle；另须核对新 1.3 receipt 的 `results[0].before_evidence_refs` 经 EvidenceRecord → 两层 JSON Resource → 外 scope Artifact 的实际诊断，不能因旧消费者先报错而漏检新消费者。
3. 核对正式字段 registry 与合同/schema 的对应、EvidenceRecord ID 唯一性、缺失/重复 ID 拒绝；普通 JSON 任意同名字符串不自动获得正式字段语义。验证合法同 scope 且声明完整的嵌套 JSON evidence 可接受、同一资源不同消费者分别使用自己的 input_refs/book/scope，以及合法 typed frame 仍使用明确子消费者上下文。
4. 核对 Artifact/frame → evidence ID → Resource → Artifact 边纳入混合 DAG。作者 mixed-cycle 控制明确包含一个未重算的叶摘要，只能证明图检查先于摘要检查的定位行为，不能描述为摘要自洽的完整循环包；原反例和合法正包仍须独立通过字节/摘要核对。
5. 有界复现：原反例及合法递归正包；核对作者 10 个直接控制的真实分类，并用少量直接控制独立确认消费者隔离/正式字段解析。已有两 scope/typed frame 正包、直接声明/scope/跨书/伪 frame/混合环及 SESSION-02、CONVERSION-07 的受影响静态回归合并复核一次即可。若复用 R2 的 36 条矩阵，只报告 7 静态接受、23 预期拒绝、1 组五项 match、5 mismatch，不计成 36 项功能通过，也不另加五项凑数。

可参考最短入口：`python -X utf8 -B examples/a03/P2-R3-evidence-closure/replay.py --case original --expect UNDECLARED_REFERENCE`。它的退出 0 表示符合“预期拒绝”；实际运行请使用隔离目录，原件只读，输出到本次独立审阅目录。完整控制脚本先审静态安全再运行；所有 stdout/stderr、argv/cwd/PID、超时与退出记录从启动时保存，失败材料保留。

## 收口与交付

若这一个缺口闭合，给 **ACCEPTED_STATIC_LIMITED（EvidenceRecord 消费者闭包）**，同时列明整体 A03 功能未验收、两项残余仍阻塞；若缺口未闭合，给一个确定且可复现的最小反例后冻结，不自行追加修订轮或无限搜索无关边界。不得把执行方测试数或前检当成独立结论。

只新增 `D:/1800/docs/tasks/A03-P2-R3-evidence-closure-review-report.md` 与 `D:/1800/docs/evidence/A03/review/P2-R3-evidence-closure/`。报告包含输入版本/摘要、独立命令与结果、必要正反样例、真实分类、完整清单、自有进程结束及限制。不要改 state、旧报告或任何产品源码；完成后冻结并结束，由调度裁定后续范围。

禁止产品/planner/DB/native session、网络/浏览器/平台/profile/凭据/OCR/模型、安装依赖、提交/推送/集成、联系执行者/B/其他任务。本轮不批准 oracle 采用、跨侧共同合同、原生 profile 接纳或 I01。被拒字段重置专项保持 **NOT_EXECUTED_NO_RERUN_VARIANT_OR_DELEGATION**，不复跑、不变形、不委派、不建议再测。
