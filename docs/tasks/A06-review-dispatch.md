# A06 固定包接收独立验收派发

2026-10-18。沿用 [独立验收任务](A06-independent-review.md) 的四入口及有限版本范围。调度完成固定交付和释放预检后，续派已登记验收对话 `01a14e21-162e-7840-9052-501984bc3d75`；不新增测试矩阵或业务资格。

## 固定对象

- 组合基线：`a1c3c3b2d452ecbdf5c57a8b7372e7d53de0f8d8`。
- 最终交付：`761d9afed8b9d3d33851ad3d79b0bee7c294089d`。
- 第一实现候选：`9076d35e81678cdba8ad8651e95a44265fdc345c`。冻结后实现、消费者、配方和测试不变；最终交付只追加说明与证据。
- 作者仓库：`D:/1800-worktrees/a06`，只读其固定 Git 对象，不在作者目录运行。
- 同提交报告 `docs/tasks/A06-execution-report.md`：SHA256 `deba7a12f2b74b9261a8404ce19885fcea3c574d68f8e1bbd9761a8c2e7df0bb`。
- 同提交清单 `docs/evidence/A06/manifest.json`：SHA256 `e37efb2ba44b6005cb4c15e095ab22e00d804c4884ce988d6b613cb8b5189d33`。
- 同提交释放证明 `docs/evidence/A06/author/release.json`：SHA256 `2f7eb5d6203ae7e7c441170c03ef17d012e7139df64423635c38ada30120283c`。作者已 completed/idle；父驱动结束，10 个同步子调用均返回，未开启后台进程或平台会话。原记录没有子进程 OS PID，不补造；本次独立外层记录可以补充自己的真实 PID。
- 调度预检：`docs/evidence/coordinator/heartbeat-20261018-0839/A06-delivery-preflight.json`。
- B 固定输入仍为 `D:/1800/.local/stages/coordinator/b-handoff-0e5434f/B-46007447-Q16-offline-HOLD-2026-10-17.zip`；ZIP SHA256 `b2bed674f87cde7fb2df4fdf31dec9ede08f494fc6190f654abda51dd4dae89d`；manifest SHA256 `3952a42e5ea966a0ec039564c71dc1db242c061af807aa730ac1f7f015e8189f`。

## 现在执行的原有限范围

从冻结 raw Git 字节建立自己的代码副本及新输出目录，核对固定 ZIP。Git 一律 `-c core.longpaths=true`、`GIT_NO_LAZY_FETCH=1`，本地缺件不得联网补。生成自己的三份确定性变体，不使用作者 generated 活目录，不执行 B 脚本、生产者或查询任何 SQLite。

真实公共入口为 `annotation.source.b_handoff.receive_package`、`python -m annotation.source.b_handoff` 和 `examples/a06/consume.py`；固定外层驱动 `examples/a06/verify.py <fixed-zip> <new-output-dir> <new-variants-dir>` 可用于原任务复现。先读配方，保留非破坏层重封关系；每个主入口仅一次，核对实际来源和到达层。

四主入口固定预期为原件 HOLD、坏资源 `RESOURCE_INVALID/RESOURCE`、陈旧 Check `STALE_CHECK/CURRENT_BINDING`、未知版本 `UNSUPPORTED_VERSION/VERSION`。有限版本分派按原任务核对 0.4/0.5 历史档案与当前顶层拒绝、0.6 明确拒绝、0.7 有限只读。必要公共 C01 导入及三个已有消费者按原任务调用，不重跑全套 C01/A02。

原包开发阶段的嵌套结果/历史绑定失败保持原件。冻结四例通过仅是作者事实，独立复现和判断另记。错误中的内存地址不作为稳定字符串标准；判定 code/path/layer。已有 scope、typed 渲染、content fragments、来源码点、历史引用和当前绑定检查按原任务核对，不追加未约定的新标准。

当前包保持 HOLD、business_acceptance=false、c01_execution_eligible=false。缺失历史引用继续显式 `UNRESOLVED_HISTORY_REFERENCE` 和 `UNCONFIRMED_REQUIREDNESS`，不得默认可选或伪造完整闭合；不把可导入、可诊断或版本拒绝当作 B→C01 可执行映射、内容验收或共同合同确认。

本次是第一候选的独立验收。失败保全并给调度明确缺口，不能自行修候选或重跑业务；后续是否使用第二候选须按已定规则由调度决定，不能新增第三包。输出仅主目录 `docs/tasks/A06-review-report.md` 与 `docs/evidence/A06/review/`，记录真实固定输入/输出、命令、原始流、摘要、范围和释放，不修改 state/index、作者材料或提交，不联系作者/B，不推送。
