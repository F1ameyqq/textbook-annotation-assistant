# A06 第二、最终候选：F01 独立差量复验

2026-10-18。按 [第二最终纠正任务](A06-second-final-correction.md) 和 [原独立验收范围](A06-independent-review.md)，续派现有独立验收对话 `01a14e21-162e-7840-9052-501984bc3d75`。这是第二候选的最后差量复验，不重跑已保留的第一候选全集，也不新增标准。

## 固定对象与交付预检

- 作者固定交付：`d78737815279965f660057bea0a572b426098aaa`；第二实现冻结：`43ebdd21f2dc6803ae322b95776806e167884749`。
- 作者仓库：`D:/1800-worktrees/a06`，只读固定 Git 对象；第一交付 `761d9afed8b9d3d33851ad3d79b0bee7c294089d`，原公共基线 `a1c3c3b2d452ecbdf5c57a8b7372e7d53de0f8d8`。
- 同提交报告 `docs/tasks/A06-second-final-execution-report.md`：9325 bytes，SHA256 `11fd37526062a92a034a29c5ad591449db5e33388cc16812f49c1757796ff66d`。
- 同提交清单 `docs/evidence/A06/second-final/manifest.json`：7426 bytes，SHA256 `5e09e958ed0d97ea51b855918a777182278cd9f52c9af98b630a001205e533db`。
- 同提交释放 `docs/evidence/A06/second-final/release.json`：4188 bytes，SHA256 `5cc99900a4195965cfe516f377bb30ed19fcd9e5e9b66ae227c4390209be301b`。
- 产品差量仅 `src/annotation/source/b_handoff/reader.py`，SHA256 `a80acf8a15d7c822c82ef6720a6125e79cfcee0498ac60d3f1c7a80ca030cd61`。实现冻结至最终交付的产品、配方和测试保持原字节。
- 调度预检记录：`docs/evidence/coordinator/a06-second-final-preflight-20261018/preflight.json`。预检不代替独立验收。
- 原本地 B ZIP 路径仍为 `D:/1800/.local/stages/coordinator/b-handoff-0e5434f/B-46007447-Q16-offline-HOLD-2026-10-17.zip`，11681712 bytes，SHA256 `b2bed674f87cde7fb2df4fdf31dec9ede08f494fc6190f654abda51dd4dae89d`，manifest SHA256 `3952a42e5ea966a0ec039564c71dc1db242c061af807aa730ac1f7f015e8189f`。

## 本次复验

先读固定差量与配方，从 raw Git bytes 导出自己的源码副本、新变体和输出目录。Git 使用 `-c core.longpaths=true`、`GIT_NO_LAZY_FETCH=1`，缺件不联网补。不在作者目录运行，不使用作者 generated 活目录。既有依赖即可，无安装、B 脚本/生产者、SQL、平台、profile、凭据或付费模型调用。

静态核对固定14项 stage 的结果层 kind/schema 门、接线与独立结果定位；窄字段核对仅限已观察14组和原定未知版本/错 kind。冻结后的两个完整公共入口各一次：

1. 原固定 ZIP 返回 HOLD，14项结果层核验可定位。原34/66/127、身份绑定、历史未决、optional=null、business_acceptance=false 和 c01_execution_eligible=false 保持。
2. 由固定新配方在自己的副本生成非最终 `inline_apply` 结果未知版本变体，正确重封非破坏层；公共入口必须到达结果层 `UNSUPPORTED_VERSION / VERSION`，不能以外层摘要拒绝代替。

可用固定 `examples/a06/make_stage_result_variant.py` 与 `verify_second_final.py` 路由输入输出，独立记录实际 import 来源、argv/cwd、PID、原始流及退出码；不替换候选业务函数或守卫。作者变体SHA `5911f8d572c97027f0ac12a5c1dbe3e190e59a6391904fdd91cef6501bf91af8` 供配方比对，不冒充 B 的新交付。

核对相关实现原字节保全后，坏资源、陈旧Check、原有限顶层/历史版本矩阵和C01三消费者沿用第一独立报告 `docs/tasks/A06-review-report.md` 的有限结果，不重跑全集。第一报告 SHA256 `fdefde2e92095b9e922ae264a6b9595af5d93ee4c6dd5f5f980e941a031c0ae4`、507成员清单 SHA256 `b3842a023b39c1f26ba42db6eab93329adfae4ad084e756b09cb67a780af5624`、释放 SHA256 `3917bf27b1d013dad625b2bfdb9b779fcc877dabe15380b147f8405399f64ea9`。原 F01 是静态发现，不声称此前动态证明绕过。

## 收口与边界

只新增主目录 `docs/tasks/A06-second-final-review-report.md` 与 `docs/evidence/A06/review/second-final/`，保留首轮报告/证据。新报告、原字节清单与释放证明绑定上述固定提交；明确 ACCEPTED / REWORK / BLOCKED 及继承范围，不修改 state、索引、作者材料，不提交/合并/推送或联系 B/作者。

第二冻结后遇失败即保留、释放并固定报告，不修后重跑、不第三候选、不改名恢复额度。作者两次冻结均已消耗。

有限 A06 接收通过只表示固定包只读 HOLD/拒绝接口可用。0.4/0.5 仍仅绑定历史诊断、当前顶层拒绝；0.6 无完整正例，未知版本拒绝。UNRESOLVED_HISTORY_REFERENCE、UNCONFIRMED_REQUIREDNESS 与共同映射未确认保持，不授予 C01 执行资格，也不把 B 内容或联合业务判为通过。I01-A 已由调度完成有限 synthetic 本地集成，但不替代真实 B 正向链证明。
