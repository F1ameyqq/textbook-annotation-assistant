# A07 Q1 首候选：固定独立验收派发

2026-10-18。续派已登记验收对话 `01a14edb-bdc9-7370-890c-3b301b6ea414`，不创建重复任务。作者 `01a14edd-f319-7b70-8993-62e04de3a2d4` 已交付并释放。按 [原执行范围](A07-Q1-offline-simulation.md) 与 [原独立标准](A07-Q1-independent-review.md) 开始实际验收，不增加矩阵或新的业务标准。

## 固定版本及预检

- 工作流：`b1c84db9d1d5603a4fd6aa5487d7c45ec6fca50a`。
- 实际运行产品候选：`6dad9b9a40a10989c102d91cf7b54f19c012015f`，tree `77f0761d050061a037ade088266f68ead4c6d930`。
- 最终交付：`d2e710c817cf85505ac4fad4919dd51d1062d33a`，tree `e96d1d546d9cd2158126d3fc36a4a6014cdf1aa6`。
- 固定执行报告：最终交付内 `docs/tasks/A07-Q1-execution-report.md`，raw SHA256 `404e3795d99b13312783fc8cfc46575a3d0b60c7050488ae62d54fb2724044df`。
- 交付清单：最终交付内 `docs/evidence/A07/execution/delivery-raw-git-manifest.json`，raw SHA256 `111918592d83446bba6d485f4d3f49d797787e925ed630f31f149c14c1ddcdcf`。
- 授权：`docs/approvals/A07-Q1-offline-business-approval.json`，raw SHA256 `cf6f675cfd98d438d7d465fc553e0ebbf1bfff71bd62f8453854f8527015cb6c`。

[调度预检](../evidence/coordinator/a07-preflight-20261018/preflight.json)核对63个成员/10,217,431 bytes及排除清单自身后的64条新增；29,296条工作流原路径和候选全部路径原bytes保全，产品新增11条，无旧产品修改。只读辅助核对还确认白名单和报告18条相对链接均符合。作者PID75456、26148再次查无存活，监督记录exit0/reaped，作者对话已idle且工作树干净。预检未执行任何新业务，不构成独立接受。

## 本次执行方式

1. 只读审最终交付的报告/原清单/固定证据，独立核对边界。自己的运行目录用短路径隔离检出，例如 `D:/1800-worktrees/a07-q1-review`；不得写作者目录或主调度文件。长路径管理工具若失败，可使用 `git -c core.longpaths=true worktree add --no-checkout`、必要目录 sparse checkout 后 `read-tree -mu HEAD` 在全新目录完成检出，不清理已有目录。
2. **正常试验的运行目录 HEAD 固定为产品候选 `6dad9b9a40a10989c102d91cf7b54f19c012015f`**，并使用相同 `--expected-candidate`。不要把最终报告交付 d2e710c8 当成此次实际运行候选，不能修改 HEAD 守卫。最终报告/清单通过 Git blob 从 d2e710c8 读取；必要时只读导出另目录。
3. 按固定 `examples/a07/README.md` 准备自己的全新输入、run_id 和输出目录。授权/政策摘要使用raw字节。只在独立目录完成原有限窄检查和**一次**正常真实来源到模拟目标试验；180/240外层和原内层边界保持。禁止为多收集证据重跑成功业务或回放作者目标。
4. 核对固定授权和新单题政策、六白名单/原图坐标/题答关系、31问题/78依据及30排除；实际五项PRE_APPLY、TARGET、C01计划/写前复算、六框内存变更、独立读回及回执。有限负控按原任务，不扩展B版本或A03持久化矩阵。不得以模型视觉替代用户授权，也不得把A用户批准升级为B共同采用。
5. 输出新的 `docs/tasks/A07-Q1-review-report.md` 和 `docs/evidence/A07/review/`，含固定审查与实际运行版本、raw清单、结果/层级、消耗和自有进程释放。作者证据全保留。结论仍限A本地单题离线建议，调度核证之后才ACCEPTED/集成；不推送、不向B发消息、不连接平台。

作者已消耗1次冻结候选/1次完整试验/1次成功/1次业务dispatch，不能再派作者重复正常业务。独立此前准备阶段0业务/0写入，当前首次正式验收额度为一次正常试验；若失败固定报告交接，不自行修改产品、重跑或恢复额度。
